"""Tests del reparto equilibrado al recortar el contexto.

`RAGServiceCompleto` pone a la descomposicion de consultas el tope que no
tenia: en lugar de enviar al modelo los hasta `TOP_K · n` fragmentos que
produce la fusion, conserva `TOP_K` repartidos entre las subpreguntas.

Lo que se fija aqui es la propiedad que justifica la clase: **ninguna
subpregunta se queda sin representacion**. Una version anterior recortaba
pidiendo al modelo que ordenara por utilidad, y al medirla resulto que
concentraba los cinco fragmentos en una sola subpregunta --desequilibrio 2,17
frente a 1,83 de la linea base--, que es justo lo que la descomposicion venia
a evitar.
"""
from types import SimpleNamespace

from app.services.rag_service import TOP_K
from app.services.rag_service_completo import RAGServiceCompleto


def _doc(id_: str, score: float = 0.5):
    return SimpleNamespace(id=id_, score=score,
                           metadata={"document_name": "m.pdf", "text": "x"})


def _repartir(listas, tope=TOP_K):
    return RAGServiceCompleto._repartir(listas, tope)


# ── El reparto no deja ninguna subpregunta fuera ───────────────────────────

def test_con_dos_subpreguntas_el_reparto_es_equilibrado():
    """Cinco huecos entre dos subpreguntas son 3/2, nunca 5/0."""
    a = [_doc(f"a{i}") for i in range(5)]
    b = [_doc(f"b{i}") for i in range(5)]

    elegidos = [d.id for d in _repartir([a, b])]

    assert len(elegidos) == TOP_K
    assert sum(1 for x in elegidos if x.startswith('a')) == 3
    assert sum(1 for x in elegidos if x.startswith('b')) == 2


def test_con_tres_subpreguntas_ninguna_se_queda_sin_nada():
    a = [_doc(f"a{i}") for i in range(5)]
    b = [_doc(f"b{i}") for i in range(5)]
    c = [_doc(f"c{i}") for i in range(5)]

    elegidos = [d.id for d in _repartir([a, b, c])]

    assert len(elegidos) == TOP_K
    for prefijo in 'abc':
        assert any(x.startswith(prefijo) for x in elegidos), \
            f'la subpregunta {prefijo} se quedo sin fragmentos'


def test_se_toma_lo_mejor_de_cada_subpregunta_primero():
    """Las listas llegan ordenadas por puntuacion: en la primera ronda debe
    tomarse el primer elemento de cada una."""
    a = [_doc("a-mejor"), _doc("a-peor")]
    b = [_doc("b-mejor"), _doc("b-peor")]

    elegidos = [d.id for d in _repartir([a, b], tope=2)]
    assert elegidos == ["a-mejor", "b-mejor"]


# ── Casos de borde ──────────────────────────────────────────────────────────

def test_un_fragmento_compartido_no_ocupa_dos_huecos():
    """Si el mismo fragmento aparece en dos subpreguntas se incluye una vez, y
    el hueco liberado lo aprovecha el siguiente de esa lista."""
    compartido = _doc("compartido")
    a = [compartido, _doc("a1"), _doc("a2")]
    b = [compartido, _doc("b1"), _doc("b2")]

    elegidos = [d.id for d in _repartir([a, b], tope=4)]

    assert len(elegidos) == len(set(elegidos)), 'no puede repetirse ninguno'
    assert elegidos.count("compartido") == 1


def test_si_una_subpregunta_tiene_pocos_la_otra_cubre_el_resto():
    """El reparto es equilibrado, no rigido: si a una le faltan fragmentos, el
    tope se completa con los de la otra en vez de desperdiciar huecos."""
    a = [_doc(f"a{i}") for i in range(5)]
    b = [_doc("b0")]

    elegidos = [d.id for d in _repartir([a, b])]

    assert len(elegidos) == TOP_K
    assert "b0" in elegidos
    assert sum(1 for x in elegidos if x.startswith('a')) == 4


def test_no_se_cuelga_si_todas_las_listas_se_agotan():
    """Con menos fragmentos que el tope devuelve los que haya, sin bucle."""
    elegidos = _repartir([[_doc("a0")], [_doc("b0")]], tope=TOP_K)
    assert len(elegidos) == 2


def test_listas_vacias_devuelven_vacio():
    assert _repartir([[], []]) == []


def test_nunca_se_devuelven_mas_del_tope():
    listas = [[_doc(f"{p}{i}") for i in range(20)] for p in 'abc']
    assert len(_repartir(listas, tope=TOP_K)) == TOP_K
