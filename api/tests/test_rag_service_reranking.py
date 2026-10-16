"""Tests del reordenado de fragmentos.

Es la segunda mejora que el trabajo presenta como aportacion, y la que mas
propiedades AFIRMA en la memoria sin que hasta ahora las comprobara nadie. Lo
que se fija aqui es exactamente lo que el apartado 5.3 sostiene:

    1. el umbral se aplica ANTES de reordenar, de modo que la abstencion es la
       misma que la de la linea base **por construccion**,
    2. ante cualquier fallo del modelo se conserva el orden original: el
       reordenado nunca puede impedir una respuesta,
    3. no se pierde ningun fragmento recuperado, aunque el modelo omita
       numeros, repita o invente posiciones,
    4. se piden CANDIDATOS a la busqueda, no TOP_K: reordenar los mismos cinco
       fragmentos solo cambiaria su orden y hit@5 no podria moverse,
    5. al generador llegan como mucho TOP_K fragmentos, de manera que el
       contexto no crece.

Son tests de logica pura: sin red y sin coste. La verificacion de extremo a
extremo esta en `experimentos/ejecutar_dataset.py --configuracion reranking`.
"""
import contextlib
from types import SimpleNamespace

import pytest

from app.services import rag_service_reranking as mod
from app.services.rag_service import RELEVANCE_THRESHOLD, TOP_K
from app.services.rag_service_reranking import CANDIDATOS, RAGServiceReranking


def _doc(id_: str, score: float, texto: str = "contenido") -> SimpleNamespace:
    return SimpleNamespace(id=id_, score=score,
                           metadata={"document_name": "manual.pdf", "text": texto})


class _Cliente:
    """Doble del cliente de OpenAI. `texto=None` hace que la llamada falle."""

    def __init__(self, texto):
        self._texto = texto
        self.llamadas = 0
        self.chat = SimpleNamespace(
            completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        self.llamadas += 1
        if self._texto is None:
            raise RuntimeError("la API no responde")
        mensaje = SimpleNamespace(content=self._texto)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=mensaje)],
            usage=SimpleNamespace(prompt_tokens=4800, completion_tokens=22),
        )


def _servicio(texto_modelo, docs_base=None, tokens=5):
    svc = RAGServiceReranking.__new__(RAGServiceReranking)
    svc.client = _Cliente(texto_modelo)
    svc.top_k_pedido = []
    # La inicializa `generate_response`, que aqui no se invoca.
    svc.llamadas_auxiliares = []

    def _base(query, namespace, top_k=None):
        svc.top_k_pedido.append(top_k)
        return list(docs_base or []), tokens

    svc._recuperar_base = _base
    return svc


@pytest.fixture(autouse=True)
def _sin_observabilidad(monkeypatch):
    @contextlib.contextmanager
    def _paso(nombre, entrada=None):
        yield {}
    monkeypatch.setattr(mod.observabilidad, "paso", _paso)


@pytest.fixture(autouse=True)
def _super_parcheado(monkeypatch):
    monkeypatch.setattr(mod.RAGService, "_recuperar",
                        lambda self, q, ns, top_k=None: self._recuperar_base(q, ns, top_k))


# ── El umbral va antes, y por eso la abstencion no cambia ──────────────────

def test_si_ningun_candidato_supera_el_umbral_devuelve_vacio():
    """La propiedad que preserva la abstencion. Y no se llama al modelo: no
    tiene sentido pagar por reordenar lo que se va a descartar entero."""
    bajos = [_doc(f"c{i}", RELEVANCE_THRESHOLD - 0.01) for i in range(10)]
    svc = _servicio("0,1,2", bajos)

    docs, tokens = svc._recuperar("consulta ajena", "ns")

    assert docs == []
    assert tokens == 5, "los tokens del embedding se devuelven igualmente"
    assert svc.client.llamadas == 0, "no debe llamarse al modelo sin candidatos"


def test_el_umbral_filtra_antes_de_reordenar():
    """Un fragmento por debajo del umbral no puede aparecer en el resultado
    aunque el modelo lo coloque el primero."""
    docs = [_doc("bueno", 0.60), _doc("malo", 0.10), _doc("otro", 0.45)]
    svc = _servicio("0,1,2", docs)

    resultado, _ = svc._recuperar("x", "ns")

    assert [d.id for d in resultado] == ["bueno", "otro"]
    assert all(d.score >= RELEVANCE_THRESHOLD for d in resultado)


# ── El reordenado nunca impide una respuesta ───────────────────────────────

def test_si_el_modelo_falla_se_conserva_el_orden_original():
    docs = [_doc("a", 0.9), _doc("b", 0.8), _doc("c", 0.7)]
    svc = _servicio(None, docs)

    resultado, _ = svc._recuperar("x", "ns")
    assert [d.id for d in resultado] == ["a", "b", "c"]


def test_una_respuesta_ilegible_conserva_el_orden_original():
    docs = [_doc("a", 0.9), _doc("b", 0.8)]
    svc = _servicio("no he entendido la pregunta", docs)

    resultado, _ = svc._recuperar("x", "ns")
    assert [d.id for d in resultado] == ["a", "b"]


def test_un_solo_candidato_no_se_manda_a_reordenar():
    svc = _servicio("0", [_doc("unico", 0.9)])
    resultado, _ = svc._recuperar("x", "ns")

    assert [d.id for d in resultado] == ["unico"]
    assert svc.client.llamadas == 0, "con un solo fragmento no hay nada que ordenar"


# ── No se pierde ningun fragmento ──────────────────────────────────────────

def test_reordena_segun_lo_que_dice_el_modelo():
    docs = [_doc("a", 0.9), _doc("b", 0.8), _doc("c", 0.7)]
    svc = _servicio("2,0,1", docs)

    resultado, _ = svc._recuperar("x", "ns")
    assert [d.id for d in resultado] == ["c", "a", "b"]


def test_los_fragmentos_que_el_modelo_omite_van_al_final():
    """Si el modelo solo nombra dos de tres, el tercero no se pierde: se anade
    al final en su orden original."""
    docs = [_doc("a", 0.9), _doc("b", 0.8), _doc("c", 0.7)]
    svc = _servicio("2,0", docs)

    resultado, _ = svc._recuperar("x", "ns")
    assert [d.id for d in resultado] == ["c", "a", "b"]


def test_ignora_indices_repetidos_y_fuera_de_rango():
    docs = [_doc("a", 0.9), _doc("b", 0.8)]
    svc = _servicio("1, 1, 99, 0", docs)

    resultado, _ = svc._recuperar("x", "ns")
    assert [d.id for d in resultado] == ["b", "a"]


def test_tolera_el_formato_con_espacios_y_texto():
    docs = [_doc("a", 0.9), _doc("b", 0.8)]
    svc = _servicio("El orden es: 1, 0", docs)

    resultado, _ = svc._recuperar("x", "ns")
    assert [d.id for d in resultado] == ["b", "a"]


# ── Se ensancha la busqueda y se recorta el resultado ──────────────────────

def test_se_piden_CANDIDATOS_a_la_busqueda_no_TOP_K():
    """Reordenar los mismos TOP_K fragmentos solo cambiaria su orden: hit@5 no
    podria moverse. El reordenador solo aporta si antes hay de donde elegir."""
    svc = _servicio("0", [_doc("a", 0.9)])
    svc._recuperar("x", "ns")

    assert svc.top_k_pedido == [CANDIDATOS]
    assert CANDIDATOS > TOP_K


def test_al_generador_llegan_como_mucho_TOP_K_fragmentos():
    """El contexto no crece: es lo que distingue a esta mejora de la
    descomposicion, que si aumenta el numero de fragmentos enviados."""
    docs = [_doc(f"c{i}", 0.9 - i * 0.01) for i in range(CANDIDATOS)]
    orden = ",".join(str(i) for i in range(CANDIDATOS))
    svc = _servicio(orden, docs)

    resultado, _ = svc._recuperar("x", "ns")
    assert len(resultado) == TOP_K


# ── La llamada del reordenador se factura ──────────────────────────────────

def test_el_reordenado_queda_registrado_como_coste():
    """Es la llamada mas cara de las auxiliares: recibe los fragmentos
    candidatos completos, en torno a 5.000 tokens de entrada."""
    docs = [_doc("a", 0.9), _doc("b", 0.8)]
    svc = _servicio("1,0", docs)
    svc._recuperar("x", "ns")

    assert len(svc.llamadas_auxiliares) == 1
    anotada = svc.llamadas_auxiliares[0]
    assert anotada["operacion"] == "reordenado"
    assert anotada["tokens_entrada"] == 4800


def test_sin_candidatos_no_hay_coste_que_registrar():
    """Coherente con que tampoco se llame al modelo: si el umbral descarta
    todo, el reordenado no cuesta nada."""
    bajos = [_doc(f"c{i}", 0.10) for i in range(5)]
    svc = _servicio("0,1", bajos)
    svc._recuperar("x", "ns")

    assert svc.llamadas_auxiliares == []


def test_un_reordenado_fallido_no_registra_coste():
    docs = [_doc("a", 0.9), _doc("b", 0.8)]
    svc = _servicio(None, docs)
    svc._recuperar("x", "ns")

    assert svc.llamadas_auxiliares == []


def test_un_fragmento_mal_colocado_por_el_coseno_puede_entrar_en_los_cinco():
    """El caso que justifica toda la mejora: el fragmento util estaba en la
    posicion 12 por similitud coseno y el reordenador lo sube a la primera."""
    docs = [_doc(f"c{i}", 0.9 - i * 0.01) for i in range(CANDIDATOS)]
    svc = _servicio("12,0,1,2,3", docs)

    resultado, _ = svc._recuperar("x", "ns")
    assert resultado[0].id == "c12"
    assert len(resultado) == TOP_K
