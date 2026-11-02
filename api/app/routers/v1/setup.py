from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import Base, engine, get_db
from app.core.security import create_access_token, get_password_hash
from app.db.models.company import Company
from app.db.models.notification_type import NotificationType
from app.db.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.setup import SetupRequest, SetupResponse

router = APIRouter()

# Tipos de notificación que el código emite. No son un enum: el servicio los
# resuelve por nombre contra la tabla `notification_types`, y si el nombre no
# está sembrado lanza ValueError. Como los llamadores envuelven la creación en
# try/except —una notificación nunca debe romper la operación que la origina—,
# una base sin estas filas se queda sin notificaciones **en silencio**.
#
# Por eso se siembran aquí, junto a la creación de tablas: la documentación
# atribuía el seed a un `create_tables.py` que nunca existió en el repositorio.
TIPOS_DE_NOTIFICACION = [
    {
        "name": "document_processed",
        "label": "Documento procesado",
        "description": "El documento se indexó y ya se puede consultar.",
        "icon": "file-check",
        "color": "#10B981",
    },
    {
        "name": "document_failed",
        "label": "Error al procesar documento",
        "description": "El documento no se pudo procesar.",
        "icon": "file-x",
        "color": "#EF4444",
    },
    {
        "name": "document_deleted",
        "label": "Documento eliminado",
        "description": "El documento se retiró de la base de conocimiento.",
        "icon": "trash",
        "color": "#6B7280",
    },
    {
        "name": "knowledge_gap_found",
        "label": "Pregunta sin respuesta",
        "description": "Una consulta no encontró respuesta en los documentos.",
        "icon": "help-circle",
        "color": "#8B5CF6",
    },
    {
        "name": "knowledge_gap_resolved",
        "label": "Pregunta resuelta",
        "description": "Se resolvió una pregunta que no tenía respuesta.",
        "icon": "check-circle",
        "color": "#10B981",
    },
    {
        "name": "document_requested",
        "label": "Documento solicitado",
        "description": "Un administrador te pidió un documento para responder una pregunta.",
        "icon": "file-plus",
        "color": "#2563EB",
    },
]


def _sembrar_tipos_de_notificacion(db: Session) -> None:
    """Inserta los tipos que falten, sin tocar los que ya estén.

    Es idempotente a propósito: `setup` solo corre una vez, pero si en el
    futuro se añade un tipo nuevo, volver a ejecutar esto no duplica nada.
    """
    existentes = {n for (n,) in db.query(NotificationType.name).all()}
    for tipo in TIPOS_DE_NOTIFICACION:
        if tipo["name"] not in existentes:
            db.add(NotificationType(**tipo, is_active=True))


@router.post(
    "/",
    response_model=SetupResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Inicializar el sistema (solo funciona si no existe ningún usuario)",
)
async def setup(payload: SetupRequest, db: Session = Depends(get_db)):
    # Bloquear si ya existen usuarios — el sistema ya fue inicializado
    # Si las tablas no existen aún, el count falla y se permite continuar
    try:
        if UserRepository(db).count_all() > 0:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="El sistema ya fue inicializado. Este endpoint está deshabilitado.",
            )
    except HTTPException:
        raise
    except Exception:
        pass  # tablas aún no creadas — se crean abajo con create_all

    # Crear tablas si no existen
    Base.metadata.create_all(bind=engine)

    # Sembrar los tipos de notificación. Sin esto, ninguna notificación llega
    # a crearse y el fallo es invisible: los llamadores lo capturan.
    _sembrar_tipos_de_notificacion(db)

    # Crear empresa
    company = Company(
        name=payload.company_name,
        email=payload.company_email,
        plan="pro",
        max_users=100,
        max_documents=10000,
        is_active=True,
    )
    db.add(company)
    db.flush()  # obtener company.id sin hacer commit aún

    # Crear superadmin
    user = User(
        company_id=company.id,
        full_name=payload.full_name,
        email=payload.email,
        hashed_password=get_password_hash(payload.password),
        role="superadmin",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(company)
    db.refresh(user)

    token = create_access_token(data={
        "sub": user.email,
        "company_id": user.company_id,
        "role": user.role,
    })

    return SetupResponse(
        message="Sistema inicializado correctamente.",
        company_id=company.id,
        user_id=user.id,
        access_token=token,
    )
