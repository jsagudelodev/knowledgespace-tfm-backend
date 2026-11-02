from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.db.models.assistant import Assistant
from app.db.models.user import User
from app.repositories.assistant_repository import AssistantRepository
from app.repositories.document_repository import DocumentRepository
from app.routers.v1.security import get_company_context, get_current_admin_user
from app.schemas.assistant import AssistantCreate, AssistantResponse, AssistantUpdate
from app.schemas.document import DocumentResponse

router = APIRouter()


def _get_or_404(db: Session, assistant_id: int, company_id: int) -> Assistant:
    assistant = AssistantRepository(db).get_of_company(assistant_id, company_id)
    if not assistant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asistente no encontrado")
    return assistant


def _with_counts(db: Session, assistant: Assistant) -> AssistantResponse:
    doc_count = DocumentRepository(db).count_by_assistant(assistant.id)
    widget_count = AssistantRepository(db).count_widgets(assistant.id)
    response = AssistantResponse.model_validate(assistant)
    return response.model_copy(update={"document_count": doc_count, "widget_count": widget_count})


# Leer asistentes queda abierto (el chat los lista); crearlos, editarlos o
# borrarlos cambia lo que responde toda la empresa y exige admin.
@router.post("/", response_model=AssistantResponse, status_code=status.HTTP_201_CREATED, summary="Crear asistente")
async def create_assistant(
    data: AssistantCreate,
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin_user),
    company_id: int = Depends(get_company_context),
):
    assistant = Assistant(**data.model_dump(), company_id=company_id)
    assistant = AssistantRepository(db).create(assistant)
    return _with_counts(db, assistant)


@router.get("/", response_model=List[AssistantResponse], summary="Listar asistentes")
async def list_assistants(
    skip: int = 0,
    limit: int = 100,
    active_only: Optional[bool] = None,
    db: Session = Depends(get_db),
    company_id: int = Depends(get_company_context),
):
    assistants = AssistantRepository(db).list_by_company(
        company_id, skip=skip, limit=limit, active_only=active_only
    )
    return [_with_counts(db, a) for a in assistants]


@router.get("/{assistant_id}", response_model=AssistantResponse, summary="Obtener asistente")
async def get_assistant(
    assistant_id: int,
    db: Session = Depends(get_db),
    company_id: int = Depends(get_company_context),
):
    return _with_counts(db, _get_or_404(db, assistant_id, company_id))


@router.put("/{assistant_id}", response_model=AssistantResponse, summary="Actualizar asistente")
async def update_assistant(
    assistant_id: int,
    data: AssistantUpdate,
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin_user),
    company_id: int = Depends(get_company_context),
):
    assistant = _get_or_404(db, assistant_id, company_id)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(assistant, key, value)
    assistant = AssistantRepository(db).update(assistant)
    return _with_counts(db, assistant)


@router.delete("/{assistant_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Eliminar asistente")
async def delete_assistant(
    assistant_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin_user),
    company_id: int = Depends(get_company_context),
):
    assistant = _get_or_404(db, assistant_id, company_id)

    # Cada asistente es un espacio de conocimiento con su propia documentación:
    # borrarlo mientras tenga documentos o widgets vinculados dejaría esos
    # registros huérfanos a nivel empresa, filtrándose luego a otros espacios
    # vía el namespace compartido. Se exige reasignarlos o borrarlos antes.
    doc_count = DocumentRepository(db).count_by_assistant(assistant_id)
    widget_count = AssistantRepository(db).count_widgets(assistant_id)
    if doc_count or widget_count:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"No se puede eliminar: tiene {doc_count} documento(s) y {widget_count} widget(s) "
                "vinculados. Reasígnalos a otro asistente o elimínalos primero."
            ),
        )

    assistant.deleted_at = datetime.now(timezone.utc)
    db.commit()
    return None


@router.get("/{assistant_id}/documents", response_model=List[DocumentResponse], summary="Documentos del asistente")
async def list_assistant_documents(
    assistant_id: int,
    db: Session = Depends(get_db),
    company_id: int = Depends(get_company_context),
):
    _get_or_404(db, assistant_id, company_id)
    return DocumentRepository(db).get_by_assistant(assistant_id)
