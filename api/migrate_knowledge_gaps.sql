-- Migración manual de la tabla knowledge_gaps — módulo "Preguntas sin respuesta".
-- Este proyecto no usa Alembic (ver CLAUDE.md), y el `create_all` del endpoint
-- de setup solo crea tablas que falten: no altera una que ya existe.
--
-- Idempotente: ADD COLUMN IF NOT EXISTS / CREATE INDEX IF NOT EXISTS,
-- se puede correr más de una vez sin efectos secundarios.
--
-- Uso: pegar en Supabase → SQL Editor → Run.

BEGIN;

ALTER TABLE knowledge_gaps
    ADD COLUMN IF NOT EXISTS resolved_document_id INTEGER REFERENCES documents(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS ignore_reason         VARCHAR(30),
    ADD COLUMN IF NOT EXISTS assigned_to           INTEGER REFERENCES users(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS requested_at          TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS due_at                TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS note                  TEXT,
    ADD COLUMN IF NOT EXISTS recurrence_count      INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS reopened_at           TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS verify_score_before   FLOAT,
    ADD COLUMN IF NOT EXISTS verify_score_after    FLOAT,
    ADD COLUMN IF NOT EXISTS verified_at           TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS verify_passed         BOOLEAN,
    ADD COLUMN IF NOT EXISTS variants              JSONB,
    ADD COLUMN IF NOT EXISTS candidates            JSONB,
    ADD COLUMN IF NOT EXISTS volume                INTEGER DEFAULT 1,
    ADD COLUMN IF NOT EXISTS channel               VARCHAR(20),
    ADD COLUMN IF NOT EXISTS trend                 VARCHAR(20);

CREATE INDEX IF NOT EXISTS ix_knowledge_gaps_company_status_created
    ON knowledge_gaps (company_id, status, created_at);

COMMIT;
