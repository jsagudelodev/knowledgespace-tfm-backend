"""Tests del cálculo de costo — sin BD ni llamadas externas.

Estos números son la base de la promesa "eficiencia en costes de
inferencia" del proyecto: si el cálculo de precio está mal, cada cifra
que se le muestre al usuario (y a la defensa del TFM) está mal.
"""
from unittest.mock import MagicMock

from app.services.cost_tracking_service import PRICING, CostTrackingService


def test_calculate_cost_gpt4o_mini_known_pricing():
    # 1000 tokens de entrada + 1000 de salida al precio publicado de gpt-4o-mini
    cost = CostTrackingService.calculate_cost("gpt-4o-mini", input_tokens=1000, output_tokens=1000)
    expected = PRICING["gpt-4o-mini"]["input"] + PRICING["gpt-4o-mini"]["output"]
    assert cost == round(expected, 6)


def test_calculate_cost_zero_tokens_is_zero():
    assert CostTrackingService.calculate_cost("gpt-4o-mini", input_tokens=0, output_tokens=0) == 0.0


def test_calculate_cost_embedding_model_has_no_output_cost():
    # Los modelos de embeddings no tienen tokens de salida — pasar output_tokens
    # no debería sumar nada si el modelo no define precio de "output".
    cost = CostTrackingService.calculate_cost(
        "text-embedding-3-small", input_tokens=1000, output_tokens=1000
    )
    assert cost == PRICING["text-embedding-3-small"]["input"]


def test_calculate_cost_unknown_model_falls_back_to_gpt4o_mini():
    cost_unknown = CostTrackingService.calculate_cost("modelo-que-no-existe", input_tokens=1000)
    cost_known = CostTrackingService.calculate_cost("gpt-4o-mini", input_tokens=1000)
    assert cost_unknown == cost_known


def test_calculate_cost_scales_linearly_with_tokens():
    cost_1k = CostTrackingService.calculate_cost("gpt-4o", input_tokens=1000, output_tokens=0)
    cost_2k = CostTrackingService.calculate_cost("gpt-4o", input_tokens=2000, output_tokens=0)
    assert round(cost_2k, 6) == round(cost_1k * 2, 6)


# ── duration_ms — añadido el 20 de octubre para tener latencia de producción
# con dato propio, no solo medida en experimentos ──────────────────────────

def test_record_persiste_la_duracion_en_la_operacion_chat():
    """`duration_ms` debe llegar intacto al objeto que se guarda — es lo que
    permite, en adelante, detectar con datos propios si el sistema responde
    lento, sin depender de entrar a Langfuse para verlo."""
    db = MagicMock()
    costo = CostTrackingService(db).record(
        company_id=1, model="gpt-4o-mini", operation="chat",
        input_tokens=100, output_tokens=50, duration_ms=2345,
    )
    guardado = db.add.call_args[0][0]
    assert guardado.duration_ms == 2345
    assert costo is not None


def test_record_sin_duracion_queda_en_none():
    """Las llamadas de embedding y las auxiliares (descomposición, reordenado)
    no se miden por separado — `duration_ms` debe poder omitirse sin romper
    el registro, y quedar en None en vez de en 0 (que se leería como
    'instantáneo', una medición falsa, no la ausencia de una)."""
    db = MagicMock()
    CostTrackingService(db).record(
        company_id=1, model="text-embedding-3-small", operation="embedding",
        input_tokens=10,
    )
    guardado = db.add.call_args[0][0]
    assert guardado.duration_ms is None
