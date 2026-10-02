"""Dependencias de autenticación y autorización compartidas por todos los
routers. `get_current_user` valida el JWT y es la base del aislamiento
multi-tenant: de él sale el `company_id` con el que se filtra todo."""
from typing import Optional

from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_access_token
from app.db.models.user import User
from app.repositories.user_repository import UserRepository

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
    request: Request = None,
) -> User:
    invalid = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales inválidas",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_access_token(credentials.credentials)
    if not payload:
        raise invalid

    email: str = payload.get("sub")
    if not email:
        raise invalid

    user = UserRepository(db).get_by_email(email)
    if not user:
        raise invalid

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Usuario inactivo")

    # Disponible para middlewares de rate-limiting
    if request:
        request.state.user_id = user.id
        request.state.company_id = user.company_id

    return user


async def get_current_admin_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Admin de empresa o superadmin de plataforma."""
    if current_user.role not in ("admin", "superadmin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Se requieren permisos de administrador")
    return current_user


async def get_current_superadmin(
    current_user: User = Depends(get_current_user),
) -> User:
    """Solo superadmin de plataforma — acceso total sin filtro de empresa."""
    if current_user.role != "superadmin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Se requieren permisos de superadministrador")
    return current_user


def is_superadmin(user: User) -> bool:
    return user.role == "superadmin"


async def get_company_context(
    x_company_context: Optional[int] = Header(None, alias="X-Company-Context"),
    current_user: User = Depends(get_current_admin_user),
) -> int:
    """Company_id efectivo: un superadmin puede sobrescribirlo via X-Company-Context."""
    if x_company_context is not None and current_user.role == "superadmin":
        return x_company_context
    return current_user.company_id
