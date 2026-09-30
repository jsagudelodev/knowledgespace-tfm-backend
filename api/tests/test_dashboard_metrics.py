"""Test de _metricas_de_documentos — decide qué número ve el usuario en la
tarjeta de documentos del panel de inicio, a partir del recuento por estado
que devuelve la base."""
from app.routers.v1.dashboard import _metricas_de_documentos


def test_pending_y_processing_se_suman_en_processing():
    # Para quien mira el panel, ambos estados significan lo mismo: el
    # documento todavía no se puede consultar.
    m = _metricas_de_documentos({"pending": 2, "processing": 3, "completed": 5})
    assert m.processing == 5
    assert m.completed == 5


def test_total_incluye_los_fallidos():
    # Un documento `failed` sigue ocupando sitio en la lista de la empresa:
    # contarlo evita que el total del panel no cuadre con lo que se ve en
    # /documents.
    m = _metricas_de_documentos({"completed": 4, "failed": 1})
    assert m.total == 5
    assert m.completed == 4
    assert m.processing == 0


def test_empresa_sin_documentos_devuelve_ceros():
    m = _metricas_de_documentos({})
    assert (m.total, m.completed, m.processing) == (0, 0, 0)


def test_estado_desconocido_cuenta_en_el_total_pero_no_en_los_desgloses():
    # Si algún día se añade un estado nuevo al enum, el panel no debe
    # reventar ni inventarse en qué casilla ponerlo.
    m = _metricas_de_documentos({"completed": 1, "archivado": 7})
    assert m.total == 8
    assert m.completed == 1
    assert m.processing == 0
