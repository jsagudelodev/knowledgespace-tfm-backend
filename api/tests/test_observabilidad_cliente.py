"""Tests de `observabilidad.cliente()`.

Hace falta una puerta publica al cliente de Langfuse para operaciones que
`paso` y `anotar_traza` no cubren -- datasets, en este caso, para
`experimentos/langfuse_dataset.py`--. El resto del modulo evita exponer
`_cliente` directamente para que todo el estado de la instrumentacion viva en
un unico sitio; esto fija que la funcion publica se comporte bien en los dos
casos que importan.
"""
from app.core import observabilidad


def test_sin_langfuse_activo_falla_con_mensaje_claro(monkeypatch):
    """Un experimento que necesita Langfuse y lo usa sin comprobar antes
    `activo()` debe enterarse de inmediato con un mensaje util, no fallar mas
    adelante con un AttributeError sobre `None`."""
    monkeypatch.setattr(observabilidad, "_activo", False)
    monkeypatch.setattr(observabilidad, "_cliente", None)

    try:
        observabilidad.cliente()
        raise AssertionError("deberia haber lanzado")
    except RuntimeError as e:
        assert "LANGFUSE_ENABLED" in str(e)


def test_con_langfuse_activo_devuelve_el_cliente(monkeypatch):
    centinela = object()
    monkeypatch.setattr(observabilidad, "_activo", True)
    monkeypatch.setattr(observabilidad, "_cliente", centinela)

    assert observabilidad.cliente() is centinela
