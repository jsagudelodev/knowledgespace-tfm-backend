""""Vincular documento" ofrece documentos, no fragmentos.

Con varios fragmentos del mismo documento entre los más parecidos, el panel
mostraba el mismo nombre repetido (p. ej. agentes_ia.md tres veces).
"""
from types import SimpleNamespace

from app.services import knowledge_gap_index_service as svc


def _match(document_id, chunk_index, score):
    return SimpleNamespace(
        score=score,
        metadata={"document_id": document_id, "chunk_index": chunk_index, "document_name": f"doc-{document_id}.md"},
    )


def test_un_candidato_por_documento_con_su_mejor_fragmento(monkeypatch):
    matches = [_match(45, 0, 0.78), _match(45, 1, 0.68), _match(7, 2, 0.60), _match(45, 3, 0.54)]
    monkeypatch.setattr(svc, "_search", lambda *a, **k: matches)

    candidatos = svc.find_candidates("que es un agente de IA", 8, 1)

    assert [(c["document_id"], c["chunk_id"], c["score"]) for c in candidatos] == [(45, 0, 0.78), (7, 2, 0.6)]


def test_como_mucho_top_k_documentos(monkeypatch):
    matches = [_match(d, 0, 0.9 - d / 100) for d in range(1, 6)]
    monkeypatch.setattr(svc, "_search", lambda *a, **k: matches)

    assert [c["document_id"] for c in svc.find_candidates("q", 8, 1, top_k=3)] == [1, 2, 3]


def test_pide_mas_fragmentos_de_los_que_devuelve(monkeypatch):
    pedidos = {}

    def fake_search(question, company_id, assistant_id, top_k):
        pedidos["top_k"] = top_k
        return []

    monkeypatch.setattr(svc, "_search", fake_search)
    svc.find_candidates("q", 8, 1, top_k=3)

    assert pedidos["top_k"] > 3
