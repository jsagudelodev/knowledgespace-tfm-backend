# Manejo de errores

Cómo trata KnowledgeSpace los errores, de la base de datos a la pantalla, en los
dos repositorios. Actualizado el 2026-11-04, tras revisar el código con el
criterio con el que se evalúa: cada afirmación de este documento se comprobó
contra el código y la cubre un test.

---

## 1. Tres principios

1. **El usuario recibe un mensaje que entiende; el detalle técnico va al log.**
   Ninguna respuesta incluye rutas, claves de S3, SQL ni el mensaje crudo de un
   SDK. La traza completa queda en el log del servidor, con el método y la
   ruta, para poder reconstruir el fallo.
2. **Se distingue quién falló.** Un error de la petición (4xx) no es lo mismo
   que la caída de un proveedor externo (503) ni que un defecto propio (500).
   El código de estado lo dice, y el frontend actúa en consecuencia.
3. **Lo secundario nunca rompe lo principal.** Si falla una notificación, el
   registro de un costo o una traza de Langfuse, la operación del usuario se
   completa igual y el fallo queda en el log.

---

## 2. Backend

### 2.1 Capas, de dentro afuera

| Capa | Qué ocurre | Código | Dónde |
|---|---|---|---|
| **Validación de entrada** | Pydantic rechaza la petición antes de llegar al endpoint: tipos, longitudes, textos vacíos (`min_length=1`), correos | **422** | `app/schemas/` |
| **Autenticación y permisos** | Token ausente o caducado; rol insuficiente (permisos por rol del 2026-11-02) | **401** / **403** | `routers/v1/security.py` |
| **Errores de negocio** | Recurso inexistente o de otra empresa, duplicados, estados no permitidos | **404**, **409**, **400** | cada router, con `HTTPException` |
| **Servicios externos** | OpenAI, Pinecone o S3 no responden | **503** | excepciones propias + manejador global |
| **Reindexado en Preguntas sin respuesta** | El índice rechaza el alias o la respuesta escrita | **502** | `routers/v1/knowledge_gaps.py` |
| **Cualquier otro fallo** | Un defecto propio, la base de datos caída… | **500** | manejador global |

Uso actual en los routers: 30 respuestas 404, 11 de 409, 6 de 403, 4 de 400, 2
de 401, 3 de 502 y 1 de 503 explícitas, más las que generan Pydantic (422) y el
manejador global (503 y 500).

**El aislamiento entre empresas también se expresa como 404, no como 403:** un
recurso de otra empresa se responde como inexistente, para no revelar que
existe.

### 2.2 Excepciones propias de los servicios externos

`app/core/exceptions.py`. Cada servicio de infraestructura lanza la suya en vez
de una `Exception` genérica, para que quien la capture atienda solo el fallo
esperado y no enmascare un defecto propio —un `TypeError`, por ejemplo— como si
fuera una caída del proveedor.

| Excepción | Servicio | Se lanza al… |
|---|---|---|
| `EmbeddingError` | OpenAI (embeddings) | convertir un texto en vector |
| `VectorStoreError` | Pinecone | insertar, buscar, listar o borrar vectores |
| `StorageError` | AWS S3 | descargar, borrar o firmar una URL temporal |
| `DocumentExtractionError` | PDF / DOCX / TXT | extraer el texto de un documento |
| `RAGUnavailableError` | pipeline del chat | fallar el embedding de la consulta, la búsqueda o la generación; lleva `etapa` |

### 2.3 El manejador global

`app/core/error_handlers.py`, registrado en `main.py`. Atiende lo que ningún
endpoint captura:

- `EmbeddingError`, `VectorStoreError`, `StorageError` → **503**:
  *«Un servicio externo no está disponible en este momento. Intenta de nuevo en
  unos segundos.»*
- cualquier otra excepción → **500**: *«Error interno del servidor.»*

Siempre en JSON con la forma de `HTTPException` (`{"detail": ...}`), la que ya
lee el frontend. `HTTPException` y la validación (422) siguen con los
manejadores propios de FastAPI.

**Antes del 2026-11-04** no había ninguno: un fallo no previsto llegaba como un
500 en **texto plano**, y cuatro respuestas de `documents.py` (subir, borrar y
descargar de S3; listar fragmentos de Pinecone) devolvían `str(e)` al cliente,
con la clave del archivo o el error del SDK. Esas cuatro ya no capturan: dejan
que el error llegue al manejador global.

### 2.4 El chat

- `RAGUnavailableError` → **503** con la etapa que falló: *«El asistente no
  está disponible en este momento (falló la etapa: búsqueda vectorial). Vuelve a
  intentarlo en unos segundos.»*
- **En streaming**, si el fallo ocurre cuando ya se enviaron trozos de la
  respuesta, el código HTTP ya no se puede cambiar: el error se comunica como un
  evento más (`{"type": "error", "etapa": ...}`) y el frontend lo muestra.
- Las tres capturas registran la traza con `exc_info=True`.

### 2.5 Procesos en segundo plano

La ingesta de un documento (extraer, trocear, generar embeddings, indexar)
corre después de responder a la subida. Si falla, el documento pasa a
**`failed`**, se guarda el error original en `error_message`, se avisa al
autor con una notificación *«no se pudo procesar. Puedes reintentarlo desde
Documentos»* y se registra la traza. El documento se puede **reintentar** desde
el listado.

**Lo que ve el usuario no es el error original.** La API lo traduce al
responder (`app/schemas/mensajes_documento.py`) a un mensaje que dice qué pasó
y qué hacer; el original se queda en la base de datos y en el log para
diagnosticar. Se traduce al responder, no al guardar, para que valga también
con los documentos que fallaron antes del cambio.

| Error original (prefijo) | Lo que ve el usuario |
|---|---|
| *No se pudo extraer texto…* | No se pudo leer el texto del archivo. Si es un PDF escaneado, no tiene texto seleccionable: prueba con una versión que sí lo tenga. |
| *Tipo de archivo … no soportado* | Este tipo de archivo no se admite. Formatos válidos: PDF, DOCX, TXT y MD. |
| *…S3…* | No se encontró el archivo almacenado. Vuelve a subir el documento. |
| *Error generando embedding…* | El servicio de IA no respondió al procesar el documento. Reinténtalo en unos minutos. |
| *…Pinecone…* | No se pudo guardar el documento en el índice de búsqueda. Reinténtalo en unos minutos. |
| cualquier otro | No se pudo procesar el documento. Reinténtalo; si vuelve a fallar, comprueba que el archivo se abre bien. |

### 2.6 Efectos secundarios: nunca rompen la operación

| Efecto | Si falla… |
|---|---|
| Notificación de documento | la operación sigue; aviso en el log |
| Registro de costo (`cost_tracking`) | la respuesta del chat llega igual; `rollback` y aviso en el log |
| Traza de Langfuse | el chat responde igual; aviso en el log |
| Borrado de vectores al eliminar un documento | el documento se borra igual; aviso en el log con su id (antes era un `pass` sin rastro) |
| Verificación automática al resolver una pregunta | la pregunta queda resuelta «sin verificar» y admite reintento manual |

---

## 3. Frontend

### 3.1 El interceptor global

`src/app/core/interceptors/error.interceptor.ts`, sobre cada respuesta HTTP:

| Error | Qué hace |
|---|---|
| **401** (salvo en el login) | cierra la sesión, avisa *«Tu sesión expiró»* y lleva al login |
| **403** | avisa *«No tienes permiso para realizar esta acción»* |
| **0** (sin red) o **≥ 500** | avisa *«Error del servidor. Intenta de nuevo en unos segundos»* |
| 4xx de negocio (400, 404, 409, 422) | nada: lo decide el componente, que sabe qué estaba haciendo |

Siempre **relanza el error**, para que el componente también reaccione.

### 3.2 Sin avisos dobles

`avisadoPorElInterceptor(err)` dice si el interceptor ya avisó (0, 401, 403,
≥ 500). Los componentes lo usan para dar su mensaje propio solo en el resto.
Lo usan las acciones del usuario que hasta el 2026-11-04 fallaban en silencio
ante un 4xx:

| Acción | Mensaje |
|---|---|
| Calificar una respuesta (pulgar) | *No se pudo guardar la calificación.* |
| Descargar un documento desde las fuentes del chat | *No se pudo descargar el documento.* |
| Borrar una notificación (papelera) | *No se pudo eliminar la notificación.* |
| Eliminar varias notificaciones | *No se pudieron eliminar las notificaciones.* |
| Marcar como leídas (en bloque o desde la campana) | *No se pudieron marcar como leídas.* |

Otras pantallas ya tenían mensajes propios por caso. El chat, por ejemplo,
distingue *«Sin conexión»*, *«Esta conversación ya no existe»* (404), *«No
tienes acceso»* (403) y *«El servidor no responde»* (5xx).

### 3.3 Errores que se ignoran a propósito

Doce llamadas ignoran su error (`error: () => {}`), y cada una lleva el motivo
comentado en el código. Son de dos tipos:

- **Cargas secundarias**: categorías y asistentes para un filtro, contadores,
  la empresa tras el login. Si fallan, la pantalla sigue funcionando con menos
  datos, y si fue la red o el servidor el interceptor ya avisó.
- **Actualizaciones optimistas**: marcar como leída al abrir una notificación.
  Se refleja en pantalla al momento; si el servidor falla, avisa el
  interceptor y al recargar vuelve a salir como no leída.

---

## 4. Un recorrido completo: S3 caído al descargar

1. El usuario pulsa *descargar* en las fuentes del chat.
2. `S3Service.generar_url_temporal` falla y lanza `StorageError("Error
   generando URL temporal: ...NoSuchKey...")`.
3. El endpoint no lo captura. El manejador global registra en el log
   `[Error] StorageError en GET /api/v1/documents/45/download: ...`, con la
   traza, y responde **503** con el mensaje genérico.
4. El interceptor del frontend ve un ≥ 500 y avisa *«Error del servidor…»*.
5. El componente comprueba `avisadoPorElInterceptor` → `true`, y no repite el
   aviso. El usuario ve **un** mensaje y la clave de S3 no sale del servidor.

---

## 5. Tests

| Test | Qué garantiza |
|---|---|
| `api/tests/test_manejo_de_errores.py` (10) | 503 si falla un proveedor, 500 si no, siempre JSON; la respuesta no filtra el detalle técnico; el error queda en el log con la ruta; las `HTTPException` no cambian; la app real registra los manejadores; **ningún router devuelve `str(e)` en el `detail`** (comprobado contra el código anterior: falla) |
| `api/tests/test_mensaje_documento_fallido.py` (10) | cada tipo de fallo de la ingesta tiene su mensaje legible; la respuesta de la API no lleva el error técnico; el original no se toca |
| `api/tests/test_feedback_router_convert_gap.py` | convertir en pregunta sin respuesta no depende de las notificaciones |
| `api/tests/test_permisos_por_rol.py` | que las rutas de gestión exigen rol admin, y las de aportar y leer siguen abiertas |
| `src/app/core/interceptors/error.interceptor.spec.ts` (6) | 401 fuera y dentro del login, 403, sin red, 500, y que un 404 de negocio no dispara aviso global |
| `src/app/core/interceptors/avisos-de-error.spec.ts` (6) | qué errores cubre el interceptor; las acciones del usuario avisan ante un 4xx y no avisan dos veces ante un 5xx |

---

## 6. Limitaciones conocidas

- **El 500 del manejador global sale sin cabeceras CORS.** En Starlette, el
  manejador de `Exception` corre fuera del middleware de CORS, así que el
  navegador ve un error de red (estado 0) en vez del 500. Para el usuario el
  efecto es el mismo —el interceptor trata 0 y 5xx igual—, pero el cuerpo JSON
  no llega al navegador. Los 503 de proveedores sí pasan por CORS.
- **Sin reintentos automáticos** ante caídas de un proveedor: el mensaje invita
  a reintentar a mano.
- **Sin identificador de petición** que una el error que ve el usuario con su
  línea del log, y sin alertas: el log es el de Cloud Run.
- **Sin integración continua**: los tests se ejecutan a mano antes de cada push
  (ver `ALCANCE_TFM.md`).
