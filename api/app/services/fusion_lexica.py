"""Fusión de búsqueda densa y léxica, compartida por dos configuraciones.

Igual que `reordenador.MezclaReordenado`, esto vive aparte porque lo usan
**dos** clases con necesidades distintas: `RAGServiceHibrido`, que fusiona una
única búsqueda, y `RAGServiceDescomposicionHibrida`, que necesita fusionar por
separado cada subpregunta antes de repartir el resultado entre ellas. El
mecanismo —BM25 sobre el *namespace* completo, fusión por posición— es el
mismo en ambos casos; lo que cambia es cuántas veces se invoca y qué se hace
con el resultado.

Ver `rag_service_hibrido.py` para el porqué completo del diseño: por qué BM25
y similitud coseno no se pueden comparar por valor, por qué el umbral debe
aplicarse **antes** de llamar a esto y nunca después, y por qué un fragmento
rescatado solo por BM25 lleva el umbral como valor centinela en vez de `None`.
"""
import logging
from types import SimpleNamespace
from typing import Any, Dict, List, Tuple

from app.core.config import settings
from app.services.indice_lexico import IndiceLexico
from app.services.rag_service import RELEVANCE_THRESHOLD

logger = logging.getLogger("uvicorn.error")


class MezclaLexica:
    """Aporta la fusión densa + BM25. Espera `self.pinecone_service`."""

    @staticmethod
    def _como_documento_lexico(fragmento: Dict[str, Any]):
        """Ver el porqué del valor centinela en `rag_service_hibrido.py`:
        un fragmento rescatado por BM25 no tiene puntuación coseno real, y
        `generate_response` vuelve a filtrar por `score >= umbral` sobre lo
        que `_recuperar` devuelva."""
        return SimpleNamespace(
            id=fragmento["chunk_id"],
            score=RELEVANCE_THRESHOLD,
            metadata={
                "document_id": fragmento.get("document_id"),
                "document_name": fragmento.get("document_name", "?"),
                "chunk_index": fragmento.get("chunk_index"),
                "text": fragmento.get("text", ""),
                "rescatado_por_bm25": True,
            },
        )

    @staticmethod
    def _fusionar_rrf(
        densos: List[Any], lexicos: List[Tuple[str, float]], por_id: Dict[str, Any],
    ) -> List[Any]:
        """*Reciprocal Rank Fusion*: combina dos rankings por la posición que
        ocupa cada elemento en cada uno, no por su puntuación —es lo que
        permite mezclar coseno y BM25 sin inventar una conversión entre
        escalas—."""
        k = settings.RAG_RRF_K
        puntuacion_rrf: Dict[str, float] = {}

        for posicion, doc in enumerate(densos, start=1):
            puntuacion_rrf[doc.id] = puntuacion_rrf.get(doc.id, 0.0) + 1.0 / (k + posicion)
        for posicion, (doc_id, _bm25) in enumerate(lexicos, start=1):
            puntuacion_rrf[doc_id] = puntuacion_rrf.get(doc_id, 0.0) + 1.0 / (k + posicion)

        # El orden importa: `por_id` trae un centinela para TODO el corpus,
        # incluidos los fragmentos que ya eran densos. Si se sobrescribiera al
        # revés, un fragmento con puntuación coseno real perdería esa medición.
        objetos_por_id = dict(por_id)
        objetos_por_id.update({d.id: d for d in densos})

        ordenados = sorted(puntuacion_rrf.items(), key=lambda par: par[1], reverse=True)
        return [objetos_por_id[doc_id] for doc_id, _ in ordenados if doc_id in objetos_por_id]

    def _fusionar_con_bm25(self, query: str, relevantes: List[Any], namespace: str) -> List[Any]:
        """Fusiona una lista de candidatos densos **ya filtrados por umbral**
        con lo que BM25 encuentre para `query` sobre el `namespace` completo.

        `relevantes` vacío significa que no hay evidencia densa, y aquí nunca
        se llama en ese caso: quien invoca esta función es responsable de
        comprobarlo antes, porque es la propiedad que preserva la abstención.
        """
        if not relevantes:
            return []
        try:
            corpus = self.pinecone_service.listar_namespace(namespace)
        except Exception as e:  # noqa: BLE001
            logger.warning(
                "[RAG~] No se pudo listar el namespace, solo se usa la búsqueda densa: %s", e
            )
            return relevantes

        indice = IndiceLexico([(f["chunk_id"], f["text"]) for f in corpus])
        lexicos = indice.buscar(query, top_k=settings.RAG_CANDIDATOS_LEXICOS)
        por_id = {f["chunk_id"]: self._como_documento_lexico(f) for f in corpus}
        return self._fusionar_rrf(relevantes, lexicos, por_id)
