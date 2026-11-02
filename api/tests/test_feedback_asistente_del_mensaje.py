"""El feedback se atribuye al asistente que de verdad respondió el mensaje, no
al seleccionado en pantalla al calificar. Encontrado el 2026-11-02: en una
conversación reabierta la pantalla selecciona el primer asistente activo, y la
pregunta sin respuesta derivada acababa en otro espacio de conocimiento."""
import asyncio
from types import SimpleNamespace

from app.routers.v1 import feedback as feedback_module
from app.schemas.feedback import FeedbackCreate


class _QueryFalsa:
    def __init__(self, fila, filtros):
        self._fila = fila
        self._filtros = filtros

    def join(self, *a, **kw):
        return self

    def filter(self, *args):
        self._filtros.extend(str(a) for a in args)
        return self

    def first(self):
        return self._fila


class _DBFalsa:
    def __init__(self, fila=None):
        self.fila = fila
        self.filtros = []
        self.agregados = []

    def query(self, *a):
        return _QueryFalsa(self.fila, self.filtros)


def test_usa_el_asistente_guardado_en_el_mensaje():
    db = _DBFalsa(fila=(5,))
    assert feedback_module._asistente_del_mensaje(db, 547, company_id=8) == 5


def test_el_mensaje_se_busca_solo_dentro_de_la_empresa():
    """Si no, un message_id ajeno filtraría qué asistente usó otra empresa."""
    db = _DBFalsa(fila=None)
    assert feedback_module._asistente_del_mensaje(db, 547, company_id=8) is None
    assert any("company_id" in f for f in db.filtros)


def test_sin_mensaje_no_consulta_nada():
    db = _DBFalsa(fila=(5,))
    assert feedback_module._asistente_del_mensaje(db, None, company_id=8) is None
    assert db.filtros == []


def test_el_feedback_prefiere_el_asistente_del_mensaje_al_de_la_pantalla(monkeypatch):
    creado = {}

    class _RepoFalso:
        def __init__(self, db):
            pass

        def create(self, fb):
            creado["fb"] = fb
            return fb

    monkeypatch.setattr(feedback_module, "FeedbackRepository", _RepoFalso)
    monkeypatch.setattr(feedback_module, "_asistente_del_mensaje", lambda db, mid, cid: 5)

    data = FeedbackCreate(assistant_id=2, message_id=547, rating=1)
    asyncio.run(feedback_module.submit_feedback(data, db=None, current_user=SimpleNamespace(id=1, company_id=8)))

    assert creado["fb"].assistant_id == 5


def test_si_el_mensaje_es_antiguo_vale_el_de_la_pantalla(monkeypatch):
    """Los mensajes anteriores a la migración tienen assistant_id NULL."""
    creado = {}

    class _RepoFalso:
        def __init__(self, db):
            pass

        def create(self, fb):
            creado["fb"] = fb
            return fb

    monkeypatch.setattr(feedback_module, "FeedbackRepository", _RepoFalso)
    monkeypatch.setattr(feedback_module, "_asistente_del_mensaje", lambda db, mid, cid: None)

    data = FeedbackCreate(assistant_id=2, message_id=100, rating=1)
    asyncio.run(feedback_module.submit_feedback(data, db=None, current_user=SimpleNamespace(id=1, company_id=8)))

    assert creado["fb"].assistant_id == 2
