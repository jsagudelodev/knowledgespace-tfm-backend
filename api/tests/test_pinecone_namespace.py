"""Tests del aislamiento multi-tenant por namespace — la invariante que
RAGService depende para que un asistente/espacio nunca vea documentos de
otro asistente/espacio de la misma empresa (ver fix del fallback cruzado)."""
from app.services.pinecone_service import PineconeService


def test_namespace_sin_asistente_es_solo_de_empresa():
    assert PineconeService.construir_namespace(5) == "company-5"


def test_namespace_con_asistente_incluye_ambos_ids():
    assert PineconeService.construir_namespace(5, 3) == "company-5-assistant-3"


def test_namespace_de_dos_asistentes_de_la_misma_empresa_son_distintos():
    # Esta es la propiedad concreta que evita que el espacio A vea documentos del espacio B.
    ns_a = PineconeService.construir_namespace(5, assistant_id=1)
    ns_b = PineconeService.construir_namespace(5, assistant_id=2)
    assert ns_a != ns_b


def test_namespace_con_assistant_id_none_equivale_a_no_pasar_asistente():
    assert PineconeService.construir_namespace(5, assistant_id=None) == PineconeService.construir_namespace(5)
