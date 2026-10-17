"""RAG avanzado completo: descompone y recorta con reparto equilibrado.

Combina la descomposición de consultas con un tope de contexto, que es el que
a aquella le faltaba.

## El problema que resuelve

La descomposición resolvió la cobertura de las preguntas compuestas —del 48 %
al 88 %— pero **ensancha sin recortar**. Cada subpregunta aporta `TOP_K`
fragmentos y la fusión los conserva todos:

    "¿Cómo se compara con GANs y VAEs?"
      → 2 subpreguntas → 5 + 5 → fusión → 9 fragmentos al modelo

Nueve fragmentos frente a los cinco de la línea base son unos 1.800 tokens
adicionales y casi el doble de coste por consulta. Con tres subpreguntas
podrían llegar quince: **no había tope en ninguna parte**.

## Por qué el reparto en turnos y no el reordenado

La primera versión de esta clase recortaba pidiendo al modelo que ordenara los
fragmentos por utilidad y conservando los cinco primeros. **Se midió y no
funcionó.** Sobre las seis parejas de preguntas compuestas:

    base                  cobertura 48 %   desequilibrio 1,83
    reordenado y recorte  cobertura 52 %   desequilibrio 2,17   <- peor reparto
    descomposición sola   cobertura 88 %   desequilibrio 0,83   (pero 10 fragmentos)

El reordenador elige los fragmentos «más útiles» y se concentra en una de las
subpreguntas, que es exactamente lo que la descomposición venía a evitar. Y
cobraba una llamada al modelo por hacerlo.

El reparto en turnos no decide cuál es mejor: **garantiza que ninguna
subpregunta se quede sin representación**, tomando por rondas el mejor
fragmento aún no incluido de cada una. No cuesta ninguna llamada.

## Sobre el techo de la cobertura

Conviene tenerlo presente al leer las cifras. La cobertura se define como la
proporción de los `2 · TOP_K` fragmentos que las preguntas por separado
recuperarían, de modo que **enviando `TOP_K` fragmentos el máximo alcanzable
ronda el 50 %**. El 88 % de la descomposición solo era posible enviando el
doble de contexto. Comparar ambas cifras sin decirlo sería engañoso: no miden
el mismo presupuesto.

Lo que esta clase persigue, por tanto, no es recuperar aquel 88 %, que es
inalcanzable con cinco fragmentos, sino **repartir esos cinco entre las
subpreguntas en lugar de dejar que una se los lleve todos**.

## Qué se conserva

**La abstención no cambia.** El umbral se aplica antes del recorte: si ningún
fragmento lo supera, el sistema se abstiene exactamente como la línea base.

**Ante una consulta simple el comportamiento es el de la base.** Si no hay
descomposición no hay nada que repartir ni que recortar.
"""
import logging
from typing import Any, List, Tuple

from app.core import observabilidad
from app.services.rag_service import RELEVANCE_THRESHOLD, TOP_K
from app.services.rag_service_avanzado import RAGServiceAvanzado

logger = logging.getLogger("uvicorn.error")


class RAGServiceCompleto(RAGServiceAvanzado):
    """Descomposición de consultas con tope de contexto y reparto equilibrado."""

    @staticmethod
    def _repartir(listas: List[List[Any]], tope: int) -> List[Any]:
        """Toma por rondas el mejor fragmento aún no incluido de cada lista.

        Con dos subpreguntas y un tope de cinco, el reparto es 3/2 y no 5/0.
        Las listas llegan ya ordenadas por puntuación, de modo que en cada
        ronda se toma lo mejor que le queda a cada subpregunta.
        """
        elegidos: List[Any] = []
        vistos: set = set()
        indices = [0] * len(listas)

        while len(elegidos) < tope:
            avanzo = False
            for i, docs in enumerate(listas):
                if len(elegidos) >= tope:
                    break
                # Se salta lo ya incluido por otra subpregunta: un fragmento
                # compartido no debe ocupar dos huecos.
                while indices[i] < len(docs) and docs[indices[i]].id in vistos:
                    indices[i] += 1
                if indices[i] < len(docs):
                    d = docs[indices[i]]
                    elegidos.append(d)
                    vistos.add(d.id)
                    indices[i] += 1
                    avanzo = True
            if not avanzo:
                break   # todas las listas agotadas

        return elegidos

    def _recuperar(self, query: str, namespace: str, top_k: int = None) -> Tuple[List[Any], int]:
        with observabilidad.paso("descomposicion", entrada=query) as traza:
            subpreguntas = self._descomponer(query)
            traza["subpreguntas"] = subpreguntas
            traza["n"] = len(subpreguntas)

        if len(subpreguntas) == 1:
            logger.info("[RAG*] Consulta simple, recuperación estándar")
            return super(RAGServiceAvanzado, self)._recuperar(
                subpreguntas[0], namespace, top_k=top_k
            )

        listas, tokens = self._recuperar_cada_una(subpreguntas, namespace, top_k)

        # El umbral va antes del recorte, y por subpregunta, para que la
        # abstención siga siendo la de la línea base.
        listas = [[d for d in docs
                   if float(getattr(d, "score", 0)) >= RELEVANCE_THRESHOLD]
                  for docs in listas]

        if not any(listas):
            logger.info("[RAG*] Ningún fragmento supera el umbral; se abstiene como la base")
            return [], tokens

        total = len({d.id for docs in listas for d in docs})
        if total <= TOP_K:
            logger.info("[RAG*] %d fragmentos únicos, no hay nada que recortar", total)
            return self._fusionar(listas), tokens

        with observabilidad.paso("reparto", entrada={"subpreguntas": len(listas)}) as traza:
            elegidos = self._repartir(listas, TOP_K)
            traza["disponibles"] = total
            traza["conservados"] = [getattr(d, "id", "?") for d in elegidos]
            traza["por_subpregunta"] = [
                sum(1 for d in elegidos if any(d.id == x.id for x in docs))
                for docs in listas
            ]

        logger.info(
            "[RAG*] %d subpreguntas -> %d fragmentos únicos -> %d al modelo (reparto %s)",
            len(listas), total, len(elegidos),
            "/".join(str(sum(1 for d in elegidos if any(d.id == x.id for x in docs)))
                     for docs in listas),
        )
        return elegidos, tokens
