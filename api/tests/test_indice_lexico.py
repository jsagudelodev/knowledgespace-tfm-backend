"""Tests del indice BM25 en memoria.

Lo que se fija aqui: que discrimina (un fragmento con el termino puntua mas
que uno sin el), que respeta la frecuencia inversa de documento (un termino
raro pesa mas que uno comun), que no rompe con consultas o corpus vacios, y
que el resultado viene ordenado y acotado a top_k.
"""
from app.services.indice_lexico import IndiceLexico


def test_un_fragmento_sin_el_termino_no_aparece():
    indice = IndiceLexico([
        ("a", "los gatos duermen en el tejado"),
        ("b", "los perros ladran en el jardin"),
    ])
    resultado = indice.buscar("gatos", top_k=5)
    assert [doc_id for doc_id, _ in resultado] == ["a"]


def test_ordena_por_puntuacion_de_mayor_a_menor():
    indice = IndiceLexico([
        ("menciona_una_vez", "el embedding es un vector"),
        ("menciona_tres_veces", "embedding embedding embedding es una representacion"),
        ("no_menciona", "los autoencoders comprimen datos"),
    ])
    resultado = indice.buscar("embedding", top_k=5)
    ids = [doc_id for doc_id, _ in resultado]
    assert ids[0] == "menciona_tres_veces"
    assert "no_menciona" not in ids


def test_un_termino_raro_puntua_mas_que_uno_comun():
    """El IDF favorece los terminos que aparecen en pocos documentos. "el"
    esta en todos; "hiperparametro" solo en uno."""
    indice = IndiceLexico([
        ("objetivo", "el hiperparametro controla el entrenamiento"),
        ("c2", "el modelo aprende de los datos"),
        ("c3", "el resultado depende del dataset"),
        ("c4", "el proceso termina cuando converge"),
    ])
    solo_comun = dict(indice.buscar("el", top_k=5))
    con_raro = dict(indice.buscar("hiperparametro", top_k=5))
    # "hiperparametro" aparece en un solo documento: su IDF es alto y su
    # puntuacion en ese documento debe superar la que "el" -presente en
    # los cuatro- logra en el mismo documento.
    assert con_raro["objetivo"] > solo_comun["objetivo"]


def test_top_k_acota_el_resultado():
    indice = IndiceLexico([(f"d{i}", "palabra comun") for i in range(10)])
    assert len(indice.buscar("palabra", top_k=3)) == 3


def test_consulta_sin_terminos_conocidos_no_devuelve_nada():
    indice = IndiceLexico([("a", "los gatos duermen")])
    assert indice.buscar("xenomorfo inexistente", top_k=5) == []


def test_corpus_vacio_no_rompe():
    indice = IndiceLexico([])
    assert indice.buscar("cualquier cosa", top_k=5) == []


def test_consulta_vacia_no_rompe():
    indice = IndiceLexico([("a", "los gatos duermen")])
    assert indice.buscar("", top_k=5) == []


def test_tokenizacion_ignora_mayusculas_y_puntuacion():
    indice = IndiceLexico([("a", "¿Qué es un VAE? Un VAE es...")])
    resultado = indice.buscar("vae", top_k=5)
    assert resultado and resultado[0][0] == "a"
