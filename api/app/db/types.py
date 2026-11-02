from sqlalchemy import Integer
from sqlalchemy.types import TypeDecorator


class IntBoolean(TypeDecorator):
    """Booleano en Python, guardado como INTEGER 0/1 en la base de datos.

    `companies.is_active` y `categories.is_active` son INTEGER en la BD real,
    pero los modelos los declaraban `Boolean`: Postgres rechazaba cualquier
    INSERT/UPDATE de esas columnas ("column is_active is of type integer but
    expression is of type boolean"), así que crear una categoría o una empresa
    daba 500. Se ajusta el código y no el esquema para no tocar una BD que
    también usa el producto comercial.
    """

    impl = Integer
    cache_ok = True

    def process_bind_param(self, value, dialect):
        return None if value is None else int(bool(value))

    def process_result_value(self, value, dialect):
        return None if value is None else bool(value)
