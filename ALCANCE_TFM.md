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
- **Mitigación de alucinaciones**: umbral de relevancia y capas de validación
  sobre la respuesta del LLM — ver `docs/tutorials/04_alucinaciones.py`.
- **Tracking de costo por solicitud LLM** — ver `app/services/cost_tracking_service.py`.
- **Knowledge gaps** (preguntas sin respuesta satisfactoria, para retroalimentar
  la base de conocimiento).

## Explícitamente fuera de alcance de la defensa

Por ser decisiones de comercialización y no limitaciones técnicas o parte de
la contribución académica (mismo criterio ya aplicado en el frontend al
widget público embebible):

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

- Cobertura de tests: 4 archivos de test unitario sobre lógica pura (RAG,
  costos, namespaces de Pinecone) — sin tests de integración end-to-end.
- Sin CI/CD automatizado en este repositorio (el pipeline de Cloud Build
  pertenece a la infraestructura comercial, excluida por lo anterior).
