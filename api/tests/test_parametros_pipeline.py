"""Tests de los parametros del pipeline.

Los siete parametros que gobiernan la recuperacion y la generacion salen de
`settings`, de modo que se ajustan por variable de entorno sin tocar codigo.
Antes eran constantes de modulo: probar otro umbral exigia editar un fichero y
redesplegar, lo que en la practica significaba que nadie los probaba.

Lo que se fija aqui es doble:

    1. que los nombres de modulo --los que citan los experimentos y el
       capitulo 5-- sigan reflejando lo que dice la configuracion, para que no
       puedan divergir en silencio,
    2. que los valores por defecto sean los que midieron los experimentos.
       Cambiar uno invalida las cifras de la memoria, asi que debe ser
       deliberado y no un descuido.
"""
from app.core.config import settings
from app.services.rag_service import (
    DEFAULT_TEMPERATURE,
    MAX_RESPONSE_TOKENS,
    RELEVANCE_THRESHOLD,
    TOP_K,
)
from app.services.rag_service_avanzado import MAX_SUBPREGUNTAS
from app.services.rag_service_reranking import CANDIDATOS
from app.services.reordenador import RECORTE

# ── Los nombres de modulo reflejan la configuracion ────────────────────────

def test_los_parametros_salen_de_la_configuracion():
    """Si alguien vuelve a escribir un valor a mano en un servicio, la
    variable de entorno dejaria de tener efecto sin que nada avisara."""
    assert RELEVANCE_THRESHOLD == settings.RAG_UMBRAL_RELEVANCIA
    assert TOP_K == settings.RAG_TOP_K
    assert MAX_RESPONSE_TOKENS == settings.RAG_MAX_TOKENS_RESPUESTA
    assert DEFAULT_TEMPERATURE == settings.RAG_TEMPERATURA
    assert MAX_SUBPREGUNTAS == settings.RAG_MAX_SUBPREGUNTAS
    assert CANDIDATOS == settings.RAG_CANDIDATOS_REORDENADO
    assert RECORTE == settings.RAG_RECORTE_REORDENADO


# ── Los valores por defecto son los que se midieron ────────────────────────

def test_el_umbral_es_el_medido():
    """0,30 cae en la banda vacia entre el ruido maximo de una consulta ajena
    (0,258) y la senal minima de un fragmento legitimo (0,393), medidos el
    2026-10-09. Cambiarlo obliga a repetir esa medicion."""
    assert RELEVANCE_THRESHOLD == 0.30


def test_la_temperatura_es_cero():
    """Un sistema que debe responder solo con el contexto recibido no redacta
    con margen creativo. Medido: la fidelidad pasa de 0,888 a 0,939."""
    assert DEFAULT_TEMPERATURE == 0.0


def test_top_k_es_cinco():
    """Es el numero sobre el que se calcularon hit@k, MRR y el coste por
    consulta de todo el capitulo 5."""
    assert TOP_K == 5


def test_el_reordenador_pide_mas_candidatos_de_los_que_conserva():
    """Reordenar los mismos TOP_K fragmentos solo cambiaria su orden: hit@5 no
    podria moverse porque serian los mismos documentos."""
    assert CANDIDATOS > TOP_K


def test_el_reordenador_ve_el_fragmento_completo():
    """Con 400 caracteres --el 40 % del texto-- descartaba el fragmento que
    permitia responder y conservaba otro que solo contenia la frase ancla. El
    indice guarda 1.000 caracteres por fragmento."""
    assert RECORTE >= 1000


# ── Coherencia entre parametros ────────────────────────────────────────────

def test_el_umbral_esta_en_un_rango_que_tiene_sentido():
    """Una similitud coseno vive entre -1 y 1, y en este corpus las legitimas
    rondan 0,4-0,7. Un umbral fuera de ahi delata una errata."""
    assert 0.0 < RELEVANCE_THRESHOLD < 1.0


def test_la_temperatura_esta_en_el_rango_que_admite_el_proveedor():
    assert 0.0 <= DEFAULT_TEMPERATURE <= 2.0


def test_los_enteros_son_positivos():
    for nombre, valor in (("TOP_K", TOP_K),
                          ("MAX_RESPONSE_TOKENS", MAX_RESPONSE_TOKENS),
                          ("MAX_SUBPREGUNTAS", MAX_SUBPREGUNTAS),
                          ("CANDIDATOS", CANDIDATOS),
                          ("RECORTE", RECORTE)):
        assert valor > 0, f"{nombre} no puede ser {valor}"
