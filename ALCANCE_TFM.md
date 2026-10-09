# Alcance académico de esta entrega (TFM)

Este repositorio es la versión de **KnowledgeSpace — Backend** entregada como
Trabajo Fin de Máster. Es una copia con alcance reducido del producto en
desarrollo activo; el repositorio comercial es privado y continúa
evolucionando por separado.

## Núcleo académico (contribución del TFM)

- **Pipeline RAG**: ingesta de PDFs, chunking, embeddings (OpenAI) y búsqueda
  vectorial (Pinecone) — ver `docs/RAG_PIPELINE.md`.
- **Aislamiento multi-tenant**: namespaces de Pinecone y filtrado por
  `company_id` extraído del JWT en cada recurso — ver `docs/MODELO_DATOS.md`.
- **Mitigación de alucinaciones**: umbral de relevancia medido sobre el corpus
  (`RAGService.RELEVANCE_THRESHOLD`, con la justificación en
  `docs/RAG_PIPELINE.md` §6) y un prompt restrictivo que prohíbe responder fuera
  del contexto recuperado. **No hay validación posterior sobre la respuesta
  generada**: el LLM-as-judge existe como ejercicio en
  `docs/practica-tfm/5.5_llm_as_judge.py`, no en el código productivo. Ver
  `docs/tutorials/04_alucinaciones.py`.
- **Tracking de costo por solicitud LLM** — ver `app/services/cost_tracking_service.py`.
- **Knowledge gaps** (preguntas sin respuesta satisfactoria, para retroalimentar
  la base de conocimiento).

## Explícitamente fuera de alcance de la defensa

Por ser decisiones de comercialización y no limitaciones técnicas o parte de
la contribución académica (mismo criterio ya aplicado en el frontend al
widget público embebible):

- **Widget público embebible**: su router (`/api/v1/widgets`), su repositorio,
  sus esquemas y el endpoint `GET /assistants/{id}/widgets` se retiraron de esta
  entrega, en coherencia con el mismo criterio ya aplicado en el frontend.

  **El modelo de datos permanece** (`app/db/models/widget.py`, la relación
  `Assistant.widgets`, el conteo `widget_count` que impide borrar un asistente
  con widgets vinculados, y los campos `widget_id` / `channel` en `feedback` y
  `knowledge_gaps`). No es código olvidado: el canal de origen distingue si una
  pregunta sin respuesta llegó desde un sitio público o desde el chat interno, y
  esa distinción es parte de la lógica de knowledge gaps que sí se defiende.

- Infraestructura de despliegue de producción (identificadores de proyecto
  cloud, URLs internas, cuentas de servicio, triggers de CI/CD).
- El campo `plan` (`basic|pro|enterprise`) en `Company` es un modelo de datos
  ilustrativo de tiering multi-tenant; **no implementa cobro, checkout ni
  gating real** — no hay lógica de monetización en este código.
- CRUD administrativo de companies/users/notifications: es soporte necesario
  para que el multi-tenant funcione, no la contribución de investigación.

## Material de defensa

- `docs/tutorials/README.md` — tutoriales interactivos ejecutables, con
  sección "Para la defensa" y sugerencia de demo en vivo.
- `docs/DEFENSA_TECNICA_AMPLIADA.md` — petición exacta al LLM, seguridad,
  multi-tenancy en Postgres, decisiones de stack, y la pregunta de
  contribución académica.

## Limitaciones conocidas

- Cobertura de tests: 5 archivos y 21 tests unitarios sobre lógica pura
  —construcción del contexto RAG, cálculo de costos, namespaces de Pinecone,
  métricas del dashboard y períodos de knowledge gaps—. **Sin tests de
  integración**: ninguno levanta la aplicación ni toca la base de datos, en
  parte porque `Base.metadata.create_all` no funciona sobre SQLite
  (`assistants.quick_prompts` usa `JSONB`, exclusivo de Postgres), así que una
  base en memoria para pruebas exigiría declarar variantes por dialecto.
- Sin CI/CD automatizado en este repositorio (el pipeline de Cloud Build
  pertenece a la infraestructura comercial, excluida por lo anterior).
- El aislamiento entre empresas se apoya en la comprobación explícita de
  `company_id` en cada router y en los namespaces de Pinecone, no en
  permisos a nivel de fila ni en roles sobre documentos: cualquier
  administrador ve todos los espacios de su propia empresa.
