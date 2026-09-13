# KnowSpace

Plataforma SaaS multi-tenant para gestión de conocimiento con IA.  
Backend REST API construido con FastAPI y desplegado en Google Cloud Run.

---

## Tabla de contenidos

- [Stack tecnológico](#stack-tecnológico)
- [Estructura del proyecto](#estructura-del-proyecto)
- [Desarrollo local](#desarrollo-local)
- [Primer arranque](#primer-arranque)
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
| CI/CD           | Google Cloud Build (trigger: `main`) |

---

## Estructura del proyecto

```
KnowledgeSpace/
├── api/                        # Servicio backend
│   ├── main.py                 # Entrada FastAPI + registro de routers
│   ├── requirements.txt
│   ├── create_tables.py        # Script de migración (bloqueado en producción)
│   ├── .env.example            # Variables de entorno requeridas
│   └── app/
│       ├── core/               # Configuración, base de datos, seguridad JWT
│       ├── db/
│       │   └── models/         # Modelos SQLAlchemy (13 tablas)
│       ├── repositories/       # Capa de acceso a datos (patrón repositorio)
│       ├── routers/v1/         # Endpoints REST (10 módulos)
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
# 1. Clonar y activar entorno virtual
git clone https://github.com/jsagudelodev/KnowledgeSpace.git
cd KnowledgeSpace

python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Linux / Mac

# 2. Instalar dependencias
pip install -r api/requirements.txt

# 3. Configurar variables de entorno
cp api/.env.example api/.env
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

## Despliegue

Esta es la versión de alcance académico entregada como TFM (ver
[ALCANCE_TFM.md](ALCANCE_TFM.md)). El servicio de demostración corre en Google
Cloud Run, construido con el `Dockerfile` de la raíz del repo (Gunicorn +
UvicornWorker) y una base de datos PostgreSQL gestionada.

Los detalles operativos de la infraestructura de producción comercial
(identificadores de proyecto, URLs internas, cuentas de servicio, triggers de
CI/CD) se excluyen deliberadamente de esta entrega por no ser parte de la
contribución académica — mismo criterio ya aplicado al widget público
embebido (ver `ALCANCE_TFM.md`).

Para desplegar tu propia instancia: build de la imagen con el `Dockerfile`
raíz, variables de entorno según `api/.env.example`, y cualquier proveedor
compatible con contenedores (Cloud Run, Render, Railway, etc.).

---

## Documentación

| Documento               | Descripción                                  |
|-------------------------|----------------------------------------------|
| `docs/PENDIENTES.md`    | Tareas técnicas pendientes del backend       |
| `docs/MODELO_DATOS.md`  | Modelo de datos: entidades y relaciones      |
| `api/.env.example`      | Variables de entorno requeridas con ejemplos |
