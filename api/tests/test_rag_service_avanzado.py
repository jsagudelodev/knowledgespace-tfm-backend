"""Tests de la descomposicion de consultas.

Es la primera de las dos mejoras que el trabajo presenta como aportacion
—cobertura conjunta del 48 % al 88 % sobre preguntas compuestas— y hasta ahora
no la cubria ninguna prueba.

Lo que se fija aqui son las propiedades que la memoria AFIRMA, no el detalle de
la implementacion:

    1. ante cualquier fallo del modelo se recupera como la linea base: la
       mejora nunca puede convertirse en un punto de fallo,
    2. una descomposicion vacia o excesiva se descarta,
    3. con una sola subpregunta el comportamiento es identico al de la base,
    4. al fusionar no se pierde ningun fragmento ni se duplica ninguno, y cada
       uno conserva su MEJOR puntuacion,
    5. los tokens de todas las subpreguntas se suman.

Son tests de logica pura: el cliente de OpenAI y la recuperacion de la clase
base se sustituyen por dobles, de modo que no hay red, no cuestan nada y corren
en milisegundos. La verificacion de extremo a extremo contra el indice real
esta en `experimentos/medir_preguntas_compuestas.py`.
"""
from types import SimpleNamespace

import pytest

from app.services import rag_service_avanzado as mod
from app.services.rag_service_avanzado import MAX_SUBPREGUNTAS, RAGServiceAvanzado


def _doc(id_: str, score: float) -> SimpleNamespace:
    return SimpleNamespace(id=id_, score=score,
                           metadata={"document_name": "manual.pdf", "text": "contenido"})


class _ClienteQueResponde:
    """Doble del cliente de OpenAI que devuelve un texto fijo."""

    def __init__(self, texto):
        self._texto = texto
        self.llamadas = 0

        completions = SimpleNamespace(create=self._create)
        self.chat = SimpleNamespace(completions=completions)

    def _create(self, **kwargs):
        self.llamadas += 1
        mensaje = SimpleNamespace(content=self._texto)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=mensaje)],
            usage=SimpleNamespace(prompt_tokens=120, completion_tokens=18),
        )


class _ClienteQueFalla:
    def __init__(self):
        def _create(**kwargs):
            raise RuntimeError("la API no responde")
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=_create))


def _servicio(cliente, recuperaciones=None):
    """Construye el servicio sin tocar `__init__`, que abriria conexiones.

    `recuperaciones` es un diccionario {consulta: (docs, tokens)} con el que se
    sustituye la recuperacion de la clase base.
    """
    svc = RAGServiceAvanzado.__new__(RAGServiceAvanzado)
    svc.client = cliente
    # La inicializa `generate_response`, que aqui no se invoca.
    svc.llamadas_auxiliares = []

    llamadas = []

    def _base(query, namespace, top_k=None):
        llamadas.append(query)
        return recuperaciones.get(query, ([], 0))

    svc._recuperar_base = _base
    svc.llamadas_base = llamadas
    return svc




def _parchear_super(monkeypatch, svc):
    """Redirige `RAGService._recuperar` al doble del servicio."""
    monkeypatch.setattr(mod.RAGService, "_recuperar",
                        lambda self, q, ns, top_k=None: self._recuperar_base(q, ns, top_k))


# ── La descomposicion nunca puede impedir una respuesta ─────────────────────

def test_si_el_modelo_falla_se_usa_la_consulta_original(monkeypatch):
    """Es la propiedad mas importante: la mejora no puede ser un punto de fallo."""
    svc = _servicio(_ClienteQueFalla())
    assert svc._descomponer("que es un VAE y que es la geometria semantica") == [
        "que es un VAE y que es la geometria semantica"
    ]


def test_una_descomposicion_vacia_se_descarta():
    svc = _servicio(_ClienteQueResponde("   \n  \n "))
    assert svc._descomponer("una pregunta") == ["una pregunta"]


def test_una_descomposicion_excesiva_se_descarta():
    """Mas de MAX_SUBPREGUNTAS indica que el modelo esta desmenuzando matices
    en vez de separar temas, y cada una anade contexto que se paga."""
    demasiadas = "\n".join(f"pregunta {i}" for i in range(MAX_SUBPREGUNTAS + 1))
    svc = _servicio(_ClienteQueResponde(demasiadas))
    assert svc._descomponer("una pregunta") == ["una pregunta"]


def test_el_limite_exacto_de_subpreguntas_se_acepta():
    justas = "\n".join(f"pregunta {i}" for i in range(MAX_SUBPREGUNTAS))
    svc = _servicio(_ClienteQueResponde(justas))
    assert len(svc._descomponer("una pregunta")) == MAX_SUBPREGUNTAS


def test_las_lineas_en_blanco_no_cuentan_como_subpreguntas():
    svc = _servicio(_ClienteQueResponde("que es un VAE\n\n  \nque es una GAN\n"))
    assert svc._descomponer("x") == ["que es un VAE", "que es una GAN"]


# ── Con una sola subpregunta, el comportamiento es el de la base ────────────

def test_una_sola_subpregunta_delega_en_la_clase_base(monkeypatch):
    """La memoria afirma que ante una consulta simple ambas configuraciones
    devuelven lo mismo. Aqui se fija que solo se hace UNA busqueda, y con el
    texto que devolvio el descompositor."""
    docs = [_doc("c1", 0.7), _doc("c2", 0.5)]
    svc = _servicio(_ClienteQueResponde("que es la similitud coseno"),
                    {"que es la similitud coseno": (docs, 11)})
    _parchear_super(monkeypatch, svc)

    resultado, tokens = svc._recuperar("que es la similitud coseno", "ns")

    assert resultado == docs
    assert tokens == 11
    assert svc.llamadas_base == ["que es la similitud coseno"]


# ── La fusion no pierde ni duplica ──────────────────────────────────────────

def test_fusiona_sin_duplicar_y_conserva_la_mejor_puntuacion(monkeypatch):
    """Un mismo fragmento puede aparecer en varias busquedas. Se conserva una
    sola vez y con la puntuacion MAS ALTA, porque es la que refleja su
    relevancia maxima para el conjunto de la consulta."""
    svc = _servicio(
        _ClienteQueResponde("que es un VAE\nque es la geometria semantica"),
        {
            "que es un VAE": ([_doc("a", 0.60), _doc("compartido", 0.40)], 7),
            "que es la geometria semantica": ([_doc("b", 0.55), _doc("compartido", 0.80)], 9),
        },
    )
    _parchear_super(monkeypatch, svc)

    docs, tokens = svc._recuperar("que es un VAE y que es la geometria semantica", "ns")

    assert [d.id for d in docs] == ["compartido", "a", "b"]
    assert docs[0].score == 0.80, "debe conservarse la mejor puntuacion, no la primera"
    assert len({d.id for d in docs}) == len(docs), "no puede haber duplicados"


def test_suma_los_tokens_de_todas_las_subpreguntas(monkeypatch):
    """Cada subpregunta se vectoriza por separado y todas se facturan."""
    svc = _servicio(
        _ClienteQueResponde("primera\nsegunda"),
        {"primera": ([_doc("a", 0.5)], 7), "segunda": ([_doc("b", 0.5)], 9)},
    )
    _parchear_super(monkeypatch, svc)

    _, tokens = svc._recuperar("primera y segunda", "ns")
    assert tokens == 16


# ── La llamada del descompositor se factura ────────────────────────────────

def test_la_descomposicion_queda_registrada_como_coste():
    """Es una llamada de pago al modelo dentro de una funcionalidad que el
    trabajo presenta como aportacion. Un registro de costes incompleto no es
    un registro de costes."""
    svc = _servicio(_ClienteQueResponde("primera\nsegunda"))
    svc._descomponer("primera y segunda")

    assert len(svc.llamadas_auxiliares) == 1
    anotada = svc.llamadas_auxiliares[0]
    assert anotada["operacion"] == "descomposicion"
    assert anotada["tokens_entrada"] == 120
    assert anotada["tokens_salida"] == 18


def test_una_descomposicion_fallida_no_registra_coste():
    """Si la llamada no llego a completarse no hay nada que facturar."""
    svc = _servicio(_ClienteQueFalla())
    svc._descomponer("x")
    assert svc.llamadas_auxiliares == []


def test_se_busca_una_vez_por_subpregunta(monkeypatch):
    """Es el nucleo de la mejora: cada subpregunta se vectoriza por separado,
    que es precisamente lo que el pipeline base no hace."""
    svc = _servicio(
        _ClienteQueResponde("primera\nsegunda\ntercera"),
        {"primera": ([], 1), "segunda": ([], 1), "tercera": ([], 1)},
    )
    _parchear_super(monkeypatch, svc)

    svc._recuperar("todo junto", "ns")
    assert svc.llamadas_base == ["primera", "segunda", "tercera"]
