"""Tests de `routers/v1/feedback.convert_to_gap` — el endpoint "Enviar a
preguntas sin respuesta".

El bug real encontrado el 2026-10-28 verificando esto con datos reales: la
respuesta devolvía el feedback SIN enriquecer (`question`, `answer`,
`assistant_name`, `conversation_id`, `sources_count`, `rag_score`,
`user_full_name` quedaban en `None`, aunque los datos sí existían), porque
intentaba "refrescarlo" con `get_by_company(..., limit=1)` -que solo trae el
feedback más reciente de TODA la empresa, casi nunca el que se acaba de
convertir- y caía al objeto original, que nunca pasó por `_enrich`. El
frontend reemplaza la fila entera con esta respuesta
(`feedback-list.component.ts`), así que el bug era visible: la fila se
quedaba sin pregunta ni respuesta citada hasta recargar la página.

Son tests de lógica pura: `FeedbackRepository` se sustituye por un doble, y la
función async del router se llama directamente con `asyncio.run`.
"""
import asyncio
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.routers.v1 import feedback as feedback_module
from app.schemas.feedback import FeedbackConvertGap


def _feedback(id_=12, knowledge_gap_id=None):
    return SimpleNamespace(id=id_, knowledge_gap_id=knowledge_gap_id)


def _usuario(company_id=8, user_id=1):
    return SimpleNamespace(id=user_id, company_id=company_id)


class _RepoFalso:
    def __init__(self, feedback):
        self._feedback = feedback
        self.enriquecido_con = None

    def get_of_company(self, feedback_id, company_id):
        return self._feedback if self._feedback.id == feedback_id else None

    def convert_to_gap(self, feedback, question, company_id, user_id):
        feedback.knowledge_gap_id = 99
        return SimpleNamespace(id=99, question=question)

    def _enrich(self, feedbacks):
        self.enriquecido_con = feedbacks
        for f in feedbacks:
            # Simula lo que de verdad hace `_enrich`: adjunta los campos
            # calculados que no son columnas de la tabla.
            f.question = "que es un agente de IA"
            f.answer = "Un agente de IA es..."
            f.assistant_name = "Demo"


def _patch(monkeypatch, repo):
    monkeypatch.setattr(feedback_module, "FeedbackRepository", lambda db: repo)


def test_la_respuesta_viene_enriquecida_no_el_feedback_crudo(monkeypatch):
    """El caso que estaba roto: question/answer/assistant_name deben venir
    poblados en la respuesta, no en None."""
    fb = _feedback()
    repo = _RepoFalso(fb)
    _patch(monkeypatch, repo)

    resultado = asyncio.run(
        feedback_module.convert_to_gap(12, FeedbackConvertGap(question="que es un agente de IA"),
                                        db=None, current_user=_usuario())
    )

    assert resultado is fb
    assert resultado.question == "que es un agente de IA"
    assert resultado.answer == "Un agente de IA es..."
    assert resultado.assistant_name == "Demo"
    # Se enriqueció justo el feedback convertido, no una lista arbitraria.
    assert repo.enriquecido_con == [fb]


def test_feedback_inexistente_da_404(monkeypatch):
    repo = _RepoFalso(_feedback(id_=12))
    _patch(monkeypatch, repo)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(feedback_module.convert_to_gap(
            999, FeedbackConvertGap(question="x"), db=None, current_user=_usuario()))
    assert exc.value.status_code == 404


def test_un_feedback_ya_convertido_no_se_puede_convertir_de_nuevo(monkeypatch):
    repo = _RepoFalso(_feedback(knowledge_gap_id=5))
    _patch(monkeypatch, repo)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(feedback_module.convert_to_gap(
            12, FeedbackConvertGap(question="x"), db=None, current_user=_usuario()))
    assert exc.value.status_code == 409


def test_convertir_no_crea_notificaciones():
    """Retirado el 2026-11-04: convertir lo hace un admin y el aviso "Nueva
    pregunta sin respuesta" le llegaba a él mismo. Ni convertir ni resolver
    importan ya el servicio de notificaciones."""
    from app.routers.v1 import knowledge_gaps

    assert not hasattr(feedback_module, "NotificationService")
    assert not hasattr(knowledge_gaps, "NotificationService")
