""""Pedir documento" se retiró el 2026-11-03: asignaba la pregunta a una persona
y la dejaba "en curso" sin resolverla, y junto a "vincular documento" confundía.
El administrador resuelve con dos vías: escribir la respuesta o un documento."""
from app.routers.v1 import knowledge_gaps
from app.routers.v1.setup import TIPOS_DE_NOTIFICACION


def test_no_existe_la_ruta_de_pedir_documento():
    rutas = {ruta.path for ruta in knowledge_gaps.router.routes}

    assert "/{gap_id}/request-document" not in rutas
    assert "/{gap_id}/answer" in rutas
    assert "/{gap_id}/link" in rutas


def test_las_instalaciones_nuevas_no_siembran_el_aviso_de_documento_solicitado():
    assert "document_requested" not in {t["name"] for t in TIPOS_DE_NOTIFICACION}
