from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

import app.db.models  # noqa: F401 — registra todos los mappers antes de que SQLAlchemy resuelva relaciones

from app.core.config import settings
from app.core.database import engine
from app.routers.v1.auth import router as auth_router
from app.routers.v1.users import router as users_router
from app.routers.v1.companies import router as companies_router
from app.routers.v1.categories import router as categories_router
from app.routers.v1.tags import router as tags_router
from app.routers.v1.documents import router as documents_router
from app.routers.v1.assistants import router as assistants_router
from app.routers.v1.chat import router as chat_router
from app.routers.v1.conversation import router as conversation_router
from app.routers.v1.message import router as message_router
from app.routers.v1.feedback import router as feedback_router
from app.routers.v1.notification import router as notification_router
from app.routers.v1.knowledge_gaps import router as knowledge_gaps_router
from app.routers.v1.cost_tracking import router as cost_tracking_router
from app.routers.v1.dashboard import router as dashboard_router
from app.routers.v1.setup import router as setup_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicializa recursos al arrancar y los libera al apagar."""
    from app.services.pinecone_service import PineconeService
    PineconeService().asegurar_indice()
    yield


app = FastAPI(
    title="KnowledgeSpace API",
    version="0.1.0",
    description="Backend SaaS multi-tenant para gestión de conocimiento con IA.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth_router,         prefix="/api/v1/auth",          tags=["auth"])
app.include_router(users_router,        prefix="/api/v1/users",         tags=["users"])
app.include_router(companies_router,    prefix="/api/v1/companies",     tags=["companies"])
app.include_router(categories_router,   prefix="/api/v1/categories",    tags=["categories"])
app.include_router(tags_router,         prefix="/api/v1/tags",          tags=["tags"])
app.include_router(documents_router,    prefix="/api/v1/documents",     tags=["documents"])
app.include_router(assistants_router,   prefix="/api/v1/assistants",    tags=["assistants"])
app.include_router(chat_router,         prefix="/api/v1/chat",          tags=["chat"])
app.include_router(conversation_router, prefix="/api/v1/conversations", tags=["conversations"])
app.include_router(message_router,      prefix="/api/v1/messages",      tags=["messages"])
app.include_router(feedback_router,       prefix="/api/v1/feedback",        tags=["feedback"])
app.include_router(notification_router,   prefix="/api/v1/notifications",   tags=["notifications"])
app.include_router(knowledge_gaps_router, prefix="/api/v1/knowledge-gaps",   tags=["knowledge-gaps"])
app.include_router(cost_tracking_router,  prefix="/api/v1/cost-tracking",    tags=["cost-tracking"])
app.include_router(dashboard_router,      prefix="/api/v1/dashboard",        tags=["dashboard"])
app.include_router(setup_router,          prefix="/api/v1/setup",            tags=["setup"])


@app.get("/", tags=["health"])
async def root():
    return {"message": "KnowledgeSpace API funcionando"}


@app.get("/health", tags=["health"])
async def health_check():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception as exc:
        db_status = f"unhealthy: {exc}"

    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "database": db_status,
    }
