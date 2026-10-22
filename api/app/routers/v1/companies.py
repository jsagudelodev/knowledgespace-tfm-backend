from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.db.models.company import Company
from app.db.models.user import User
from app.repositories.company_repository import CompanyRepository
from app.routers.v1.security import get_current_superadmin, get_current_user
from app.schemas.company import CompanyCreate, CompanyResponse, CompanyUpdate

router = APIRouter()


@router.get("/me", response_model=CompanyResponse, summary="Obtener mi empresa")
async def get_my_company(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    company = CompanyRepository(db).get(current_user.company_id)
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empresa no encontrada")
    return company


@router.get("/", response_model=List[CompanyResponse], summary="Listar todas las empresas (superadmin)")
async def list_companies(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_superadmin),
):
    return CompanyRepository(db).get_all()


@router.post(
    "/", response_model=CompanyResponse, status_code=status.HTTP_201_CREATED, summary="Crear empresa (superadmin)"
)
async def create_company(
    data: CompanyCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_superadmin),
):
    repo = CompanyRepository(db)
    if repo.get_by_email(data.email):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El email ya está registrado")
    return repo.create(Company(**data.model_dump()))


@router.get("/{company_id}", response_model=CompanyResponse, summary="Obtener empresa por ID (superadmin)")
async def get_company(
    company_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_superadmin),
):
    company = CompanyRepository(db).get(company_id)
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empresa no encontrada")
    return company


@router.put("/{company_id}", response_model=CompanyResponse, summary="Actualizar empresa (superadmin)")
async def update_company(
    company_id: int,
    data: CompanyUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_superadmin),
):
    repo = CompanyRepository(db)
    company = repo.get(company_id)
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empresa no encontrada")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(company, key, value)
    return repo.update(company)


@router.delete("/{company_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Eliminar empresa (superadmin)")
async def delete_company(
    company_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_superadmin),
):
    repo = CompanyRepository(db)
    company = repo.get(company_id)
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empresa no encontrada")
    repo.delete(company)
    return None
