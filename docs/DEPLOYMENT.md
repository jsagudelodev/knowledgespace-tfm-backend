# KnowledgeSpace — Despliegue

Esta es la versión de alcance académico entregada como TFM (ver
[../ALCANCE_TFM.md](../ALCANCE_TFM.md)). Los detalles operativos de la
infraestructura de producción comercial (proyecto GCP, URLs internas, cuentas
de servicio) se excluyen deliberadamente de esta entrega, igual que otros
aspectos de comercialización — no son parte de la contribución académica.

## Backend — contenedor genérico

Construido con el `Dockerfile` de la raíz del repo (Gunicorn + UvicornWorker).
Compatible con cualquier plataforma de contenedores (Cloud Run, Render,
Railway, Fly.io, etc.).

Variables de entorno requeridas: ver `api/.env.example`.

```bash
docker build -t knowledgespace-api .
docker run -p 8080:8080 --env-file api/.env knowledgespace-api
```

## Frontend

Build estático de Angular (`npm run build`), servible desde cualquier hosting
estático o contenedor Node. Ver el repo del frontend para su Dockerfile.

## Desarrollo local

### Backend
```bash
cd api
python -m uvicorn main:app --host 0.0.0.0 --port 8002 --reload
```

### Frontend
```bash
ng serve
# Corre en http://localhost:4200 con environment.development.ts
```

### Environments disponibles
| Archivo | Uso |
|---|---|
| `environment.ts` | Base / referencia |
| `environment.development.ts` | Local (`ng serve`) |
| `environment.production.ts` | Build de producción |
| `environment.qa.ts` | QA / staging |
