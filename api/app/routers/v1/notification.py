from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List

from app.core.database import get_db
from app.db.models.user import User
from app.routers.v1.security import get_current_user
from app.services.notification_service import NotificationService
from app.schemas.notification import NotificationResponse, NotificationUnreadCount, NotificationCounts

router = APIRouter()


@router.get(
    "/counts",
    response_model=NotificationCounts,
    summary="Recuentos por categoría de filtro y total de no leídas",
)
async def get_counts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return NotificationService(db).get_counts(
        company_id=current_user.company_id,
        user_id=current_user.id,
        role=current_user.role,
    )


@router.get(
    "/unread-count",
    response_model=NotificationUnreadCount,
    summary="Número de notificaciones no leídas",
)
async def get_unread_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    count = NotificationService(db).get_unread_count(
        company_id=current_user.company_id,
        user_id=current_user.id,
        role=current_user.role,
    )
    return {"count": count}


@router.get(
    "/",
    response_model=List[NotificationResponse],
    summary="Listar notificaciones del usuario autenticado",
)
async def list_notifications(
    read: Optional[bool] = Query(None, description="true=leídas, false=no leídas, omitir=todas"),
    type: Optional[str] = Query(None, description="Filtrar por tipo (name del notification_type)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return NotificationService(db).list_notifications(
        company_id=current_user.company_id,
        user_id=current_user.id,
        role=current_user.role,
        read=read,
        type_filter=type,
        skip=skip,
        limit=limit,
    )


# No hay endpoint para crear notificaciones, y es deliberado.
#
# El que había aceptaba `company_id` y `user_id` del cuerpo de la petición sin
# compararlos con el token, así que cualquier usuario autenticado podía insertar
# notificaciones en otra empresa. Eso contradice la regla del proyecto —el
# `company_id` sale del JWT, nunca del cuerpo— y además nadie lo llamaba: las
# notificaciones las crea el backend al procesar un documento o resolver una
# pregunta sin respuesta, a través de `NotificationService.create`.


@router.patch(
    "/{notification_id}/read",
    response_model=NotificationResponse,
    summary="Marcar una notificación como leída",
)
async def mark_as_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    notification = NotificationService(db).mark_as_read(
        notification_id=notification_id,
        company_id=current_user.company_id,
        user_id=current_user.id,
        role=current_user.role,
    )
    if not notification:
        raise HTTPException(status_code=404, detail="Notificación no encontrada")
    return notification


@router.post(
    "/read-all",
    response_model=dict,
    summary="Marcar todas las notificaciones como leídas",
)
async def mark_all_as_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    updated = NotificationService(db).mark_all_as_read(
        company_id=current_user.company_id,
        user_id=current_user.id,
        role=current_user.role,
    )
    return {"updated": updated}
