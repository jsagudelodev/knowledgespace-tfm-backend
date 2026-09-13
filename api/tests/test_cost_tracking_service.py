"""Tests del cálculo de costo — sin BD ni llamadas externas.

Estos números son la base de la promesa "eficiencia en costes de
inferencia" del proyecto: si el cálculo de precio está mal, cada cifra
que se le muestre al usuario (y a la defensa del TFM) está mal.
"""
from app.services.cost_tracking_service import CostTrackingService, PRICING


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
