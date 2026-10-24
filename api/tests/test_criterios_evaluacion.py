"""Tests de los criterios si/no de la evaluacion (`experimentos/criterios.py`).

Los tipos `premisa_falsa` y `parcial` se juzgan con un criterio propio, no con
RAGAS. Aqui se fija la parte que no depende del modelo juez: que cada tipo
tenga su criterio, que el prompt lleve las tres piezas que el juez necesita y
que el veredicto se lea bien, incluido el caso en que el juez no contesta lo
que se le pidio.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "experimentos"))

from criterios import (  # noqa: E402
    CRITERIOS,
    aplica,
    construir_prompt,
    interpretar_veredicto,
    justificacion,
)


def test_hay_criterio_para_los_dos_tipos_que_ragas_no_juzga():
    assert set(CRITERIOS) == {"premisa_falsa", "parcial"}
    assert aplica("parcial") and not aplica("literal")


def test_el_prompt_lleva_pregunta_referencia_respuesta_y_criterio():
    prompt = construir_prompt("parcial", "¿Qué es X y quién lo creó?",
                              "X es tal cosa. Su creador no aparece.", "X es tal cosa.")
    assert "¿Qué es X y quién lo creó?" in prompt
    assert "Su creador no aparece." in prompt
    assert "X es tal cosa." in prompt
    assert CRITERIOS["parcial"] in prompt


def test_el_criterio_parcial_acepta_formulaciones_equivalentes():
    """Regresion del 2026-10-23: el juez rechazo "no encontré información
    sobre X en los documentos" por no ser la frase literal de la referencia."""
    assert "formulación equivalente" in CRITERIOS["parcial"]
    assert "no encontré información" in CRITERIOS["parcial"]


def test_un_tipo_sin_criterio_es_un_error():
    with pytest.raises(ValueError):
        construir_prompt("literal", "p", "r", "x")


@pytest.mark.parametrize("texto, esperado", [
    ("SI\nCorrige la premisa.", True),
    ("Sí.\nLa rechaza.", True),
    ("si, porque la corrige", True),
    ("NO\nLa acepta.", False),
    ("No.", False),
    ("Quizás\nNo está claro.", None),
    ("", None),
])
def test_interpreta_el_veredicto(texto, esperado):
    assert interpretar_veredicto(texto) is esperado


def test_un_no_en_la_justificacion_no_cambia_un_si():
    """Solo cuenta la primera palabra: 'no aporta el dato' es parte del porqué."""
    assert interpretar_veredicto("SI\nNo aporta el dato del creador.") is True


def test_la_justificacion_es_lo_que_sigue_al_veredicto():
    assert justificacion("NO\nNombra a NVIDIA.") == "Nombra a NVIDIA."
    assert justificacion("SI") == ""
