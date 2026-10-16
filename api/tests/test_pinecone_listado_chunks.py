"""Tests del listado de fragmentos de un documento.

Permite ver en que quedo dividido un documento tras la ingesta. Lo que se fija
aqui es lo que costo encontrar al implementarlo:

    1. `list` pagina y la forma de cada pagina DEPENDE DE LA VERSION del
       cliente de Pinecone. La 9.1 devuelve objetos `ListResponse` con un
       atributo `vectors`; versiones anteriores devuelven listas de cadenas.
       Recorrer la forma equivocada no da error: devuelve una lista vacia, y
       un documento sin fragmentos parece un documento mal indexado. La
       primera version de este metodo reporto los ocho documentos del corpus
       como desincronizados cuando ninguno lo estaba.
    2. el resultado va ORDENADO por indice de fragmento. Pinecone devuelve
       `doc-44-chunk-10` antes que `doc-44-chunk-2` porque ordena como texto, y
       mostrarlos asi impediria ver justamente lo que se quiere ver: por donde
       se corto el documento.

Son tests de logica pura: el indice se sustituye por un doble.
"""
from types import SimpleNamespace

from app.services.pinecone_service import PineconeService


def _vector(id_, indice, texto="contenido del fragmento"):
    return SimpleNamespace(metadata={"chunk_index": indice, "text": texto})


def _servicio(paginas, vectores):
    """Doble del indice. `paginas` imita lo que devuelve `list`."""
    svc = PineconeService.__new__(PineconeService)
    svc.nombre_indice = "test"

    class _Indice:
        def list(self, **kwargs):
            self.prefijo = kwargs.get("prefix")
            return iter(paginas)

        def fetch(self, **kwargs):
            pedidos = kwargs["ids"]
            return SimpleNamespace(
                vectors={k: v for k, v in vectores.items() if k in pedidos})

    indice = _Indice()
    svc.pc = SimpleNamespace(Index=lambda nombre: indice)
    svc._indice_doble = indice
    return svc


# ── Las dos formas que devuelve `list` segun la version ────────────────────

def test_entiende_las_paginas_con_objetos_ListResponse():
    """Es la forma de pinecone 9.1, la version instalada."""
    pagina = SimpleNamespace(vectors=[SimpleNamespace(id="doc-7-chunk-0"),
                                      SimpleNamespace(id="doc-7-chunk-1")])
    svc = _servicio([pagina], {
        "doc-7-chunk-0": _vector("doc-7-chunk-0", 0),
        "doc-7-chunk-1": _vector("doc-7-chunk-1", 1),
    })
    assert len(svc.listar_por_documento(7)) == 2


def test_entiende_las_paginas_con_listas_de_cadenas():
    """Es la forma de versiones anteriores del cliente."""
    svc = _servicio([["doc-7-chunk-0", "doc-7-chunk-1"]], {
        "doc-7-chunk-0": _vector("doc-7-chunk-0", 0),
        "doc-7-chunk-1": _vector("doc-7-chunk-1", 1),
    })
    assert len(svc.listar_por_documento(7)) == 2


# ── El orden importa ────────────────────────────────────────────────────────

def test_los_fragmentos_salen_ordenados_por_indice():
    """Pinecone ordena los identificadores como texto, de modo que el
    fragmento 10 llega antes que el 2. Mostrarlos asi impediria ver por donde
    se corto el documento, que es el proposito de este listado."""
    pagina = SimpleNamespace(vectors=[
        SimpleNamespace(id="doc-7-chunk-0"),
        SimpleNamespace(id="doc-7-chunk-10"),
        SimpleNamespace(id="doc-7-chunk-2"),
    ])
    svc = _servicio([pagina], {
        "doc-7-chunk-0": _vector("doc-7-chunk-0", 0),
        "doc-7-chunk-10": _vector("doc-7-chunk-10", 10),
        "doc-7-chunk-2": _vector("doc-7-chunk-2", 2),
    })
    assert [f["chunk_index"] for f in svc.listar_por_documento(7)] == [0, 2, 10]


# ── Casos de borde ──────────────────────────────────────────────────────────

def test_un_documento_sin_fragmentos_devuelve_lista_vacia():
    """Es lo que ocurre mientras se procesa o si la ingesta fallo. No es un
    error: el estado del documento distingue ambas situaciones."""
    svc = _servicio([], {})
    assert svc.listar_por_documento(99) == []


def test_se_consulta_por_el_prefijo_del_documento_pedido():
    """Sin el prefijo correcto se listaria el espacio entero, que puede tener
    documentos de otros asistentes."""
    svc = _servicio([], {})
    svc.listar_por_documento(44)
    assert svc._indice_doble.prefijo == "doc-44-chunk-"


def test_cada_fragmento_informa_de_su_tamano():
    """Permite ver de un vistazo si el troceado produjo fragmentos dispares."""
    pagina = SimpleNamespace(vectors=[SimpleNamespace(id="doc-7-chunk-0")])
    svc = _servicio([pagina], {"doc-7-chunk-0": _vector("doc-7-chunk-0", 0, "x" * 940)})
    assert svc.listar_por_documento(7)[0]["caracteres"] == 940
