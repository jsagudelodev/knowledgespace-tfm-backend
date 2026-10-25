"""Tests de `app/services/alcance_global.py`.

Es el filtro que evita que preguntas de alcance ("¿qué documentos tienes?")
pasen por el RAG normal -donde se verificó que alucinan, ver el docstring del
módulo-. Lo que se fija:

    1. las frases de alcance real SÍ activan el filtro,
    2. preguntas de contenido parecidas, pero NO de alcance, no lo activan
       -el caso que de verdad importa: un falso positivo aquí convierte una
       pregunta real en una lista de nombres de archivo-,
    3. la respuesta se arma solo con documentos `completed`, nunca inventa
       nada que no esté en la base de datos.

Son tests de lógica pura: el repositorio se sustituye por un doble.
"""
from types import SimpleNamespace

from app.services.alcance_global import es_pregunta_de_alcance_global, responder_alcance_global


def _doc(nombre: str, status: str = "completed") -> SimpleNamespace:
    return SimpleNamespace(original_filename=nombre, status=status)


class _RepoFalso:
    def __init__(self, por_asistente=None, por_empresa=None):
        self._por_asistente = por_asistente or {}
        self._por_empresa = por_empresa or {}

    def get_by_assistant(self, assistant_id):
        return self._por_asistente.get(assistant_id, [])

    def get_by_company(self, company_id):
        return self._por_empresa.get(company_id, [])


def _responder(monkeypatch, repo, company_id=8, assistant_id=None):
    import app.services.alcance_global as mod
    monkeypatch.setattr(mod, "DocumentRepository", lambda db: repo)
    return responder_alcance_global(db=None, company_id=company_id, assistant_id=assistant_id)


# ── El filtro SÍ se activa con las frases de alcance ────────────────────────

def test_reconoce_las_frases_de_alcance_tal_como_se_verificaron_en_el_bug():
    # Las tres preguntas exactas que se probaron contra el corpus real.
    assert es_pregunta_de_alcance_global("¿Qué documentos tienes?")
    assert es_pregunta_de_alcance_global("¿Qué temas puedo consultar?")
    assert es_pregunta_de_alcance_global("¿De qué trata la documentación disponible?")


def test_reconoce_variantes_razonables():
    assert es_pregunta_de_alcance_global("¿Cuántos documentos tienes?")
    assert es_pregunta_de_alcance_global("¿Qué información tienes?")
    assert es_pregunta_de_alcance_global("Resume todo lo que sabes")
    assert es_pregunta_de_alcance_global("  ¿qué documentos hay?  ")  # espacios sueltos
    assert es_pregunta_de_alcance_global("¿QUÉ DOCUMENTOS TIENES?")  # mayúsculas


# ── El filtro NO se activa ante preguntas de contenido parecidas ───────────

def test_no_se_activa_con_una_pregunta_de_contenido_con_palabras_parecidas():
    """Es el caso que de verdad importa: confundir esto con alcance global
    convertiría una pregunta real en una lista de nombres de archivo."""
    assert not es_pregunta_de_alcance_global("¿Qué documentos necesito para entender VAEs?")
    assert not es_pregunta_de_alcance_global("¿Qué temas trata el VAE?")
    assert not es_pregunta_de_alcance_global("¿De qué trata el paper de difusión?")
    assert not es_pregunta_de_alcance_global("¿Qué es un documento RAG?")


def test_no_se_activa_con_preguntas_normales_del_dataset():
    assert not es_pregunta_de_alcance_global("¿Qué es un agente de IA?")
    assert not es_pregunta_de_alcance_global("¿Qué es la similitud coseno?")


# ── La respuesta se arma solo con metadatos reales ─────────────────────────

def test_lista_solo_los_documentos_completados(monkeypatch):
    repo = _RepoFalso(por_asistente={
        2: [_doc("a.pdf"), _doc("b.pdf", status="processing"), _doc("c.pdf", status="failed")],
    })
    respuesta = _responder(monkeypatch, repo, assistant_id=2)

    assert "a.pdf" in respuesta
    assert "b.pdf" not in respuesta
    assert "c.pdf" not in respuesta
    assert "1 documento" in respuesta


def test_usa_la_empresa_cuando_no_hay_asistente(monkeypatch):
    repo = _RepoFalso(por_empresa={8: [_doc("x.pdf"), _doc("y.pdf")]})
    respuesta = _responder(monkeypatch, repo, company_id=8, assistant_id=None)

    assert "x.pdf" in respuesta and "y.pdf" in respuesta
    assert "2 documentos" in respuesta


def test_sin_documentos_no_inventa_nada(monkeypatch):
    repo = _RepoFalso(por_asistente={2: []})
    respuesta = _responder(monkeypatch, repo, assistant_id=2)

    assert respuesta == "Todavía no hay documentos disponibles para consultar."


def test_no_duplica_nombres_repetidos(monkeypatch):
    repo = _RepoFalso(por_asistente={2: [_doc("a.pdf"), _doc("a.pdf")]})
    respuesta = _responder(monkeypatch, repo, assistant_id=2)

    assert "1 documento" in respuesta
