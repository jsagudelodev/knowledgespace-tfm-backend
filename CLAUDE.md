# KnowledgeSpace Backend — guía para Claude Code

## Qué es
API FastAPI de KnowledgeSpace, plataforma multiempresa de asistentes RAG.
PostgreSQL (Supabase) con SQLAlchemy 2.0 y Alembic, Pinecone como índice
vectorial, S3 para los archivos y OpenAI para embeddings y generación.
Visión general y documentación: `README.md`; alcance de la entrega:
`ALCANCE_TFM.md`.

## Estructura
```
knowledgespace-tfm-backend/
├── Dockerfile                  # imagen para Cloud Run (en la raíz)
├── api/                        # unidad desplegable
│   ├── main.py                 # app FastAPI y registro de los 15 routers
│   ├── alembic/                # migraciones versionadas (alembic upgrade head)
│   ├── migrate_*.sql           # migraciones manuales anteriores a Alembic (histórico)
│   ├── experimentos/           # experimentos EXP-01..15; índice en REGISTRO.md
│   ├── tests/                  # pytest
│   └── app/
│       ├── core/               # config (Settings), database, security (JWT),
│       │                       # error_handlers, exceptions, observabilidad
│       ├── db/models/          # 14 modelos SQLAlchemy
│       ├── repositories/       # BaseRepository[T] + uno por entidad
│       ├── routers/v1/         # endpoints REST; security.py = dependencias de rol
│       ├── schemas/            # Pydantic v2
│       └── services/           # lógica de negocio e integraciones:
│                               #   rag_factory.py elige la configuración RAG,
│                               #   rag_service*.py (seis configuraciones),
│                               #   embedding, pinecone, s3, pdf, cost_tracking,
│                               #   knowledge_gap_index_service, alcance_global
└── docs/
    ├── TFM/                    # documentación de entrega (RAG_PIPELINE, MODELO_DATOS,
    │                           # MANEJO_ERRORES, DEPLOYMENT, ENTREGA_TFM…)
    └── trabajo/                # notas de trabajo
```

## Reglas del código
- **Capas:** los routers no consultan la base de datos; eso es de los
  repositorios (lo vigila `tests/test_capas_sin_consultas_en_routers.py`; la
  única excepción es `setup.py`). Los servicios son los únicos que hablan con
  proveedores externos.
- **Multiempresa:** cada recurso se filtra por el `company_id` del usuario
  autenticado, nunca por lo que envía la petición. El JWT solo lleva el email
  (`sub`); `get_current_user` carga el usuario y su empresa de la base de
  datos. Un recurso de otra empresa responde 404, no 403.
- **Roles:** `user` | `admin` | `superadmin`, con `get_current_user`,
  `get_current_admin_user` y `get_current_superadmin` en `routers/v1/security.py`.
- **Pinecone:** un namespace por asistente, `company-{id}-assistant-{aid}`. Los
  experimentos solo escriben en namespaces `exp-*`.
- **Errores:** fallo de proveedor → 503, excepción no prevista → 500, siempre
  JSON y sin detalle técnico (`core/error_handlers.py`, `docs/TFM/MANEJO_ERRORES.md`).
- **Parámetros del RAG** en `core/config.py` (`RAG_CONFIGURACION`,
  `RAG_UMBRAL_RELEVANCIA`, `RAG_TOP_K`, `RAG_TEMPERATURA`…), por variable de
  entorno. Cambiar el modelo de embedding o el troceado obliga a reindexar y a
  repetir la medición del umbral.
- **Cifras:** solo las de `api/experimentos/resultados/` o la memoria.
- Schemas con `model_config = {"from_attributes": True}`; modelos heredan de
  `Base` (`app.core.database`).

## Desarrollo
```bash
cd api                                   # obligatorio: sys.path y ruta del .env
.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8002 --reload
.venv\Scripts\python.exe -m pytest       # tests
.venv\Scripts\python.exe -m alembic upgrade head
```
- Usar siempre el entorno virtual del proyecto, nunca el Python global.
- Swagger: `http://127.0.0.1:8002/docs`.
- Primer arranque: `POST /api/v1/setup` crea la primera empresa y su
  superadmin; solo funciona si no existe ningún usuario. Detalle en
  `COMO_ARRANCAR.md`.

## Despliegue
Cloud Run, servicio `knowledgespace-tfm-backend`, región `europe-west1`, con
despliegue continuo desde `main` (Cloud Build). Pasos y variables en
`docs/TFM/DEPLOYMENT.md`.
