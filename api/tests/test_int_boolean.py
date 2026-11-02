"""`companies.is_active` y `categories.is_active` son INTEGER en la BD real y los
modelos los declaraban `Boolean`: crear una categoría o una empresa daba 500
("column is_active is of type integer but expression is of type boolean",
verificado el 2026-11-02 creando una categoría desde la pantalla). `IntBoolean`
deja el booleano en Python y manda 0/1 a la base de datos."""
from sqlalchemy.dialects import postgresql

from app.db.models.category import Category
from app.db.models.company import Company
from app.db.types import IntBoolean


def test_manda_enteros_a_la_bd():
    t = IntBoolean()
    assert t.process_bind_param(True, None) == 1
    assert t.process_bind_param(False, None) == 0
    assert t.process_bind_param(None, None) is None


def test_devuelve_booleanos_a_python():
    t = IntBoolean()
    assert t.process_result_value(1, None) is True
    assert t.process_result_value(0, None) is False
    assert t.process_result_value(None, None) is None


def test_las_dos_columnas_afectadas_lo_usan():
    assert isinstance(Category.__table__.c.is_active.type, IntBoolean)
    assert isinstance(Company.__table__.c.is_active.type, IntBoolean)


def test_el_insert_compila_con_entero_y_no_con_booleano():
    """Es justo lo que Postgres rechazaba: el valor enlazado debe ser 1, no True."""
    stmt = Category.__table__.insert().values(company_id=8, name="x", is_active=True)
    compilado = stmt.compile(dialect=postgresql.dialect())
    valor = compilado.construct_params()["is_active"]
    procesado = Category.__table__.c.is_active.type.process_bind_param(valor, None)
    assert procesado == 1 and procesado is not True
