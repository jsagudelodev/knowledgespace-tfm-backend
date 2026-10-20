"""Test de `PineconeService.listar_namespace`.

Es `listar_por_documento` sin el filtro por documento: trae el corpus
completo que un asistente tiene indexado. Lo usa `RAGServiceHibrido` para
construir su indice lexico, y hasta ahora no tenia ningun test propio -se
cubria solo de forma indirecta, a traves de dobles, en los tests del hibrido-.
"""
from types import SimpleNamespace

from app.services.pinecone_service import PineconeService


def _vector(indice, texto, doc_id=1, nombre="m.pdf"):
    return SimpleNamespace(metadata={
        "document_id": doc_id, "document_name": nombre,
        "chunk_index": indice, "text": texto,
    })


def _servicio(ids_por_pagina, vectores):
    svc = PineconeService.__new__(PineconeService)
    svc.nombre_indice = "test"

    class _Indice:
        def list(self, **kwargs):
            self.kwargs_recibidos = kwargs
            return iter(ids_por_pagina)

        def fetch(self, **kwargs):
            pedidos = kwargs["ids"]
            return SimpleNamespace(
                vectors={k: v for k, v in vectores.items() if k in pedidos})

    svc.pc = SimpleNamespace(Index=lambda nombre: _Indice())
    return svc


def test_trae_fragmentos_de_varios_documentos_sin_filtro():
    """A diferencia de `listar_por_documento`, aqui no se pasa `prefix`: debe
    traer fragmentos de cualquier documento del espacio."""
    ids = [["doc-1-chunk-0", "doc-2-chunk-0"]]
    vectores = {
        "doc-1-chunk-0": _vector(0, "texto del primero", doc_id=1),
        "doc-2-chunk-0": _vector(0, "texto del segundo", doc_id=2),
    }
    svc = _servicio(ids, vectores)

    fragmentos = svc.listar_namespace("company-8-assistant-1")

    assert {f["document_id"] for f in fragmentos} == {1, 2}


def test_un_namespace_vacio_devuelve_lista_vacia():
    svc = _servicio([], {})
    assert svc.listar_namespace("vacio") == []


def test_no_pasa_prefijo_al_listar():
    """El prefijo es lo que distingue `listar_por_documento` de este metodo:
    aqui no debe filtrarse por ningun documento concreto."""
    svc = PineconeService.__new__(PineconeService)
    svc.nombre_indice = "test"
    capturado = {}

    class _Indice:
        def list(self, **kwargs):
            capturado.update(kwargs)
            return iter([])

    svc.pc = SimpleNamespace(Index=lambda nombre: _Indice())
    svc.listar_namespace("ns")

    assert "prefix" not in capturado
    assert capturado.get("namespace") == "ns"
