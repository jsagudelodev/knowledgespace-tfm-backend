# Observabilidad del pipeline RAG

Cómo se audita una respuesta después de que ocurra: qué se preguntó, qué
fragmentos se recuperaron, con qué puntuación, cuáles superaron el umbral y qué
respondió el modelo.

Implementado el 9 de octubre de 2026. Fuente de la sección 6.3 de la memoria.

---

## Por qué existe

Hasta ahora el pipeline **no dejaba rastro**: `rag_service.py`, `chat.py` y
`pinecone_service.py` no tenían una sola llamada a `logger`. Cuando una
respuesta salía mal no había forma de saber si el problema estaba en la
recuperación, en el umbral o en el modelo.

Eso no es una carencia teórica. Durante cuatro meses hubo cuatro documentos
indexados en un *namespace* que el sistema no consultaba: la interfaz los
mostraba como procesados, el chat respondía con normalidad, y simplemente nunca
recuperaba nada de ellos. **Nada falló de forma visible.** El problema se
descubrió auditando el índice contra la base de datos, no por un error (ver
`NUCLEO_RAG.md` §0).

Con trazas, ese fallo se habría visto el primer día: una consulta sobre Tema 1
devolviendo cinco fragmentos de Tema 3.

---

## Dos niveles: traza y observación

Langfuse organiza todo en dos conceptos:

- **Traza** (*trace*): una operación completa. Aquí, **una consulta del usuario**.
- **Observación** (*span*): una etapa dentro de la traza.

Una traza es un árbol de observaciones. Cada consulta del sistema genera cinco:

```
rag.consulta                        ← traza raíz (decorador)
├── embedding_consulta        SPAN        instrumentada a mano
│   └── OpenAI-embedding      EMBEDDING   automática
├── recuperacion              SPAN        instrumentada a mano
└── OpenAI-generation         GENERATION  automática
```

**Dos son automáticas.** El cliente de OpenAI se sustituye por el envoltorio de
Langfuse, que registra cada llamada con su modelo, sus tokens y su coste sin que
el código que lo invoca cambie. Las otras dos se marcan explícitamente, porque
Langfuse no puede adivinar que este sistema tiene un umbral de relevancia.

---

## Qué se registra, y por qué eso

| Observación | Contenido |
|---|---|
| `embedding_consulta` | tokens consumidos y dimensiones del vector |
| `OpenAI-embedding` | modelo, tokens, coste |
| `recuperacion` | *namespace*, `top_k`, y **cada fragmento con su documento, su puntuación y si supera el umbral** |
| `OpenAI-generation` | modelo, temperatura, tokens de entrada y salida, coste |
| traza raíz | `company_id`, `assistant_id`, *namespace*, cuántos se recuperaron y cuántos superaron el umbral |

**Lo que da valor a la traza es el umbral.** Que una llamada a OpenAI costó
tanto lo sabe cualquier herramienta; que tres de cinco fragmentos no llegaron a
`0.30` solo lo sabe este sistema, y es lo que explica por qué la respuesta salió
como salió.

### La etiqueta `sin_contexto`

Cuando ningún fragmento supera el umbral, la traza se marca con esa etiqueta:

```python
etiquetas = ["rag"] + ([] if relevant_docs else ["sin_contexto"])
```

Filtrando por ella se obtienen **todas las consultas en las que el sistema debió
abstenerse**. Esa lista es material de evaluación directo: ahí se comprueba si
el umbral está bien calibrado y si el modelo obedece la instrucción de responder
"No encontré información sobre este tema en los documentos de la empresa".

---

## Decisiones de diseño

### La dependencia es opcional

`LANGFUSE_ENABLED` está en `false` por defecto y las claves pueden quedar
vacías. El resto de credenciales del `.env` son obligatorias —sin ellas la
aplicación no arranca—, pero esta no: **quien clone el repositorio debe poder
levantarlo sin darse de alta en un servicio de terceros.** Sin Langfuse se
pierden las trazas; el registro por `logger` sigue disponible.

Verificado: la misma consulta con las trazas apagadas devuelve las mismas cinco
fuentes y los mismos 1.648 tokens de entrada.

### Toda la condicionalidad vive en un módulo

`app/core/observabilidad.py` concentra el "si está activo o no". Sin él,
`rag_service` se llenaría de `if settings.LANGFUSE_ENABLED`. Con él, el pipeline
se lee igual en ambos casos:

| Función | Con Langfuse | Sin Langfuse |
|---|---|---|
| `cliente_openai()` | el envoltorio trazado | `openai.OpenAI` |
| `observar(nombre)` | decorador de traza | devuelve la función intacta |
| `paso(nombre)` | abre una observación | entrega un diccionario que se descarta |
| `anotar_traza(...)` | escribe sesión, etiquetas y metadatos | no hace nada |

Es una abstracción con **dos implementaciones reales**, no una envoltura
especulativa. La distinción importa: en este proyecto se descartó deliberadamente
abstraer otras piezas que solo tenían una implementación.

### Un fallo de las trazas nunca rompe una respuesta

Todas las operaciones de Langfuse van dentro de `try`. El SDK además envía en
segundo plano y por lotes. Es el mismo criterio que en el registro de costes:
perder un dato contable o una traza es aceptable; romper la respuesta al
usuario, no.

Quedó demostrado por accidente: el primer intento tenía el *host* equivocado y
una llamada a una API retirada. Las dos consultas de prueba **se respondieron
con normalidad** —cinco fuentes y cero fuentes, tokens correctos— mientras las
trazas fallaban en segundo plano.

---

## Cómo activarlo

1. Crear un proyecto en Langfuse Cloud (plan gratuito) o levantarlo en local con
   Docker.
2. Copiar la clave pública y la secreta.
3. En `api/.env`:

```
LANGFUSE_ENABLED=true
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=https://us.cloud.langfuse.com
```

### ⚠️ La región

Langfuse Cloud tiene **dos regiones con hosts distintos**:

```
Europa           https://cloud.langfuse.com
Estados Unidos   https://us.cloud.langfuse.com
```

Unas claves de una región contra el host de la otra devuelven:

```
401 {"message":"Invalid credentials. Confirm that you've configured the correct host."}
```

Se parece a unas claves mal copiadas y no lo es. Ocurrió al configurarlo por
primera vez. Para comprobarlo:

```python
from langfuse import Langfuse
Langfuse(public_key=..., secret_key=..., host=...).auth_check()
```

---

## Notas de implementación

**Langfuse 4 cambió la API respecto a la 3.** Dos cosas que rompen al seguir
documentación antigua:

- `start_as_current_span` pasó a ser `start_as_current_observation`, con un
  parámetro `as_type`.
- `update_current_trace` desapareció. Los metadatos van por
  `update_current_span`; la sesión y las etiquetas se escriben directamente
  sobre el *span* de OpenTelemetry, que es el soporte real de la versión 4.

**Arrastra la pila de OpenTelemetry.** `langfuse==4.17.0` instala 14 paquetes
transitivos. Es el estándar de trazas sobre el que Langfuse está construido, no
una dependencia caprichosa, pero conviene saberlo: `requirements.txt` pasa de
una veintena de líneas a tener un árbol de observabilidad detrás.

**Las organizaciones nuevas no tienen la API antigua.** Las creadas a partir del
16 de septiembre de 2026 reciben `410 LEGACY_API_UNAVAILABLE_FOR_NEW_ORGANIZATION`
en `/api/public/traces` y `/api/public/observations`. El endpoint vigente es
`/api/public/v2/observations`, que exige `fromStartTime` y **solo devuelve
resúmenes**: para ver el contenido de cada paso hay que entrar en la interfaz.

---

## Estado y limitaciones

**Funcionando:** instrumentación completa, credenciales válidas, trazas llegando
con sus cinco observaciones, sesión y latencia registradas.

**Lo que falta:**

- **Ejecutar un dataset contra el RAG desde Langfuse**, que es la segunda mitad
  de lo que pidió el tutor. Requiere el conjunto de evaluación.
- **Instrumentar la ingesta.** Solo está trazada la consulta; subir un documento
  —extracción, fragmentación, *embeddings*, indexado— no deja traza.
- **Puntuaciones automáticas.** Langfuse admite asociar evaluaciones a cada
  traza; hoy no se envía ninguna. Es el punto de unión natural con RAGAS.

**Lo que no cubre:** la instrumentación registra lo que ocurrió, no si estuvo
bien. Una consulta compuesta que recupera la mitad de la evidencia deja una
traza de aspecto impecable, con sus cinco fragmentos sobre el umbral (ver
`NUCLEO_RAG.md` §3). Detectar eso necesita evaluación, no observabilidad.
