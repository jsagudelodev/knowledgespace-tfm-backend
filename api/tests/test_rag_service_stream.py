"""Tests de `generate_response_stream`.

No sustituye a `generate_response` -viven lado a lado, ver el docstring del
metodo en `rag_service.py`-, asi que lo que importa fijar aqui es que:

    1. entrega los mismos trozos de texto que el modelo fue generando, en
       orden, y termina con un evento `done` cuyo contenido es la union de
       todos ellos,
    2. ese evento final trae las MISMAS fuentes que construiria
       `generate_response` para los mismos fragmentos recuperados -la
       logica de que es citable no depende de como se entrega la respuesta-,
    3. un fallo del proveedor durante el streaming se traduce a
       `RAGUnavailableError`, igual que en la ruta sin streaming.

Son tests de logica pura: el cliente de OpenAI y la recuperacion se
sustituyen por dobles.
"""
from types import SimpleNamespace

import pytest

from app.services.rag_service import RAGService, RAGUnavailableError


def _doc(score: float, nombre: str = "manual.pdf") -> SimpleNamespace:
    return SimpleNamespace(
        id="doc-1-chunk-0", score=score,
        metadata={"document_id": 1, "document_name": nombre, "text": "contenido", "chunk_index": 0},
    )


def _chunk_delta(texto):
    return SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=texto))], usage=None)


def _chunk_final_con_uso(prompt_tokens, completion_tokens):
    """El ultimo chunk de un stream con `stream_options={"include_usage": True}`
    no trae ningun `choice`, solo el consumo total."""
    return SimpleNamespace(choices=[], usage=SimpleNamespace(
        prompt_tokens=prompt_tokens, completion_tokens=completion_tokens))


class _ClienteStream:
    def __init__(self, chunks):
        self._chunks = chunks
        completions = SimpleNamespace(create=self._create)
        self.chat = SimpleNamespace(completions=completions)

    def _create(self, **kwargs):
        assert kwargs["stream"] is True
        assert kwargs["stream_options"] == {"include_usage": True}
        return iter(self._chunks)


class _ClienteQueFallaAMitad:
    def __init__(self, chunks_antes_de_fallar):
        self._chunks = chunks_antes_de_fallar
        completions = SimpleNamespace(create=self._create)
        self.chat = SimpleNamespace(completions=completions)

    def _create(self, **kwargs):
        def _generador():
            yield from self._chunks
            raise RuntimeError("la conexion se cortó a mitad de la respuesta")
        return _generador()


def _servicio(cliente, docs, monkeypatch):
    svc = RAGService.__new__(RAGService)
    svc.client = cliente
    svc.embedding_service = SimpleNamespace(modelo="text-embedding-3-small")
    monkeypatch.setattr(RAGService, "_recuperar", lambda self, q, ns, top_k=None: (docs, 7))
    return svc


# ── Los trozos llegan en orden y se acumulan en el evento final ─────────────

def test_las_deltas_llegan_en_orden_y_se_acumulan_en_el_evento_final(monkeypatch):
    chunks = [
        _chunk_delta("Un agente "),
        _chunk_delta("de IA es un sistema"),
        _chunk_final_con_uso(prompt_tokens=120, completion_tokens=6),
    ]
    svc = _servicio(_ClienteStream(chunks), [_doc(0.8)], monkeypatch)

    eventos = list(svc.generate_response_stream("que es un agente", company_id=1))

    deltas = [e for e in eventos if e["type"] == "delta"]
    assert [d["content"] for d in deltas] == ["Un agente ", "de IA es un sistema"]

    final = eventos[-1]
    assert final["type"] == "done"
    assert final["content"] == "Un agente de IA es un sistema"
    assert final["input_tokens"] == 120
    assert final["output_tokens"] == 6
    assert final["token_count"] == 126


# ── Las fuentes del evento final coinciden con las de generate_response ─────

def test_las_fuentes_del_evento_final_son_las_mismas_que_construiria_generate_response(monkeypatch):
    docs = [_doc(0.75, "agentes_ia.md")]
    svc = _servicio(_ClienteStream([_chunk_delta("x"), _chunk_final_con_uso(1, 1)]), docs, monkeypatch)

    eventos = list(svc.generate_response_stream("x", company_id=1))
    fuentes_stream = eventos[-1]["sources"]

    assert fuentes_stream == RAGService._build_sources(docs)
    assert fuentes_stream[0]["document_name"] == "agentes_ia.md"


# ── Un fallo del proveedor se traduce igual que en la ruta sin streaming ───

def test_un_fallo_a_mitad_del_stream_se_traduce_a_rag_unavailable(monkeypatch):
    cliente = _ClienteQueFallaAMitad([_chunk_delta("esto si llega")])
    svc = _servicio(cliente, [_doc(0.8)], monkeypatch)

    with pytest.raises(RAGUnavailableError) as exc_info:
        list(svc.generate_response_stream("x", company_id=1))

    assert exc_info.value.etapa == "generación de la respuesta"


def test_un_fallo_inmediato_del_proveedor_tambien_se_traduce(monkeypatch):
    class _ClienteQueFallaDeEntrada:
        def __init__(self):
            def _create(**kwargs):
                raise RuntimeError("la API no responde")
            self.chat = SimpleNamespace(completions=SimpleNamespace(create=_create))

    svc = _servicio(_ClienteQueFallaDeEntrada(), [_doc(0.8)], monkeypatch)

    with pytest.raises(RAGUnavailableError):
        list(svc.generate_response_stream("x", company_id=1))
