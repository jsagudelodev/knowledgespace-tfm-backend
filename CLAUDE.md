# KnowSpace Backend - Claude AI Assistant Guide

## Project Overview
FastAPI backend for KnowSpace (SaaS multi-tenant) with PostgreSQL (Supabase) and JWT authentication.

## Project Structure
```
KnowledgeSpace/
├── api/                        # Python FastAPI backend (deployable unit)
│   ├── main.py                 # FastAPI app entry point, router registration
│   ├── requirements.txt
│   ├── create_tables.py        # Script: crea tablas y seed de notification_types
│   ├── Dockerfile              # Multi-stage build para Cloud Run
│   ├── .dockerignore
│   ├── .env                    # Variables locales (no commitear)
│   ├── .env.example
│   └── app/
│       ├── core/
│       │   ├── config.py       # Pydantic Settings — todas las env vars
│       │   ├── database.py     # Base, engine, SessionLocal, get_db  ← fuente única
│       │   └── security.py     # JWT: create_access_token, decode_token
│       ├── db/
│       │   └── models/         # SQLAlchemy ORM models (13 tablas)
│       │       ├── user.py
│       │       ├── company.py
│       │       ├── assistant.py
│       │       ├── category.py
│       │       ├── tag.py
│       │       ├── document.py
│       │       ├── conversation.py
│       │       ├── message.py
│       │       ├── feedback.py
│       │       ├── notification.py
│       │       ├── notification_type.py
│       │       ├── knowledge_gap.py
│       │       └── widget.py
│       ├── repositories/       # Patrón repositorio (BaseRepository[T] genérico)
│       │   ├── base.py
│       │   ├── user_repository.py
│       │   ├── company_repository.py
│       │   ├── category_repository.py
│       │   ├── tag_repository.py
│       │   ├── document_repository.py
│       │   └── feedback_repository.py
│       ├── routers/
│       │   └── v1/             # Todos los endpoints REST
│       │       ├── auth.py         # /api/v1/auth
│       │       ├── users.py        # /api/v1/users
│       │       ├── companies.py    # /api/v1/companies
│       │       ├── categories.py   # /api/v1/categories
│       │       ├── tags.py         # /api/v1/tags
│       │       ├── documents.py    # /api/v1/documents
│       │       ├── conversation.py # /api/v1/conversations
│       │       ├── message.py      # /api/v1/messages
│       │       ├── feedback.py     # /api/v1/feedback
│       │       ├── notification.py # /api/v1/notifications
│       │       ├── knowledge_gaps.py # /api/v1/knowledge-gaps
│       │       └── security.py     # get_current_user, get_current_admin_user, get_current_superadmin
│       ├── schemas/            # Pydantic v2 schemas (validación request/response)
│       │   ├── user.py
│       │   ├── company.py
│       │   ├── category.py
│       │   ├── tag.py
│       │   ├── document.py
│       │   ├── conversation.py
│       │   ├── message.py
│       │   ├── feedback.py
│       │   ├── notification.py
│       │   ├── notification_type.py
│       │   ├── knowledge_gap.py
│       │   └── token.py
│       └── services/           # Lógica de negocio / integraciones externas
│           ├── document_service.py
│           ├── notification_service.py
│           ├── pdf_service.py
│           ├── s3_service.py
│           ├── embedding_service.py        # OpenAI embeddings
│           ├── pinecone_service.py         # vector store (namespaces por empresa/asistente)
│           ├── rag_service.py              # retrieval + generación del chat
│           └── knowledge_gap_index_service.py  # candidatos/alias/respuesta/verificación de Preguntas sin respuesta — ver docs/RAG_PIPELINE.md §8
├── docs/                       # Documentación técnica
├── venv/                       # Virtual environment (activar desde raíz)
└── CLAUDE.md
```

## Database Connection
- **ORM**: SQLAlchemy 2.0
- **Database**: PostgreSQL (Supabase)
- **Fuente única**: `app/core/database.py` → `Base`, `engine`, `SessionLocal`, `get_db`
- Todos los modelos importan `Base` desde `app.core.database`

## Auth & Roles
- JWT via `python-jose`; tokens en `Authorization: Bearer <token>`
- Roles: `user` | `admin` | `superadmin`
- Guards en `app/routers/v1/security.py`:
  - `get_current_user` — cualquier usuario activo
  - `get_current_admin_user` — admin o superadmin
  - `get_current_superadmin` — solo superadmin

## Multi-tenant
Cada recurso está filtrado por `company_id` extraído del JWT, nunca del request body.

## Key Patterns
1. **Models**: heredan de `Base` (`app.core.database`)
2. **Schemas**: `model_config = {"from_attributes": True}` (Pydantic v2, sin `class Config`)
3. **Routers**: `async def` + `Depends(get_db)` + `Depends(get_current_user)`
4. **Repositories**: `BaseRepository[T]` genérico en `repositories/base.py`
5. **Enum de estado**: `DocumentStatus(str, Enum)` en `schemas/document.py`

## Development
```bash
# Activar venv (desde raíz del proyecto)
venv\Scripts\activate          # Windows
source venv/bin/activate       # Linux/Mac

# Arrancar servidor (desde api/)
cd api
uvicorn main:app --reload --port 8002
```

- **Swagger UI**: `http://127.0.0.1:8002/docs`
- **Crear tablas**: `python create_tables.py` (desde `api/`)

## Deploy — GCP Cloud Run
```bash
cd api
gcloud builds submit --tag gcr.io/TU_PROYECTO/knowspace-api
gcloud run deploy knowspace-api --image gcr.io/TU_PROYECTO/knowspace-api \
  --platform managed --region us-central1 \
  --set-env-vars="DATABASE_URL=...,SECRET_KEY=..."
```
