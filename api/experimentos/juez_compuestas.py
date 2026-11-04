"""Criterio para juzgar la respuesta a una pregunta compuesta (EXP-13, parte B).

Una pregunta compuesta une dos preguntas en un mismo mensaje. Lo que importa
de la respuesta no es una nota global sino **qué hace con cada parte**: si la
contesta, si dice que no tiene información o si la ignora. Una respuesta que
desarrolla bien la primera y no menciona la segunda parece completa y no lo
es, y ese es justo el fallo que la descomposición pretende corregir.

Por eso el juez clasifica cada parte por separado, y aparte dice si la
respuesta afirma algo que no está en el contexto que recibió el sistema.

    RESPONDE   la contesta
    ABSTIENE   dice que no tiene información sobre ella
    OMITE      no la menciona

Como `criterios.py`, el módulo no importa nada pesado y se prueba sin llamar a
la API.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Dict, List, Optional

TRATAMIENTOS = ("responde", "abstiene", "omite")

PLANTILLA = """Eres un evaluador estricto de un sistema de preguntas y respuestas.
El sistema solo debe responder con la información del CONTEXTO que recibe.

El usuario hizo dos preguntas en un mismo mensaje:
PREGUNTA A: {a}
PREGUNTA B: {b}

CONTEXTO que recibió el sistema:
{contexto}

RESPUESTA DEL SISTEMA:
{respuesta}

Para cada pregunta, indica cómo la trata la respuesta:
- RESPONDE: la contesta.
- ABSTIENE: dice que no tiene información sobre ella.
- OMITE: no la menciona.

Indica además si la respuesta INVENTA, es decir, si afirma algo que no está en el CONTEXTO.

Contesta exactamente con estas cuatro líneas:
A: RESPONDE, ABSTIENE u OMITE
B: RESPONDE, ABSTIENE u OMITE
INVENTA: SI o NO
MOTIVO: una frase"""


def construir_prompt(a: str, b: str, contextos: List[str], respuesta: str) -> str:
    # Numerados para que el juez pueda distinguir los fragmentos; sin contexto
    # se dice expresamente, porque un bloque vacío se puede leer como un error.
    contexto = "\n\n".join(f"[{i}] {c.strip()}" for i, c in enumerate(contextos, start=1))
    return PLANTILLA.format(
        a=a.strip(), b=b.strip(),
        contexto=contexto or "(ningún fragmento superó el umbral de relevancia)",
        respuesta=respuesta.strip(),
    )


def _sin_tildes(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto)
                   if unicodedata.category(c) != "Mn").lower()


def _campo(texto: str, nombre: str) -> Optional[str]:
    m = re.search(rf"^\s*\**{nombre}\**\s*:\s*\**\s*([a-z]+)", texto, re.M)
    return m.group(1) if m else None


def interpretar(texto: str) -> Dict[str, object]:
    """Lee las cuatro líneas del juez.

    Un campo ilegible se devuelve como None, igual que en `criterios.py`: se
    cuenta aparte en vez de adivinarlo, para no inflar ni hundir la tasa con
    un fallo del juez.
    """
    plano = _sin_tildes(texto or "")
    a, b = _campo(plano, "a"), _campo(plano, "b")
    inventa = _campo(plano, "inventa")
    motivo = re.search(r"^\s*\**motivo\**\s*:\s*(.+)$", texto or "", re.M | re.I)
    return {
        "a": a if a in TRATAMIENTOS else None,
        "b": b if b in TRATAMIENTOS else None,
        "inventa": {"si": True, "no": False}.get(inventa),
        "motivo": motivo.group(1).strip() if motivo else "",
    }


def responde_ambas(veredicto: Dict[str, object]) -> bool:
    return veredicto["a"] == "responde" and veredicto["b"] == "responde"
