"""Reordenado de fragmentos por utilidad, compartido por dos configuraciones.

La búsqueda vectorial ordena por similitud coseno entre la pregunta y cada
fragmento. Esa medida es barata y funciona bien para descartar lo irrelevante,
pero es tosca para ordenar lo relevante entre sí: compara dos vectores
calculados por separado, sin que el fragmento haya «visto» nunca la pregunta.

Esto vive aparte porque lo usan **dos** clases con propósitos distintos:

  `RAGServiceReranking`   ensancha la búsqueda y reordena para mejorar el orden
  `RAGServiceCompleto`    reordena para **recortar** lo que produjo la
                          descomposición de consultas

Son usos opuestos del mismo mecanismo —uno busca más candidatos, el otro tiene
demasiados— y por eso el reordenado se expone como una mezcla y no como parte
de una u otra jerarquía.

## Limitación que conviene declarar

El reordenador es un modelo de lenguaje, de modo que **el resultado no es
estrictamente determinista**, ni siquiera a temperatura 0. Un reordenador de
tipo *cross-encoder* lo sería, a cambio de incorporar al servicio una
dependencia de varios cientos de megabytes. Al citar cifras obtenidas con
cualquiera de las dos configuraciones hay que decirlo.
"""
import logging
import re
from typing import Any, List

from app.core.config import settings

logger = logging.getLogger("uvicorn.error")

# Cuánto texto de cada fragmento ve el reordenador.
#
# **Empezó en 400 y se subió a 1.000 tras medirlo.** Con 400 juzgaba con el
# 40 % de cada fragmento y descartó, en la pregunta 8 del conjunto de
# evaluación, el de mayor puntuación —la tabla comparativa que permitía
# responder— quedándose con otro que contenía la frase ancla pero no la
# respuesta. El sistema pasó de contestar correctamente a abstenerse.
#
# 1.000 es el texto completo que el índice guarda por fragmento, de modo que el
# reordenador ve lo mismo que verá el modelo generativo.
RECORTE = settings.RAG_RECORTE_REORDENADO

PROMPT_REORDENADO = """Ordena los fragmentos por su utilidad para responder la pregunta.

Pregunta: {pregunta}

Fragmentos:
{fragmentos}

Devuelve ÚNICAMENTE los números de los fragmentos, del más útil al menos útil, separados por comas.
No añadas explicaciones, texto ni numeración propia. Ejemplo de respuesta válida: 3,1,7,2
Incluye todos los números, sin repetir ninguno."""


class MezclaReordenado:
    """Aporta `_ordenar`. Espera `self.client` y `self._anotar_llamada`."""

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
            self._anotar_llamada("reordenado", respuesta)
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
