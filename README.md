# KnowledgeSpace — Backend

Plataforma SaaS multi-tenant para gestión de conocimiento con IA.  
Backend REST API construido con FastAPI y desplegado en Google Cloud Run.

---

## Tabla de contenidos

- [Stack tecnológico](#stack-tecnológico)
- [Estructura del proyecto](#estructura-del-proyecto)
- [Desarrollo local](#desarrollo-local)
- [Primer arranque](#primer-arranque)
- [Tests](#tests)
- [Despliegue](#despliegue)
- [Documentación](#documentación)

---

## Stack tecnológico

| Capa            | Tecnología                        |
|-----------------|-----------------------------------|
| Lenguaje        | Python 3.11                       |
| Framework       | FastAPI 0.115                     |
| ORM             | SQLAlchemy 2.0                    |
| Base de datos   | PostgreSQL (Supabase)             |
| Autenticación   | JWT — `python-jose` + `passlib`   |
| Servidor        | Gunicorn + Uvicorn workers        |
| Contenedor      | Docker (multi-stage build)        |
| Deploy          | Google Cloud Run                  |
| Migraciones     | Alembic                           |
| Despliegue continuo | Cloud Run conectado a GitHub (ver nota) |

> **Sobre el CI/CD.** Hay **despliegue continuo**: Cloud Run está conectado a
> este repositorio y cada `push` a `main` construye la imagen y la despliega
> (igual que Vercel con el frontend). **No hay integración continua**: ningún
> pipeline ejecuta los tests ni el *linting* como requisito antes de desplegar;
> se ejecutan a mano (ver [Tests](#tests)). Ver `ALCANCE_TFM.md`.

---

## Estructura del proyecto

```
knowledgespace-tfm-backend/
├── api/                        # Servicio backend
│   ├── main.py                 # Entrada FastAPI + registro de routers
│   ├── requirements.txt
│   ├── alembic/                # Migraciones de esquema (Alembic)
│   ├── migrate_*.sql           # Migraciones manuales anteriores a Alembic (histórico)
│   ├── tests/                  # Tests con pytest
│   ├── experimentos/           # Evaluación: dataset, RAGAS, resultados
│   ├── .env.example            # Variables de entorno requeridas
│   └── app/
│       ├── core/               # Configuración, base de datos, seguridad JWT
│       ├── db/
│       │   └── models/         # Modelos SQLAlchemy (14 de las 23 tablas, ver ALCANCE_TFM.md)
│       ├── repositories/       # Capa de acceso a datos (patrón repositorio)
│       ├── routers/v1/         # Endpoints REST (15 routers + security.py, las dependencias de auth)
│       ├── schemas/            # Validación de request/response con Pydantic v2
│       └── services/           # Lógica de negocio e integraciones externas
├── docs/                       # Documentación técnica
├── Dockerfile                  # Multi-stage build para Cloud Run
├── .dockerignore
└── README.md
```

---

## Desarrollo local

### Requisitos

- Python 3.11+
- PostgreSQL accesible (o cuenta Supabase)

### Instalación

```bash
# 1. Clonar y crear el entorno virtual dentro de api/
git clone https://github.com/jsagudelodev/knowledgespace-tfm-backend.git
cd knowledgespace-tfm-backend/api

python -m venv .venv
.venv\Scripts\activate       # Windows
source .venv/bin/activate    # Linux / Mac

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Configurar variables de entorno
cp .env.example .env
# Editar api/.env con tus valores
```

### Arrancar el servidor

```bash
cd api
uvicorn main:app --reload --port 8002
```

| Recurso       | URL                          |
|---------------|------------------------------|
| Swagger UI    | http://127.0.0.1:8002/docs   |
| Health check  | http://127.0.0.1:8002/health |

---

## Primer arranque

Cuando la base de datos está vacía, usa el endpoint de setup para crear las tablas, la primera empresa y el superadmin en un solo paso:

```http
POST /api/v1/setup/
Content-Type: application/json

{
  "company_name": "Mi Empresa",
  "company_email": "admin@empresa.com",
  "full_name": "Admin Principal",
  "email": "admin@empresa.com",
  "password": "TuPassword123!"
}
```

**Respuesta:**
```json
{
  "message": "Sistema inicializado correctamente.",
  "company_id": 1,
  "user_id": 1,
  "access_token": "eyJ..."
}
```

> Este endpoint se deshabilita automáticamente (HTTP 403) una vez que existen usuarios en la base de datos.

---

## Tests

Siempre desde `api/` y con su `.venv` activado: desde la raíz, `pytest` no
encuentra el paquete `app`.
`pytest` viene en `requirements.txt`; `ruff`, en `requirements-dev.txt`.

```bash
cd api
pip install -r requirements-dev.txt
pytest
ruff check .
```

---

## Despliegue

La aplicación está desplegada y se puede probar en
https://knowledgespace-tfm-frontend.vercel.app (el usuario de demostración se
indica en la memoria, no en el repositorio).

- **Backend:** Google Cloud Run (`europe-west1`), construido con el
  `Dockerfile` de la raíz (Gunicorn + workers de Uvicorn). Cloud Run está
  conectado a este repositorio y despliega en cada `push` a `main`.
- **Frontend:** Vercel, conectado al repositorio `knowledgespace-tfm-frontend`.
- **Base de datos:** PostgreSQL gestionado en Supabase; el esquema se migra con
  Alembic (`cd api && alembic upgrade head`).

La guía completa —servicios que usa la aplicación, cómo reconstruir el archivo
de credenciales y los pasos en Cloud Run y Vercel— está en
[docs/TFM/DEPLOYMENT.md](docs/TFM/DEPLOYMENT.md). Para desplegar en otro
proveedor basta con la imagen del `Dockerfile` y las variables de
`api/.env.example`.

---

## Documentación

| Documento               | Descripción                                  |
|-------------------------|----------------------------------------------|
| `docs/TFM/ENTREGA_TFM.md` | Índice de la entrega del TFM: qué pide la guía y dónde está |
| `docs/TFM/DEPLOYMENT.md`  | Guía de despliegue y credenciales            |
| `docs/TFM/RAG_PIPELINE.md` | El pipeline RAG y sus decisiones            |
| `docs/TFM/MODELO_DATOS.md`  | Modelo de datos: entidades y relaciones      |
| `docs/TFM/MANEJO_ERRORES.md` | Manejo de errores, del backend a la pantalla |
| `docs/TFM/DATASET_PREGUNTAS.md` | Dataset de evaluación y resultados     |
| `api/experimentos/REGISTRO.md` | Índice de los experimentos y sus mediciones |
| `api/experimentos/GUIA_PRUEBAS.md` | Qué mide cada experimento y cómo reproducirlo |
| `docs/TFM/DIAGRAMA_FLUJO_RAG.md` | Diagramas del flujo de una consulta y de las seis configuraciones |
| `COMO_ARRANCAR.md`      | Arranque local paso a paso                   |
| `ALCANCE_TFM.md`        | Qué entra en la entrega y qué no             |
| `api/.env.example`      | Variables de entorno requeridas con ejemplos |

El registro de lo hecho cada día, en los dos repositorios, está en el
`CHANGELOG.md` del frontend
([knowledgespace-tfm-frontend](https://github.com/jsagudelodev/knowledgespace-tfm-frontend)).
