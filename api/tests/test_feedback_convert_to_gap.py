"""Tests de `FeedbackRepository.convert_to_gap` — el fallo real encontrado el
2026-10-26 revisando producción: "hola" estaba duplicado 11 veces en
`knowledge_gaps`, y había tres pares de duplicados exactos (mismo texto, con
minutos o segundos de diferencia), porque `convert_to_gap` creaba una fila
nueva siempre, sin comprobar si ya existía una pregunta igual abierta.

Lo que se fija aquí:

    1. una pregunta con el texto EXACTO (normalizado) de un gap ya abierto no
       crea una fila nueva: suma 1 a `volume` del que ya existe,
    2. espacios/saltos de línea y mayúsculas no cuentan como pregunta distinta
       -el caso real: "Evolución Arquitectónica y Modelos\nGenerativos" vs la
       misma frase sin el salto de línea-,
    3. una pregunta de verdad distinta sí crea su propio gap,
    4. un gap ya resuelto o ignorado no absorbe una pregunta nueva en
       silencio: debe volver a abrirse como caso propio.

Son tests de lógica pura: `Session` se sustituye por un doble que imita
`query().filter().all()`, `add`, `flush`, `commit`, `refresh`.
"""
from types import SimpleNamespace

from app.repositories.feedback_repository import FeedbackRepository


def _gap_existente(id_, question, status="open", volume=1, assistant_id=None):
    return SimpleNamespace(id=id_, question=question, status=status, volume=volume, assistant_id=assistant_id)


def _feedback(assistant_id=None, widget_id=None, message=None):
    return SimpleNamespace(
        assistant_id=assistant_id, widget_id=widget_id, message=message,
        knowledge_gap_id=None, status="pending",
    )


class _QueryFalsa:
    def __init__(self, resultados, filtros_capturados):
        self._resultados = resultados
        self._filtros_capturados = filtros_capturados

    def filter(self, *args, **kwargs):
        self._filtros_capturados.extend(args)
        return self

    def all(self):
        return self._resultados


class _DBFalsa:
    def __init__(self, gaps_existentes=None):
        self._gaps_existentes = gaps_existentes or []
        self.agregados = []
        self.filtros_capturados = []

    def query(self, modelo):
        return _QueryFalsa(self._gaps_existentes, self.filtros_capturados)

    def add(self, obj):
        self.agregados.append(obj)

    def flush(self):
        pass

    def commit(self):
        pass

    def refresh(self, obj):
        pass


# ── El caso real: texto exacto repetido no crea una fila nueva ────────────

def test_una_pregunta_igual_a_un_gap_abierto_suma_volumen_en_vez_de_duplicar():
    existente = _gap_existente(1, "hola", volume=3)
    db = _DBFalsa(gaps_existentes=[existente])
    repo = FeedbackRepository(db)
    feedback = _feedback()

    resultado = repo.convert_to_gap(feedback, "hola", company_id=8, user_id=1)

    assert resultado is existente
    assert existente.volume == 4
    assert db.agregados == []  # nada nuevo se insertó
    assert feedback.knowledge_gap_id == 1
    assert feedback.status == "converted"


def test_espacios_saltos_de_linea_y_mayusculas_no_cuentan_como_pregunta_distinta():
    """Es el caso real: 'Evolución Arquitectónica y Modelos\\nGenerativos'
    estaba duplicado por un salto de línea de más en una de las dos copias."""
    existente = _gap_existente(1, "Evolución Arquitectónica y Modelos\nGenerativos")
    db = _DBFalsa(gaps_existentes=[existente])
    repo = FeedbackRepository(db)
    feedback = _feedback()

    repo.convert_to_gap(feedback, "evolución arquitectónica y modelos   generativos", company_id=8, user_id=1)

    assert existente.volume == 2
    assert db.agregados == []


def test_el_asistente_tiene_que_coincidir_tambien():
    """La misma pregunta a DOS asistentes distintos son dos gaps distintos,
    no uno: cada asistente es su propio espacio de conocimiento."""
    existente = _gap_existente(1, "hola", assistant_id=2)
    db = _DBFalsa(gaps_existentes=[existente])
    repo = FeedbackRepository(db)
    feedback = _feedback(assistant_id=5)  # asistente distinto

    repo.convert_to_gap(feedback, "hola", company_id=8, user_id=1)

    assert existente.volume == 1  # no se tocó
    assert len(db.agregados) == 1  # se creó una fila nueva


# ── Una pregunta de verdad distinta crea su propio gap ─────────────────────

def test_una_pregunta_distinta_si_crea_un_gap_nuevo():
    existente = _gap_existente(1, "hola")
    db = _DBFalsa(gaps_existentes=[existente])
    repo = FeedbackRepository(db)
    feedback = _feedback()

    repo.convert_to_gap(feedback, "que es un transformer", company_id=8, user_id=1)

    assert existente.volume == 1
    assert len(db.agregados) == 1
    assert db.agregados[0].question == "que es un transformer"


# ── Un gap resuelto o ignorado no absorbe nada en silencio ─────────────────

def test_un_gap_ya_resuelto_no_absorbe_la_pregunta_repetida():
    """Comprobación defensiva en memoria -no solo confiar en el filtro SQL-:
    si por lo que sea la consulta devolviera un gap ya resuelto, el propio
    bucle debe descartarlo igual."""
    resuelto = _gap_existente(1, "hola", status="resolved")
    db = _DBFalsa(gaps_existentes=[resuelto])
    repo = FeedbackRepository(db)
    feedback = _feedback()

    repo.convert_to_gap(feedback, "hola", company_id=8, user_id=1)

    assert resuelto.volume == 1  # no se tocó
    assert len(db.agregados) == 1  # se abrió como caso propio


def test_la_busqueda_de_duplicados_se_restringe_a_gaps_abiertos():
    """No basta con confiar en que la base de datos no nos de un resuelto por
    accidente: se verifica que el propio repositorio arma el filtro de
    estado -si alguien lo quitara sin querer, un "hola" ya resuelto podría
    absorber en silencio una pregunta nueva en vez de abrir su propio caso-."""
    db = _DBFalsa(gaps_existentes=[])
    repo = FeedbackRepository(db)
    feedback = _feedback()

    repo.convert_to_gap(feedback, "hola", company_id=8, user_id=1)

    filtros_como_texto = " ".join(str(f) for f in db.filtros_capturados)
    assert "status" in filtros_como_texto and "IN" in filtros_como_texto.upper()
