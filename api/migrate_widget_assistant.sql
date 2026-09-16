-- Migración manual de la tabla widgets — corrección de diseño: un widget es
-- el despliegue público de UN asistente, no una entidad standalone con su
-- propia copia de modelo/prompt. Ver docs/MODELO_DATOS.md §2.9 para el
-- razonamiento completo.
--
-- Este proyecto no usa Alembic (ver CLAUDE.md), así que create_tables.py
-- (Base.metadata.create_all) no altera una tabla que ya existe — de ahí
-- esta migración manual.
--
-- NO es idempotente en el DELETE (solo debe correr una vez, sobre el
-- estado real detectado antes de escribir este archivo: 1 widget huérfano
-- con assistant_id NULL). Los DROP COLUMN sí usan IF EXISTS por seguridad
-- si se re-ejecuta por error.
--
-- Uso: pegar en Supabase → SQL Editor → Run.

BEGIN;

-- 1. Quitar el widget huérfano sin asistente enlazado (data de prueba,
--    verificado antes de esta migración: 'Widget Soporte Técnico - DevCorp').
DELETE FROM widgets WHERE assistant_id IS NULL;

-- 2. Quitar los campos duplicados — el modelo/prompt/documentos se heredan
--    del Assistant enlazado, no se vuelven a guardar en el widget.
ALTER TABLE widgets
    DROP COLUMN IF EXISTS system_prompt,
    DROP COLUMN IF EXISTS temperature,
    DROP COLUMN IF EXISTS max_tokens,
    DROP COLUMN IF EXISTS model_name;

-- 3. Hacer obligatorio el enlace a un asistente (antes nullable).
ALTER TABLE widgets
    ALTER COLUMN assistant_id SET NOT NULL;

-- 4. Cambiar el borrado en cascada: si se borra el asistente, ya no tiene
--    sentido mantener un widget sin modelo/documentos que ofrecer — antes
--    quedaba "huérfano" (SET NULL), ahora se borra junto con su asistente.
ALTER TABLE widgets
    DROP CONSTRAINT widgets_assistant_id_fkey,
    ADD CONSTRAINT widgets_assistant_id_fkey
        FOREIGN KEY (assistant_id) REFERENCES assistants(id) ON DELETE CASCADE;

COMMIT;
