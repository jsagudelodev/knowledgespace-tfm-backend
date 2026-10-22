"""Tests de la validacion del modelo de un asistente.

El costo de cada consulta se calcula con la tabla `PRICING`. Un modelo que no
este en ella se registraria con el precio de gpt-4o-mini sin avisar, asi que la
API solo acepta modelos con precio al crear o editar un asistente.
"""
import pytest
from pydantic import ValidationError

from app.core.config import settings
from app.schemas.assistant import AssistantCreate, AssistantUpdate
from app.services.cost_tracking_service import MODELOS_CHAT

# Los que ofrece el selector del formulario (`assistant-form.component.ts`).
# Si el frontend anade uno sin precio, este test lo detecta.
MODELOS_DEL_FORMULARIO = ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"]


@pytest.mark.parametrize("modelo", MODELOS_DEL_FORMULARIO)
def test_acepta_los_modelos_del_formulario(modelo):
    assert AssistantCreate(name="Ventas", model=modelo).model == modelo


def test_rechaza_un_modelo_sin_precio_al_crear():
    with pytest.raises(ValidationError, match="Modelo no soportado"):
        AssistantCreate(name="Ventas", model="gpt-5")


def test_rechaza_un_modelo_sin_precio_al_editar():
    with pytest.raises(ValidationError, match="Modelo no soportado"):
        AssistantUpdate(model="gpt-5")


def test_editar_sin_tocar_el_modelo_sigue_permitido():
    assert AssistantUpdate(name="Otro nombre").model is None


def test_los_embeddings_no_son_modelos_de_chat():
    assert not any(m.startswith("text-embedding") for m in MODELOS_CHAT)


def test_el_modelo_por_defecto_tiene_precio():
    """Es el que usa el chat cuando la empresa no tiene asistente."""
    assert settings.OPENAI_CHAT_MODEL in MODELOS_CHAT
