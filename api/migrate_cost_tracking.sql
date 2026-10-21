-- Migración manual de la tabla cost_tracking — módulo "Cost Tracking".
-- La tabla YA EXISTÍA en la BD (creada hace meses por una integración
-- anterior que luego se quitó del código, dejando datos históricos hasta
-- 2026-06-18) — por eso esto es ALTER TABLE, no CREATE TABLE.
--
-- Idempotente: ADD COLUMN IF NOT EXISTS / CREATE INDEX IF NOT EXISTS,
-- se puede correr más de una vez sin efectos secundarios.
--
-- Uso: pegar en Supabase → SQL Editor → Run.

BEGIN;

ALTER TABLE cost_tracking
    ADD COLUMN IF NOT EXISTS operation VARCHAR(20) NOT NULL DEFAULT 'chat';

-- Añadido el 2026-10-20: cuánto tardó la petición al proveedor, en
-- milisegundos. Antes del registro había medición de latencia solo en los
-- experimentos (contra un dataset fijo), nunca en consultas reales de
-- producción. NULL en las filas de operación 'embedding' y en las llamadas
-- auxiliares (descomposición, reordenado): solo la fila 'chat' —la respuesta
-- final al usuario— guarda la duración, porque es la que representa la
-- latencia que de verdad percibe quien pregunta.
ALTER TABLE cost_tracking
    ADD COLUMN IF NOT EXISTS duration_ms INTEGER;

CREATE INDEX IF NOT EXISTS ix_cost_tracking_company_id      ON cost_tracking (company_id);
CREATE INDEX IF NOT EXISTS ix_cost_tracking_user_id         ON cost_tracking (user_id);
CREATE INDEX IF NOT EXISTS ix_cost_tracking_assistant_id    ON cost_tracking (assistant_id);
CREATE INDEX IF NOT EXISTS ix_cost_tracking_document_id     ON cost_tracking (document_id);
CREATE INDEX IF NOT EXISTS ix_cost_tracking_model           ON cost_tracking (model);
CREATE INDEX IF NOT EXISTS ix_cost_tracking_created_at      ON cost_tracking (created_at);
CREATE INDEX IF NOT EXISTS ix_cost_tracking_company_created ON cost_tracking (company_id, created_at);

COMMIT;
