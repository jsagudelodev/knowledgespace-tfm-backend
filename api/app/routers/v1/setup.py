from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db, Base, engine
from app.core.security import get_password_hash, create_access_token
from app.db.models.company import Company
from app.db.models.user import User
from app.schemas.setup import SetupRequest, SetupResponse

router = APIRouter()


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
        if db.query(User).count() > 0:
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
