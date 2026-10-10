# Pipeline RAG — KnowledgeSpace

> **RAG** (Retrieval Augmented Generation) es la técnica que permite al LLM responder usando *únicamente* los documentos de la empresa, sin inventar información. Este documento explica cómo está implementado en KnowledgeSpace.

---

## Tabla de contenidos

1. [Visión general](#1-visión-general)
2. [Tecnologías involucradas](#2-tecnologías-involucradas)
3. [Pipeline de Ingesta — subir un documento](#3-pipeline-de-ingesta--subir-un-documento)
4. [Pipeline de Consulta — enviar un mensaje](#4-pipeline-de-consulta--enviar-un-mensaje)
5. [Aislamiento multi-tenant (namespaces)](#5-aislamiento-multi-tenant-namespaces)
6. [Parámetros clave y dónde cambiarlos](#6-parámetros-clave-y-dónde-cambiarlos)
7. [Manejo de errores](#7-manejo-de-errores)
8. [Otros consumidores de embeddings/Pinecone](#8-otros-consumidores-de-embeddingspinecone)
9. [Pendientes y mejoras futuras](#9-pendientes-y-mejoras-futuras)

---

## 1. Visión general

El sistema tiene **dos pipelines independientes**:

```
INGESTA (una vez por documento)
  Usuario sube archivo
       │
       ▼
  S3 (almacenamiento) ──► Extracción de texto ──► Chunks ──► Embeddings ──► Pinecone

CONSULTA (en cada mensaje de chat)
  Usuario escribe pregunta
       │
       ▼
  Embedding de la pregunta ──► Búsqueda en Pinecone ──► Contexto ──► OpenAI LLM ──► Respuesta
```

La **ingesta** procesa el documento una sola vez y almacena su representación vectorial en Pinecone.
La **consulta** nunca toca los archivos originales — solo busca en Pinecone y llama al LLM.

---

## 2. Tecnologías involucradas

| Componente | Tecnología | Propósito |
|---|---|---|
| Almacenamiento de archivos | AWS S3 | Guardar PDFs, DOCX, TXT originales |
| Extracción de texto | PyPDF2, python-docx | Convertir archivos binarios a texto plano |
| Embeddings | OpenAI `text-embedding-3-small` | Convertir texto en vectores numéricos (1536 dimensiones) |
| Vector store | Pinecone (serverless) | Almacenar y buscar vectores por similitud semántica |
| LLM | OpenAI (configurable por asistente) | Generar la respuesta en lenguaje natural |
| Background tasks | FastAPI `BackgroundTasks` | Procesar documentos sin bloquear la respuesta al cliente |

---

## 3. Pipeline de Ingesta — subir un documento

### Flujo completo

```
POST /api/v1/documents/upload
         │
         ├─ 1. Validar tipo (pdf/docx/txt) y tamaño (≤ 10 MB)
         │
         ├─ 2. Subir archivo a S3
         │      key: company-{id}/{uuid}.{ext}
         │
         ├─ 3. Guardar registro en BD con status = "processing"
         │
         └─ 4. Responder al cliente inmediatamente (201 Created)
               │
               └── [Background Task] _procesar_documento_background()
                         │
                         ├─ 5. Descargar archivo desde S3 a memoria (BytesIO)
                         │
                         ├─ 6. Extraer texto según tipo
                         │      PDF  → PyPDF2.PdfReader
                         │      DOCX → python-docx paragraphs
                         │      TXT  → decode UTF-8
                         │
                         ├─ 7. Dividir en chunks
                         │      chunk_size = 1000 caracteres
                         │      overlap    = 200 caracteres
                         │
                         ├─ 8. Generar embeddings en batch (100 chunks/llamada)
                         │      modelo: text-embedding-3-small → 1536 dim
                         │
                         ├─ 9. Subir vectores a Pinecone
                         │      namespace: "company-{id}" o "company-{id}-assistant-{id}"
                         │      metadata por vector: document_id, document_name,
                         │                           company_id, assistant_id,
                         │                           chunk_index, text (primeros 1000 chars)
                         │
                         └─ 10. Actualizar BD
                                status = "completed" + page_count + chunk_count
                                (o "failed" + error_message si algo falla)
```

### Archivos involucrados

| Archivo | Responsabilidad |
|---|---|
| `routers/v1/documents.py` | Endpoint `/upload`, validaciones, lanzar background task |
| `services/document_service.py` | `validate_file_type()`, `validate_file_size()` |
| `services/s3_service.py` | `subir_archivo()`, `descargar_a_memoria()` |
| `services/pdf_service.py` | `procesar()` — extrae texto y divide en chunks |
| `services/embedding_service.py` | `generar_embeddings_batch()` |
| `services/pinecone_service.py` | `upsert_vectores()` |
| `repositories/document_repository.py` | Guardar y actualizar el registro del documento |

### Chunking con overlap

```
Texto original: [...AAAAAABBBBBBBBBCCCCCCC...]
                        ↑ chunk_size=1000

Chunk 1: [...AAAAAABBBBBB...]  (posición 0 → 1000)
Chunk 2: [...BBBBBBCCCCCCC...] (posición 800 → 1800)  ← overlap de 200 chars
Chunk 3: [...]                 (posición 1600 → 2600)
```

El **overlap** evita que una respuesta quede cortada entre dos chunks. Si una oración empieza al final del chunk 1, también aparece al principio del chunk 2, garantizando que Pinecone siempre encuentre el contexto completo.

### Retry

Si el procesamiento falla (S3 caído, OpenAI error, Pinecone timeout), el documento queda con `status = "failed"` y se puede reintentar sin re-subir el archivo:

```
POST /api/v1/documents/{id}/retry
```

---

## 4. Pipeline de Consulta — enviar un mensaje

### Flujo completo

```
POST /api/v1/chat/message
  { "message": "¿Cuál es la política de vacaciones?", "assistant_id": 3 }
         │
         ├─ 1. Resolver asistente
         │      Si se pasa assistant_id → verificar que existe y está activo
         │      Si no → usar el primero activo de la empresa
         │      Si no hay ninguno → continuar con configuración genérica
         │
         ├─ 2. Resolver conversación
         │      Si se pasa conversation_id → verificar que pertenece al usuario
         │      Si no → crear nueva conversación (título = primeros 50 chars del mensaje)
         │
         ├─ 3. Cargar historial (últimos 20 mensajes de la conversación)
         │
         ├─ 4. Guardar mensaje del usuario en BD (role = "user")
         │
         └─ RAGService.generate_response()
                   │
                   ├─ 5. Embed de la pregunta
                   │      text-embedding-3-small → vector de 1536 floats
                   │
                   ├─ 6. Búsqueda semántica en Pinecone (top_k = 5)
                   │      Intenta primero el namespace del asistente
                   │      Si no hay resultados → fallback al namespace de la empresa
                   │
                   ├─ 7. Filtrar por relevancia
                   │      Descartar chunks con score < 0.30 (RELEVANCE_THRESHOLD)
                   │      Score = similitud coseno entre query y chunk (0.0 → 1.0)
                   │
                   ├─ 8. Construir contexto
                   │      "[Fuente 1] nombre_documento (relevancia: 0.82)\n{texto_chunk}"
                   │      "[Fuente 2] ..."
                   │
                   ├─ 9. Construir prompt para OpenAI
                   │      [system] → system_prompt del asistente (o DEFAULT_SYSTEM_PROMPT)
                   │      [system] → contexto de documentos
                   │      [user]   → historial de conversación
                   │      [user]   → pregunta actual
                   │
                   ├─ 10. Llamar al LLM
                   │       modelo:      del asistente (default: gpt-4o-mini)
                   │       temperature: del asistente (default: 0.7)
                   │       max_tokens:  1000
                   │
                   └─ 11. Guardar respuesta en BD (role = "assistant")
                           + sources (lista de documentos usados)
                           + token_count

         └─ Responder al cliente: ChatResponse
                { message_id, conversation_id, content, sources, token_count }
```

### Archivos involucrados

| Archivo | Responsabilidad |
|---|---|
| `routers/v1/chat.py` | Endpoint `/message`, resolver asistente y conversación |
| `services/rag_service.py` | `generate_response()` — embedding + búsqueda + LLM |
| `services/embedding_service.py` | `generar_embedding()` — embed de la query |
| `services/pinecone_service.py` | `buscar_vectores()` — búsqueda semántica |
| `repositories/conversation_repository.py` | Crear/obtener conversación |
| `repositories/message_repository.py` | Guardar mensajes (user + assistant) |

### Sistema de mensajes al LLM

```python
messages = [
    {"role": "system", "content": "<system_prompt del asistente>"},
    {"role": "system", "content": "Contexto de documentos:\n[Fuente 1]...\n[Fuente 2]..."},
    {"role": "user",   "content": "Mensaje anterior del usuario"},    # historial
    {"role": "assistant", "content": "Respuesta anterior"},           # historial
    {"role": "user",   "content": "Pregunta actual"},
]
```

El contexto viaja como **segundo mensaje system** para que el LLM lo trate como instrucción, no como parte de la conversación. El historial se inyecta entre el contexto y la pregunta actual.

---

## 5. Aislamiento multi-tenant (namespaces)

Pinecone usa **namespaces** para aislar completamente los datos entre empresas y asistentes. Un namespace es simplemente un prefijo que agrupa vectores — no hay forma de que una búsqueda en el namespace de empresa A devuelva resultados de empresa B.

```
Empresa 5, sin asistente:   namespace = "company-5"
Empresa 5, asistente 3:     namespace = "company-5-assistant-3"
Empresa 7, asistente 1:     namespace = "company-7-assistant-1"
```

### Aislamiento estricto por espacio (sin fallback cruzado)

```
¿Hay assistant_id en el request?
    Sí → buscar únicamente en "company-{id}-assistant-{aid}"
          Sin resultados → responder "no encontré información" (no se busca en otro namespace)
    No → buscar directamente en "company-{id}"
```

**Corregido el 2026-09-08.** Antes, un asistente sin resultados propios caía a buscar en
`company-{id}` (el pool general de la empresa) — esto permitía que un asistente citara
documentos de *otro* asistente/espacio de la misma empresa, rompiendo el aislamiento que
esta misma sección describe. Ahora, si se especifica `assistant_id`, la búsqueda no sale de
su namespace: sin contexto relevante, el `DEFAULT_SYSTEM_PROMPT` ya cubre la respuesta
correcta ("No encontré información sobre este tema en los documentos de la empresa"). El
fallback a `company-{id}` solo aplica cuando **no** se especifica ningún asistente.

### Cuándo los vectores van a cada namespace

| Situación | Namespace destino |
|---|---|
| Documento subido sin `assistant_id` | `company-{id}` |
| Documento subido con `assistant_id` | `company-{id}-assistant-{aid}` |
| Borrar un asistente con documentos o widgets vinculados | **Bloqueado** (`409 Conflict`) desde 2026-09-08 — hay que reasignarlos o borrarlos antes. Ya no es posible dejar vectores huérfanos vía soft delete del asistente. |

---

## 6. Parámetros clave y dónde cambiarlos

| Parámetro | Valor actual | Dónde |
|---|---|--------|
| Umbral de relevancia | `0.30` | `rag_service.py → RELEVANCE_THRESHOLD` |
| Tokens máximos respuesta | `1000` | `rag_service.py → MAX_RESPONSE_TOKENS` |
| Resultados Pinecone (top_k) | `5` | `rag_service.py → generate_response()` |
| Historial incluido | `20 mensajes` | `routers/v1/chat.py` |
| Tamaño de chunk | `1000 chars` | `pdf_service.py → PDFService.procesar()` |
| Overlap entre chunks | `200 chars` | `pdf_service.py → PDFService.procesar()` |
| Batch de embeddings | `100 textos` | `embedding_service.py → generar_embeddings_batch()` |
| Modelo de embedding | `text-embedding-3-small` | `config.py → OPENAI_EMBEDDING_MODEL` |
| Modelo LLM (default) | `gpt-4o-mini` | `config.py → OPENAI_CHAT_MODEL` |
| Temperatura LLM (default) | `0.7` | `rag_service.py → generate_response()` |
| Tamaño máximo de archivo | `10 MB` | `document_service.py → MAX_SIZE_MB` |
| Tipos de archivo soportados | `pdf, docx, txt` | `document_service.py → SUPPORTED_TYPES` |
| Dimensiones del índice Pinecone | `1536` | `pinecone_service.py → DIMENSION` |

### Cómo ajustar el umbral de relevancia

- **Bajar el umbral** (ej. `0.20`): el LLM recibe más contexto, pero puede incluir chunks poco relacionados → más riesgo de respuestas imprecisas.
- **Subir el umbral** (ej. `0.50`): más precisión, pero si ningún chunk supera el umbral el LLM responde "No encontré información..." aunque haya algo remotamente útil.

#### De dónde sale el `0.30`

No es un valor por convención: cae dentro de la banda vacía que separa señal
de ruido en el corpus indexado.

**Medido dos veces, con dos configuraciones de fragmentación distintas.** La
segunda medición se hizo precisamente porque la primera había quedado obsoleta:
al pasar de fragmentación por caracteres a por oraciones cambia la distribución
de similitudes, de modo que un umbral medido sobre la configuración anterior ya
no describe el sistema.

##### Medición vigente — 2026-10-09

Índice `company-8-assistant-1`: 87 fragmentos, 8 documentos, fragmentación por
oraciones, embeddings `text-embedding-3-small`, `top_k=5`. Nueve consultas en
tres familias.

| Tipo de consulta | Ejemplos | score top-1 | score top-5 |
|---|---|---|---|
| **Cubierta por el corpus** | GANs, VAE, difusión, geometría semántica | 0.487 – 0.589 | **0.393** – 0.470 |
| Tangencial al dominio | transformer, entrenar una red neuronal | 0.531 – 0.566 | 0.359 – 0.482 |
| **Ajena al corpus** | capital de Francia, paella, billete de tren | 0.139 – **0.258** | 0.124 – 0.187 |

Los dos extremos que importan:

- **0.258** — score máximo alcanzado por una consulta irrelevante ("¿cómo
  preparo una paella?").
- **0.393** — score mínimo de un fragmento legítimamente recuperado: el quinto
  resultado de la consulta cubierta peor servida, no el primero. Se toma el
  quinto porque un umbral que solo respetara el primer resultado descartaría la
  evidencia complementaria que el modelo sí debe ver.

Banda vacía de **0.135**, con centro en **0.326**. El umbral `0.30` cae dentro,
con `+0.042` de margen sobre el ruido y `+0.093` bajo la señal.

**Separación limpia:** las cuatro consultas cubiertas pasan sus cinco
fragmentos; las tres ajenas no pasan ninguno.

##### Comparación con la medición original — junio de 2026

Aquella se hizo sobre 70 fragmentos troceados **por caracteres**.

| | Junio (caracteres) | Octubre (oraciones) |
|---|---|---|
| Ruido máximo | 0.229 | **0.258** |
| Señal mínima | 0.389 | 0.393 |
| Banda vacía | 0.160 | **0.135** |
| Centro de la banda | 0.309 | **0.326** |
| Margen sobre el ruido | 0.071 | **0.042** |

**Conclusión: el `0.30` sigue siendo válido, pero con menos holgura.** La banda
se estrechó un 16 % y el margen frente al ruido cayó un 41 %. El umbral ya no
está en el centro de la banda, sino desplazado hacia el lado permisivo.

Se mantiene en `0.30` por una razón deliberada: dentro de la banda, un valor más
bajo es más permisivo —deja pasar algún fragmento flojo— y uno más alto es más
estricto —descarta evidencia complementaria—. Ante un sistema cuyo cometido es
responder con documentación propia, el error de descartar evidencia válida es
peor que el de incluir un fragmento mediocre, porque el *prompt* restrictivo ya
protege del segundo. Subirlo a `0.33`, el centro medido, sería igual de
defendible.

**Un hallazgo de la segunda medición:** las consultas tangenciales bajaron
mucho. "¿Qué es la arquitectura transformer?" pasó de `0.459–0.502` en el quinto
fragmento a `0.359`. Siguen superando el umbral, pero por poco margen. La
fragmentación por oraciones discrimina mejor lo que el corpus cubre de verdad
frente a lo que solo roza.

**Cómo reproducirla.** El experimento está automatizado:

```bash
cd api
.venv\Scripts\python.exe experimentos\medir_umbral.py --empresa 8 --asistente 1
```

No llama al modelo generativo: solo genera los embeddings de las nueve
consultas, cuyo coste es de millonésimas de dólar. Los resultados quedan
versionados en `experimentos/resultados/umbral_AAAA-MM-DD.json`.

**Cuándo hay que repetirla.** Siempre que cambie el corpus, la estrategia de
fragmentación, el modelo de embeddings o el idioma. Un umbral fuera de la banda
deja pasar ruido o descarta evidencia legítima, y nada en el sistema avisa de
que ha dejado de ser válido — tal como ocurrió entre junio y octubre.

**Alcance de esta medición.** Son 9 consultas sobre un corpus, no un benchmark
formal con dataset de referencia (ver la limitación reconocida en
`doc/DEFENSA_TFM.md` del repositorio frontend). Además, el umbral separa
**tema de no-tema**, no respuesta precisa de respuesta vaga: las consultas
tangenciales puntúan tan alto como las cubiertas — "¿qué es un transformer?"
obtiene `0.575` frente al `0.503` de "¿qué es un VAE?". Filtrar ruido es su
función; la pertinencia fina la cubre el prompt restrictivo, no el umbral.

**Si cambias de modelo de embeddings o de idioma, esta medición deja de
valer.** Los rangos de similitud coseno no son transferibles entre modelos:
habría que repetir el ejercicio antes de reutilizar el `0.30`.

#### Sobre `VERIFY_THRESHOLD = 0.70`

Es otro umbral con otra finalidad: el `0.30` decide qué entra al contexto de
una consulta; el `0.70` decide si una pregunta sin respuesta quedó realmente
resuelta tras añadir documentación (`knowledge_gap_index_service.py`). Es
deliberadamente más exigente, porque declarar cerrado un hueco de conocimiento
requiere evidencia fuerte, no meramente relacionada. **Este valor no tiene la
medición anterior detrás** — se fijó por criterio, y queda anotado como tal.

---

## 7. Manejo de errores

### Durante la ingesta (background task)

| Error | Comportamiento |
|---|---|
| S3 inaccesible | Lanza excepción → `status = "failed"`, `error_message` guardado |
| Archivo corrupto / sin texto | `"No se pudo extraer texto del documento"` → `status = "failed"` |
| OpenAI sin respuesta | Excepción en `EmbeddingService` → `status = "failed"` |
| Pinecone timeout | Excepción en `PineconeService` → `status = "failed"` |
| Tipo no soportado | `PDFService.procesar()` lanza excepción → `status = "failed"` |

El cliente **nunca ve estos errores directamente** porque ya recibió el `201 Created`. Debe consultar el estado del documento con `GET /api/v1/documents/{id}` y usar `POST /api/v1/documents/{id}/retry` si falló.

### Durante la consulta (síncrono)

| Situación | Comportamiento |
|---|---|
| OpenAI sin API key | `500 Internal Server Error` |
| Pinecone sin API key | `500 Internal Server Error` |
| Sin resultados en Pinecone (todos bajo umbral) | El LLM recibe contexto vacío y responde: *"No encontré información sobre este tema en los documentos de la empresa."* |
| Asistente inactivo o eliminado | `404 Asistente no encontrado o inactivo` |
| Conversación de otro usuario | `404 Conversación no encontrada` |

### Eliminación de documentos

Al eliminar un documento se ejecutan tres pasos en orden:

1. Eliminar vectores de Pinecone (`eliminar_por_documento`)
2. Eliminar archivo de S3 (`eliminar_archivo`)
3. Eliminar registro de la BD

Si Pinecone falla en el paso 1, el error se ignora y se continúa (el documento deja de existir en la BD, por lo que sus vectores quedan huérfanos pero inaccesibles). Si S3 falla en el paso 2, se lanza `500` y el registro de BD no se borra.

---

## 8. Otros consumidores de embeddings/Pinecone

`app/services/knowledge_gap_index_service.py` reutiliza `EmbeddingService` y
`PineconeService` (mismo patrón de namespace con fallback asistente → empresa que
usa `RAGService.generate_response`) para el módulo de Preguntas sin respuesta:

- `find_candidates` — busca documentos candidatos para una pregunta sin responder.
- `best_score` — reejecuta la pregunta contra el índice al verificar una resolución (`POST /knowledge-gaps/{id}/verify`).
- `index_answer` — indexa una respuesta escrita a mano como chunk propio (`POST /knowledge-gaps/{id}/answer`).
- `index_alias` — indexa la pregunta y sus variantes como alias de un documento existente al vincular (`POST /knowledge-gaps/{id}/link`).

Ver `BACKLOG_BACKEND.md` → Módulo 7B para el detalle de endpoints.

---

## 9. Pendientes y mejoras futuras

| Mejora | Descripción | Impacto |
|---|---|---|
| Registro automático de `KnowledgeGap` al responder el chat | Cuando ningún chunk supera el umbral, guardar la pregunta en `knowledge_gaps` en el momento — hoy solo existe la conversión manual desde Feedback (`POST /api/v1/feedback/{id}/convert-gap`), ver Módulo 7B en `BACKLOG_BACKEND.md` | P1 |
| Auditar vectores huérfanos de antes del 2026-09-08 | Ya no es posible generar nuevos huérfanos (el borrado de un asistente con documentos/widgets vinculados está bloqueado), pero asistentes borrados *antes* de ese fix pueden tener vectores viejos sin dueño en Pinecone — revisar y limpiar manualmente si aplica | P3 |
| Streaming SSE | `StreamingResponse` con `text/event-stream` para que la respuesta aparezca token a token | P1 |
| Reranking | Tras recuperar top_k=10, usar un modelo de reranking (ej. Cohere) para seleccionar los 5 más relevantes antes de construir el contexto | P2 |
| Chunks por párrafo | En vez de chunks por caracteres, dividir respetando párrafos naturales del documento | P2 |
| Soporte de tablas en DOCX | `python-docx` extrae párrafos pero no celdas de tabla | P2 |
| Caché de embeddings de query | Si el mismo usuario repite la pregunta, reusar el embedding en vez de llamar a OpenAI | P3 |
| Modelo de embedding multilingüe | Si la empresa opera en varios idiomas, evaluar `multilingual-e5-large` | P3 |
