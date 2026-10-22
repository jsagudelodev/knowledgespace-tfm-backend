"""Descomposición de consultas con reparto equilibrado, cada subpregunta
fusionada con BM25.

Combina las dos mejoras medidas por separado, cada una contra un problema
distinto:

    RAGServiceCompleto    resuelve la cobertura de las preguntas compuestas
                          (la pregunta tiene DOS temas, un solo vector no
                          representa bien a ninguno)
    RAGServiceHibrido     resuelve la fidelidad de las respuestas, rescatando
                          evidencia que la similitud coseno pasó por alto
                          (la pregunta tiene UN tema, pero mal representado
                          vectorialmente)

No compiten: la primera opera **entre** subpreguntas —cuántos fragmentos le
tocan a cada una—, la segunda opera **dentro** de una búsqueda —qué
fragmentos concretos rescata—. El ejemplo que motivó esta clase es
precisamente uno donde la densa fallaba por la segunda razón: ante
«diferencias entre GAN y VAE» —una sola pregunta de comparación, no una
compuesta—, los cinco fragmentos devueltos por la búsqueda densa explicaban
el VAE con detalle pero mencionaban la GAN solo de pasada; el sistema generador
completó el mecanismo de la GAN con conocimiento de entrenamiento, el tercer
modo de alucinación documentado en el apartado 5.4. Medido el 19 de octubre de
2026: `RAGServiceHibrido` solo, sobre esa misma pregunta, sí rescata el
fragmento que explica el funcionamiento competitivo —«si el discriminador
acierta, el generador mejora»— que la búsqueda densa dejaba fuera.

## Por qué no bastaba con una de las dos

`RAGServiceCompleto` reparte entre subpreguntas, pero cada subpregunta sigue
alimentándose solo de la búsqueda densa: si una de ellas tiene el mismo
problema que el ejemplo anterior —evidencia presente mal representada
vectorialmente—, el reparto no lo soluciona, solo decide cuántos huecos le
tocan a una evidencia que de todas formas llegó incompleta.

`RAGServiceHibrido`, medido solo, no ayuda con las preguntas compuestas —de
hecho las empeora frente a la línea base, del 48 % al 28 % de cobertura
conjunta medida el 19 de octubre de 2026—, porque no descompone: BM25 busca
sobre la consulta completa, con el mismo problema de vector único que arrastra
la búsqueda densa.

## El diseño

    1. descomponer la consulta         (como RAGServiceAvanzado)
    2. para CADA subpregunta:
         a. búsqueda densa ensanchada
         b. filtro por umbral           ← igual que RAGServiceCompleto
         c. fusión con BM25             ← igual que RAGServiceHibrido,
                                           pero una vez por subpregunta,
                                           con el texto de ESA subpregunta
    3. si ninguna subpregunta tiene evidencia → abstención
    4. si hay más fragmentos que el presupuesto, repartir en turnos
       entre las subpreguntas — mismo mecanismo que RAGServiceCompleto

Con una sola subpregunta este flujo se reduce exactamente al comportamiento de
`RAGServiceHibrido`: no hay bifurcación especial para ese caso, la misma
secuencia de pasos sobre una lista de una sola subpregunta produce el mismo
resultado.

## Coste

El de `RAGServiceCompleto` —descomponer cuesta una llamada al modelo— más el
de `RAGServiceHibrido` por cada subpregunta —BM25 no cuesta tokens, pero
construye el índice léxico una vez por subpregunta en lugar de una vez por
consulta—. Sobre una pregunta compuesta de dos temas, el índice léxico se
reconstruye dos veces en vez de una.
"""
import logging
from typing import Any, List, Tuple

from app.core import observabilidad
from app.core.config import settings
from app.services.fusion_lexica import MezclaLexica
from app.services.rag_service import RELEVANCE_THRESHOLD, TOP_K
from app.services.rag_service_completo import RAGServiceCompleto

logger = logging.getLogger("uvicorn.error")


class RAGServiceDescomposicionHibrida(MezclaLexica, RAGServiceCompleto):
    """Descomposición + reparto equilibrado, con cada subpregunta fusionada
    con BM25 antes de repartir."""

    def _recuperar(self, query: str, namespace: str, top_k: int = None) -> Tuple[List[Any], int]:
        top_k = TOP_K if top_k is None else top_k
        subpreguntas = self._descomponer(query)
        logger.info("[RAG#] Descomposición: %d subpregunta(s)", len(subpreguntas))

        # Se ensancha la búsqueda densa de cada subpregunta, igual que hace
        # RAGServiceHibrido, para que BM25 tenga margen con el que fusionar.
        listas_densas, tokens = self._recuperar_cada_una(
            subpreguntas, namespace, settings.RAG_CANDIDATOS_LEXICOS
        )

        listas_fusionadas: List[List[Any]] = []
        for sub, docs in zip(subpreguntas, listas_densas, strict=True):
            relevantes = [d for d in docs
                          if float(getattr(d, "score", 0)) >= RELEVANCE_THRESHOLD]
            if not relevantes:
                listas_fusionadas.append([])
                continue
            listas_fusionadas.append(self._fusionar_con_bm25(sub, relevantes, namespace))

        if not any(listas_fusionadas):
            logger.info("[RAG#] Ningún fragmento supera el umbral; se abstiene como la base")
            return [], tokens

        total = len({d.id for docs in listas_fusionadas for d in docs})
        if total <= top_k:
            logger.info("[RAG#] %d fragmentos únicos, no hay nada que recortar", total)
            return self._fusionar(listas_fusionadas), tokens

        with observabilidad.paso("reparto", entrada={"subpreguntas": len(listas_fusionadas)}) as traza:
            elegidos = self._repartir(listas_fusionadas, top_k)
            traza["disponibles"] = total
            traza["conservados"] = [getattr(d, "id", "?") for d in elegidos]

        logger.info(
            "[RAG#] %d subpreguntas -> %d fragmentos únicos (tras fusión con BM25) -> %d al modelo",
            len(listas_fusionadas), total, len(elegidos),
        )
        return elegidos, tokens
