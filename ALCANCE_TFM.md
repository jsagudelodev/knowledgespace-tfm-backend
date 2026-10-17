# Alcance académico de esta entrega (TFM)

Este repositorio es la versión de **KnowledgeSpace — Backend** entregada como
Trabajo Fin de Máster. Es una copia con alcance reducido del producto en
desarrollo activo; el repositorio comercial es privado y continúa
evolucionando por separado.

## Núcleo académico (contribución del TFM)

- **Pipeline RAG con cuatro configuraciones comparables**: línea base (Naive
  RAG con filtro por umbral), descomposición de consultas, reordenado de
  fragmentos y descomposición con tope de contexto — seleccionables por
  variable de entorno sin tocar código (`app/services/rag_factory.py`). Las
  cuatro conviven a propósito: la línea base es el término de comparación de
  todas las mediciones del capítulo 5, y sustituirla por la variante elegida
  habría hecho desaparecer el punto de referencia. Ver
  `docs/ARQUITECTURAS_RAG.md` para la taxonomía completa y por qué se
  descartaron otras (RAG híbrido, agéntico, GraphRAG).
- **Aislamiento multi-tenant**: namespaces de Pinecone y filtrado por
  `company_id` extraído del JWT en cada recurso — ver `docs/MODELO_DATOS.md`.
- **Mitigación de alucinaciones, con dos niveles de evidencia**:
  - En producción: umbral de relevancia medido sobre el corpus
    (`RAGService.RELEVANCE_THRESHOLD`, justificado en `docs/RAG_PIPELINE.md`
    §6 y revalidado tras el cambio de chunking) y un prompt restrictivo que
    prohíbe responder fuera del contexto recuperado. **No hay validación
    posterior sobre la respuesta generada dentro del camino de producción.**
  - Como evaluación experimental (`api/experimentos/`, fuera del camino de
    producción): un conjunto con preguntas de control —con respuesta en el
    corpus— y preguntas fuera de corpus mide la tasa de abstención correcta y
    la de falsa abstención, y RAGAS (`evaluar_ragas.py`) mide fidelidad y
    relevancia de las respuestas con un LLM juez. Es la evidencia cuantitativa
    de que el sistema no inventa sin volverse inservible por exceso de
    prudencia.
- **Observabilidad con Langfuse** (opcional, activable por variable de
  entorno): traza cada consulta —fragmentos recuperados, puntuaciones,
  llamadas auxiliares de descomposición y reordenado— para poder auditar una
  respuesta después de ocurrida. Ver `app/core/observabilidad.py`.
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

- **Ocho tablas sin código detrás**: `budget_limits`, `quota_alerts`,
  `audit_logs`, `support_tickets`, `courses`, `quizzes`, `quiz_results` y
  `enrollments`. De las veintitrés tablas del esquema, catorce tienen modelo
  ORM; estas ocho son esquema heredado del producto comercial y del proyecto
  hermano TrainIQ. **No son trabajo pendiente**: se declaran fuera de alcance
  con el mismo criterio que el widget.

  Dos de ellas **contienen datos obsoletos de junio de 2026**, cuando el módulo
  de presupuesto operaba en el producto comercial. `budget_limits` fija un tope
  de 2,00 USD mensuales con `current_monthly_spend` en 0,00, cifra que **no
  refleja el gasto real**: ese vive en `cost_tracking`, que sí se mantiene al
  día. El detalle está en `docs/MODELO_DATOS.md` §3.5.

  Lo que sí se entrega es el **registro** del consumo, que es lo que exige el
  requisito RNF-4: cada llamada al proveedor anota tokens, modelo, importe y
  organización, con las operaciones distinguidas. Hacer cumplir un tope es la
  parte que queda fuera.

## Material de defensa

- `docs/tutorials/README.md` — tutoriales interactivos ejecutables, con
  sección "Para la defensa" y sugerencia de demo en vivo.
- `docs/DEFENSA_TECNICA_AMPLIADA.md` — petición exacta al LLM, seguridad,
  multi-tenancy en Postgres, decisiones de stack, y la pregunta de
  contribución académica.

## Limitaciones conocidas

- Cobertura de tests: 13 archivos y 91 tests unitarios sobre lógica pura
  —las cuatro configuraciones del pipeline RAG, construcción del contexto,
  cálculo de costos, namespaces de Pinecone, métricas del dashboard y períodos
  de knowledge gaps—. **Sin tests de integración**: ninguno levanta la
  aplicación ni toca la base de datos, en parte porque
  `Base.metadata.create_all` no funciona sobre SQLite (`assistants.quick_prompts`
  usa `JSONB`, exclusivo de Postgres), así que una base en memoria para pruebas
  exigiría declarar variantes por dialecto.
- Sin CI/CD automatizado en este repositorio (el pipeline de Cloud Build
  pertenece a la infraestructura comercial, excluida por lo anterior).
- El aislamiento entre empresas se apoya en la comprobación explícita de
  `company_id` en cada router y en los namespaces de Pinecone, no en
  permisos a nivel de fila ni en roles sobre documentos: cualquier
  administrador ve todos los espacios de su propia empresa.
