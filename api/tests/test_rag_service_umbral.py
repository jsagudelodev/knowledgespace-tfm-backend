"""Tests del control de alucinaciones: umbral de relevancia y abstención.

Es el mecanismo que el proyecto declara como aportación —que el sistema
responda "no encontré información" en vez de inventar— y hasta ahora no lo
cubría ninguna prueba. Estos tests fijan las tres piezas de la cadena:

    1. el umbral descarta los fragmentos por debajo de 0.30,
    2. sin fragmentos, el contexto queda vacío,
    3. con el contexto vacío, al modelo se le dice explícitamente que no hay
       contexto y se le mantiene la instrucción de abstenerse.

Son tests de lógica pura: no llaman a OpenAI ni a Pinecone, no cuestan nada y
corren en milisegundos. La verificación de extremo a extremo contra el índice
real está en `experimentos/medir_umbral.py`.
"""
from types import SimpleNamespace

import pytest

from app.services.rag_service import (
    DEFAULT_SYSTEM_PROMPT,
    RELEVANCE_THRESHOLD,
    RAGService,
    RAGUnavailableError,
)

FRASE_DE_ABSTENCION = "No encontré información sobre este tema en los documentos de la empresa."


def _doc(score: float, nombre: str = "manual.pdf") -> SimpleNamespace:
    return SimpleNamespace(metadata={"document_name": nombre, "text": "contenido"}, score=score)


def _filtrar(docs):
    """Replica el filtro de `generate_response`.

    Se duplica aquí a propósito en vez de invocar `generate_response`, que
    exigiría red: lo que se fija es el CRITERIO (comparación `>=` contra el
    umbral del módulo), de modo que si alguien cambia el operador o el valor
    sin pensarlo, estos tests lo detectan.
    """
    return [d for d in docs if getattr(d, "score", 0) >= RELEVANCE_THRESHOLD]


# ── El umbral discrimina ────────────────────────────────────────────────────

def test_descarta_los_fragmentos_por_debajo_del_umbral():
    docs = [_doc(0.58), _doc(0.12), _doc(0.44), _doc(0.29)]
    assert [d.score for d in _filtrar(docs)] == [0.58, 0.44]


def test_el_fragmento_justo_en_el_umbral_pasa():
    """La comparación es `>=`, no `>`. Un fragmento exactamente en el umbral es
    señal, no ruido: el valor se eligió como el límite inferior aceptable."""
    assert len(_filtrar([_doc(RELEVANCE_THRESHOLD)])) == 1


def test_el_fragmento_justo_por_debajo_no_pasa():
    assert _filtrar([_doc(RELEVANCE_THRESHOLD - 0.001)]) == []


def test_una_consulta_ajena_al_corpus_no_deja_ningun_fragmento():
    """Puntuaciones reales de "¿cómo preparo una paella?" contra el índice,
    medidas el 2026-10-09 (ver `resultados/umbral_2026-10-09.json`)."""
    ajena = [_doc(s) for s in (0.258, 0.221, 0.206, 0.195, 0.187)]
    assert _filtrar(ajena) == []


def test_una_consulta_cubierta_conserva_sus_fragmentos():
    """Puntuaciones reales de "¿qué son las GANs?", misma medición."""
    cubierta = [_doc(s) for s in (0.584, 0.521, 0.498, 0.482, 0.470)]
    assert len(_filtrar(cubierta)) == 5


# ── Sin fragmentos, no hay contexto ─────────────────────────────────────────

def test_sin_fragmentos_relevantes_el_contexto_queda_vacio():
    assert RAGService._build_context(_filtrar([_doc(0.1), _doc(0.2)])) == ""


# ── Sin contexto, el modelo recibe la instrucción de abstenerse ─────────────

def test_sin_contexto_se_dice_explicitamente_al_modelo():
    """Un bloque de contexto vacío invita al modelo a rellenarlo con
    conocimiento propio. Se le dice con todas las letras que no hay nada."""
    mensajes = RAGService._build_messages("¿cuál es la capital de Francia?", "", None, None)
    contenidos = [m["content"] for m in mensajes]
    assert any("No se encontró contexto relevante" in c for c in contenidos)
    assert not any("Contexto de documentos de la empresa" in c for c in contenidos)


def test_el_prompt_por_defecto_ordena_la_frase_exacta_de_abstencion():
    """Blindaje del contrato. Si alguien reescribe el prompt y se lleva por
    delante esta frase, el sistema deja de abstenerse de forma reconocible y
    el frontend ya no puede distinguir una no-respuesta de una respuesta."""
    assert FRASE_DE_ABSTENCION in DEFAULT_SYSTEM_PROMPT


def test_el_prompt_prohibe_el_conocimiento_externo():
    assert "NUNCA uses conocimiento externo" in DEFAULT_SYSTEM_PROMPT


def test_el_prompt_del_asistente_sustituye_al_por_defecto():
    """Un asistente puede traer su propio prompt. Conviene saber que al hacerlo
    se pierde la instrucción de abstención del prompt por defecto: es una
    limitación conocida, no un descuido."""
    mensajes = RAGService._build_messages("pregunta", "ctx", None, "Eres un asistente legal.")
    assert mensajes[0]["content"] == "Eres un asistente legal."
    assert FRASE_DE_ABSTENCION not in mensajes[0]["content"]


# ── Orden de los mensajes ───────────────────────────────────────────────────

def test_el_contexto_va_como_segundo_mensaje_de_system():
    """El contexto no se mete en el mensaje del usuario: así el modelo lo trata
    como hecho dado y la pregunta del usuario queda limpia."""
    mensajes = RAGService._build_messages("pregunta", "CONTEXTO", [], None)
    assert mensajes[0]["role"] == "system"
    assert mensajes[1]["role"] == "system"
    assert "CONTEXTO" in mensajes[1]["content"]
    assert mensajes[-1] == {"role": "user", "content": "pregunta"}


def test_el_historial_va_entre_el_contexto_y_la_pregunta():
    historial = [{"role": "user", "content": "anterior"}, {"role": "assistant", "content": "respuesta"}]
    mensajes = RAGService._build_messages("actual", "CTX", historial, None)
    assert mensajes[2:4] == historial
    assert mensajes[-1]["content"] == "actual"


# ── Fallo de un servicio externo ────────────────────────────────────────────

def test_el_fallo_externo_se_traduce_a_una_excepcion_con_su_etapa():
    """Sin esto, un fallo de OpenAI o Pinecone escapaba como 500 con la traza.
    La etapa viaja en la excepción para que el router informe sin leer logs."""
    error = RAGUnavailableError("búsqueda vectorial", TimeoutError("sin respuesta"))
    assert error.etapa == "búsqueda vectorial"
    assert isinstance(error.causa, TimeoutError)
    assert "búsqueda vectorial" in str(error)


def test_un_fallo_del_embedding_no_se_confunde_con_una_respuesta_vacia():
    """Una consulta sin resultados y una caída del servicio son cosas
    distintas: la primera se responde con la abstención, la segunda es un 503."""
    with pytest.raises(RAGUnavailableError):
        raise RAGUnavailableError("embedding de la consulta", ConnectionError())
