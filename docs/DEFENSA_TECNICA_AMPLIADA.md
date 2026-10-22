---
description: "Complemento a doc/DEFENSA_TFM.md del frontend — cubre las áreas que ese documento no toca: petición exacta al LLM, seguridad, multi-tenancy en Postgres, decisiones de stack y la pregunta de contribución académica."
---

# Defensa técnica ampliada

Este documento **no repite** lo ya cubierto en `doc/DEFENSA_TFM.md` (RAG vs
fine-tuning, embeddings, Pinecone vs pgvector, alucinaciones, evaluación,
limitaciones). Cubre las preguntas que un profesor hace cuando ya validó lo
anterior y empieza a presionar en detalle de implementación.

---

## 1. Cómo se hace exactamente la petición al LLM

Código real: `api/app/services/rag_service.py`, método `generate_response`.

```python
response = self.client.chat.completions.create(
    model=effective_model,        # "gpt-4o-mini" por defecto, override posible
    messages=messages,
    temperature=effective_temperature,  # 0.0 por defecto — era 0.7, bajada tras medirlo (ver RAG_PIPELINE.md §6)
    max_tokens=MAX_RESPONSE_TOKENS,     # 1000
)
```

**Es una llamada síncrona, no streaming.** El cliente espera la respuesta
completa antes de recibir nada — no hay Server-Sent Events ni WebSocket hacia
el LLM (el frontend tampoco lo implementa, ver `BACKLOG_FRONTEND.md`). Es una
simplificación consciente: streaming mejora la percepción de velocidad pero
complica el manejo de errores a mitad de respuesta y el cálculo de costo
(hay que sumar tokens progresivamente). Para el alcance del TFM, la llamada
síncrona es más simple de razonar y de testear.

**El array `messages` tiene un orden deliberado** (los 4 elementos):

```
1. system → DEFAULT_SYSTEM_PROMPT (reglas: usa solo el contexto, no inventes)
2. system → el contexto recuperado de Pinecone, como segundo mensaje de system
3. user/assistant → historial de la conversación (si existe)
4. user → la pregunta actual
```

**Por qué el contexto va en un mensaje `system` separado y no pegado al
mensaje del usuario:** así el modelo lo trata como un hecho dado, no como
algo que el usuario está afirmando — reduce que el LLM lo contradiga o lo
reinterprete, y mantiene la pregunta del usuario limpia sin miles de tokens
de documentos diluyendo la intención real. Esto es una decisión de diseño
del *prompting*, no un detalle trivial — si te preguntan "¿por qué no
armaste un solo mensaje con todo?", esta es la respuesta.

**Qué pasa si no hay contexto relevante:** se manda explícitamente el texto
*"No se encontró contexto relevante..."* en vez de un mensaje vacío. Un hueco
silencioso invita al modelo a rellenarlo con conocimiento propio — exactamente
lo que se quiere evitar (ver alucinaciones en `doc/DEFENSA_TFM.md` §4).

**Parámetros que se pueden override por asistente:** `system_prompt_override`,
`model_override`, `temperature_override` — cada asistente (`assistants`)
puede tener su propia personalidad/tono sin tocar código, solo configuración
en base de datos.

---

## 2. Seguridad

### Autenticación — JWT

Código: `api/app/core/security.py`.

- **Algoritmo:** HS256, clave simétrica (`SECRET_KEY`, obligatoria — la app
  **falla al arrancar** si no está definida, no en el primer request que la
  use — ver `config.py`, `Settings` sin default para campos sensibles).
- **Expiración:** 24 horas (`ACCESS_TOKEN_EXPIRE_MINUTES = 1440`). No hay
  refresh token — al expirar, el usuario vuelve a hacer login. Simplificación
  consciente: un sistema de refresh tokens añade complejidad (revocación,
  rotación) que no es el foco de este TFM.
- **Hashing de contraseñas:** bcrypt como esquema principal;
  `sha256_crypt` queda marcado `deprecated="auto"` en passlib — esto permite
  que contraseñas antiguas (si las hubiera con otro esquema) sigan
  verificando y se re-hasheen a bcrypt automáticamente en el siguiente login
  exitoso (`needs_update` de passlib), sin migración manual.

### Autorización — multi-tenancy en PostgreSQL

Esto es distinto del aislamiento por namespace de Pinecone (cubierto en
`doc/DEFENSA_TFM.md` §3) — aquí es el aislamiento de **datos relacionales**
(usuarios, documentos, conversaciones), y es el patrón que se repite en
**todos** los routers administrativos. Ejemplo real, `api/app/routers/v1/users.py`:

```python
def _get_user_in_company(repo, user_id: int, company_id: int) -> User:
    user = repo.get(user_id)
    if not user or user.company_id != company_id:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return user
```

**Dos decisiones deliberadas aquí, ambas defendibles si te preguntan:**

1. **El filtro nunca viene del request, siempre del usuario autenticado**
   (`current_user.company_id`, inyectado por `Depends(get_current_admin_user)`).
   El token firmado solo lleva el email (`sub`); con él se carga el usuario de
   la base de datos, y su empresa es la que cuenta. Un usuario nunca puede
   pasar `company_id=5` en el body o la URL para acceder a otra empresa — el
   valor se ignora si viene del cliente. Y como la empresa se lee en cada
   petición, desactivar o mover a un usuario surte efecto de inmediato.
2. **404, no 403, cuando el recurso es de otra empresa.** Si devolvieras 403
   ("prohibido"), un atacante confirma que el `user_id` *existe* en algún
   lado — solo que no puede verlo. Con 404 ("no encontrado"), la empresa A
   ni siquiera puede confirmar que el usuario `id=42` existe en la empresa B.
   Es el mismo principio que aplican GitHub/Stripe en sus APIs multi-tenant.

### CORS

`ALLOWED_ORIGINS` en `config.py` es una whitelist explícita (no `*`),
sobreescribible por entorno. En esta entrega TFM apunta a `localhost` — en
producción real se sobreescribe con la URL del frontend desplegado.

### Qué NO está cubierto (limitación honesta)

No hay rate limiting a nivel de API (un cliente puede hacer login N veces
por segundo sin bloqueo), no hay CSRF token (mitigado parcialmente por ser
una API JSON pura, no formularios), y no hay rotación de `SECRET_KEY`. Para
un TFM son limitaciones aceptables de nombrar, no de esconder.

---

## 3. Por qué este stack (FastAPI + SQLAlchemy + Pydantic)

Pregunta típica: *"¿por qué no Django, que trae más cosas de fábrica?"*

- **Contratos tipados de punta a punta.** Pydantic valida el request antes de
  que llegue a la lógica de negocio, y genera el schema de respuesta — el
  mismo modelo sirve de validación *y* de documentación. Con Django + DRF
  serializers se logra algo parecido, pero con más código de por medio.
- **OpenAPI/Swagger automático** (`/docs`) sin escribir una línea de
  documentación aparte — se usó literalmente en la demo de tutoriales
  (`docs/tutorials/`) y sirve para que el jurado explore la API en vivo.
- **Async nativo.** FastAPI está construido sobre Starlette/ASGI — relevante
  porque las llamadas a OpenAI/Pinecone son I/O de red; aunque hoy el
  servicio de RAG llama de forma síncrona al SDK de OpenAI (simplicidad de
  implementación), la app corre bajo Uvicorn con workers async, lista para
  I/O concurrente donde se necesite (ver también `main.py` + `BackgroundTasks`
  para el procesamiento asíncrono de PDFs, sin necesidad de Celery).
- **Menos "magia" que Django.** Para un proyecto de un desarrollador (no un
  equipo), un framework más explícito (SQLAlchemy directo, sin ORM-magic de
  Django) es más fácil de razonar bajo presión de tiempo de un TFM.

---

## 4. Estrategia real de chunking (corrección importante)

Código: `api/app/services/pdf_service.py`, método `dividir_en_chunks`.

**Esto es una ventana deslizante de caracteres, escrita a mano — no usa
LangChain ni ningún splitter de terceros:**

```python
def dividir_en_chunks(texto: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    chunks = []
    start = 0
    while start < len(texto):
        chunks.append(texto[start: start + chunk_size])
        start += chunk_size - overlap
    return [c for c in chunks if c.strip()]
```

- **`chunk_size = 1000` caracteres, `overlap = 200`** (20% de solape) — el
  overlap evita que una idea quede cortada exactamente en el borde entre dos
  chunks consecutivos.
- **Es character-based, no token-aware ni sentence-aware.** Puede cortar una
  palabra o una oración a la mitad. Es la limitación honesta de esta
  implementación: un splitter tipo `RecursiveCharacterTextSplitter` de
  LangChain intenta cortar en saltos de línea/oración primero y cae a
  caracteres solo como último recurso — aquí se optó por la versión más
  simple, sin la dependencia de LangChain, a cambio de fronteras de chunk
  menos "limpias" semánticamentente.
- **Por qué no se usó LangChain aquí** (si te preguntan): la única razón
  para meter una dependencia grande como LangChain sería ese único splitter
  — no justifica el peso de la librería completa para una función de <15
  líneas que se puede escribir directamente y testear sin abstracciones
  intermedias.

---

## 5. La pregunta más difícil: ¿cuál es tu contribución académica real?

Esta es la pregunta que hay que tener más clara, porque "usé la API de
OpenAI y el SDK de Pinecone" suena, mal presentado, a integración y no a
tesis. Respuesta honesta y defendible:

**La contribución de un TFM de maestría profesional (no un doctorado) no es
inventar un algoritmo nuevo de recuperación semántica — es diseñar,
implementar y validar un *sistema completo* que resuelve un problema real
con las restricciones reales que trae (multi-tenancy, costo, seguridad,
calidad medible), y que ese sistema funcione de punta a punta.**

Lo específico que sí es diseño propio, no "usar una API":

1. **El cierre del ciclo de calidad** (`knowledge_gaps` + `_auto_verify`):
   no es solo "responder preguntas", es *saber cuándo el sistema no supo
   responder*, clasificar por qué (`hard` vs `soft`), y verificar
   automáticamente si una corrección de contenido resolvió el problema. Eso
   no viene de ninguna API — es arquitectura de aplicación.
2. **El modelo de aislamiento en dos capas** (Postgres por `company_id` +
   Pinecone por namespace) diseñado y verificado con tests
   (`test_pinecone_namespace.py`), incluyendo el bug real de fallback
   cruzado que se encontró y corrigió durante el desarrollo — eso es
   ingeniería de sistemas multi-tenant, un problema no trivial.
3. **La observabilidad de costo por solicitud** (`cost_tracking`) — poder
   responder "¿cuánto cuesta atender a este cliente?" con una consulta SQL,
   no una estimación — es el tipo de instrumentación que un producto real
   necesita y que un ejemplo de tutorial de RAG normalmente no tiene.
4. **Las decisiones documentadas con sus trade-offs** (Pinecone vs pgvector,
   embeddings pequeños vs grandes, chunking manual vs LangChain) — la
   evidencia de que cada elección fue consciente y no "la primera que
   apareció en un tutorial".

**Lo que NO hay que decir:** que se inventó una técnica nueva de RAG. Eso no
es cierto y un profesor que sepa del tema lo va a notar. La honestidad sobre
el tipo de contribución (ingeniería de sistemas aplicada, no investigación
algorítmica) es más defendible que sobrevender.

---

## 6. Preguntas trampa adicionales (respuesta corta)

**¿Por qué `gpt-4o-mini` y no `gpt-4o`?**
Costo (`gpt-4o-mini` es sustancialmente más barato) y latencia, con calidad
suficiente para preguntas y respuestas acotadas a documentos — no para
razonamiento complejo. El campo `model_override` por asistente deja abierta
la puerta a usar un modelo más potente donde se justifique, sin cambiar
código.

**¿Qué pasa si dos usuarios de la misma empresa preguntan al mismo tiempo?**
Cada request es independiente (no hay estado compartido en memoria del
servicio) — SQLAlchemy maneja su propia sesión por request (`get_db`,
`Depends`), y Pinecone/OpenAI son servicios externos sin estado compartido
por request. No hay condición de carrera conocida en la ruta de consulta.
Donde sí podría haberla (no verificado con test) es en la escritura
concurrente del pipeline de ingesta de documentos.

**¿Cómo escalarías esto a miles de empresas?**
Honesto: el cuello de botella hoy no es el LLM ni Pinecone (ambos
serverless, escalan solos) — es PostgreSQL con `create_all()` en vez de
migraciones versionadas (Alembic, pendiente, ver limitaciones) y la falta de
caché de embeddings para preguntas repetidas. Es una limitación de madurez
operativa, no de arquitectura de fondo.

**¿Qué pasa con la privacidad de los documentos de cada empresa?**
Los documentos viven en S3 con clave por documento (`s3_service.py`) y los
vectores en el namespace aislado de Pinecone — ninguna empresa puede
consultar el namespace de otra por diseño (ver aislamiento, §2 y
`doc/DEFENSA_TFM.md` §3). No hay cifrado en reposo *a nivel de aplicación*
adicional al que ofrece el proveedor de storage — es una limitación a
nombrar si preguntan por cumplimiento normativo (GDPR-like).

---

*Este documento se apoya en el código real de `api/` a la fecha de esta
entrega. Cada afirmación tiene un archivo y una función detrás — pídelos
si hace falta mostrarlos en la defensa.*
