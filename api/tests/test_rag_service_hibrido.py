"""Tests del RAG hibrido: fusion de busqueda densa y lexica por posicion.

Lo que se fija aqui es la propiedad que justifica todo el diseno: el umbral
protege primero, la fusion opera despues. Si ningun candidato denso lo supera,
el hibrido se abstiene igual que la base, y BM25 no tiene voto sobre si el
sistema responde. Solo cuando ya hay evidencia densa entra en juego la parte
lexica, y puede ANADIR fragmentos que la busqueda densa no trajo.

Tambien se fija el problema de escalas que motivo el diseno: un fragmento
rescatado solo por BM25 no tiene una puntuacion coseno real, y el propio
`generate_response` heredado vuelve a filtrar por `score >= umbral` sobre lo
que `_recuperar` devuelva. Sin el valor centinela, eso rompe con un
TypeError al comparar `None >= 0.30`.
"""
from types import SimpleNamespace

import pytest

from app.services.rag_service import RELEVANCE_THRESHOLD, TOP_K
from app.services.rag_service_hibrido import RAGServiceHibrido


def _doc(id_, score):
    return SimpleNamespace(id=id_, score=score,
                           metadata={"document_name": "m.pdf", "text": "x"})


def _fragmento(chunk_id, texto="contenido"):
    return {"chunk_id": chunk_id, "document_id": 1, "document_name": "m.pdf",
            "chunk_index": 0, "text": texto}


def _servicio(densos, corpus_namespace):
    svc = RAGServiceHibrido.__new__(RAGServiceHibrido)
    svc.pinecone_service = SimpleNamespace(
        listar_namespace=lambda ns: corpus_namespace)

    def _base(query, namespace, top_k=None):
        return list(densos), 7
    svc._recuperar_base = _base
    return svc


@pytest.fixture(autouse=True)
def _super_parcheado(monkeypatch):
    import app.services.rag_service_hibrido as mod
    monkeypatch.setattr(mod.RAGService, "_recuperar",
                        lambda self, q, ns, top_k=None: self._recuperar_base(q, ns, top_k))


# ── El umbral protege antes de que BM25 tenga voto ─────────────────────────

def test_si_ningun_denso_supera_el_umbral_se_abstiene_sin_consultar_bm25():
    bajos = [_doc("a", RELEVANCE_THRESHOLD - 0.05), _doc("b", 0.10)]
    llamado = []
    svc = _servicio(bajos, [])
    svc.pinecone_service.listar_namespace = lambda ns: (llamado.append(1) or [])

    docs, tokens = svc._recuperar("x", "ns")

    assert docs == []
    assert tokens == 7
    assert not llamado, "no debe construirse el indice lexico si no hay evidencia densa"


def test_sin_ninguna_senal_un_fragmento_descartado_no_reaparece():
    """"malo" queda por debajo del umbral denso y no comparte ningún término
    con la consulta: ni la similitud ni BM25 lo recomiendan, y no debe
    colarse solo por pertenecer al corpus."""
    densos = [_doc("bueno", 0.60), _doc("malo", 0.10)]
    corpus = [_fragmento("bueno", "palabra_clave_del_tema"),
              _fragmento("malo", "texto completamente distinto y sin relacion")]
    svc = _servicio(densos, corpus)

    docs, _ = svc._recuperar("palabra_clave_del_tema", "ns")

    assert "malo" not in {d.id for d in docs}


def test_un_denso_bajo_umbral_si_puede_ser_rescatado_por_bm25_fuerte():
    """A diferencia del caso anterior: si SI comparte terminos con la
    consulta, el hibrido puede rescatarlo aunque su similitud coseno quedara
    por debajo del umbral -es precisamente lo que un hibrido aporta-."""
    densos = [_doc("otro_con_evidencia", 0.60), _doc("descartado_denso", 0.10)]
    corpus = [_fragmento("otro_con_evidencia", "tema general"),
              _fragmento("descartado_denso", "termino_exacto_buscado")]
    svc = _servicio(densos, corpus)

    docs, _ = svc._recuperar("termino_exacto_buscado", "ns")

    assert "descartado_denso" in {d.id for d in docs}


# ── La fusion puede rescatar lo que la densa no trajo ──────────────────────

def test_bm25_puede_anadir_un_fragmento_que_la_densa_no_trajo():
    densos = [_doc("denso1", 0.70)]
    corpus = [
        _fragmento("denso1", "texto generico"),
        _fragmento("rescatado", "palabra_exclusiva_y_rara"),
        _fragmento("irrelevante", "nada que ver"),
    ]
    svc = _servicio(densos, corpus)

    docs, _ = svc._recuperar("palabra_exclusiva_y_rara", "ns")

    ids = {d.id for d in docs}
    assert "denso1" in ids, "el que ya tenia evidencia densa no se pierde"
    assert "rescatado" in ids, "BM25 debe poder anadir lo que la densa no trajo"


def test_un_fragmento_rescatado_lleva_el_umbral_como_centinela_no_None():
    """Sin esto, generate_response rompe con TypeError al comparar
    `None >= RELEVANCE_THRESHOLD`."""
    densos = [_doc("denso1", 0.70)]
    corpus = [_fragmento("denso1"), _fragmento("rescatado", "palabra_unica")]
    svc = _servicio(densos, corpus)

    docs, _ = svc._recuperar("palabra_unica", "ns")

    rescatado = next(d for d in docs if d.id == "rescatado")
    assert rescatado.score == RELEVANCE_THRESHOLD
    assert rescatado.metadata["rescatado_por_bm25"] is True
    # Y el filtro posterior de generate_response no debe romper con el:
    assert rescatado.score >= RELEVANCE_THRESHOLD


def test_un_fragmento_denso_relevante_conserva_su_puntuacion_real():
    densos = [_doc("denso1", 0.73)]
    svc = _servicio(densos, [_fragmento("denso1")])

    docs, _ = svc._recuperar("x", "ns")

    assert docs[0].score == 0.73


# ── Casos de borde ──────────────────────────────────────────────────────────

def test_respeta_el_top_k_final():
    densos = [_doc(f"d{i}", 0.9 - i * 0.01) for i in range(TOP_K)]
    corpus = [_fragmento(f"d{i}") for i in range(TOP_K)] + \
             [_fragmento(f"extra{i}", f"termino{i}") for i in range(10)]
    svc = _servicio(densos, corpus)

    docs, _ = svc._recuperar("termino0 termino1 termino2", "ns")
    assert len(docs) <= TOP_K


def test_si_listar_namespace_falla_se_recupera_como_la_busqueda_densa():
    """BM25 es un complemento; si falla al listar el corpus, no debe tirar
    abajo la consulta."""
    densos = [_doc("a", 0.6), _doc("b", 0.5)]
    svc = _servicio(densos, None)

    def _rompe(ns):
        raise RuntimeError("Pinecone no responde")
    svc.pinecone_service.listar_namespace = _rompe

    docs, tokens = svc._recuperar("x", "ns")

    assert {d.id for d in docs} == {"a", "b"}
    assert tokens == 7
