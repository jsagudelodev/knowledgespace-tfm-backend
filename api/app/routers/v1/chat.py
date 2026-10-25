"""Chat con el asistente: orquesta RAG (recuperación + generación), persiste
los mensajes con sus fuentes citadas y registra el costo de inferencia.

Dos rutas conviven a propósito: `/message` (síncrona, espera la respuesta
completa) y `/message/stream` (entrega la respuesta token a token por
Server-Sent Events). No es una sustituye a la otra —ver el docstring de
`generate_response_stream` en `rag_service.py`— y ambas comparten toda la
lógica de resolución de asistente, conversación e historial: solo difiere
cómo se llama al RAG y cómo se entrega la respuesta al cliente."""
import json
import time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, get_db
from app.db.models.assistant import Assistant
from app.db.models.conversation import Conversation
from app.db.models.user import User
from app.repositories.assistant_repository import AssistantRepository
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.message_repository import MessageRepository
from app.routers.v1.security import get_current_user
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.alcance_global import es_pregunta_de_alcance_global, responder_alcance_global
from app.services.cost_tracking_service import CostTrackingService
from app.services.rag_factory import crear_rag_service
from app.services.rag_service import RAGUnavailableError

router = APIRouter()


def _resolve_assistant(db: Session, company_id: int, assistant_id: Optional[int]) -> Optional[Assistant]:
    """
    Resuelve el asistente a usar: el solicitado explícitamente, o si no se
    especifica, el primero activo de la empresa. Si la empresa no tiene
    ningún asistente activo, se sigue permitiendo el chat con la
    configuración por defecto (namespace de empresa, prompt genérico).
    """
    repo = AssistantRepository(db)
    if assistant_id:
        assistant = repo.get_active_of_company(assistant_id, company_id)
        if not assistant:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asistente no encontrado o inactivo")
        return assistant
    return repo.get_first_active(company_id)


def _preparar_conversacion(
    db: Session, current_user: User, payload: ChatRequest
) -> tuple[Optional[Assistant], Conversation, list[dict]]:
    """Resuelve asistente y conversación, guarda el mensaje del usuario y
    arma el historial — el primer tramo, idéntico en la ruta síncrona y en la
    de streaming, antes de que cada una llame al RAG a su manera."""
    assistant = _resolve_assistant(db, current_user.company_id, payload.assistant_id)

    conv_repo = ConversationRepository(db)
    if payload.conversation_id:
        conversation = conv_repo.get_by_id_and_user(payload.conversation_id, current_user.id)
        if not conversation:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversación no encontrada")
    else:
        conversation = conv_repo.create_for_user(
            company_id=current_user.company_id,
            user_id=current_user.id,
            title=payload.message[:50],
        )

    msg_repo = MessageRepository(db)

    # Historial ANTES de agregar el mensaje actual, para no duplicarlo en el prompt
    history = msg_repo.get_by_conversation(conversation.id, skip=0, limit=20)
    conversation_history = [{"role": m.role, "content": m.content} for m in history]

    msg_repo.create_message(conversation_id=conversation.id, role="user", content=payload.message)

    return assistant, conversation, conversation_history


def _registrar_costes(
    db: Session, company_id: int, user_id: int, conversation_id: int,
    assistant_id: Optional[int], result: dict, duracion_ms: int,
) -> Optional[float]:
    """Registra el coste de la generación, el embedding de la consulta y
    cualquier llamada auxiliar (descomposición, reordenado) — igual para la
    ruta síncrona y la de streaming, ambas terminan con el mismo `result`.

    Recibe identificadores sueltos y no los objetos `User`/`Conversation`/
    `Assistant` a propósito: en la ruta de streaming se llama mucho después de
    que termine la función del endpoint, con una sesión de base de datos
    distinta a la que cargó esos objetos —ver `_generar_eventos_sse`—, y un
    objeto ORM de otra sesión ya cerrada lanza `DetachedInstanceError` en
    cuanto se le toca un atributo."""
    cost_usd = CostTrackingService(db).record(
        company_id=company_id,
        model=result["model"],
        operation="chat",
        input_tokens=result["input_tokens"],
        output_tokens=result["output_tokens"],
        user_id=user_id,
        conversation_id=conversation_id,
        assistant_id=assistant_id,
        duration_ms=duracion_ms,
    )

    # Embeber la pregunta es una segunda llamada de pago a OpenAI, aparte de la
    # del modelo generativo. Se registra aparte para que `operation` distinga
    # ambas. El importe redondea a cero por la precisión de la columna
    # (Numeric(12,6)), pero los tokens quedan exactos: el costo real siempre es
    # recomputable a partir de ellos y del modelo, ambos almacenados.
    CostTrackingService(db).record(
        company_id=company_id,
        model=result["embedding_model"],
        operation="embedding",
        input_tokens=result["embedding_tokens"],
        user_id=user_id,
        conversation_id=conversation_id,
        assistant_id=assistant_id,
    )

    # Las configuraciones avanzadas llaman al modelo una vez más —para
    # descomponer la consulta o para reordenar los fragmentos— y esas llamadas
    # se facturan igual que las otras dos. Se registran con su propia
    # `operation` para que el desglose por tipo siga siendo legible y para
    # poder responder cuánto cuesta cada mejora, no solo si funciona.
    # En la configuración básica la lista viene vacía y este bucle no se ejecuta.
    for llamada in result.get("llamadas_auxiliares", []):
        CostTrackingService(db).record(
            company_id=company_id,
            model=llamada["modelo"],
            operation=llamada["operacion"],
            input_tokens=llamada["tokens_entrada"],
            output_tokens=llamada["tokens_salida"],
            user_id=user_id,
            conversation_id=conversation_id,
            assistant_id=assistant_id,
            duration_ms=llamada.get("duracion_ms"),
        )

    return cost_usd


@router.post("/message", response_model=ChatResponse, summary="Enviar mensaje al chat IA")
async def chat_message(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    assistant, conversation, conversation_history = _preparar_conversacion(db, current_user, payload)
    msg_repo = MessageRepository(db)

    # Preguntas de alcance global ("¿qué documentos tienes?") no pasan por el
    # RAG: la recuperación por similitud nunca puede responderlas bien, por
    # diseño. Ver `app/services/alcance_global.py` para el porqué completo.
    # Sin llamada a OpenAI ni a Pinecone, así que no hay coste que registrar.
    if es_pregunta_de_alcance_global(payload.message):
        contenido = responder_alcance_global(db, current_user.company_id, assistant.id if assistant else None)
        assistant_message = msg_repo.create_message(
            conversation_id=conversation.id, role="assistant", content=contenido, sources=[], token_count=0,
        )
        return ChatResponse(
            message_id=assistant_message.id,
            conversation_id=conversation.id,
            role="assistant",
            content=assistant_message.content,
            sources=[],
            created_at=assistant_message.created_at,
            assistant_id=assistant.id if assistant else None,
            cost_usd=0.0,
        )

    # El pipeline depende de dos servicios externos —OpenAI y Pinecone— que
    # pueden fallar por cuota, tiempo de espera o caída. Sin esta traducción, el
    # cliente recibía un 500 con la traza en lugar de un mensaje accionable.
    # Se responde 503 y no 500 porque el fallo es de disponibilidad y reintentar
    # tiene sentido; el detalle técnico queda en el log, no en la respuesta.
    #
    # El mensaje del usuario ya se guardó arriba y se conserva aunque esto
    # falle: la pregunta se hizo, y perderla haría que el reintento no tuviera
    # el historial completo.
    # Qué configuración atiende la consulta lo decide `RAG_CONFIGURACION`, no
    # este enrutador: las tres clases conviven y el chat no tiene por qué saber
    # cuál está activa. Ver `rag_factory` para el porqué de cada una.
    rag = crear_rag_service()
    inicio = time.perf_counter()
    try:
        result = rag.generate_response(
            query=payload.message,
            company_id=current_user.company_id,
            conversation_history=conversation_history,
            assistant_id=assistant.id if assistant else None,
            system_prompt_override=assistant.system_prompt if assistant else None,
            model_override=assistant.model if assistant else None,
        )
    except RAGUnavailableError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "El asistente no está disponible en este momento "
                f"(falló la etapa: {e.etapa}). Vuelve a intentarlo en unos segundos."
            ),
        ) from e
    duracion_ms = round((time.perf_counter() - inicio) * 1000)

    assistant_message = msg_repo.create_message(
        conversation_id=conversation.id,
        role="assistant",
        content=result["content"],
        sources=result["sources"],
        token_count=result.get("token_count"),
    )

    cost_usd = _registrar_costes(
        db, current_user.company_id, current_user.id, conversation.id,
        assistant.id if assistant else None, result, duracion_ms,
    )

    return ChatResponse(
        message_id=assistant_message.id,
        conversation_id=conversation.id,
        role="assistant",
        content=assistant_message.content,
        sources=result["sources"],
        created_at=assistant_message.created_at,
        assistant_id=assistant.id if assistant else None,
        cost_usd=cost_usd,
    )


def _generar_eventos_sse(
    rag,
    message: str,
    company_id: int,
    user_id: int,
    assistant_id: Optional[int],
    system_prompt_override: Optional[str],
    model_override: Optional[str],
    conversation_id: int,
    conversation_history: list[dict],
):
    """El cuerpo del streaming, como función de módulo y no anidada en el
    endpoint para poder probarla con dobles —igual que el resto del
    proyecto—, sin levantar la aplicación ni tocar una base de datos real.

    Recibe identificadores sueltos (`company_id`, `user_id`, `conversation_id`,
    `assistant_id`) y no los objetos `User`/`Conversation`/`Assistant`, y abre
    su PROPIA sesión de base de datos en vez de recibir la del endpoint.

    Es a propósito, no una preferencia de estilo: la dependencia `Depends(get_db)`
    cierra su sesión en cuanto la función del endpoint *retorna* —que para una
    `StreamingResponse` ocurre justo después de construirla, antes de que este
    generador escriba un solo byte—. Usar esa sesión aquí dentro, o un objeto
    ORM cargado con ella (`current_user.company_id`, por ejemplo), lanza
    `DetachedInstanceError` en cuanto el proceso ya lleva un rato corriendo:
    pasó inadvertido en las primeras pruebas porque el primer acceso
    (`_preparar_conversacion`) sí ocurre a tiempo, dentro del endpoint.

    Eventos emitidos, cada uno una línea `data: <json>\\n\\n`:

    - `delta`: un trozo de texto (`content`), según va llegando del modelo.
    - `done`: la respuesta ya está completa y persistida. Trae `message_id`,
      `conversation_id`, `sources` y `cost_usd` — lo mismo que devuelve
      `ChatResponse` en la ruta síncrona, para que el cliente pueda terminar
      de pintar la respuesta igual en ambos casos.
    - `error`: el RAG falló (OpenAI o Pinecone no respondieron). Puede llegar
      DESPUÉS de uno o más `delta` —la conexión se cae a mitad de la
      respuesta—, así que el cliente debe tratar un `error` como el cierre
      definitivo del stream, no como algo que se recupera solo.
    """
    db = SessionLocal()
    try:
        msg_repo = MessageRepository(db)

        # Preguntas de alcance global ("¿qué documentos tienes?") no pasan
        # por el RAG, en streaming tampoco — ver `app/services/alcance_global.py`.
        # Se entrega como un único `delta` (no hay nada que trocear: no vino
        # de un modelo generándola palabra a palabra) y el `done` sin coste.
        if es_pregunta_de_alcance_global(message):
            contenido = responder_alcance_global(db, company_id, assistant_id)
            yield f"data: {json.dumps({'type': 'delta', 'content': contenido})}\n\n"
            assistant_message = msg_repo.create_message(
                conversation_id=conversation_id, role="assistant", content=contenido, sources=[], token_count=0,
            )
            payload_done = {
                "type": "done",
                "message_id": assistant_message.id,
                "conversation_id": conversation_id,
                "sources": [],
                "assistant_id": assistant_id,
                "cost_usd": 0.0,
            }
            yield f"data: {json.dumps(payload_done)}\n\n"
            return

        inicio = time.perf_counter()
        try:
            for evento in rag.generate_response_stream(
                query=message,
                company_id=company_id,
                conversation_history=conversation_history,
                assistant_id=assistant_id,
                system_prompt_override=system_prompt_override,
                model_override=model_override,
            ):
                if evento["type"] == "delta":
                    yield f"data: {json.dumps({'type': 'delta', 'content': evento['content']})}\n\n"
                    continue

                # type == "done": el RAG ya terminó, falta persistir y facturar
                # -exactamente lo que hace la ruta síncrona tras `generate_response`-.
                duracion_ms = round((time.perf_counter() - inicio) * 1000)
                assistant_message = msg_repo.create_message(
                    conversation_id=conversation_id,
                    role="assistant",
                    content=evento["content"],
                    sources=evento["sources"],
                    token_count=evento.get("token_count"),
                )
                cost_usd = _registrar_costes(
                    db, company_id, user_id, conversation_id, assistant_id, evento, duracion_ms,
                )
                payload_done = {
                    "type": "done",
                    "message_id": assistant_message.id,
                    "conversation_id": conversation_id,
                    "sources": evento["sources"],
                    "assistant_id": assistant_id,
                    "cost_usd": cost_usd,
                }
                yield f"data: {json.dumps(payload_done)}\n\n"
        except RAGUnavailableError as e:
            # Ya pueden haberse enviado trozos de respuesta: no hay manera de
            # cambiar el código de estado HTTP a esta altura, así que el fallo
            # se comunica como un evento más, no como un 503 -eso solo es
            # posible si el error ocurre antes del primer `yield`-.
            yield f"data: {json.dumps({'type': 'error', 'etapa': e.etapa})}\n\n"
    finally:
        db.close()


@router.post("/message/stream", summary="Enviar mensaje al chat IA, con la respuesta en streaming")
async def chat_message_stream(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Igual que `/message`, pero la respuesta llega por *Server-Sent Events*
    a medida que el modelo la va generando, en vez de de un solo golpe al
    final. No reduce el tiempo total de la consulta —el RAG hace exactamente
    el mismo trabajo—, reduce la ESPERA hasta que aparece el primer token. Ver
    `_generar_eventos_sse` para la forma de los eventos y por qué recibe
    identificadores sueltos en vez de los objetos de esta sesión."""
    assistant, conversation, conversation_history = _preparar_conversacion(db, current_user, payload)
    rag = crear_rag_service()

    return StreamingResponse(
        _generar_eventos_sse(
            rag,
            message=payload.message,
            company_id=current_user.company_id,
            user_id=current_user.id,
            assistant_id=assistant.id if assistant else None,
            system_prompt_override=assistant.system_prompt if assistant else None,
            model_override=assistant.model if assistant else None,
            conversation_id=conversation.id,
            conversation_history=conversation_history,
        ),
        media_type="text/event-stream",
    )
