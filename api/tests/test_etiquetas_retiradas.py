"""Las etiquetas se retiraron el 2026-11-02: eran un CRUD que nunca se vinculó a
ningún documento (ni tabla intermedia ni columna en `documents`), y la
categoría ya cubre la organización. Se conserva el modelo `Tag` para no
borrar la tabla; lo que no debe volver es la API."""
import importlib.util


def test_no_existe_la_api_de_etiquetas():
    assert importlib.util.find_spec("app.routers.v1.tags") is None
    assert importlib.util.find_spec("app.repositories.tag_repository") is None
    assert importlib.util.find_spec("app.schemas.tag") is None


def test_el_modelo_se_conserva_para_no_borrar_la_tabla():
    from app.db.models.tag import Tag

    assert Tag.__tablename__ == "tags"
