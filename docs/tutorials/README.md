# Tutoriales Interactivos: LLM, RAG, Embeddings, Pinecone

Estos scripts te enseñan cómo funciona tu proyecto desde **el código real hacia afuera**. No son ejemplos ficticios — usan tu BD, tus documentos, tu Pinecone.

## Estructura

```
00_explorar_proyecto.py       ← Empieza AQUÍ. Ve qué datos tienes
01_embeddings_real.py         ← Entiende qué es un embedding
02_pinecone_busqueda.py       ← Cómo Pinecone busca documentos
03_rag_completo.py            ← El flujo end-to-end
04_alucinaciones.py           ← Cómo prevenimos que el LLM invente cosas
```

## Cómo ejecutar

Desde la raíz del repositorio, o desde cualquier otro directorio:

```bash
python docs/tutorials/00_explorar_proyecto.py
```

Cada script se sitúa solo: calcula la ruta de `api/` a partir de su propia
ubicación (`__file__`) y hace `chdir` ahí antes de importar nada. Eso es
necesario porque los scripts importan el paquete `app`, que vive dentro de
`api/`, y porque `app/core/config.py` carga el `.env` por ruta relativa al
directorio de trabajo.

Requisito previo: `api/.env` configurado con las credenciales reales
(`DATABASE_URL`, `OPENAI_API_KEY`, `PINECONE_API_KEY`). Ver `COMO_ARRANCAR.md`.

## Paso a paso

### 0️⃣ Preparación

```bash
python docs/tutorials/00_explorar_proyecto.py
```

Esto te dirá:
- Qué empresas/asistentes/documentos tienes
- Qué IDs editar en los siguientes scripts

**Si no tienes datos:** sube un documento desde el frontend primero.

### 1️⃣ Embeddings

```bash
# Edita DOCUMENT_ID en el script (ve el paso anterior para los IDs)
python ..\docs\tutorials\01_embeddings_real.py
```

**Qué aprenderás:**
- Un embedding = números que representan el *significado* del texto
- Cómo se dividen los documentos en chunks (trozos pequeños)
- La similitud coseno: cómo Pinecone mide si dos chunks hablan de lo mismo
- Por qué OpenAI genera 1536 números por chunk

**Conceptos clave:**
```
"¿Cuánto cuesta un iPhone?" → [0.123, -0.456, ..., 0.789] (1536 números)
"¿Cuál es el precio de un móvil?" → [0.125, -0.451, ..., 0.785] 
                                     (muy parecido al anterior)
```

### 2️⃣ Búsqueda en Pinecone

```bash
# Edita QUERY (tu pregunta) y ASSISTANT_ID
python ..\docs\tutorials\02_pinecone_busqueda.py
```

**Qué aprenderás:**
- Tu pregunta se convierte a embedding (igual que los chunks)
- Pinecone busca qué chunks tienen embeddings más similares
- El "score" (0.0-1.0) = cuán seguro está Pinecone de que es relevante
- Los top 5 chunks se devuelven

**Conceptos clave:**
```
score >= 0.70 → "muy seguro, es relevante"
score 0.5-0.70 → "bastante seguro"
score 0.3-0.5 → "dudoso"
score < 0.3 → "muy dudoso" (no se pasa al LLM)
```

### 3️⃣ Flujo RAG Completo

```bash
# Edita QUERY y ASSISTANT_ID
python ..\docs\tutorials\03_rag_completo.py
```

**IMPORTANTE:** Este script llama a OpenAI. Tiene costo (típicamente < $0.001 por llamada).

**Qué aprenderás:**
- Cómo se "construye" el prompt que se envía al LLM:
  1. Instrucciones del sistema
  2. El contexto (los chunks de Pinecone)
  3. El historial de la conversación
  4. La pregunta del usuario
- Qué tokens gasta el LLM (entrada vs salida)
- Cómo se calcula el costo
- Las fuentes que el LLM usó para responder

**Conceptos clave:**
```
Prompt que el LLM ve:
┌─ Sistema: "Responde basado SOLO en el contexto"
├─ Contexto: "Los 5 chunks de Pinecone van aquí"
├─ Historial: "Conversación previa..."
└─ Usuario: "¿Tu pregunta?"
```

### 4️⃣ Alucinaciones

```bash
python ..\docs\tutorials\04_alucinaciones.py
```

**Qué aprenderás:**
- Qué es una alucinación (LLM inventa cosas que no están en los documentos)
- 4 CONTROLES que las previenen:
  1. **RELEVANCE_THRESHOLD = 0.30** — chunks débiles no llegan al LLM
  2. **PROMPT RESTRICTIVO** — el LLM sabe que NO debe alucinar
  3. **AISLAMIENTO** — cada espacio ve solo sus documentos
  4. **REGISTRO** — preguntas sin respuesta se documentan
- Diferencia entre LLM "libre" vs LLM "restringido"

## Conceptos que conectan todo

```
┌─ EMBEDDING (Tutorial 1)
│  └─ Convertir texto a números
│
├─ PINECONE (Tutorial 2)
│  └─ Guardar esos números + buscar similares
│
├─ CONSTRUCCIÓN DE CONTEXTO (Tutorial 3)
│  └─ Tomar los chunks encontrados
│  └─ Armarlos en un bloque de texto coherente
│
├─ LLM / GENERACIÓN (Tutorial 3)
│  └─ El LLM lee contexto + pregunta
│  └─ Genera la respuesta
│
└─ PREVENCIÓN DE ALUCINACIONES (Tutorial 4)
   └─ Threshold + Prompt + Aislamiento + Registro
```

## Dónde se encuentran los archivos en el código real

- `EmbeddingService`: `api/app/services/embedding_service.py`
- `PineconeService`: `api/app/services/pinecone_service.py`
- `RAGService`: `api/app/services/rag_service.py`
- `DEFAULT_SYSTEM_PROMPT`: `api/app/services/rag_service.py` línea 12
- `RELEVANCE_THRESHOLD`: `api/app/services/rag_service.py` línea 9

## Preguntas frecuentes

### ¿Por qué 1536 dimensiones?
OpenAI eligió ese número. Es un equilibrio entre:
- Más dimensiones = más información capturada (mejor)
- Menos dimensiones = más rápido y barato (mejor)
- 1536 es el sweet spot para `text-embedding-3-small`

### ¿Qué es un namespace?
Compartimento en Pinecone. Aislamiento:
```
Empresa 1, Asistente A → namespace "company-1-assistant-1"
Empresa 1, Asistente B → namespace "company-1-assistant-2"
Empresa 2, Asistente A → namespace "company-2-assistant-1"
```
Cuando buscas, solo buscas en TU namespace.

### ¿Qué es el score?
Similitud coseno entre dos vectores (0 = distintos, 1 = idénticos).
Pinecone devuelve los chunks con score más alto.

### ¿Por qué el threshold es 0.30?
Es un umbral bajo a propósito:
- Threshold muy alto (ej. 0.80) → pocos resultados, usuario se frustra
- Threshold muy bajo (ej. 0.10) → muchos falsos positivos, alucinaciones
- 0.30 es empírico: "bastante seguro de que es relevante"

### ¿Cuánto cuesta una pregunta?
Típicamente:
- Embedding (pregunta): ~0.000002 USD
- Chat (respuesta): ~0.0001-0.0005 USD
- Total: ~0.0001-0.0006 USD = 0.01-0.06 centavos

Se registra en `cost_tracking` tabla (ver `03_rag_completo.py`).

## Ejercicios prácticos

### Ejercicio 1: Variar similaridad

**Objetivo:** Entender qué hace que un embedding sea "similar" a otro

Edita `01_embeddings_real.py`:
```python
# Agregar estas preguntas similares
textos_similares = [
    chunks[0],  # Un chunk del documento
    "resumen de: " + chunks[0],
    "¿qué dice lo siguiente? " + chunks[0],
    chunks[1],  # Otro chunk distinto
]
```

**Qué deberías ver:**
- chunks[0] vs "resumen de: ..." → score muy alto (>0.9) = misma información
- chunks[0] vs chunks[1] → score bajo (0.1-0.5) = información diferente

**Concepto:** El embedding captura *significado*, no palabras exactas.

---

### Ejercicio 2: Manipular el threshold

**Objetivo:** Ver cómo el RELEVANCE_THRESHOLD controla qué llega al LLM

Edita `02_pinecone_busqueda.py`:
```python
# Después de obtener resultados, filtra manualmente:
threshold = 0.30
high_relevance = [r for r in results if r.get("score", 0) >= threshold]
low_relevance = [r for r in results if r.get("score", 0) < threshold]

print(f"Alta relevancia (>= {threshold}): {len(high_relevance)} chunks")
print(f"Baja relevancia (< {threshold}): {len(low_relevance)} chunks")
```

**Qué deberías ver:**
- Con threshold 0.30: algunos resultados se incluyen
- Edita a 0.70: resultados se reducen
- Edita a 0.10: resultados aumentan (pero más ruido)

**Concepto:** El threshold es el equilibrio entre "confianza" y "cobertura".

---

### Ejercicio 3: Prompt restrictivo vs libre

**Objetivo:** Ver la diferencia entre un LLM sin restricciones y uno controlado

Edita `04_alucinaciones.py`:
```python
# Agrega una tercera prueba:
print(f"\n   Test C: CON CONTEXTO REAL (chunks del proyecto)")
try:
    # Toma los chunks del tutorial 1 y úsalos como contexto
    chunks_reales = "Aquí van los chunks reales de tu documento"
    response = client.chat.completions.create(
        model=settings.OPENAI_CHAT_MODEL,
        messages=[
            {"role": "system", "content": DEFAULT_SYSTEM_PROMPT},
            {"role": "system", "content": f"Contexto:\n{chunks_reales}"},
            {"role": "user", "content": "¿Qué dice esto?"},
        ],
        max_tokens=100,
    )
    print(f"   Respuesta: {response.choices[0].message.content}")
    print(f"   ✓ El LLM responde basado SOLO en el contexto")
except Exception as e:
    print(f"   ❌ Error: {e}")
```

**Concepto:** El prompt restrictivo + contexto = respuestas confiables.

---

### Ejercicio 4: Costo acumulado

**Objetivo:** Medir cuánto cuesta hacer múltiples preguntas

Edita `03_rag_completo.py`:
```python
# Haz un loop de preguntas
queries = [
    "¿Qué es esto?",
    "¿Cómo funciona?",
    "¿Cuál es el precio?",
]

total_cost = 0
for q in queries:
    # Copia el código de generate_response() aquí
    # Suma los costos
    total_cost += cost_de_esta_pregunta

print(f"Costo total de {len(queries)} preguntas: ${total_cost:.6f}")
print(f"Costo promedio por pregunta: ${total_cost/len(queries):.6f}")
```

**Concepto:** El costo compuesto: embeddings + LLM se suma.

---

### Ejercicio 5: Comparar asistentes

**Objetivo:** Ver cómo cada asistente ve sus propios documentos (aislamiento)

Si tienes múltiples asistentes, edita `02_pinecone_busqueda.py`:
```python
# Ejecuta lo mismo con ASSISTANT_ID = 1, luego con = 2
# Los resultados deberían ser DIFERENTES
# Porque cada asistente tiene su propio namespace
```

**Concepto:** namespace aislamiento = datos privados por espacio.

---

## Para la defensa

Estos tutoriales son **exactamente** lo que vas a explicar:

1. **Arquitectura RAG**: los 5 pasos (embedding, Pinecone, contexto, LLM, respuesta)
2. **Aislamiento multi-tenant**: namespaces, company_id, assistant_id
3. **Mitigación de alucinaciones**: 4 capas de defensa
4. **Costo de inferencia**: dónde se registra, cómo se mide
5. **Verificación de conocimiento**: las Preguntas sin respuesta

Puedes ejecutar uno de estos scripts EN LA DEFENSA en vivo si quieres demostrar funcionamiento real.

**Sugerencia de demostración en vivo:**
1. Abre `03_rag_completo.py`
2. Edita QUERY con una pregunta del público
3. Corre el script → muestra cómo busca, qué encuentra, cuánto cuesta
4. Explica mientras se ejecuta: "Ves cómo busca en Pinecone? Esos son los chunks. El LLM los ve así: ..."
5. Demuestra el costo: "Esta pregunta costó $X, que es rastreable en la tabla `cost_tracking`"
