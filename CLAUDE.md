# KnowSpace Backend - Claude AI Assistant Guide

## Project Overview
FastAPI backend for KnowSpace (SaaS multi-tenant) with PostgreSQL (Supabase) and JWT authentication.

## Project Structure
```
KnowledgeSpace/
├── api/                        # Python FastAPI backend (deployable unit)
│   ├── main.py                 # FastAPI app entry point, router registration
│   ├── requirements.txt
│   ├── migrate_*.sql           # Migraciones manuales (no hay Alembic)
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
Cada recurso está filtrado por el `company_id` del usuario autenticado, nunca del request body. El JWT solo lleva el email (`sub`); `get_current_user` carga el usuario de la base de datos y su empresa sale de ahí.

## Key Patterns
1. **Models**: heredan de `Base` (`app.core.database`)
2. **Schemas**: `model_config = {"from_attributes": True}` (Pydantic v2, sin `class Config`)
3. **Routers**: `async def` + `Depends(get_db)` + `Depends(get_current_user)`
4. **Repositories**: `BaseRepository[T]` genérico en `repositories/base.py`
5. **Enum de estado**: `DocumentStatus(str, Enum)` en `schemas/document.py`

## Development
```bash
# Instalar dependencias (solo la primera vez)
cd api
pip install -r requirements.txt

# Arrancar servidor — SIEMPRE desde api/
python -m uvicorn main:app --host 127.0.0.1 --port 8002 --reload
```

> El `cd api` no es opcional y resuelve dos cosas distintas: pone `api/` en
> `sys.path` (para que `main` y el paquete `app` se importen) **y** deja el
> directorio de trabajo donde está el `.env`, que `config.py` carga por ruta
> relativa. Lanzar desde la raíz con `--app-dir api` arregla lo primero pero no
> lo segundo, y la app falla con 5 errores de validación de Pydantic.
> Ver `COMO_ARRANCAR.md` para el detalle.

- **Swagger UI**: `http://127.0.0.1:8002/docs`
- **Crear tablas y sembrar datos iniciales**: `POST /api/v1/setup` — no hay
  script. El endpoint de bootstrap hace `Base.metadata.create_all`, siembra los
  tipos de notificación y crea la primera empresa con su superadmin. Solo
  funciona si no existe ningún usuario; ver `README.md`.

## Deploy — GCP Cloud Run
```bash
cd api
gcloud builds submit --tag gcr.io/TU_PROYECTO/knowspace-api
gcloud run deploy knowspace-api --image gcr.io/TU_PROYECTO/knowspace-api \
  --platform managed --region us-central1 \
  --set-env-vars="DATABASE_URL=...,SECRET_KEY=..."
```
