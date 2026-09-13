from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_password_hash
from app.db.models.user import User
from app.repositories.user_repository import UserRepository
from app.routers.v1.security import get_current_admin_user
from app.schemas.user import AdminPasswordReset, UserCreate, UserResponse, UserUpdate

router = APIRouter()


def _get_user_in_company(repo: UserRepository, user_id: int, company_id: int) -> User:
    user = repo.get(user_id)
    if not user or user.company_id != company_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    return user


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED, summary="Crear usuario")
async def create_user(
    data: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    repo = UserRepository(db)
    if repo.get_by_email(data.email):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El email ya está registrado")

    new_user = User(
        email=data.email,
        full_name=data.full_name,
        hashed_password=get_password_hash(data.password),
        role=data.role,
        company_id=current_user.company_id,
    )
    return repo.create(new_user)


@router.get("/", response_model=List[UserResponse], summary="Listar usuarios")
async def list_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    return UserRepository(db).get_by_company(current_user.company_id, skip=skip, limit=limit)


@router.get("/{user_id}", response_model=UserResponse, summary="Obtener usuario")
async def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    return _get_user_in_company(UserRepository(db), user_id, current_user.company_id)


@router.put("/{user_id}", response_model=UserResponse, summary="Actualizar usuario")
async def update_user(
    user_id: int,
    data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    repo = UserRepository(db)
    user = _get_user_in_company(repo, user_id, current_user.company_id)

    if data.email and data.email != user.email:
        if repo.get_by_email(data.email):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El email ya está registrado")
        user.email = data.email

    if data.full_name is not None:
        user.full_name = data.full_name
    if data.role is not None:
        user.role = data.role
    if data.is_active is not None:
        user.is_active = data.is_active
    if data.password:
        user.hashed_password = get_password_hash(data.password)

    return repo.update(user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Eliminar usuario")
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    repo = UserRepository(db)
    user = _get_user_in_company(repo, user_id, current_user.company_id)
    repo.delete(user)
    return None


@router.patch("/{user_id}/reset-password", summary="Restablecer contraseña (admin)")
async def reset_password(
    user_id: int,
    data: AdminPasswordReset,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    repo = UserRepository(db)
    user = _get_user_in_company(repo, user_id, current_user.company_id)
    user.hashed_password = get_password_hash(data.new_password)
    repo.update(user)
    return {"message": "Contraseña restablecida correctamente"}
