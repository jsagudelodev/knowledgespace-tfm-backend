"""Tests del criterio de las preguntas compuestas (`experimentos/juez_compuestas.py`).

Se fija la parte que no depende del modelo juez: que el prompt lleve las dos
preguntas, el contexto y la respuesta, y que el veredicto se lea bien, incluido
el caso en que el juez no contesta en el formato pedido.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "experimentos"))

from juez_compuestas import construir_prompt, interpretar, responde_ambas  # noqa: E402


def test_el_prompt_lleva_las_dos_preguntas_el_contexto_numerado_y_la_respuesta():
    prompt = construir_prompt("que es un VAE", "que es la tokenizacion",
                              ["Un VAE codifica.", "Tokenizar es partir."], "Un VAE codifica.")
    assert "PREGUNTA A: que es un VAE" in prompt
    assert "PREGUNTA B: que es la tokenizacion" in prompt
    assert "[1] Un VAE codifica." in prompt and "[2] Tokenizar es partir." in prompt
    assert prompt.rstrip().endswith("MOTIVO: una frase")


def test_sin_contexto_el_prompt_lo_dice_en_vez_de_dejar_un_hueco():
    prompt = construir_prompt("a", "b", [], "No encontré información.")
    assert "ningún fragmento superó el umbral" in prompt


def test_lee_las_cuatro_lineas():
    v = interpretar("A: RESPONDE\nB: OMITE\nINVENTA: NO\nMOTIVO: No menciona la tokenización.")
    assert v == {"a": "responde", "b": "omite", "inventa": False,
                 "motivo": "No menciona la tokenización."}
    assert not responde_ambas(v)


def test_tolera_minusculas_tildes_y_negritas():
    v = interpretar("**A:** responde\n**B:** abstiene\n**INVENTA:** SÍ\n**MOTIVO:** Añade un dato.")
    assert (v["a"], v["b"], v["inventa"]) == ("responde", "abstiene", True)


def test_un_campo_ilegible_queda_en_none_en_vez_de_adivinarse():
    v = interpretar("A: QUIZAS\nB: RESPONDE\nMOTIVO: dudoso")
    assert v["a"] is None and v["b"] == "responde" and v["inventa"] is None
    assert not responde_ambas(v)


def test_responde_ambas_exige_las_dos_partes():
    assert responde_ambas({"a": "responde", "b": "responde"})
    assert not responde_ambas({"a": "responde", "b": "abstiene"})
