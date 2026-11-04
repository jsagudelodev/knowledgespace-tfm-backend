from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.orm import Session, selectinload

from app.db.models.notification import Notification, NotificationEntityType
from app.db.models.notification_type import NotificationType
from app.db.models.user import User
from app.schemas.notification import NotificationCreate


class NotificationService:
    """
    Avisos internos de empresa: documentos procesados o fallidos, preguntas
    sin respuesta detectadas y resueltas.

    Cada notificación pertenece a un usuario: la bandeja es personal. Un aviso
    para los administradores (`create_for_admins`) se guarda como una copia por
    cada admin activo de la empresa. Hasta el 2026-11-03 se guardaba una sola
    fila con `user_id = NULL` que veían todos los admins, y entonces "leída" era
    compartida: un admin que la marcaba se la quitaba de "No leídas" a los
    demás, y borrarla se la habría borrado a todos. La migración
    `c4e8a2f6d1b3` repartió esas filas antiguas.

    El tipo de notificación no es un enum del código sino una fila de
    `notification_types` — se pasa por nombre (`type_name`) y se resuelve a
    su ID. Un tipo no sembrado en BD lanza ValueError, por eso los llamadores
    envuelven la creación en try/except: una notificación es un efecto
    secundario y nunca debe romper la operación que la origina.
    """

    def __init__(self, db: Session):
        self.db = db

    # ── Helpers internos ──────────────────────────────────────────────────────

    def _get_type_id(self, type_name: str) -> int:
        """Obtiene el ID de un NotificationType dado su nombre, o lanza error si no existe."""
        nt = self.db.query(NotificationType).filter_by(name=type_name).first()
        if not nt:
            raise ValueError(f"Tipo de notificación '{type_name}' no encontrado")
        return nt.id

    def _with_type(self, query):
        """Aplica selectinload de notification_type para evitar lazy load en contexto async."""
        return query.options(selectinload(Notification.notification_type))

    def _own(self, company_id: int, user_id: int):
        """Las notificaciones de un usuario: de su empresa y suyas. La empresa
        se comprueba además del usuario, como en el resto de recursos."""
        return (
            Notification.company_id == company_id,
            Notification.user_id == user_id,
        )

    def _fetch_by_id(self, notification_id: int) -> Optional[Notification]:
        """Re-fetch con notification_type cargado tras un commit."""
        return self._with_type(
            self.db.query(Notification).filter(Notification.id == notification_id)
        ).first()

    # ── Creación ─────────────────────────────────────────────────────────────

    def create(self, data: NotificationCreate) -> Notification:
        notification = Notification(
            company_id=data.company_id,
            user_id=data.user_id,
            type_id=data.type_id,
            title=data.title,
            message=data.message,
            entity_type=data.entity_type,
            entity_id=data.entity_id,
        )
        self.db.add(notification)
        self.db.commit()
        return self._fetch_by_id(notification.id)

    def create_for_user(
        self,
        company_id: int,
        user_id: int,
        type_name: str,
        title: str,
        message: str,
        entity_type: Optional[NotificationEntityType] = None,
        entity_id: Optional[int] = None,
    ) -> Notification:
        """Crea una notificación dirigida a un usuario específico (no broadcast)."""
        notification = Notification(
            company_id=company_id,
            user_id=user_id,
            type_id=self._get_type_id(type_name),
            title=title,
            message=message,
            entity_type=entity_type,
            entity_id=entity_id,
        )
        self.db.add(notification)
        self.db.commit()
        return self._fetch_by_id(notification.id)

    def create_for_admins(
        self,
        company_id: int,
        type_name: str,
        title: str,
        message: str,
        entity_type: Optional[NotificationEntityType] = None,
        entity_id: Optional[int] = None,
    ) -> List[Notification]:
        """Crea una copia de la notificación para cada admin activo de la empresa."""
        type_id = self._get_type_id(type_name)
        admins = (
            self.db.query(User.id)
            .filter(
                User.company_id == company_id,
                User.role.in_(("admin", "superadmin")),
                User.is_active.is_(True),
            )
            .all()
        )
        notifications = [
            Notification(
                company_id=company_id,
                user_id=admin_id,
                type_id=type_id,
                title=title,
                message=message,
                entity_type=entity_type,
                entity_id=entity_id,
            )
            for (admin_id,) in admins
        ]
        self.db.add_all(notifications)
        self.db.commit()
        return notifications

    # ── Consulta ──────────────────────────────────────────────────────────────

    def list_notifications(
        self,
        company_id: int,
        user_id: int,
        read: Optional[bool] = None,
        type_filter: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> List[Notification]:
        query = self._with_type(self.db.query(Notification)).filter(*self._own(company_id, user_id))
        if read is not None:
            query = query.filter(Notification.read == read)
        if type_filter:
            query = query.join(Notification.notification_type).filter(
                NotificationType.name.like(f'{type_filter}%')
            )
        return (
            query.order_by(Notification.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_unread_count(self, company_id: int, user_id: int) -> int:
        return (
            self.db.query(Notification)
            .filter(*self._own(company_id, user_id), Notification.read.is_(False))
            .count()
        )

    def get_counts(self, company_id: int, user_id: int) -> dict:
        base = self.db.query(Notification).filter(*self._own(company_id, user_id))
        type_base = base.join(Notification.notification_type)
        return {
            "todas": base.count(),
            "unread": base.filter(Notification.read.is_(False)).count(),
            "read": base.filter(Notification.read.is_(True)).count(),
            "documents": type_base.filter(NotificationType.name.like("document%")).count(),
            "budget": type_base.filter(NotificationType.name.like("budget%")).count(),
            "knowledge_gap": type_base.filter(NotificationType.name.like("knowledge%")).count(),
        }

    def get_by_id(self, notification_id: int, company_id: int) -> Optional[Notification]:
        return self._with_type(self.db.query(Notification)).filter(
            Notification.id == notification_id,
            Notification.company_id == company_id,
        ).first()

    # ── Marcado de lectura ────────────────────────────────────────────────────

    def mark_as_read(
        self, notification_id: int, company_id: int, user_id: int
    ) -> Optional[Notification]:
        notification = (
            self.db.query(Notification)
            .filter(Notification.id == notification_id, *self._own(company_id, user_id))
            .first()
        )
        if not notification:
            return None
        if not notification.read:
            notification.read = True
            notification.read_at = datetime.now(timezone.utc)
            self.db.commit()
        return self._fetch_by_id(notification_id)

    def mark_all_as_read(self, company_id: int, user_id: int) -> int:
        now = datetime.now(timezone.utc)
        updated = (
            self.db.query(Notification)
            .filter(*self._own(company_id, user_id), Notification.read.is_(False))
            .update({"read": True, "read_at": now}, synchronize_session=False)
        )
        self.db.commit()
        return updated

    # ── Borrado ───────────────────────────────────────────────────────────────
    # Cada usuario limpia su bandeja y solo puede borrar lo suyo: por eso las
    # notificaciones son por usuario y no compartidas.

    def delete(self, notification_id: int, company_id: int, user_id: int) -> bool:
        deleted = (
            self.db.query(Notification)
            .filter(Notification.id == notification_id, *self._own(company_id, user_id))
            .delete(synchronize_session=False)
        )
        self.db.commit()
        return deleted > 0

    def delete_read(self, company_id: int, user_id: int) -> int:
        """Borra las notificaciones ya leídas del usuario. Las no leídas se
        conservan: nunca se borra en bloque algo que el usuario no ha visto."""
        deleted = (
            self.db.query(Notification)
            .filter(*self._own(company_id, user_id), Notification.read.is_(True))
            .delete(synchronize_session=False)
        )
        self.db.commit()
        return deleted
