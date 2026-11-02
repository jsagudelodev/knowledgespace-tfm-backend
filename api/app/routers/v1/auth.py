"""Autenticación y perfil propio: login con JWT y gestión de los datos del
usuario autenticado.

No hay registro público: los usuarios los crea un administrador de la empresa
(`POST /api/v1/users`), que toma la empresa del token y nunca de la petición."""
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import create_access_token, get_password_hash, verify_password
from app.db.models.user import User
from app.repositories.user_repository import UserRepository
from app.routers.v1.security import get_current_user
from app.schemas.user import ChangePassword, ProfileUpdate, UserResponse

router = APIRouter()


@router.post("/login", summary="Iniciar sesión")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = UserRepository(db).get_by_email(form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales incorrectas")

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Usuario inactivo")

    access_token = create_access_token(
        data={"sub": user.email},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse, summary="Obtener perfil propio")
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.put("/me", response_model=UserResponse, summary="Actualizar perfil propio")
async def update_profile(
    data: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    current_user.full_name = data.full_name
    return UserRepository(db).update(current_user)


@router.put("/change-password", summary="Cambiar contraseña")
async def change_password(
    data: ChangePassword,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(data.current_password, current_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La contraseña actual es incorrecta")

    if verify_password(data.new_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="La nueva contraseña debe ser diferente a la actual"
        )

    current_user.hashed_password = get_password_hash(data.new_password)
    UserRepository(db).update(current_user)
    return {"message": "Contraseña actualizada correctamente"}
