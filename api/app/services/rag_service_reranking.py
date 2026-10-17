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
from typing import Any, List, Tuple

from app.core import observabilidad
from app.services.rag_service import RELEVANCE_THRESHOLD, TOP_K, RAGService
from app.services.reordenador import MezclaReordenado

logger = logging.getLogger("uvicorn.error")

# Cuántos fragmentos se piden a Pinecone antes de reordenar. Veinte da margen
# para rescatar evidencia mal colocada sin que el prompt del reordenador se
# vuelva desmesurado: son 20 extractos de 400 caracteres, unos 2.000 tokens.
CANDIDATOS = 20

class RAGServiceReranking(MezclaReordenado, RAGService):
    """RAG con reordenado de los fragmentos recuperados.

    Se mantiene como clase aparte, y no como una modificación de `RAGService`,
    por el mismo motivo que `RAGServiceAvanzado`: para que la línea base siga
    existiendo y la comparación pueda repetirse sobre el mismo conjunto de
    evaluación en cualquier momento.
    """

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
