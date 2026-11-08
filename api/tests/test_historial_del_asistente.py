"""Historial que recibe el modelo: solo el del asistente elegido y el reciente.

Dos fallos encontrados al revisar el código el 2026-11-07: al cambiar de
asistente en la misma conversación, el nuevo recibía en su historial las
preguntas y respuestas del anterior; y el historial se cortaba en los 20
mensajes MÁS ANTIGUOS, no en los más recientes.

Como `test_notificaciones_por_usuario.py`, usa SQLite en memoria con solo las
tablas implicadas: lo que se prueba son los filtros y el orden de la consulta.
"""
from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.db.models.company import Company
from app.db.models.conversation import Conversation
from app.db.models.message import Message
from app.db.models.user import User
from app.repositories.message_repository import MessageRepository

DEMO, EBIS = 1, 2
INICIO = datetime(2026, 11, 7, 12, 0, 0)


@pytest.fixture
def db():
    engine = create_engine("sqlite://")
    tablas = [Company.__table__, User.__table__, Conversation.__table__, Message.__table__]
    Base.metadata.create_all(engine, tables=tablas)
    session = sessionmaker(bind=engine)()
    session.add_all([
        Company(id=1, name="Acme", email="acme@acme.test"),
        User(id=10, company_id=1, email="u@acme.test", full_name="User", hashed_password="x", role="user"),
        Conversation(id=100, company_id=1, user_id=10, title="Chat IA"),
    ])
    session.commit()
    yield session
    session.close()


def _mensaje(db, n, role, content, assistant_id):
    """Mensaje `n` de la conversación, con una marca de tiempo creciente."""
    db.add(Message(conversation_id=100, role=role, content=content,
                   assistant_id=assistant_id, created_at=INICIO + timedelta(seconds=n)))
    db.commit()


def test_no_mezcla_asistentes(db):
    # Una pregunta a Demo, que se abstiene, y luego otra a EBIS.
    _mensaje(db, 1, "user", "que es ReAct", DEMO)
    _mensaje(db, 2, "assistant", "No encontré información sobre este tema...", DEMO)
    _mensaje(db, 3, "user", "otra pregunta a EBIS", EBIS)
    _mensaje(db, 4, "assistant", "respuesta de EBIS", EBIS)

    historial = MessageRepository(db).historial_del_asistente(100, EBIS)

    assert [m.content for m in historial] == ["otra pregunta a EBIS", "respuesta de EBIS"]
    assert all(m.assistant_id == EBIS for m in historial)


def test_trae_los_mas_recientes_en_orden_cronologico(db):
    for n in range(25):
        _mensaje(db, n, "user" if n % 2 == 0 else "assistant", f"m{n}", EBIS)

    historial = MessageRepository(db).historial_del_asistente(100, EBIS, limite=20)

    # Antes salían m0..m19; los que importan para "¿y eso cuánto cuesta?" son
    # los últimos.
    assert [m.content for m in historial] == [f"m{n}" for n in range(5, 25)]


def test_sin_asistente_no_mezcla_con_los_de_un_asistente(db):
    _mensaje(db, 1, "user", "sin asistente", None)
    _mensaje(db, 2, "user", "con EBIS", EBIS)

    assert [m.content for m in MessageRepository(db).historial_del_asistente(100, None)] == ["sin asistente"]
    assert [m.content for m in MessageRepository(db).historial_del_asistente(100, EBIS)] == ["con EBIS"]
