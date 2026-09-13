# ── Stage 1: dependencies ────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

RUN pip install --no-cache-dir --upgrade pip

COPY api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Stage 2: runtime ─────────────────────────────────────────────────────────
FROM python:3.11-slim

# Non-root user for security
RUN addgroup --system app && adduser --system --ingroup app app

WORKDIR /app

# Copy installed packages from builder stage
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin/gunicorn /usr/local/bin/gunicorn
COPY --from=builder /usr/local/bin/uvicorn  /usr/local/bin/uvicorn

# Copy only the backend source (api/ → /app)
COPY --chown=app:app api/ .

# Directory for local file uploads (external volume in production)
RUN mkdir -p uploads && chown app:app uploads

USER app

# ── Runtime configuration ─────────────────────────────────────────────────────
ENV PORT=8080
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV DEBUG=False
ENV GUNICORN_WORKERS=2
ENV GUNICORN_TIMEOUT=300

EXPOSE $PORT

CMD exec gunicorn main:app \
    --bind "0.0.0.0:${PORT}" \
    --workers ${GUNICORN_WORKERS} \
    --worker-class uvicorn.workers.UvicornWorker \
    --timeout ${GUNICORN_TIMEOUT} \
    --keep-alive 5 \
    --access-logfile - \
    --error-logfile -
