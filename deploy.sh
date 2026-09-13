#!/usr/bin/env bash
# deploy.sh — construye la imagen y despliega en Google Cloud Run
# Uso: ./deploy.sh [PROJECT_ID] [REGION]

set -euo pipefail

# ── Configuración ─────────────────────────────────────────────────────────────
PROJECT_ID=${1:-$(gcloud config get-value project)}
REGION=${2:-us-central1}
SERVICE_NAME="knowspace-api"
IMAGE="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

echo "▶ Proyecto : ${PROJECT_ID}"
echo "▶ Región   : ${REGION}"
echo "▶ Imagen   : ${IMAGE}"
echo ""

# ── 1. Build y push de la imagen ──────────────────────────────────────────────
echo "── [1/3] Construyendo imagen Docker..."
gcloud builds submit ./api \
    --tag "${IMAGE}" \
    --project "${PROJECT_ID}"

# ── 2. Despliegue en Cloud Run ────────────────────────────────────────────────
echo ""
echo "── [2/3] Desplegando en Cloud Run..."
gcloud run deploy "${SERVICE_NAME}" \
    --image "${IMAGE}" \
    --platform managed \
    --region "${REGION}" \
    --project "${PROJECT_ID}" \
    --allow-unauthenticated \
    --memory 512Mi \
    --cpu 1 \
    --min-instances 0 \
    --max-instances 10 \
    --timeout 120 \
    --concurrency 80 \
    --set-env-vars "$(
        grep -v '^#' api/.env \
        | grep -v '^$' \
        | tr '\n' ',' \
        | sed 's/,$//'
    )"

# ── 3. Mostrar URL del servicio ───────────────────────────────────────────────
echo ""
echo "── [3/3] URL del servicio:"
gcloud run services describe "${SERVICE_NAME}" \
    --platform managed \
    --region "${REGION}" \
    --project "${PROJECT_ID}" \
    --format "value(status.url)"

echo ""
echo "✓ Despliegue completado."
