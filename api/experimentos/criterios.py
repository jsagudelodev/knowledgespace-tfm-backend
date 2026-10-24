"""Criterios si/no para los tipos de pregunta que RAGAS no sabe juzgar.

RAGAS mide si la respuesta se apoya en el contexto (faithfulness) y si contesta
la pregunta (answer_relevancy), pero no sabe si una respuesta **corrige una
premisa falsa** o si **se abstiene en la parte de la pregunta que el corpus no
cubre**. Una respuesta puede ser fiel al contexto y aun asi aceptar la premisa,
o añadir de memoria el dato que falta. Esos dos fallos son los que miden los
tipos `premisa_falsa` y `parcial` del dataset.

Para cada uno hay un criterio: una pregunta concreta al modelo juez, que
responde SI o NO con una frase de justificacion. Se escribe aqui y no con la
metrica generica de RAGAS para que el criterio quede a la vista, se pueda
probar sin llamar a la API y no dependa de como cambie RAGAS entre versiones.

El modulo no importa nada pesado: lo usa `evaluar_ragas.py` desde `.venv-eval`
y lo prueban los tests desde el entorno de la aplicacion.
"""
from __future__ import annotations

import re
from typing import Dict, Optional

# Una pregunta por tipo. La referencia describe la respuesta correcta: en
# `premisa_falsa` contiene la correccion, y en `parcial`, la frase que dice que
# parte no esta en la documentacion. Por eso el juez la recibe siempre.
CRITERIOS: Dict[str, str] = {
    "premisa_falsa": (
        "La PREGUNTA contiene una premisa falsa, y la RESPUESTA DE REFERENCIA "
        "la corrige. ¿La RESPUESTA EVALUADA rechaza o corrige explícitamente esa "
        "premisa, en lugar de aceptarla y construir la explicación sobre ella?"
    ),
    # La primera version exigia, sin decirlo, la formula literal de la
    # referencia, y el juez rechazo respuestas correctas que decian "no
    # encontre informacion sobre X en los documentos de la empresa" (P25 y
    # P27, 2026-10-23). Por eso el criterio nombra ahora las formulaciones
    # equivalentes y separa las dos condiciones.
    "parcial": (
        "La PREGUNTA tiene dos partes, y la RESPUESTA DE REFERENCIA indica cuál "
        "de ellas no aparece en la documentación disponible. La RESPUESTA "
        "EVALUADA cumple si se dan las dos condiciones: (1) responde la parte "
        "que sí está en la documentación, y (2) sobre la otra parte dice que no "
        "tiene la información, con cualquier formulación equivalente (por "
        "ejemplo, «no encontré información sobre X en los documentos» o «X no "
        "aparece en la documentación»), SIN aportar ese dato por su cuenta (un "
        "nombre, una empresa o una fecha). Si aporta el dato, no cumple aunque "
        "el dato sea cierto. ¿Cumple las dos condiciones?"
    ),
}

PLANTILLA = """Eres un evaluador estricto de un sistema de preguntas y respuestas.

PREGUNTA:
{pregunta}

RESPUESTA DE REFERENCIA (la correcta):
{referencia}

RESPUESTA EVALUADA:
{respuesta}

CRITERIO:
{criterio}

Contesta en la primera línea solo SI o NO. En la segunda línea, siempre, una frase que lo justifique."""


def aplica(tipo: str) -> bool:
    return tipo in CRITERIOS


def construir_prompt(tipo: str, pregunta: str, referencia: str, respuesta: str) -> str:
    if tipo not in CRITERIOS:
        raise ValueError(f"No hay criterio para el tipo '{tipo}'")
    return PLANTILLA.format(
        pregunta=pregunta.strip(),
        referencia=referencia.strip(),
        respuesta=respuesta.strip(),
        criterio=CRITERIOS[tipo],
    )


def interpretar_veredicto(texto: str) -> Optional[bool]:
    """SI -> True, NO -> False; cualquier otra cosa -> None.

    Solo cuenta la primera palabra de la primera linea. Un veredicto ilegible
    se devuelve como None en vez de adivinarlo: se informa aparte y no entra
    en la tasa, para no inflarla ni hundirla con un fallo del juez.
    """
    primera = (texto or "").strip().splitlines()[0] if (texto or "").strip() else ""
    palabra = re.sub(r"[^a-záéíóú]", "", primera.split()[0].lower()) if primera.split() else ""
    if palabra in ("si", "sí"):
        return True
    if palabra == "no":
        return False
    return None


def justificacion(texto: str) -> str:
    lineas = [ln.strip() for ln in (texto or "").strip().splitlines() if ln.strip()]
    return " ".join(lineas[1:]) if len(lineas) > 1 else ""
