"""Operaciones sobre el índice para el módulo "Preguntas sin respuesta":
buscar documentos candidatos, indexar alias y respuestas escritas a mano, y
reejecutar una pregunta para verificar que tras resolverla ya se recupera.
Ver `docs/TFM/RAG_PIPELINE.md` §8."""
from typing import List, Optional

from app.services.embedding_service import EmbeddingService
from app.services.pinecone_service import PineconeService
from app.services.rag_service import RELEVANCE_THRESHOLD

# El umbral se importa de `rag_service`, que es su dueño: allí está la medición
# que lo justifica. Este módulo tiene que usar el mismo criterio que el chat —
# si considerara "relevante" algo que el chat descarta, detectaría huecos de
# conocimiento con una vara distinta a la que usa para responder. Mantenerlo
# duplicado dejaba que las dos copias se separasen sin que nada avisara.


def _search(question: str, company_id: int, assistant_id: Optional[int], top_k: int) -> List:
    """Busca en el namespace del asistente y, si no hay resultados, en el de la
    empresa.

    **Este fallback es deliberado y es lo contrario de lo que hace el chat.**
    `RAGService.generate_response` no cae al namespace de empresa: si el espacio
    del asistente no tiene nada relevante, responde que no encontró información,
    porque un asistente sin match llegaba a mostrar contenido de otros espacios.

    Aquí se admite porque quien decide es distinto. El chat responde solo, sin
    nadie revisando, así que no puede permitirse cruzar espacios. Este módulo
    alimenta el panel de "Preguntas sin respuesta", donde un administrador ve el
    nombre del documento candidato y decide si encaja: ampliar la búsqueda le da
    opciones que puede descartar.

    Limitación conocida: hoy no hay roles ni permisos documentales, de modo que
    cualquier administrador ve todos los espacios de su empresa. Si se añadieran
    permisos por usuario, este fallback tendría que filtrarse por ellos.
    """
    embedding = EmbeddingService().generar_embedding(question)
    pinecone_svc = PineconeService()

    matches: List = []
    if assistant_id:
        matches = pinecone_svc.buscar_vectores(
            embedding,
            top_k=top_k,
            namespace=PineconeService.construir_namespace(company_id, assistant_id),
        )
    if not matches:
        matches = pinecone_svc.buscar_vectores(
            embedding,
            top_k=top_k,
            namespace=PineconeService.construir_namespace(company_id),
        )
    return matches


def find_candidates(question: str, company_id: int, assistant_id: Optional[int], top_k: int = 3) -> List[dict]:
    """Candidatos del índice para una pregunta: documento, chunk y score, por
    encima del umbral de relevancia. Alimenta el modo "Vincular documento".

    Un candidato por documento, con su mejor fragmento: antes se devolvían los
    `top_k` fragmentos tal cual, y cuando eran del mismo documento el panel
    mostraba tres veces el mismo nombre. Se piden más fragmentos de los que se
    devuelven para que queden hasta `top_k` documentos distintos."""
    matches = _search(question, company_id, assistant_id, top_k * 4)
    candidates = []
    vistos = set()
    for m in matches:
        score = float(getattr(m, "score", 0) or 0)
        if score < RELEVANCE_THRESHOLD:
            continue
        meta = m.metadata or {}
        if not meta.get("document_id") or meta["document_id"] in vistos:
            continue
        if len(candidates) == top_k:
            break
        vistos.add(meta["document_id"])
        candidates.append({
            "document_id": meta["document_id"],
            "chunk_id": meta.get("chunk_index", 0),
            "name": meta.get("document_name", "Documento"),
            "score": round(score, 3),
        })
    return candidates


def best_score(question: str, company_id: int, assistant_id: Optional[int]) -> float:
    """Mejor score de similitud contra el índice, 0.0 si no hay resultados.
    Usado para reejecutar la pregunta al verificar una resolución."""
    matches = _search(question, company_id, assistant_id, top_k=1)
    return round(float(matches[0].score), 3) if matches else 0.0


def index_answer(
    gap_id: int,
    question: str,
    answer_text: str,
    company_id: int,
    assistant_id: Optional[int],
    answered_by: int,
) -> None:
    """Indexa una respuesta escrita a mano como chunk propio, recuperable a
    futuro por preguntas similares."""
    embedding = EmbeddingService().generar_embedding(f"{question}\n\n{answer_text}")
    namespace = PineconeService.construir_namespace(company_id, assistant_id)
    vector = {
        "id": f"gap-{gap_id}-answer",
        "values": embedding,
        "metadata": {
            "document_id": None,
            "document_name": "Respuesta directa (preguntas sin responder)",
            "company_id": company_id,
            "assistant_id": assistant_id,
            "knowledge_gap_id": gap_id,
            "answered_by": answered_by,
            # Completa: es lo que el modelo lee al usarla como fuente. Ver
            # `_vectores_de_documento` en routers/v1/documents.py.
            "text": answer_text,
        },
    }
    PineconeService().upsert_vectores([vector], namespace=namespace)


def index_alias(
    gap_id: int,
    texts: List[str],
    document_id: int,
    document_name: str,
    chunk_id: int,
    company_id: int,
    assistant_id: Optional[int],
) -> None:
    """Registra la pregunta y sus variantes como alias del documento vinculado,
    para que futuras consultas con la misma redacción lo recuperen."""
    texts = [t for t in texts if t]
    if not texts:
        return
    embeddings = EmbeddingService().generar_embeddings_batch(texts)
    namespace = PineconeService.construir_namespace(company_id, assistant_id)
    vectors = [
        {
            "id": f"gap-{gap_id}-alias-{i}",
            "values": embedding,
            "metadata": {
                "document_id": document_id,
                "document_name": document_name,
                "company_id": company_id,
                "assistant_id": assistant_id,
                "knowledge_gap_id": gap_id,
                "alias_of_chunk_id": chunk_id,
                "text": text,
            },
        }
        for i, (text, embedding) in enumerate(zip(texts, embeddings, strict=True))
    ]
    PineconeService().upsert_vectores(vectors, namespace=namespace)
