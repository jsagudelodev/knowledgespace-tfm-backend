"""Tests de `_generar_eventos_sse`, el cuerpo del endpoint de streaming del
chat (`/chat/message/stream`).

Se extrajo a función de módulo justamente para poder probarla así: con
dobles, sin TestClient ni base de datos real -este proyecto no levanta la
aplicación en los tests, ver `ALCANCE_TFM.md`-. Lo que se fija:

    1. cada evento `delta` del RAG se reenvia como una linea SSE
       `data: {...}\n\n` con el mismo contenido,
    2. el evento `done` persiste el mensaje y registra el coste -igual que
       hace la ruta sincrona tras `generate_response`- y el evento SSE final
       trae message_id, conversation_id, sources y cost_usd,
    3. un fallo del RAG a mitad de la respuesta se traduce a un evento
       `error`, no a una excepcion que tumbe la conexion sin avisar,
    4. recibe identificadores sueltos y abre SU PROPIA sesion de base de
       datos (no la de `Depends(get_db)`) -el motivo real por el que esto
       cambio de forma: esa sesion ya esta cerrada quando este generador
       corre, ver su docstring-, y la cierra al terminar pase lo que pase.
"""
import json
from types import SimpleNamespace

from app.routers.v1 import chat as chat_module
from app.routers.v1.chat import _generar_eventos_sse
from app.services.rag_service import RAGUnavailableError


class _MsgRepoFalso:
    def __init__(self):
        self.creados = []

    def create_message(self, **kwargs):
        mensaje = SimpleNamespace(id=99, **kwargs)
        self.creados.append(mensaje)
        return mensaje


class _DBFalsa:
    """Doble minimo para que `CostTrackingService.record` corra de verdad
    -incluido el calculo real del costo- sin tocar una base de datos."""
    def __init__(self):
        self.agregados = []
        self.cerrada = False

    def add(self, obj):
        self.agregados.append(obj)

    def commit(self):
        pass

    def close(self):
        self.cerrada = True


class _RAGQueResponde:
    def __init__(self, eventos):
        self._eventos = eventos

    def generate_response_stream(self, **kwargs):
        yield from self._eventos


class _RAGQueFallaAMitad:
    def __init__(self, eventos_antes_del_fallo, etapa="generación de la respuesta"):
        self._eventos = eventos_antes_del_fallo
        self._etapa = etapa

    def generate_response_stream(self, **kwargs):
        yield from self._eventos
        raise RAGUnavailableError(self._etapa, RuntimeError("se cortó"))


def _parsear_eventos(lineas_sse):
    """Cada entrada es una linea cruda `data: {...}\n\n`; se devuelve la
    lista de dicts ya decodificados, en el mismo orden."""
    return [json.loads(linea.removeprefix("data: ").rstrip("\n")) for linea in lineas_sse]


def _patch_sesion(monkeypatch, msg_repo_falso, db_falsa):
    """`_generar_eventos_sse` abre su propia sesión con `SessionLocal()` y
    construye su propio `MessageRepository(db)` -no los recibe por parámetro,
    a propósito, ver el docstring de la función-, así que se sustituyen ambos
    constructores por los dobles de este test."""
    monkeypatch.setattr(chat_module, "SessionLocal", lambda: db_falsa)
    monkeypatch.setattr(chat_module, "MessageRepository", lambda db: msg_repo_falso)


def _generar(rag, monkeypatch, msg_repo=None, db=None, **kwargs):
    msg_repo = msg_repo or _MsgRepoFalso()
    db = db or _DBFalsa()
    _patch_sesion(monkeypatch, msg_repo, db)

    defaults = dict(
        message="que es un agente de IA", company_id=8, user_id=1,
        assistant_id=None, system_prompt_override=None, model_override=None,
        conversation_id=42, conversation_history=[],
    )
    defaults.update(kwargs)
    return list(_generar_eventos_sse(rag, **defaults)), msg_repo, db


# ── Las deltas se reenvían tal cual ─────────────────────────────────────────

def test_cada_delta_se_reenvia_como_su_propio_evento_sse(monkeypatch):
    rag = _RAGQueResponde([
        {"type": "delta", "content": "Un agente "},
        {"type": "delta", "content": "de IA es..."},
        {
            "type": "done", "content": "Un agente de IA es...", "sources": [],
            "input_tokens": 100, "output_tokens": 10, "model": "gpt-4o-mini",
            "embedding_model": "text-embedding-3-small", "embedding_tokens": 5,
            "llamadas_auxiliares": [],
        },
    ])
    lineas, _, _ = _generar(rag, monkeypatch)
    eventos = _parsear_eventos(lineas)

    assert eventos[0] == {"type": "delta", "content": "Un agente "}
    assert eventos[1] == {"type": "delta", "content": "de IA es..."}


# ── El evento `done` persiste el mensaje y registra el coste ───────────────

def test_el_evento_done_persiste_el_mensaje_y_trae_el_costo(monkeypatch):
    rag = _RAGQueResponde([
        {"type": "delta", "content": "hola"},
        {
            "type": "done", "content": "hola", "sources": [{"document_name": "x.md"}],
            "input_tokens": 1000, "output_tokens": 100, "model": "gpt-4o-mini",
            "embedding_model": "text-embedding-3-small", "embedding_tokens": 5,
            "llamadas_auxiliares": [],
        },
    ])
    lineas, msg_repo, _ = _generar(rag, monkeypatch, conversation_id=42)
    final = _parsear_eventos(lineas)[-1]

    assert final["type"] == "done"
    assert final["message_id"] == 99
    assert final["conversation_id"] == 42
    assert final["sources"] == [{"document_name": "x.md"}]
    assert final["cost_usd"] is not None and final["cost_usd"] > 0

    # Se guardó como mensaje del asistente, con el contenido y fuentes del RAG.
    assert len(msg_repo.creados) == 1
    assert msg_repo.creados[0].role == "assistant"
    assert msg_repo.creados[0].content == "hola"


def test_las_llamadas_auxiliares_tambien_se_facturan(monkeypatch):
    """Una configuracion avanzada (descomposicion/reordenado) debe dejar su
    propia fila de coste, igual que en la ruta sincrona."""
    rag = _RAGQueResponde([{
        "type": "done", "content": "x", "sources": [],
        "input_tokens": 10, "output_tokens": 1, "model": "gpt-4o-mini",
        "embedding_model": "text-embedding-3-small", "embedding_tokens": 2,
        "llamadas_auxiliares": [{
            "operacion": "descomposicion", "modelo": "gpt-4o-mini",
            "tokens_entrada": 137, "tokens_salida": 9, "duracion_ms": 800,
        }],
    }])
    _, _, db = _generar(rag, monkeypatch)

    operaciones = [row.operation for row in db.agregados]
    assert operaciones == ["chat", "embedding", "descomposicion"]


# ── La sesión propia se cierra siempre, incluso si el RAG falla ────────────

def test_la_sesion_propia_se_cierra_al_terminar(monkeypatch):
    rag = _RAGQueResponde([{
        "type": "done", "content": "x", "sources": [],
        "input_tokens": 1, "output_tokens": 1, "model": "gpt-4o-mini",
        "embedding_model": "text-embedding-3-small", "embedding_tokens": 1,
        "llamadas_auxiliares": [],
    }])
    _, _, db = _generar(rag, monkeypatch)
    assert db.cerrada is True


def test_la_sesion_propia_se_cierra_incluso_si_el_rag_falla(monkeypatch):
    rag = _RAGQueFallaAMitad([], etapa="búsqueda vectorial")
    _, _, db = _generar(rag, monkeypatch)
    assert db.cerrada is True


# ── Un fallo a mitad de la respuesta se convierte en un evento `error` ─────

def test_un_fallo_a_mitad_de_la_respuesta_se_convierte_en_evento_error(monkeypatch):
    rag = _RAGQueFallaAMitad(
        [{"type": "delta", "content": "esto si llega"}],
        etapa="generación de la respuesta",
    )
    lineas, _, _ = _generar(rag, monkeypatch)
    eventos = _parsear_eventos(lineas)

    assert eventos[0] == {"type": "delta", "content": "esto si llega"}
    assert eventos[-1] == {"type": "error", "etapa": "generación de la respuesta"}
    # Ningun `done`: no hay nada que persistir de una respuesta que no se completó.
    assert not any(e["type"] == "done" for e in eventos)


def test_un_fallo_inmediato_tambien_produce_un_evento_error_sin_romper(monkeypatch):
    rag = _RAGQueFallaAMitad([], etapa="búsqueda vectorial")
    lineas, _, _ = _generar(rag, monkeypatch)
    eventos = _parsear_eventos(lineas)

    assert eventos == [{"type": "error", "etapa": "búsqueda vectorial"}]


# ── Preguntas de alcance global: ni tocan el RAG ni cuestan nada ───────────

class _RAGQueNuncaDeberiaLlamarse:
    def generate_response_stream(self, **kwargs):
        raise AssertionError("una pregunta de alcance global no debe llegar al RAG")


def test_una_pregunta_de_alcance_global_no_llega_al_rag_y_no_cuesta_nada(monkeypatch):
    monkeypatch.setattr(
        chat_module, "es_pregunta_de_alcance_global", lambda msg: True,
    )
    monkeypatch.setattr(
        chat_module, "responder_alcance_global",
        lambda db, company_id, assistant_id: "Tienes acceso a 2 documentos:\n- a.pdf\n- b.pdf",
    )
    msg_repo = _MsgRepoFalso()
    db = _DBFalsa()
    lineas, _, _ = _generar(_RAGQueNuncaDeberiaLlamarse(), monkeypatch, msg_repo=msg_repo, db=db)
    eventos = _parsear_eventos(lineas)

    assert eventos[0] == {"type": "delta", "content": "Tienes acceso a 2 documentos:\n- a.pdf\n- b.pdf"}
    final = eventos[-1]
    assert final["type"] == "done"
    assert final["cost_usd"] == 0.0
    assert msg_repo.creados[0].content == "Tienes acceso a 2 documentos:\n- a.pdf\n- b.pdf"
    # Ninguna fila de coste: no hubo llamada a OpenAI ni a Pinecone que facturar.
    assert db.agregados == []
    assert db.cerrada is True
