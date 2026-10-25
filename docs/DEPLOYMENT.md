# KnowledgeSpace — Guía de despliegue

Cómo reconstruir KnowledgeSpace desde cero: qué servicios necesita, cómo armar
el archivo de credenciales, cómo desplegar el backend en Google Cloud Run y el
frontend en Vercel, y cómo comprobar que funciona. Es la base del anexo 10.1 de
la memoria; la otra mitad del anexo, cómo se usa la aplicación, está en
`knowledgespace-tfm-frontend/doc/MANUAL_USUARIO.md`.

**Despliegue de demostración del TFM** (activo desde el 2026-10-22):

| Pieza | Repositorio | Plataforma | Dirección |
|---|---|---|---|
| Backend (FastAPI) | `knowledgespace-tfm-backend` | Google Cloud Run, región `europe-west1`, servicio `knowledgespace-tfm-backend` | https://knowledgespace-tfm-backend-130090995386.europe-west1.run.app |
| Frontend (Angular) | `knowledgespace-tfm-frontend` | Vercel, proyecto `knowledgespace-tfm-frontend` | https://knowledgespace-tfm-frontend.vercel.app |

Las dos piezas se despliegan solas con cada `push` a `main` de su repositorio.

> No confundir con `knowspace-api` (Cloud Run, `us-central1`): es el backend del
> producto comercial, se despliega desde otro repositorio y no forma parte de
> esta entrega.

---

## 1. Servicios externos

| Servicio | Para qué | Obligatorio |
|---|---|---|
| **PostgreSQL** (Supabase) | Empresas, usuarios, asistentes, documentos, conversaciones, costos, knowledge gaps | Sí |
| **Pinecone** | Índice vectorial de los fragmentos (un namespace por empresa y asistente) | Sí |
| **OpenAI** | Embeddings (`text-embedding-3-small`) y generación (`gpt-4o-mini`) | Sí |
| **AWS S3** | Almacenamiento de los documentos subidos | Sí |
| **Langfuse** | Trazas del pipeline RAG | No: con `LANGFUSE_ENABLED=false` todo funciona igual |
| **SMTP** | Envío de correos | No: `SMTP_ENABLED=false` |
| **Google Cloud** (Cloud Run + Cloud Build) | Alojar el backend | Solo para desplegar |
| **Vercel** | Alojar el frontend | Solo para desplegar |

**El índice de Pinecone se crea solo.** Si `PINECONE_INDEX_NAME` no existe, el
backend lo crea al arrancar con 1536 dimensiones (las de
`text-embedding-3-small`), métrica coseno y modo serverless en AWS `us-east-1`
(`app/services/pinecone_service.py`).

---

## 2. El archivo de credenciales

Todas las variables están en `api/.env.example`, con un comentario que explica
cada una. Para reconstruir el archivo:

```bash
cp api/.env.example api/.env
```

y rellenar:

| Variable | De dónde sale |
|---|---|
| `SECRET_KEY` | Generarla: `python -c "import secrets; print(secrets.token_hex(32))"` |
| `DATABASE_URL` | Supabase → Settings → Database → Connection string (modo *session*) |
| `OPENAI_API_KEY` | platform.openai.com → API keys |
| `PINECONE_API_KEY`, `PINECONE_INDEX_NAME` | app.pinecone.io → API Keys; el índice se crea solo |
| `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`, `S3_BUCKET_NAME` | Un usuario IAM con permisos sobre el bucket |
| `ALLOWED_ORIGINS` | Las direcciones exactas del frontend, sin barra final, en formato de lista: `["http://localhost:4200","https://knowledgespace-tfm-frontend.vercel.app"]` |
| `LANGFUSE_*` | Opcional. Ojo con la región del host (ver el comentario en `.env.example`) |
| `RAG_*` | Dejar los valores del ejemplo: son los medidos en el capítulo 5 |

`api/.env` está en `.gitignore`: las credenciales nunca se suben al repositorio.

---

## 3. Ejecutar en local

### Backend

Requiere Python 3.11 o superior.

```bash
cd api
python -m venv .venv
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # Linux / Mac
pip install -r requirements.txt
uvicorn main:app --reload --port 8002
```

Detalle paso a paso, y los problemas conocidos, en `COMO_ARRANCAR.md`.

### Frontend

Requiere Node.js 20 o superior.

```bash
cd knowledgespace-tfm-frontend
npm install
npm start          # http://localhost:4200, contra el backend local (environment.ts)
```

---

## 4. Desplegar el backend en Google Cloud Run

El backend se construye con el `Dockerfile` de la **raíz** del repositorio:
imagen de Python 3.11 en dos etapas, usuario sin privilegios y Gunicorn con
workers de Uvicorn en el puerto 8080.

### Despliegue continuo desde GitHub (el que está en uso)

1. En la consola de Google Cloud, **Cloud Run → Crear servicio**.
2. Elegir **Implementar continuamente desde un repositorio** y conectar GitHub
   con el repositorio `knowledgespace-tfm-backend`, rama `main`.
3. En el tipo de compilación, **Dockerfile**, con la ruta `/Dockerfile` (la
   raíz, no `api/`).
4. Nombre del servicio `knowledgespace-tfm-backend`, región `europe-west1`, y
   permitir invocaciones sin autenticar: la API tiene su propia autenticación
   con JWT.
5. En **Variables y secretos**, añadir las variables del archivo `api/.env`
   (sección 2). `ALLOWED_ORIGINS` debe incluir la dirección de Vercel.
6. Crear. Cloud Build construye la imagen y la despliega; a partir de ahí, cada
   `push` a `main` repite el proceso.

### Despliegue manual con la CLI (alternativa)

```bash
gcloud run deploy knowledgespace-tfm-backend \
    --source . \
    --region europe-west1 \
    --allow-unauthenticated
```

Las variables de entorno se configuran después en la consola, o con
`--set-env-vars`, sin escribir nunca las claves en un archivo versionado.

### Primer arranque: crear las tablas y el administrador

Con la base de datos vacía, el endpoint de configuración crea las tablas, la
primera empresa y el superadministrador en un solo paso, y se deshabilita solo
(HTTP 403) cuando ya existen usuarios:

```bash
curl -X POST https://<backend>/api/v1/setup/ \
  -H "Content-Type: application/json" \
  -d '{"company_name":"Mi Empresa","company_email":"admin@empresa.com",
       "full_name":"Admin","email":"admin@empresa.com","password":"<contraseña>"}'
```

---

## 5. Desplegar el frontend en Vercel

1. En vercel.com, **Add New → Project** e importar el repositorio
   `knowledgespace-tfm-frontend`.
2. Vercel detecta **Angular**. Los valores que usa:
   - Build Command: `npm run build` (compila con la configuración `production`)
   - Output Directory: `dist/knowledge-space/browser`
3. Desplegar. Cada `push` a `main` vuelve a desplegar solo.

**A qué backend apunta.** La dirección de la API se fija al compilar, en
`src/environments/environment.production.ts` (`apiUrl`). Para desplegar contra
otro backend hay que cambiar ese archivo y volver a desplegar.

**Las rutas internas funcionan al recargar.** Vercel sirve `index.html` para
cualquier ruta (`/assistants`, `/dashboard`…), así que no hace falta
configuración adicional para el enrutado de Angular. Comprobado el 2026-10-24.

El repositorio incluye además un `Dockerfile` y un `server.js` para servir el
frontend desde un contenedor Node, como alternativa a Vercel.

---

## 6. Comprobar que funciona

| Comprobación | Cómo | Resultado esperado |
|---|---|---|
| El backend está vivo y conectado a la base de datos | `GET https://<backend>/health` | `{"status":"healthy","database":"healthy"}` |
| La API está publicada | Abrir `https://<backend>/docs` | La documentación interactiva (Swagger) |
| El frontend apunta al backend | Iniciar sesión en el frontend | Entra al dashboard sin errores |
| CORS bien configurado | Si el login falla, abrir la consola del navegador | Sin errores `Access-Control-Allow-Origin`; si aparecen, falta la dirección de Vercel en `ALLOWED_ORIGINS` |
| El RAG responde | Subir un PDF a un asistente y preguntarle algo de su contenido | Una respuesta con sus fuentes citadas |

---

## 7. Costos de la infraestructura

Con la configuración por defecto (mínimo de 0 instancias), Cloud Run escala a
cero cuando no hay tráfico, así que en una demostración el costo de alojamiento
es muy bajo. El costo variable es el de OpenAI por consulta, que el propio
sistema registra en `cost_tracking` (ver `docs/OBSERVABILIDAD.md` y el apartado
3.3 de la memoria).
