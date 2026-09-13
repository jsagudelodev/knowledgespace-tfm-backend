"""Test de _period_cutoff — de él depende qué preguntas caen dentro de
'resueltas en el periodo' y qué tan lejos mira el % de cobertura en el
resumen de Preguntas sin respuesta."""
from datetime import datetime, timezone

from app.routers.v1.knowledge_gaps import _period_cutoff


def test_period_90d_es_aproximadamente_90_dias_atras():
    delta = datetime.now(timezone.utc) - _period_cutoff("90d")
    assert 89 <= delta.days <= 90


def test_period_12m_es_aproximadamente_un_anio_atras():
    delta = datetime.now(timezone.utc) - _period_cutoff("12m")
    assert 364 <= delta.days <= 365


def test_period_month_es_el_inicio_del_mes_actual():
    cutoff = _period_cutoff("month")
    now = datetime.now(timezone.utc)
    assert cutoff.year == now.year
    assert cutoff.month == now.month
    assert cutoff.day == 1
    assert cutoff.hour == 0 and cutoff.minute == 0 and cutoff.second == 0


def test_period_desconocido_cae_a_inicio_de_mes():
    # Cualquier valor no reconocido debe comportarse como "month", no reventar.
    assert _period_cutoff("valor-invalido").day == 1
