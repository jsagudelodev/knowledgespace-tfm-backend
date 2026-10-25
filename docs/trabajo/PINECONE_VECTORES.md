# Pinecone — Arquitectura Vectorial

> Referencia de implementación para el vector store de KnowledgeSpace.
> Servicios relacionados: `api/app/services/pinecone_service.py`, `api/app/services/embedding_service.py`

---

## Tabla de contenidos

1. [¿Qué es un vector y por qué usamos Pinecone?](#1-qué-es-un-vector-y-por-qué-usamos-pinecone)
2. [Estructura del índice](#2-estructura-del-índice)
3. [Namespaces — aislamiento multi-tenant](#3-namespaces--aislamiento-multi-tenant)
4. [Estructura de un vector](#4-estructura-de-un-vector)
5. [Operaciones disponibles](#5-operaciones-disponibles)
6. [Búsqueda semántica — cómo funciona el score](#6-búsqueda-semántica--cómo-funciona-el-score)
7. [Embeddings — de texto a vector](#7-embeddings--de-texto-a-vector)
8. [Ciclo de vida de los vectores](#8-ciclo-de-vida-de-los-vectores)
9. [Configuración y variables de entorno](#9-configuración-y-variables-de-entorno)
10. [Casos límite y comportamientos importantes](#10-casos-límite-y-comportamientos-importantes)

---

## 1. ¿Qué es un vector y por qué usamos Pinecone?

Un **embedding** es la representación numérica del significado de un texto. OpenAI convierte cualquier fragmento de texto en una lista de 1536 números (floats) que capturan su semántica.

```
"política de vacaciones"  →  [0.023, -0.187, 0.441, ..., 0.019]  (1536 dims)
"días de descanso anuales" →  [0.031, -0.201, 0.438, ..., 0.022]  (1536 dims)
```

Ambas frases significan cosas parecidas → sus vectores son **cercanos** en el espacio de 1536 dimensiones. Una base de datos relacional (PostgreSQL) no puede hacer esta búsqueda por proximidad eficientemente — Pinecone sí, en milisegundos, sobre millones de vectores.

**Por qué Pinecone y no pgvector:**
- Pinecone es serverless: no hay índices que administrar ni re-indexar al agregar datos.
- La búsqueda ANN (Approximate Nearest Neighbor) ya está optimizada — no requiere tuning de parámetros HNSW ni IVFFlat.
- Se escala automáticamente con el volumen de datos.

---

## 2. Estructura del índice

KnowledgeSpace usa **un único índice** para todas las empresas:

```
Índice: "knowspace"  (configurable en PINECONE_INDEX_NAME)
├── Métrica:    cosine
├── Dimensión:  1536   (fija por text-embedding-3-small)
├── Tipo:       serverless
└── Cloud/Región: AWS us-east-1
```

El aislamiento entre empresas se logra con **namespaces** (no con índices separados). Esto reduce costos y simplifica la administración.

### Inicialización automática

Al arrancar la app, `lifespan()` en `main.py` llama a `PineconeService().asegurar_indice()`, que crea el índice si no existe:

```python
# pinecone_service.py
def asegurar_indice(self) -> None:
    indices = [idx.name for idx in self.pc.list_indexes().indexes]
    if self.nombre_indice not in indices:
        self.pc.create_index(
            name=self.nombre_indice,
            dimension=self.DIMENSION,   # 1536
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
        )
```

Si el índice ya existe, la llamada no hace nada. Es seguro llamarla en cada arranque.

---

## 3. Namespaces — aislamiento multi-tenant

Un namespace es un **espacio lógico dentro del índice** que aísla vectores. Las búsquedas solo devuelven resultados del namespace consultado — nunca cruzan a otro.

### Convención de nombres

```python
# pinecone_service.py → construir_namespace()

"company-5"              # empresa 5, documentos sin asistente asignado
"company-5-assistant-3"  # empresa 5, asistente 3
"company-12-assistant-1" # empresa 12, asistente 1
```

### Cuándo se usa cada namespace

```
┌─────────────────────────────────────────────────────────────────────┐
│  Al SUBIR un documento                                              │
│                                                                     │
│  assistant_id = None  →  namespace "company-{cid}"                 │
│  assistant_id = 3     →  namespace "company-{cid}-assistant-3"      │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│  Al BUSCAR (chat)                                                   │
│                                                                     │
│  1. Buscar en namespace del asistente                               │
│  2. Si no hay resultados → fallback a namespace de la empresa       │
│                                                                     │
│  Esto permite que el asistente use sus documentos propios,          │
│  pero si no tiene nada relevante busca en el pool general.          │
└─────────────────────────────────────────────────────────────────────┘
```

### Por qué no un índice por empresa

| Enfoque | Pros | Contras |
|---|---|---|
| Un índice, namespaces por empresa | Bajo costo, administración simple | No permite métricas distintas por empresa |
| Un índice por empresa | Aislamiento total, métricas independientes | Costoso (Pinecone cobra por índice), complejo |

Para el volumen actual de KnowledgeSpace, **namespaces** es la opción correcta.

---

## 4. Estructura de un vector

Cada chunk de texto genera un vector con la siguiente forma:

```python
{
    "id": "doc-42-chunk-7",          # único en todo el índice
    "values": [0.023, -0.187, ...],  # 1536 floats — el embedding
    "metadata": {
        "document_id":   42,
        "document_name": "manual_rrhh.pdf",
        "company_id":    5,
        "assistant_id":  3,          # None si no tiene asistente
        "chunk_index":   7,          # posición del chunk dentro del doc
        "text":          "El período de vacaciones anual es de...",  # max 1000 chars
    }
}
```

### Convención del ID

```
"doc-{document_id}-chunk-{chunk_index}"

doc-42-chunk-0   → primer chunk del documento 42
doc-42-chunk-1   → segundo chunk
doc-42-chunk-27  → último chunk (si tiene 28 chunks)
```

Esta convención permite eliminar todos los vectores de un documento usando el filtro `document_id` en la metadata, sin necesidad de guardar los IDs individuales en la BD.

### Metadata guardada en Pinecone

La metadata sirve para dos propósitos:

1. **Filtrado** — `eliminar_por_documento()` usa `filter: {document_id: 42}` para borrar solo los chunks de ese documento.
2. **Mostrar fuentes** — cuando el LLM responde, `document_name` y el extracto de `text` se devuelven al cliente como `sources` para que el usuario sepa de qué documento vino la información.

> **Límite de Pinecone:** la metadata tiene un límite de 40 KB por vector. El campo `text` se trunca a 1000 caracteres para no acercarse a ese límite.

### Vectores del módulo Knowledge Gaps (Preguntas sin respuesta)

`app/services/knowledge_gap_index_service.py` agrega dos convenciones de ID
nuevas, fuera del patrón `doc-{document_id}-chunk-{chunk_index}` de la ingesta
normal — ambas viven en el mismo namespace de la empresa/asistente:

```
"gap-{gap_id}-answer"       # respuesta escrita a mano (POST /knowledge-gaps/{id}/answer)
"gap-{gap_id}-alias-{i}"    # pregunta + variantes, al vincular a un documento existente
                             # (POST /knowledge-gaps/{id}/link) — i = índice dentro de esa brecha
```

- **`gap-{id}-answer`**: `document_id` va en `None` (no hay documento real detrás)
  y agrega `knowledge_gap_id` + `answered_by` a la metadata.
- **`gap-{id}-alias-{i}`**: `document_id` es el del documento vinculado — hace que
  la nueva redacción devuelva ese mismo documento en búsquedas futuras. Agrega
  `knowledge_gap_id` y `alias_of_chunk_id` (el `chunk_index` con el que se vinculó).

Ninguno de los dos se limpia con `eliminar_por_documento()` salvo el alias
(comparte `document_id` con el documento real, así que si el documento se borra,
el alias se borra con él). El vector `answer` queda huérfano si se borra la
brecha — no hay limpieza automática para ese caso todavía.

---

## 5. Operaciones disponibles

### `upsert_vectores` — insertar o actualizar

```python
PineconeService().upsert_vectores(vectores, namespace="company-5-assistant-3")
```

Upsert significa "insert or update". Si un vector con el mismo ID ya existe, se sobreescribe. Esto permite re-procesar un documento (retry) sin dejar vectores duplicados.

### `buscar_vectores` — búsqueda semántica

```python
resultados = PineconeService().buscar_vectores(
    vector_consulta=embedding_de_la_query,  # [1536 floats]
    top_k=5,                                # máximo de resultados
    namespace="company-5",
)
# resultados → lista de Match con .id, .score, .metadata
```

Devuelve los `top_k` vectores más similares al vector consulta, ordenados de mayor a menor score.

### `eliminar_por_documento` — limpieza al borrar un documento

```python
PineconeService().eliminar_por_documento(
    document_id=42,
    namespace="company-5-assistant-3"
)
```

Usa el filtro de metadata `{document_id: 42}` para eliminar todos los chunks del documento de una sola llamada, sin necesidad de conocer los IDs individuales.

También se llama, con el mismo efecto idempotente, antes de cada reindexado (ver `docs/TFM/RAG_PIPELINE.md`). **Si el namespace todavía no existe** —el primer documento que se indexa para un asistente nuevo— Pinecone responde 404 en vez de no borrar nada; `eliminar_por_documento` lo trata como éxito, no como error (bug real encontrado el 2026-10-24: sin esto, subir el primer documento de cualquier asistente fallaba siempre con `"Namespace not found"`).

### `eliminar_vectores` — eliminar por IDs explícitos

```python
PineconeService().eliminar_vectores(
    ids=["doc-42-chunk-0", "doc-42-chunk-1"],
    namespace="company-5"
)
```

Uso menos frecuente — se prefiere `eliminar_por_documento` porque no requiere conocer los IDs.

---

## 6. Búsqueda semántica — cómo funciona el score

Pinecone calcula la **similitud coseno** entre el vector de la consulta y cada vector almacenado:

```
score = cos(θ) = (A · B) / (|A| × |B|)

score = 1.0  → vectores idénticos (misma dirección)
score = 0.0  → vectores perpendiculares (sin relación semántica)
score < 0    → no ocurre con embeddings de texto (siempre ≥ 0)
```

### Umbral de relevancia

```python
# rag_service.py
RELEVANCE_THRESHOLD = 0.30

relevant_docs = [d for d in raw_docs if d.score >= RELEVANCE_THRESHOLD]
```

Los chunks que no superan `0.30` se descartan antes de construir el contexto. Si ninguno lo supera, el LLM recibe contexto vacío y responde que no encontró información.

### Referencia práctica de scores

| Score | Interpretación |
|---|---|
| `0.85 – 1.0` | El chunk responde directamente la pregunta |
| `0.65 – 0.84` | Información relacionada, probablemente útil |
| `0.45 – 0.64` | Temáticamente cercano, contexto de apoyo |
| `0.30 – 0.44` | Relación débil — se incluye pero puede añadir ruido |
| `< 0.30` | Descartado — probablemente irrelevante |

> Los valores exactos dependen del modelo de embedding y del idioma. Con `text-embedding-3-small` en español, `0.30` es un punto de corte razonable. Para contenido muy técnico o jerga específica, bajar a `0.25` puede ayudar.

---

## 7. Embeddings — de texto a vector

El modelo `text-embedding-3-small` de OpenAI convierte cualquier texto en un vector de **1536 dimensiones**. La dimensión es fija — no depende del largo del texto.

### Generación en batch (ingesta)

```python
# embedding_service.py
def generar_embeddings_batch(self, textos: List[str], batch_size: int = 100):
    for i in range(0, len(textos), batch_size):
        batch = textos[i : i + batch_size]
        respuesta = self.cliente.embeddings.create(model=self.modelo, input=batch)
        # ordena por índice — la API no garantiza el orden de respuesta
        embeddings = [item.embedding for item in sorted(respuesta.data, key=lambda x: x.index)]
```

Un documento con 300 chunks genera **3 llamadas** a OpenAI (300 / 100 = 3 batches), no 300. Esto reduce latencia y costo.

### Generación unitaria (consulta)

```python
# embedding_service.py
def generar_embedding(self, texto: str) -> List[float]:
    respuesta = self.cliente.embeddings.create(model=self.modelo, input=texto)
    return respuesta.data[0].embedding
```

Cada mensaje de chat genera una llamada independiente para convertir la pregunta en vector.

### Costo orientativo de embeddings

`text-embedding-3-small` cuesta **$0.02 / 1M tokens**. Un chunk de 1000 caracteres ≈ 250 tokens. Un documento de 100 páginas ≈ 500 chunks ≈ 125K tokens ≈ **$0.0025** por documento procesado.

---

## 8. Ciclo de vida de los vectores

```
Documento subido
      │
      ▼
status = "processing"
      │
      ▼
Vectores en Pinecone ──────────────────────────────────────────┐
      │                                                        │
      ▼                                                        │
status = "completed"                                           │
      │                                                        │
      │  El documento existe y sus vectores están activos      │
      │                                                        ▼
      │                                               Búsquedas del chat
      │                                               los encuentran
      │
      │  Usuario borra el documento
      ▼
eliminar_por_documento() → vectores eliminados de Pinecone
      │
      ▼
Archivo eliminado de S3
      │
      ▼
Registro eliminado de BD
```

### Casos donde los vectores quedan huérfanos

| Situación | Estado en Pinecone | Consecuencia |
|---|---|---|
| `status = "failed"` | Puede haber vectores parciales si el pipeline falló a mitad | Se sobreescriben con el retry (upsert) |
| Asistente eliminado (soft delete) | Vectores en `company-{id}-assistant-{aid}` permanecen | No se devuelven en búsquedas futuras (el asistente ya no existe), pero ocupan espacio |
| Documento re-procesado (retry) | Upsert sobreescribe los vectores existentes | Sin duplicados |

> **Deuda técnica:** al hacer soft delete de un asistente, se debería llamar a `PineconeService().eliminar_vectores(filter={assistant_id: X}, namespace=...)` para limpiar su namespace. Actualmente no está implementado.

---

## 9. Configuración y variables de entorno

```env
# .env
PINECONE_API_KEY=pc-xxxxxxxxxxxx
PINECONE_INDEX_NAME=knowspace      # nombre del índice (default: "knowspace")
OPENAI_API_KEY=sk-xxxxxxxxxxxx
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
```

Todos los valores se leen desde `app/core/config.py` vía `pydantic-settings`. Nunca hardcodear la API key en el código.

---

## 10. Casos límite y comportamientos importantes

### El namespace no existe aún

Si se hace una búsqueda en un namespace vacío (la empresa acaba de crearse y no ha subido documentos), Pinecone devuelve una lista vacía — no lanza error. El chat responde con el mensaje de "no encontré información".

### Mismo documento re-procesado

El retry llama a `upsert_vectores` con los mismos IDs (`doc-{id}-chunk-{i}`). Pinecone hace un upsert — sobreescribe los valores y metadata. No quedan duplicados.

### Documentos muy cortos (< 1 chunk)

Si el texto extraído tiene menos de 1000 caracteres, `dividir_en_chunks` genera exactamente 1 chunk. El documento se indexa igualmente.

### Documentos sin texto extraíble

Si `PDFService.procesar()` devuelve texto vacío (PDF escaneado sin OCR, imagen embebida), se lanza `Exception("No se pudo extraer texto del documento")` y el documento queda en `status = "failed"`. Pendiente: integrar un servicio OCR (ej. AWS Textract) para este caso.

### Límite de metadata por vector

Pinecone acepta hasta **40 KB de metadata** por vector. El campo `text` se trunca a 1000 caracteres para evitar acercarse a ese límite. Si se añaden más campos a la metadata en el futuro, recalcular si el total sigue bajo 40 KB.

### Consistencia entre BD y Pinecone

La BD y Pinecone son dos almacenes independientes — no hay transacciones distribuidas entre ellos. Si la app cae justo después de subir vectores a Pinecone pero antes de hacer `db.commit()`, el documento quedará en `status = "processing"` en la BD pero con vectores en Pinecone. El retry lo resuelve (upsert sobreescribe).
