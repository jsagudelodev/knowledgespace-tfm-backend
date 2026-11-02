""""Pedir documento" asignaba a una persona sin avisarle (encontrado en la prueba
de punta a punta del 2026-11-02). Ahora el responsable recibe una notificación
dirigida a él, para que pueda subir el documento sin depender del admin."""
from types import SimpleNamespace

from app.routers.v1 import knowledge_gaps


class _ServicioFalso:
    creadas = []

    def __init__(self, db):
        pass

    def create_for_user(self, **kw):
        _ServicioFalso.creadas.append(kw)


def _gap(assigned_to=14, note=None):
    return SimpleNamespace(id=35, company_id=8, assigned_to=assigned_to, note=note,
                           question="¿Cuál es el horario de soporte?")


def _admin():
    return SimpleNamespace(id=8, full_name="Sebastian Agudelo")


def test_avisa_al_responsable(monkeypatch):
    _ServicioFalso.creadas = []
    monkeypatch.setattr(knowledge_gaps, "NotificationService", _ServicioFalso)

    knowledge_gaps._notify_document_requested(None, _gap(note="El PDF de soporte"), _admin())

    aviso = _ServicioFalso.creadas[0]
    assert aviso["user_id"] == 14
    assert aviso["type_name"] == "document_requested"
    assert "horario de soporte" in aviso["message"]
    assert "El PDF de soporte" in aviso["message"]


def test_no_avisa_si_se_lo_asigna_a_si_mismo(monkeypatch):
    _ServicioFalso.creadas = []
    monkeypatch.setattr(knowledge_gaps, "NotificationService", _ServicioFalso)

    knowledge_gaps._notify_document_requested(None, _gap(assigned_to=8), _admin())

    assert _ServicioFalso.creadas == []


def test_sin_responsable_no_hay_aviso(monkeypatch):
    _ServicioFalso.creadas = []
    monkeypatch.setattr(knowledge_gaps, "NotificationService", _ServicioFalso)

    knowledge_gaps._notify_document_requested(None, _gap(assigned_to=None), _admin())

    assert _ServicioFalso.creadas == []


def test_el_tipo_se_siembra_en_instalaciones_nuevas():
    from app.routers.v1.setup import TIPOS_DE_NOTIFICACION
    assert "document_requested" in {t["name"] for t in TIPOS_DE_NOTIFICACION}
