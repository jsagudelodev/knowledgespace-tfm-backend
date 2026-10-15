"""RAG avanzado: reordenado de los fragmentos recuperados.

Extiende `RAGService` cambiando **únicamente cómo se recuperan los fragmentos**.
El umbral de relevancia, el prompt restrictivo, la construcción del contexto, el
registro de coste, las trazas y la abstención se heredan sin modificación.

En la taxonomía de Gao et al. (2023) esta es una optimización
**post-recuperación**, hermana de la descomposición de consultas de
`rag_service_avanzado`, que es pre-recuperación. Ambas sitúan el sistema en
*Advanced RAG* sobre la misma línea base *Naive*.

## El problema que resuelve

La búsqueda vectorial ordena por similitud coseno entre la pregunta y cada
fragmento. Esa medida es barata y funciona bien para descartar lo irrelevante,
pero es tosca para ordenar lo relevante entre sí: compara dos vectores
calculados por separado, sin que el fragmento haya «visto» nunca la pregunta.

La línea base lo muestra con claridad (`experimentos/ejecutar_dataset.py`,
2026-10-11):

    hit@1 = 0,25     la evidencia llega la primera 1 de cada 4 veces
    hit@3 = 0,50
    hit@5 = 0,67     pero está entre las cinco 2 de cada 3 veces

El sistema **encuentra** la evidencia y la **coloca abajo**. Ese hueco entre
`hit@1` y `hit@5` es el síntoma que un reordenador corrige, y estaba previsto
en el apartado 5.2 de la memoria antes de medirlo.

## La estrategia

    consulta
       │
       ├── búsqueda vectorial, CANDIDATOS=20   ← se ensancha
       │
       ├── filtro por umbral 0,30              ← antes de reordenar
       │
       ├── el modelo reordena los supervivientes
       │
       └── se conservan los TOP_K mejores      ← al modelo llegan 5, como siempre

**Por qué se ensancha antes.** Reordenar los mismos cinco fragmentos solo
cambia su orden: `hit@5` no podría moverse. El reordenador aporta algo cuando
puede rescatar fragmentos que la similitud coseno dejó en las posiciones 6 a 20.

**Por qué el umbral va antes del reordenado.** Para que la abstención no
cambie. Pinecone devuelve los candidatos ordenados por puntuación, de modo que
si ninguno de los cinco primeros supera el umbral, tampoco lo superará ninguno
del sexto al vigésimo. Si no sobrevive nada, esta clase devuelve lo mismo que
la base y el sistema se abstiene igual. **La propiedad se cumple por
construcción, no por suerte**, pero se vuelve a medir de todos modos.

## Coste

Una llamada adicional al modelo por consulta, que recibe los fragmentos
candidatos recortados y devuelve un orden. El contexto que llega al modelo
generativo **no crece**: siguen siendo `TOP_K` fragmentos.

## Limitación que conviene declarar

El reordenador es un modelo de lenguaje, de modo que **el resultado no es
estrictamente determinista**, ni siquiera a temperatura 0. Un reordenador de
tipo *cross-encoder* lo sería, a cambio de incorporar al servicio una
dependencia de varios cientos de megabytes. Se eligió el modelo por no añadir
dependencias, y la consecuencia es que esta configuración, a diferencia de la
línea base, puede arrojar métricas de recuperación ligeramente distintas entre
pasadas. Al citar sus cifras hay que decirlo.
"""
import logging
import re
from typing import Any, List, Tuple

from app.core import observabilidad
from app.core.config import settings
from app.services.rag_service import RELEVANCE_THRESHOLD, TOP_K, RAGService

logger = logging.getLogger("uvicorn.error")

# Cuántos fragmentos se piden a Pinecone antes de reordenar. Veinte da margen
# para rescatar evidencia mal colocada sin que el prompt del reordenador se
# vuelva desmesurado: son 20 extractos de 400 caracteres, unos 2.000 tokens.
CANDIDATOS = 20

# Cuánto texto de cada fragmento ve el reordenador.
#
# **Empezó en 400 y se subió a 1.000 tras medirlo.** Con 400 el reordenador
# juzgaba con el 40 % de cada fragmento y descartó, en la pregunta 8 del
# conjunto de evaluación, el fragmento de mayor puntuación —la tabla
# comparativa que permitía responder— quedándose con otro que contenía la frase
# ancla pero no la respuesta. El sistema pasó de contestar correctamente a
# abstenerse.
#
# 1.000 es el texto completo que el índice guarda por fragmento, de modo que el
# reordenador ve lo mismo que verá el modelo generativo. El coste sube de unos
# 2.000 a unos 5.000 tokens de entrada por consulta reordenada.
RECORTE = 1000

PROMPT_REORDENADO = """Ordena los fragmentos por su utilidad para responder la pregunta.

Pregunta: {pregunta}

Fragmentos:
{fragmentos}

Devuelve ÚNICAMENTE los números de los fragmentos, del más útil al menos útil, separados por comas.
No añadas explicaciones, texto ni numeración propia. Ejemplo de respuesta válida: 3,1,7,2
Incluye todos los números, sin repetir ninguno."""


class RAGServiceReranking(RAGService):
    """RAG con reordenado de los fragmentos recuperados.

    Se mantiene como clase aparte, y no como una modificación de `RAGService`,
    por el mismo motivo que `RAGServiceAvanzado`: para que la línea base siga
    existiendo y la comparación pueda repetirse sobre el mismo conjunto de
    evaluación en cualquier momento.
    """

    def _ordenar(self, query: str, docs: List[Any]) -> List[Any]:
        """Devuelve los fragmentos reordenados por utilidad.

        Ante cualquier fallo —del modelo, de la red o del formato— devuelve el
        orden original. El reordenado es una mejora, nunca un punto de fallo.
        """
        if len(docs) < 2:
            return docs

        extractos = "\n".join(
            f"[{i}] {((d.metadata or {}).get('text') or '')[:RECORTE]}"
            for i, d in enumerate(docs)
        )

        try:
            respuesta = self.client.chat.completions.create(
                model=settings.OPENAI_CHAT_MODEL,
                messages=[{
                    "role": "user",
                    "content": PROMPT_REORDENADO.format(pregunta=query, fragmentos=extractos),
                }],
                temperature=0,
                max_tokens=120,
            )
            texto = (respuesta.choices[0].message.content or "").strip()
        except Exception as e:  # noqa: BLE001
            logger.warning("[RAG=] Falló el reordenado, se conserva el orden original: %s", e)
            return docs

        # El modelo puede devolver "3,1,7" o "3, 1, 7" o colar alguna palabra.
        # Se extraen los enteros y se descarta lo que no sea una posición válida
        # o esté repetido; lo que el modelo omita se añade al final en su orden
        # original, de modo que nunca se pierde un fragmento recuperado.
        vistos = set()
        orden: List[int] = []
        for n in re.findall(r"\d+", texto):
            i = int(n)
            if 0 <= i < len(docs) and i not in vistos:
                vistos.add(i)
                orden.append(i)

        if not orden:
            logger.warning("[RAG=] Reordenado descartado, respuesta ilegible: %r", texto[:80])
            return docs

        orden.extend(i for i in range(len(docs)) if i not in vistos)
        return [docs[i] for i in orden]

    def _recuperar(self, query: str, namespace: str, top_k: int = None) -> Tuple[List[Any], int]:
        """Ensancha la búsqueda, filtra por umbral, reordena y recorta."""
        candidatos, tokens = super()._recuperar(query, namespace, top_k=CANDIDATOS)

        # El umbral se aplica aquí, antes de reordenar, para que la abstención
        # sea exactamente la de la línea base: si de los veinte candidatos no
        # sobrevive ninguno, tampoco habría sobrevivido ninguno de los cinco.
        relevantes = [d for d in candidatos
                      if float(getattr(d, "score", 0)) >= RELEVANCE_THRESHOLD]

        if not relevantes:
            logger.info("[RAG=] Ningún candidato supera el umbral; se abstiene como la base")
            return [], tokens

        with observabilidad.paso("reordenado", entrada={"candidatos": len(relevantes)}) as traza:
            ordenados = self._ordenar(query, relevantes)
            traza["antes"] = [getattr(d, "id", "?") for d in relevantes[:TOP_K]]
            traza["despues"] = [getattr(d, "id", "?") for d in ordenados[:TOP_K]]
            traza["cambio"] = traza["antes"] != traza["despues"]

        finales = ordenados[:TOP_K]
        logger.info(
            "[RAG=] %d candidatos -> %d sobre umbral -> %d al modelo | reordenado=%s",
            len(candidatos), len(relevantes), len(finales),
            [getattr(d, "id", "?") for d in finales],
        )
        return finales, tokens
