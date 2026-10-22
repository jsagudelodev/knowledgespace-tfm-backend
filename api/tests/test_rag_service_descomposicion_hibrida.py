"""Tests de la clase que combina reparto equilibrado y BM25 por subpregunta.

Lo que se fija aqui: que cada subpregunta se fusiona con su PROPIO texto antes
de repartir (no con el texto de la consulta completa), que la abstencion
sigue dependiendo solo de la parte densa, y que con una sola subpregunta el
comportamiento coincide con RAGServiceHibrido -no hay bifurcacion especial
para ese caso-.
"""
from types import SimpleNamespace

import pytest

from app.services.rag_service import TOP_K
from app.services.rag_service_descomposicion_hibrida import RAGServiceDescomposicionHibrida


def _doc(id_, score):
    return SimpleNamespace(id=id_, score=score,
                           metadata={"document_name": "m.pdf", "text": "x"})


def _fragmento(chunk_id, texto="contenido"):
    return {"chunk_id": chunk_id, "document_id": 1, "document_name": "m.pdf",
            "chunk_index": 0, "text": texto}


def _servicio(texto_modelo, densos_por_subpregunta, corpus_namespace):
    """`densos_por_subpregunta` es {subpregunta: [docs]}; `texto_modelo` es lo
    que devuelve el descompositor."""
    svc = RAGServiceDescomposicionHibrida.__new__(RAGServiceDescomposicionHibrida)
    svc.client = _ClienteDescomposicion(texto_modelo)
    svc.pinecone_service = SimpleNamespace(listar_namespace=lambda ns: corpus_namespace)
    svc.llamadas_auxiliares = []

    def _base(q, ns, top_k=None):
        return list(densos_por_subpregunta.get(q, [])), 5
    svc._recuperar_base = _base
    return svc


class _ClienteDescomposicion:
    def __init__(self, texto):
        self._texto = texto
        completions = SimpleNamespace(create=self._create)
        self.chat = SimpleNamespace(completions=completions)

    def _create(self, **kwargs):
        mensaje = SimpleNamespace(content=self._texto)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=mensaje)],
            usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5),
        )


@pytest.fixture(autouse=True)
def _parches(monkeypatch):
    import contextlib

    from app.services import rag_service as rag_service_mod
    from app.services import rag_service_descomposicion_hibrida as mod

    @contextlib.contextmanager
    def _paso(nombre, entrada=None):
        yield {}
    monkeypatch.setattr(mod.observabilidad, "paso", _paso)
    # `_recuperar_cada_una` (en RAGServiceAvanzado) llama a `super()._recuperar`,
    # que por el MRO de esta clase resuelve en RAGService: es ahi donde hay
    # que parchear la busqueda densa real, no en una clase intermedia.
    monkeypatch.setattr(rag_service_mod.RAGService, "_recuperar",
                        lambda self, q, ns, top_k=None: self._recuperar_base(q, ns, top_k))


# ── Con una sola subpregunta, igual que el hibrido simple ──────────────────

def test_una_sola_subpregunta_se_fusiona_con_bm25():
    """El texto de la consulta debe compartir algun termino con el fragmento
    a rescatar: BM25 no encuentra lo que no tiene ninguna palabra en comun."""
    densos = {"termino_exacto": [_doc("a", 0.6)]}
    corpus = [_fragmento("a"), _fragmento("rescatado", "aqui aparece termino_exacto tambien")]
    svc = _servicio("termino_exacto", densos, corpus)

    docs, _ = svc._recuperar("termino_exacto", "ns")

    ids = {d.id for d in docs}
    assert "a" in ids
    assert "rescatado" in ids, "BM25 debe poder rescatar incluso con una sola subpregunta"


# ── Cada subpregunta se fusiona con SU PROPIO texto ────────────────────────

def test_bm25_usa_el_texto_de_cada_subpregunta_no_la_consulta_completa():
    """La consulta ORIGINAL (sin descomponer) lleva una palabra que ninguna
    de las dos subpreguntas contiene por separado. Si el codigo fusionara con
    el texto de la consulta completa en lugar del de cada subpregunta, un
    fragmento que solo comparte esa palabra se colaria en AMBAS fusiones. Con
    el texto de cada subpregunta, ese fragmento no deberia aparecer en
    ninguna: ni "tema_gatos" ni "tema_perros" la mencionan."""
    consulta_completa = "palabra_solo_en_la_union tema_gatos tema_perros"
    densos = {
        "tema_gatos": [_doc("g1", 0.6)],
        "tema_perros": [_doc("p1", 0.6)],
    }
    corpus = [
        _fragmento("g1", "contenido sobre felinos"),
        _fragmento("p1", "contenido sobre caninos"),
        _fragmento("trampa", "palabra_solo_en_la_union"),
    ]
    svc = _servicio("tema_gatos\ntema_perros", densos, corpus)

    docs, _ = svc._recuperar(consulta_completa, "ns")

    assert "trampa" not in {d.id for d in docs}, \
        "se fusiono con el texto de la consulta completa, no con el de cada subpregunta"


# ── La abstencion depende solo de la parte densa ───────────────────────────

def test_si_ninguna_subpregunta_tiene_densos_relevantes_se_abstiene():
    densos = {"primera": [_doc("a", 0.05)], "segunda": [_doc("b", 0.02)]}
    svc = _servicio("primera\nsegunda", densos, [_fragmento("a"), _fragmento("b")])

    docs, tokens = svc._recuperar("x", "ns")

    assert docs == []


def test_si_una_subpregunta_tiene_evidencia_y_otra_no_se_responde_con_la_que_hay():
    densos = {"con_evidencia": [_doc("a", 0.6)], "sin_evidencia": [_doc("b", 0.02)]}
    svc = _servicio("con_evidencia\nsin_evidencia", densos,
                    [_fragmento("a"), _fragmento("b")])

    docs, _ = svc._recuperar("x", "ns")

    assert "a" in {d.id for d in docs}
    assert "b" not in {d.id for d in docs}


# ── Respeta el presupuesto final ───────────────────────────────────────────

def test_respeta_el_top_k_final():
    densos = {
        "p1": [_doc(f"p1_{i}", 0.9 - i * 0.01) for i in range(TOP_K)],
        "p2": [_doc(f"p2_{i}", 0.8 - i * 0.01) for i in range(TOP_K)],
    }
    corpus = [_fragmento(f"p1_{i}") for i in range(TOP_K)] + \
             [_fragmento(f"p2_{i}") for i in range(TOP_K)]
    svc = _servicio("p1\np2", densos, corpus)

    docs, _ = svc._recuperar("x", "ns")
    assert len(docs) <= TOP_K
