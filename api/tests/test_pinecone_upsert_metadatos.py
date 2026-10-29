"""Tests de `PineconeService.upsert_vectores`: metadatos nulos.

El caso real que motivo este archivo (2026-10-28): en la aplicacion desplegada,
responder a mano una pregunta de "Preguntas sin respuesta" fallaba siempre con
502. `index_answer` guardaba la respuesta con `document_id: None` -no viene de
ningun documento- y Pinecone rechaza los metadatos nulos. Son tests de logica
pura: el indice se sustituye por un doble.
"""
from app.services.pinecone_service import PineconeService


def _servicio():
    svc = PineconeService.__new__(PineconeService)
    svc.nombre_indice = "test"

    class _Indice:
        def __init__(self):
            self.kwargs_recibidos = None

        def upsert(self, **kwargs):
            self.kwargs_recibidos = kwargs

    indice = _Indice()
    svc.pc = type("_Cliente", (), {"Index": lambda self, nombre: indice})()
    svc._indice_doble = indice
    return svc


def test_los_metadatos_nulos_no_llegan_a_pinecone():
    svc = _servicio()
    svc.upsert_vectores(
        [{"id": "gap-34-answer", "values": [0.1], "metadata": {
            "document_id": None, "assistant_id": None, "knowledge_gap_id": 34, "text": "respuesta",
        }}],
        namespace="company-1-assistant-2",
    )
    enviado = svc._indice_doble.kwargs_recibidos["vectors"][0]["metadata"]
    assert enviado == {"knowledge_gap_id": 34, "text": "respuesta"}


def test_los_metadatos_validos_se_envian_sin_cambios():
    """Cero, cadena vacia y False son valores validos para Pinecone: solo se
    descarta `None`."""
    svc = _servicio()
    metadatos = {"document_id": 7, "chunk_index": 0, "text": "", "activo": False}
    svc.upsert_vectores([{"id": "doc-7-chunk-0", "values": [0.1], "metadata": metadatos}])
    assert svc._indice_doble.kwargs_recibidos["vectors"][0]["metadata"] == metadatos
