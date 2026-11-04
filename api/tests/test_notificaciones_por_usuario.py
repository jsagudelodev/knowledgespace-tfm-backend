"""Notificaciones por usuario: cada uno tiene su bandeja y solo toca lo suyo.

Antes los avisos para administradores eran una fila compartida (`user_id`
NULL): marcarla como leída se la quitaba de "No leídas" a todos los admins.
Ahora cada notificación es de un usuario y cada uno marca y borra lo suyo sin
afectar a nadie.

A diferencia del resto de la suite, estos tests usan una base SQLite en memoria
con solo las cuatro tablas implicadas: `create_all` completo no funciona en
SQLite (`assistants.quick_prompts` es JSONB), pero estas cuatro no lo usan, y lo
que se prueba son precisamente los filtros de la consulta.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.db.models.company import Company
from app.db.models.notification import Notification
from app.db.models.notification_type import NotificationType
from app.db.models.user import User
from app.services.notification_service import NotificationService


@pytest.fixture
def db():
    engine = create_engine("sqlite://")
    tablas = [Company.__table__, User.__table__, NotificationType.__table__, Notification.__table__]
    Base.metadata.create_all(engine, tables=tablas)
    session = sessionmaker(bind=engine)()
    session.add_all([
        Company(id=1, name="Acme", email="acme@acme.test"),
        Company(id=2, name="Otra", email="otra@otra.test"),
        User(id=10, company_id=1, email="a1@acme.test", full_name="Admin 1", hashed_password="x", role="admin"),
        User(id=11, company_id=1, email="a2@acme.test", full_name="Admin 2", hashed_password="x", role="superadmin"),
        User(id=12, company_id=1, email="u@acme.test", full_name="User", hashed_password="x", role="user"),
        User(id=13, company_id=1, email="off@acme.test", full_name="Inactivo", hashed_password="x",
             role="admin", is_active=False),
        User(id=20, company_id=2, email="a@otra.test", full_name="Admin otra", hashed_password="x", role="admin"),
        NotificationType(id=2, name="document_processed", label="Documento procesado"),
    ])
    session.commit()
    yield session
    session.close()


def _aviso_admins(svc, company_id=1):
    """Un aviso igual para cada admin, cada uno con su propia fila."""
    destinatarios = [20] if company_id == 2 else [10, 11]
    for user_id in destinatarios:
        svc.create_for_user(company_id=company_id, user_id=user_id,
                            type_name="document_processed", title="t", message="m")


def test_marcar_leida_no_afecta_a_los_demas_admins(db):
    svc = NotificationService(db)
    _aviso_admins(svc)
    mia = db.query(Notification).filter_by(user_id=10).one()

    svc.mark_as_read(mia.id, company_id=1, user_id=10)

    assert svc.get_unread_count(company_id=1, user_id=10) == 0
    assert svc.get_unread_count(company_id=1, user_id=11) == 1


def test_cada_uno_borra_solo_lo_suyo(db):
    svc = NotificationService(db)
    _aviso_admins(svc)
    ajena = db.query(Notification).filter_by(user_id=11).one().id

    assert svc.delete(ajena, company_id=1, user_id=10) is False
    assert db.query(Notification).filter_by(id=ajena).count() == 1

    assert svc.delete(ajena, company_id=1, user_id=11) is True
    assert db.query(Notification).filter_by(id=ajena).count() == 0


def _tres_del_usuario(svc):
    for _ in range(3):
        svc.create_for_user(company_id=1, user_id=12, type_name="document_processed", title="t", message="m")


def test_eliminar_varias_elegidas_solo_borra_esas(db):
    svc = NotificationService(db)
    _tres_del_usuario(svc)
    a, b, c = [n.id for n in db.query(Notification).filter_by(user_id=12).order_by(Notification.id)]

    assert svc.bulk([a, c], "delete", company_id=1, user_id=12) == 2
    assert [n.id for n in db.query(Notification).filter_by(user_id=12)] == [b]


def test_marcar_varias_como_leidas(db):
    svc = NotificationService(db)
    _tres_del_usuario(svc)
    a, b, _ = [n.id for n in db.query(Notification).filter_by(user_id=12).order_by(Notification.id)]

    assert svc.bulk([a, b], "read", company_id=1, user_id=12) == 2
    assert svc.get_unread_count(company_id=1, user_id=12) == 1
    # Ya leídas: repetir no cuenta de nuevo.
    assert svc.bulk([a, b], "read", company_id=1, user_id=12) == 0


def test_ids_ajenos_metidos_en_la_lista_se_ignoran(db):
    svc = NotificationService(db)
    _tres_del_usuario(svc)
    _aviso_admins(svc)                 # de los admins 10 y 11
    _aviso_admins(svc, company_id=2)   # del admin 20, otra empresa
    mia = db.query(Notification).filter_by(user_id=12).first().id
    ajenas = [n.id for n in db.query(Notification).filter(Notification.user_id.in_([10, 11, 20]))]

    assert svc.bulk([mia, *ajenas], "delete", company_id=1, user_id=12) == 1
    assert db.query(Notification).filter(Notification.id.in_(ajenas)).count() == len(ajenas)


def test_no_se_ven_ni_se_borran_notificaciones_de_otra_empresa(db):
    svc = NotificationService(db)
    _aviso_admins(svc, company_id=2)
    de_otra = db.query(Notification).filter_by(user_id=20).one()

    # El mismo usuario pidiendo con el company_id de su token (1) no la alcanza.
    assert svc.list_notifications(company_id=1, user_id=20) == []
    assert svc.delete(de_otra.id, company_id=1, user_id=20) is False
    assert svc.list_notifications(company_id=2, user_id=20)[0].id == de_otra.id


def test_los_contadores_incluyen_las_leidas(db):
    svc = NotificationService(db)
    _aviso_admins(svc)
    mia = db.query(Notification).filter_by(user_id=10).one()
    svc.mark_as_read(mia.id, company_id=1, user_id=10)

    counts = svc.get_counts(company_id=1, user_id=10)
    assert (counts["todas"], counts["unread"], counts["read"]) == (1, 0, 1)
