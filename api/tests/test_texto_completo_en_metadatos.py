"""El texto que el modelo lee de cada fuente es el texto completo.

El caso real que motivó este archivo (2026-11-04, EXP-15): los metadatos de
cada vector guardaban `chunk[:1000]`, y `RAGService._build_context` entrega
ese texto al modelo. La búsqueda encontraba el fragmento por su texto entero,
pero el modelo solo leía los primeros 1.000 caracteres. La pregunta 26 del
conjunto de referencia se abstenía por eso: su respuesta empezaba en el
carácter 1.028 de un fragmento de 1.673. Lo mismo ocurría con las respuestas
escritas a mano en «Preguntas sin respuesta».

Son tests de lógica pura: OpenAI y Pinecone se sustituyen por dobles.
"""
from app.routers.v1.documents import _vectores_de_documento
from app.services import knowledge_gap_index_service as kgi

LARGO = "Una frase de diapositiva sin punto final " * 50   # ~2.000 caracteres


def test_los_fragmentos_largos_se_guardan_enteros():
    vectores = _vectores_de_documento(39, "Clase 2.pdf", 8, 1, ["corto.", LARGO], [[0.1], [0.2]])
    assert [v["metadata"]["text"] for v in vectores] == ["corto.", LARGO]
    assert len(vectores[1]["metadata"]["text"]) > 1000


def test_los_identificadores_siguen_la_posicion_del_fragmento():
    """El borrado previo al reindexado depende de este esquema de ids."""
    vectores = _vectores_de_documento(39, "Clase 2.pdf", 8, 1, ["a.", "b."], [[0.1], [0.2]])
    assert [v["id"] for v in vectores] == ["doc-39-chunk-0", "doc-39-chunk-1"]
    assert [v["metadata"]["chunk_index"] for v in vectores] == [0, 1]


def test_las_respuestas_escritas_a_mano_se_guardan_enteras(monkeypatch):
    enviados = []

    class _Embeddings:
        def generar_embedding(self, texto):
            return [0.1]

    monkeypatch.setattr(kgi, "EmbeddingService", _Embeddings)
    monkeypatch.setattr(kgi.PineconeService, "__init__", lambda self: None)
    monkeypatch.setattr(kgi.PineconeService, "upsert_vectores",
                        lambda self, vectores, namespace=None: enviados.extend(vectores))

    kgi.index_answer(gap_id=34, question="¿Pregunta?", answer_text=LARGO,
                     company_id=8, assistant_id=1, answered_by=2)

    assert enviados[0]["metadata"]["text"] == LARGO
