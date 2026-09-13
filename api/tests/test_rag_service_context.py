"""Test de _build_context — arma el bloque de texto que se manda al LLM como
contexto. Si numera mal las fuentes o pierde el nombre del documento, las citas
que ve el usuario final dejan de corresponder con lo que el LLM realmente usó."""
from types import SimpleNamespace

from app.services.rag_service import RAGService


def _doc(document_name: str, text: str, score: float) -> SimpleNamespace:
    return SimpleNamespace(metadata={"document_name": document_name, "text": text}, score=score)


def test_build_context_vacio_sin_documentos():
    assert RAGService._build_context([]) == ""


def test_build_context_numera_las_fuentes_desde_uno():
    docs = [_doc("politica.pdf", "texto A", 0.9), _doc("manual.pdf", "texto B", 0.8)]
    context = RAGService._build_context(docs)
    assert "[Fuente 1] politica.pdf" in context
    assert "[Fuente 2] manual.pdf" in context


def test_build_context_incluye_texto_y_score_de_cada_fuente():
    context = RAGService._build_context([_doc("manual.pdf", "contenido relevante", 0.756)])
    assert "contenido relevante" in context
    assert "0.756" in context


def test_build_context_usa_nombre_por_defecto_si_falta_metadata():
    doc_sin_nombre = SimpleNamespace(metadata={"text": "algo"}, score=0.5)
    context = RAGService._build_context([doc_sin_nombre])
    assert "Documento desconocido" in context
