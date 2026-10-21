"""RAG híbrido: búsqueda densa y léxica, fusionadas por posición.

La búsqueda densa compara significado —dos frases sobre lo mismo quedan cerca
aunque no compartan palabra alguna—. Eso es lo que permite que una pregunta
reformulada con sinónimos siga encontrando su respuesta, y es también su punto
ciego: un acrónimo, un identificador o un término técnico poco frecuente puede
no tener una representación vectorial distintiva, y la similitud coseno lo
trata como si fuera ruido. La búsqueda léxica —aquí, BM25— es la operación
inversa: ciega al significado, precisa con la letra. Un RAG híbrido combina
ambas para que lo que una pasa por alto, la otra pueda rescatarlo.

## El problema de diseño que resuelve esta clase

BM25 y la similitud coseno **no viven en la misma escala**. El umbral de
relevancia, 0,30, está medido exclusivamente sobre puntuaciones coseno —el
apartado 5.3 de la memoria documenta esa medición—; una puntuación BM25 no
tiene techo fijo y comparar una contra la otra directamente no significa nada.
Mezclarlas sin cuidado produce dos modos de fallo opuestos: si se exige que la
puntuación fusionada supere 0,30, el sistema puede dejar de abstenerse nunca
—BM25 encuentra *alguna* coincidencia de palabras funcionales en casi
cualquier corpus— o abstenerse siempre —si la fusión diluye la puntuación
densa por debajo del umbral—. Cualquiera de los dos rompería el requisito
RNF-3.

**La solución, coherente con el resto del pipeline: el umbral protege
primero, la fusión opera después.** Es el mismo patrón que `RAGServiceReranking`
—filtrar antes de reordenar— y que `RAGServiceCompleto` —filtrar antes de
repartir—. Aquí:

    1. búsqueda densa ensanchada (RAG_CANDIDATOS_LEXICOS candidatos)
    2. filtro por umbral, IDÉNTICO al de la línea base
    3. si no sobrevive nada → abstención, igual que la base;
       BM25 no tiene voto sobre si el sistema responde o no
    4. si sobrevive algo → se busca también por BM25 sobre el namespace
       completo, y los dos rankings se fusionan por POSICIÓN
       (Reciprocal Rank Fusion), no por puntuación absoluta
    5. se devuelven los TOP_K mejores de la fusión

La fusión en sí —construir el índice léxico, calcular BM25, combinar por
posición— vive en `fusion_lexica.MezclaLexica`, compartida con
`RAGServiceDescomposicionHibrida`, que necesita aplicar exactamente el mismo
mecanismo una vez por cada subpregunta.

## Qué puede aportar un fragmento rescatado solo por BM25

Un fragmento que no superó el umbral de similitud —incluso uno que la
búsqueda densa descartó por completo, con una puntuación muy baja— puede
entrar a la fusión si comparte términos fuertes con la consulta, siempre que
**otro** fragmento de la misma consulta sí haya superado el umbral —el paso 3
garantiza que nunca es la única señal—. Es precisamente la operación que un
híbrido debe aportar: rescatar evidencia que la similitud coseno descartó por
mala suerte en la representación vectorial, sin que eso abra una vía
alternativa de abstención.

## Coste

Una consulta adicional sin llamada al proveedor —BM25 corre en memoria, sin
coste de tokens— más el tiempo de construir el índice léxico sobre el
namespace completo en cada consulta. Para el corpus de este trabajo, ochenta y
siete fragmentos, es del orden de milisegundos; sobre un corpus de varios
órdenes de magnitud mayor, reconstruirlo en cada consulta dejaría de ser
gratuito y haría falta cachear el índice — ver la limitación declarada en
`indice_lexico.py`.
"""
import logging
from typing import Any, List, Tuple

from app.core.config import settings
from app.services.fusion_lexica import MezclaLexica
from app.services.rag_service import RELEVANCE_THRESHOLD, TOP_K, RAGService

logger = logging.getLogger("uvicorn.error")


class RAGServiceHibrido(MezclaLexica, RAGService):
    """RAG con búsqueda densa y léxica (BM25), fusionadas por posición."""

    def _recuperar(self, query: str, namespace: str, top_k: int = None) -> Tuple[List[Any], int]:
        top_k = TOP_K if top_k is None else top_k
        candidatos_densos, tokens = super()._recuperar(
            query, namespace, top_k=settings.RAG_CANDIDATOS_LEXICOS
        )

        relevantes = [d for d in candidatos_densos
                      if float(getattr(d, "score", 0)) >= RELEVANCE_THRESHOLD]

        if not relevantes:
            logger.info("[RAG~] Ningún candidato denso supera el umbral; se abstiene como la base")
            return [], tokens

        fusionados = self._fusionar_con_bm25(query, relevantes, namespace)

        finales = fusionados[:top_k]
        rescatados = sum(1 for d in finales if d.id not in {r.id for r in relevantes})
        logger.info(
            "[RAG~] %d densos sobre umbral -> %d al modelo (%d rescatados por BM25)",
            len(relevantes), len(finales), rescatados,
        )
        return finales, tokens
