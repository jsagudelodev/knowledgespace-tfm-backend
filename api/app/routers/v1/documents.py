"""Gestión de documentos: subida a S3 y disparo del pipeline RAG de ingesta
(extracción → chunking → embeddings → Pinecone) en segundo plano, para que el
usuario reciba respuesta inmediata mientras el documento se procesa."""
import uuid
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.db.models.document import Document
from app.db.models.notification import NotificationEntityType
from app.db.models.user import User
from app.repositories.category_repository import CategoryRepository
from app.repositories.document_repository import DocumentRepository
from app.routers.v1.security import get_company_context, get_current_user
from app.schemas.document import DocumentResponse, DocumentStatus, DocumentUpdate
from app.services.document_service import DocumentService
from app.services.notification_service import NotificationService
from app.services.pinecone_service import PineconeService
from app.services.s3_service import S3Service

router = APIRouter()


def _exigir_dueno_o_admin(documento: Document, usuario: User) -> None:
    """Un usuario puede gestionar lo que subió él; lo de otros, solo un admin.

    Subir sigue abierto a todos —aportar a la base de conocimiento no debe
    depender del admin—, pero borrar, recategorizar o reprocesar un documento
    ajeno cambia lo que el asistente responde a toda la empresa. Antes cualquier
    usuario podía borrar cualquier documento (encontrado el 2026-11-02 con la
    cuenta de demo de rol `user`).
    """
    if usuario.role in ("admin", "superadmin") or documento.uploaded_by == usuario.id:
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Solo quien subió el documento o un administrador puede modificarlo.",
    )


def _notificar_documento(
    db: Session,
    company_id: int,
    user_id: int,
    type_name: str,
    title: str,
    message: str,
    document_id: int,
) -> None:
    """
    Crea una notificación de ciclo de vida de documento sin romper el flujo si falla
    (tipo no sembrado, error de BD, etc.) — la notificación es un side-effect, no algo crítico.
    """
    import logging
    try:
        NotificationService(db).create_for_user(
            company_id=company_id,
            user_id=user_id,
            type_name=type_name,
            title=title,
            message=message,
            entity_type=NotificationEntityType.DOCUMENT,
            entity_id=document_id,
        )
    except Exception:
        logging.getLogger("uvicorn.error").warning(
            f"[Notification] No se pudo crear notificación '{type_name}' para document_id={document_id}",
            exc_info=True,
        )


def _procesar_documento_background(
    document_id: int,
    s3_key: str,
    file_type: str,
    company_id: int,
    assistant_id: Optional[int],
    original_filename: str,
    uploaded_by: int,
) -> None:
    """
    Tarea en segundo plano que ejecuta el pipeline RAG completo.

    Flujo:
      1. Descarga el archivo desde S3 a memoria
      2. Extrae el texto según el tipo de archivo
      3. Divide el texto en chunks
      4. Genera embeddings en batch (una llamada a OpenAI por cada 100 chunks)
      5. Sube los vectores a Pinecone con metadata
      6. Actualiza el estado del documento en la BD (completed / failed)

    Se ejecuta de forma asíncrona después de responder al cliente —
    el usuario ve el documento en estado "processing" mientras esto ocurre.
    """
    import logging
    import traceback

    from app.core.config import settings
    from app.core.database import SessionLocal
    from app.services.cost_tracking_service import CostTrackingService
    from app.services.embedding_service import EmbeddingService
    from app.services.pdf_service import PDFService
    logger = logging.getLogger("uvicorn.error")

    db = SessionLocal()
    try:
        logger.warning(f"[RAG] Iniciando document_id={document_id} s3_key={s3_key} file_type={file_type}")

        # ── 1 + 2. Descargar desde S3 y extraer texto ────────────────────
        # Usa chunking semántico: agrupa oraciones en vez de cortar por
        # caracteres fijos. Medido el 2026-10-07 sobre el corpus de evaluación
        # (3 documentos, 24 fragmentos): los cortes a mitad de palabra pasan
        # del 79,2 % al 0,0 %, y se indexa un 19 % menos de texto al no
        # necesitar solapamiento. La contrapartida es menor regularidad de
        # tamaño: la desviación típica sube de 107 a 228 caracteres en
        # material esquemático.
        # Cifras y método en experimentos/resultados/chunking_2026-10-07.json
        # y experimentos/README.md.
        chunks, paginas = PDFService.procesar(
            s3_key, file_type=file_type, semantico=True
        )
        logger.warning(
            f"[RAG] Texto extraído: {len(chunks)} chunks, {paginas} páginas "
            f"[chunking=semántico]"
        )

        # ── 3. Generar embeddings en batch ────────────────────────────────
        embedding_svc = EmbeddingService()
        embeddings, embedding_tokens = embedding_svc.generar_embeddings_batch_con_uso(chunks)

        # El costo ya se incurrió en OpenAI en este punto, independientemente
        # de si Pinecone/BD fallan después — se registra ya mismo.
        CostTrackingService(db).record(
            company_id=company_id,
            model=settings.OPENAI_EMBEDDING_MODEL,
            operation="embedding",
            input_tokens=embedding_tokens,
            user_id=uploaded_by,
            assistant_id=assistant_id,
            document_id=document_id,
        )

        # ── 4. Construir vectores con metadata para Pinecone ──────────────
        namespace = PineconeService.construir_namespace(company_id, assistant_id)
        vectores = [
            {
                "id": f"doc-{document_id}-chunk-{i}",
                "values": embedding,
                "metadata": {
                    "document_id": document_id,
                    "document_name": original_filename,
                    "company_id": company_id,
                    "assistant_id": assistant_id,
                    "chunk_index": i,
                    "text": chunk[:1000],   # guardar extracto del texto para mostrarlo en resultados
                },
            }
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings, strict=True))
        ]

        # ── 5. Subir a Pinecone ────────────────────────────────────────────
        pinecone_svc = PineconeService()

        # Se borran primero los vectores que este documento tuviera indexados.
        # El id de cada vector es `doc-{id}-chunk-{i}`, es decir, depende de la
        # POSICIÓN del fragmento. Un `upsert` sobrescribe las posiciones que
        # vuelve a generar, pero deja vivas las sobrantes: si el documento se
        # reprocesa y produce menos fragmentos que antes —lo que ocurre al
        # pasar de fragmentación por caracteres a por oraciones, que genera un
        # 12,5 % menos—, las posiciones finales quedan huérfanas en el índice
        # con el texto de la versión anterior, y siguen compitiendo en las
        # búsquedas. El borrado previo hace que reindexar sea idempotente.
        #
        # Va aquí, después de generar los embeddings y no antes: si la
        # extracción o la llamada a OpenAI fallan, el índice se queda como
        # estaba en vez de perder el documento.
        pinecone_svc.eliminar_por_documento(document_id, namespace=namespace)

        logger.warning(f"[RAG] Subiendo {len(vectores)} vectores a Pinecone namespace={namespace}")
        pinecone_svc.upsert_vectores(vectores, namespace=namespace)

        # ── 6. Marcar como completado ──────────────────────────────────────
        documento = DocumentRepository(db).get(document_id)
        if documento:
            documento.status = "completed"
            documento.page_count = paginas
            documento.chunk_count = len(chunks)
            db.commit()
            _notificar_documento(
                db, company_id, documento.uploaded_by, "document_processed",
                title="Documento procesado",
                message=f'"{original_filename}" ya está disponible para consultas.',
                document_id=document_id,
            )

    except Exception as exc:
        logger.error(f"[RAG] ERROR document_id={document_id}: {exc}\n{traceback.format_exc()}")
        documento = DocumentRepository(db).get(document_id)
        if documento:
            documento.status = "failed"
            documento.error_message = str(exc)
            db.commit()
            _notificar_documento(
                db, company_id, documento.uploaded_by, "document_failed",
                title="Error al procesar documento",
                # El detalle técnico (p. ej. "NoSuchKey" de S3) ya queda en
                # `error_message` y en el log; al usuario no le sirve.
                message=f'"{original_filename}" no se pudo procesar. Puedes reintentarlo desde Documentos.',
                document_id=document_id,
            )
    finally:
        db.close()


@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED, summary="Subir documento")
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    assistant_id: Optional[int] = Form(None),
    category_id: Optional[int] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    company_id: int = Depends(get_company_context),
):
    file_extension = file.filename.split(".")[-1].lower() if "." in file.filename else ""

    if not DocumentService.validate_file_type(file_extension):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tipo de archivo no soportado. Soportados: PDF, DOCX, TXT, MD",
        )

    if not DocumentService.validate_file_size(file.size):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El archivo supera el límite de 10MB")

    if category_id is not None:
        _validate_category(db, category_id, company_id)

    safe_filename = f"{uuid.uuid4().hex}.{file_extension}"

    try:
        s3 = S3Service()
        key = S3Service.construir_key(company_id, safe_filename)
        file_path = s3.subir_archivo(file, key)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error subiendo archivo a S3: {str(e)}"
        ) from e

    document = Document(
        company_id=company_id,
        uploaded_by=current_user.id,
        assistant_id=assistant_id,
        category_id=category_id,
        filename=safe_filename,
        original_filename=file.filename,
        file_path=file_path,
        file_size=file.size,
        mime_type=file.content_type,
        status=DocumentStatus.PROCESSING,
    )
    documento_creado = DocumentRepository(db).create(document)

    # Disparar el pipeline RAG en segundo plano — el cliente recibe respuesta inmediatamente
    background_tasks.add_task(
        _procesar_documento_background,
        document_id=documento_creado.id,
        s3_key=file_path,
        file_type=file_extension,
        company_id=company_id,
        assistant_id=assistant_id,
        original_filename=file.filename,
        uploaded_by=current_user.id,
    )

    return documento_creado


@router.get("/", response_model=List[DocumentResponse], summary="Listar documentos")
async def list_documents(
    db: Session = Depends(get_db),
    company_id: int = Depends(get_company_context),
):
    return DocumentRepository(db).get_by_company(company_id)


@router.get("/{document_id}", response_model=DocumentResponse, summary="Obtener documento")
async def get_document(
    document_id: int,
    db: Session = Depends(get_db),
    company_id: int = Depends(get_company_context),
):
    document = DocumentRepository(db).get_of_company(document_id, company_id)
    if not document:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    return document


@router.put("/{document_id}", response_model=DocumentResponse, summary="Actualizar documento")
async def update_document(
    document_id: int,
    document: DocumentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    company_id: int = Depends(get_company_context),
):
    repo = DocumentRepository(db)
    db_document = repo.get_of_company(document_id, company_id)
    if not db_document:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    _exigir_dueno_o_admin(db_document, current_user)
    for key, value in document.model_dump(exclude_unset=True).items():
        setattr(db_document, key, value)
    return repo.update(db_document)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Eliminar documento")
async def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    company_id: int = Depends(get_company_context),
):
    repo = DocumentRepository(db)
    db_document = repo.get_of_company(document_id, company_id)
    if not db_document:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    _exigir_dueno_o_admin(db_document, current_user)

    # 1. Eliminar vectores de Pinecone
    try:
        namespace = PineconeService.construir_namespace(
            db_document.company_id,
            db_document.assistant_id,
        )
        PineconeService().eliminar_por_documento(db_document.id, namespace=namespace)
    except Exception:
        pass   # Si Pinecone falla no bloqueamos el borrado — el documento ya no es accesible

    # 2. Eliminar archivo de S3 — primero para no dejar huérfanos
    try:
        S3Service().eliminar_archivo(db_document.file_path)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error eliminando archivo de S3: {str(e)}"
        ) from e

    # 3. Notificar al autor original, si fue otra persona quien borró
    if db_document.uploaded_by != current_user.id:
        _notificar_documento(
            db, db_document.company_id, db_document.uploaded_by, "document_deleted",
            title="Documento eliminado",
            message=f'"{db_document.original_filename}" fue eliminado por {current_user.full_name}.',
            document_id=db_document.id,
        )

    # 4. Eliminar registro de la BD
    repo.delete(db_document)
    return None


@router.get("/{document_id}/download", summary="Descargar documento")
async def download_document(
    document_id: int,
    db: Session = Depends(get_db),
    company_id: int = Depends(get_company_context),
):
    """
    Genera una URL temporal firmada (presigned URL) para descargar el archivo desde S3.
    La URL expira en 1 hora — el archivo nunca se expone públicamente.
    """
    from fastapi.responses import JSONResponse
    documento = DocumentRepository(db).get_of_company(document_id, company_id)
    if not documento:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    try:
        url = S3Service().generar_url_temporal(documento.file_path, segundos=3600)
        return JSONResponse({"url": url, "filename": documento.original_filename})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando URL de descarga: {str(e)}") from e


@router.get("/{document_id}/chunks", summary="Ver los fragmentos indexados de un documento")
async def list_document_chunks(
    document_id: int,
    db: Session = Depends(get_db),
    company_id: int = Depends(get_company_context),
):
    """Devuelve en qué fragmentos quedó dividido el documento tras la ingesta.

    Hasta ahora el sistema informaba de *cuántos* fragmentos generaba, pero no
    de cuáles. Un troceado defectuoso —un corte a mitad de una tabla, una
    sección que la extracción del PDF se dejó— solo se detectaba por sus
    efectos en las respuestas, que es tarde y es indirecto. Esto permite
    comprobarlo sobre el documento concreto.

    Los fragmentos se leen del índice vectorial y no de la base de datos,
    porque **es el índice el que responde a las consultas**: si ambos
    divergieran, lo que importa es lo que el índice contiene. El apartado 7.1
    de la memoria describe un caso en que divergieron durante meses.

    La lista viene vacía mientras el documento se procesa o si la ingesta
    falló; el campo `status` del documento distingue ambas situaciones.
    """
    documento = DocumentRepository(db).get_of_company(document_id, company_id)
    if not documento:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    namespace = PineconeService.construir_namespace(
        documento.company_id, documento.assistant_id
    )
    try:
        fragmentos = PineconeService().listar_por_documento(document_id, namespace=namespace)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"No se pudieron leer los fragmentos del índice: {e}",
        ) from e

    return {
        "document_id": document_id,
        "document_name": documento.original_filename,
        "status": documento.status,
        # El recuento guardado al ingerir y el que el índice tiene ahora. Que
        # no coincidan es la señal de desincronización que el sistema no daba.
        "chunk_count_registrado": documento.chunk_count,
        "chunk_count_indexado": len(fragmentos),
        "sincronizado": documento.chunk_count == len(fragmentos),
        "chunks": fragmentos,
    }


@router.post("/{document_id}/retry", response_model=DocumentResponse, summary="Reintentar procesamiento")
async def retry_document(
    document_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    company_id: int = Depends(get_company_context),
):
    repo = DocumentRepository(db)
    documento = repo.get_of_company(document_id, company_id)
    if not documento:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    _exigir_dueno_o_admin(documento, current_user)

    file_extension = documento.filename.split(".")[-1].lower()
    documento.status = DocumentStatus.PROCESSING
    documento.error_message = None
    repo.update(documento)

    # `uploaded_by` es obligatorio en la tarea y se le pasa el dueño original
    # del documento, no quien reintenta: el reproceso no cambia la autoría.
    # Faltaba, y la tarea moría con TypeError en segundo plano — el documento
    # se quedaba en `processing` para siempre y el usuario no veía ningún error.
    background_tasks.add_task(
        _procesar_documento_background,
        document_id=documento.id,
        s3_key=documento.file_path,
        file_type=file_extension,
        company_id=documento.company_id,
        assistant_id=documento.assistant_id,
        original_filename=documento.original_filename,
        uploaded_by=documento.uploaded_by,
    )

    return documento


def _validate_category(db: Session, category_id: int, company_id: int) -> None:
    category = CategoryRepository(db).get(category_id)
    if not category or category.company_id != company_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Categoría no encontrada")
