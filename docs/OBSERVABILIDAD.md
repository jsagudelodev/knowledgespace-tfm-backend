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
| `OpenAI-embedding` | modelo, tokens, coste — capturada automáticamente por el cliente envuelto |
| `recuperacion` | *namespace*, `top_k`, y **cada fragmento con su documento, su puntuación y si supera el umbral** |
| `OpenAI-generation` | modelo, temperatura, tokens de entrada y salida, coste |
| traza raíz | `company_id`, `assistant_id`, *namespace*, cuántos se recuperaron y cuántos superaron el umbral |

**Lo que da valor a la traza es el umbral.** Que una llamada a OpenAI costó
tanto lo sabe cualquier herramienta; que tres de cinco fragmentos no llegaron a
`0.30` solo lo sabe este sistema, y es lo que explica por qué la respuesta salió
como salió.

> **Ya no hay un `embedding_consulta` como paso manual.** Envolvía la misma
> llamada que `OpenAI-embedding` ya captura sola, porque el cliente de OpenAI
> queda instrumentado por Langfuse desde que se construye (ver más abajo, "Por
> qué un *span* manual puede sobrar"). Lo mismo ocurría con un paso
> `descomposicion` en las configuraciones que descomponen la consulta. Una
> consulta simple pasó así de siete observaciones a cinco; una compuesta, de
> once a siete. *2026-10-17.*

### Por qué un *span* manual puede sobrar

Langfuse 4 no envuelve una instancia: al importarse `langfuse.openai`,
**parchea la clase `openai.OpenAI` para todo el proceso**. A partir de ese
momento, cualquier cliente creado con esa clase —esté o no construido a través
de `observabilidad.cliente_openai()`— queda instrumentado, y cada llamada real
aparece sola en Langfuse como `OpenAI-generation` u `OpenAI-embedding`, con su
modelo, sus tokens y su coste.

Un *span* manual alrededor de esa misma llamada —`with observabilidad.paso(...)`
envolviendo `self.client.chat.completions.create(...)`— no añade una segunda
fuente de información: describe el mismo evento, una fila más. Y Langfuse Cloud
factura por volumen de observaciones ingeridas, de modo que la duplicación se
pagaba dos veces por nada, justo mientras se hacían pruebas manuales del chat y
la cuota se consumía más rápido de lo esperado.

Se retiraron los dos *spans* que envolvían una llamada al proveedor sin aportar
nada que la captura automática no tuviera ya —`embedding_consulta` en
`rag_service.py` y `descomposicion` en las dos clases que descomponen—. **No**
se tocaron `recuperacion` ni `reparto`: Pinecone no se auto-instrumenta, así que
son el único sitio donde queda visible qué recuperó el índice, con qué
puntuación y si superó el umbral. Quitarlos habría debilitado justo lo que esta
sección defiende como aportación.

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

## Verificación cruzada: Langfuse frente a `cost_tracking`

Langfuse y `cost_tracking` calculan el coste de la misma consulta por caminos
completamente independientes. No comparten tabla de precios ni código: Langfuse
usa la suya, interna del SDK; `cost_tracking_service.py` usa la propia,
declarada en `PRICING`. Lo único que ambos leen es el mismo dato real que
devuelve la API de OpenAI —los `tokens` de cada respuesta—.

Comprobado sobre una consulta real, *«qué es rag?»*, con la configuración
`descomposicion_acotada` (2026-10-17):

| Operación | Langfuse | `cost_tracking` | Coincide |
|---|---|---|---|
| Generación (respuesta) | $0,000189 | 0,000189 USD | ✅ |
| *Embedding* de la pregunta | $0,00 | 0,000000 USD | ✅ |
| Descomposición | $0,000023 | 0,000023 USD | ✅ |
| **Total** | **$0,000212** | **0,000212 USD** | ✅ |

Coinciden al último decimal en las tres operaciones. No es una coincidencia
superficial: dos sistemas que no se comunican entre sí llegando al mismo
número es la prueba de que `cost_tracking` no estima ni aproxima, calcula sobre
el consumo real que el proveedor confirmó.

**El único matiz a declarar.** Langfuse redondea a dos decimales en su
interfaz, de modo que un coste de `0,00000008` USD —cuatro tokens de
*embedding*— se muestra como `$0,00`. No es una discrepancia: es que
`cost_tracking`, con seis decimales, conserva una magnitud que la pantalla de
Langfuse no tiene espacio para mostrar.

**Cómo reproducirlo.** Localizar la traza en Langfuse por su marca de tiempo,
convertirla a UTC —la base de datos almacena en UTC y Langfuse muestra la hora
local del navegador—, y consultar `cost_tracking` en esa ventana:

```sql
SELECT created_at, operation, model, input_tokens, output_tokens, total_cost
FROM cost_tracking
WHERE created_at BETWEEN '<inicio UTC>' AND '<fin UTC>'
ORDER BY created_at;
```

Las tres filas —`chat`, `embedding`, `descomposicion`— deben sumar el mismo
total que las tres observaciones de pago en Langfuse para esa traza.

### Por qué un experimento no deja rastro en `cost_tracking`

Esta verificación solo funciona para una consulta que pasó por el chat. Al
ejecutar `langfuse_dataset.py` contra las dieciocho preguntas del conjunto de
referencia (2026-10-18), las dos corridas quedaron registradas en Langfuse
—dos *experiments*, dieciocho ítems cada uno, con sus observaciones
`OpenAI-generation`— pero **ninguna fila apareció en `cost_tracking`** para esa
ventana horaria, comprobado por consulta directa a la base de datos.

La razón no es un fallo: `CostTrackingService().record(...)` se invoca
únicamente desde `app/routers/v1/chat.py`, el enrutador HTTP. Un experimento
llama a `RAGService.generate_response` directamente, sin pasar por ahí, de
modo que nunca llega al punto donde se escribe el registro.

**Se decidió dejarlo así, de forma deliberada.** `cost_tracking` existe para
medir el **gasto real atribuible a una organización** —es la tabla que
sostiene el requisito RNF-4—, y las ejecuciones de evaluación del propio
trabajo no son consumo de un cliente: mezclarlas habría contaminado esa cifra
con actividad que no es uso del producto. El coste de los experimentos sigue
siendo observable por otras dos vías, suficientes para el propósito de medir
y documentar: el propio Langfuse, consulta por consulta, y los campos
`tokens_entrada` / `tokens_salida` que cada script de `experimentos/` guarda
en su JSON de resultados.

**Limitación de la API pública, no solo de este caso.** Confirmar el coste de
las dieciocho preguntas sin abrir la interfaz resultó imposible: el endpoint
`GET /api/public/v2/observations` devuelve, para las observaciones de tipo
`GENERATION`, los campos de coste y de modelo vacíos —`cost_details`,
`total_cost`, `model` llegan a `None` incluso cuando la observación existe y
tiene su latencia—. No hay además una operación para pedir una observación
suelta por su identificador; solo existe el listado por lotes. Es la misma
limitación de las organizaciones creadas después del 16 de septiembre de 2026
que ya se documentó más arriba: **para ver el detalle de coste de una
observación hay que entrar en la interfaz**, la API solo sirve para listar qué
existe.

---

## Estado y limitaciones

**Funcionando:** instrumentación completa, credenciales válidas, trazas llegando
con sus cinco observaciones, sesión y latencia registradas.

**Lo que falta:**

- **Ejecutar un dataset contra el RAG desde Langfuse**, que es la segunda mitad
  de lo que pidió el tutor. Requiere el conjunto de evaluación.
- **Instrumentar la ingesta por completo.** El *embedding* de los fragmentos al
  subir un documento ya queda trazado —`EmbeddingService` pide el cliente a
  `observabilidad.cliente_openai()` desde el 2026-10-17, por el mismo motivo que
  se explica más arriba—, pero la extracción, la fragmentación y el indexado en
  Pinecone no tienen ningún paso instrumentado. Solo se ve una parte del
  proceso, no su totalidad.

  **Por qué se corrigió el embedding y no de paso todo lo demás.** El problema
  no era solo que faltara instrumentar: era que el embedding de la ingesta
  dependía de un efecto secundario frágil. `EmbeddingService` creaba su cliente
  con `from openai import OpenAI` directo, y quedaba trazado solo porque el
  chat siempre instancia `RAGService` primero —lo que dispara el parche de
  Langfuse sobre la clase `OpenAI` antes de que `EmbeddingService` construya el
  suyo—. Verificado en un proceso limpio que reproducía el flujo real de
  `documents.py`: si subir un documento era el primer evento de un *worker*,
  antes de cualquier consulta de chat, esa llamada quedaba invisible. Corregido
  pidiendo el cliente en el mismo sitio que `RAGService`, con dos tests que
  comprueban la regresión.
- **Puntuaciones automáticas.** Langfuse admite asociar evaluaciones a cada
  traza; hoy no se envía ninguna. Es el punto de unión natural con RAGAS.

**Lo que no cubre:** la instrumentación registra lo que ocurrió, no si estuvo
bien. Una consulta compuesta que recupera la mitad de la evidencia deja una
traza de aspecto impecable, con sus cinco fragmentos sobre el umbral (ver
`NUCLEO_RAG.md` §3). Detectar eso necesita evaluación, no observabilidad.
