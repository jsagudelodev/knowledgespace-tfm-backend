# Núcleo RAG — auditoría y plan

Qué está implementado, qué está implementado pero sin medir, y qué falta.
Auditado contra el código el **9 de octubre de 2026**, tras la primera tutoría
(ver [`TUTORIAS.md`](TUTORIAS.md)).

> **El criterio de este documento.** El tutor no preguntó si el sistema
> funciona: preguntó cómo está construido y cómo se demuestra que funciona
> bien. Por eso aquí no basta con ✅ *implementado*. Una pieza solo cuenta como
> terminada si está **implementada, medida y documentada**.

**Leyenda**

| | Significado |
|---|---|
| ✅ | Implementado, medido y documentado |
| 🟡 | Implementado, pero sin medir o sin documentar |
| ❌ | No existe |

---

## 0. Estado del índice vectorial — **resuelto el 2026-10-09**

Auditado el 9 de octubre de 2026 contra el índice real (`trainiq`, Pinecone
serverless). El índice no se correspondía ni con lo que la base de datos decía
ni con lo que el código hacía, de modo que **ninguna medición habría sido
válida**. Saneado el mismo día; el diagnóstico se conserva porque es material
del capítulo 7.

### Estado final

| | Antes | Después |
|---|---|---|
| Namespaces | 4 | **1** (`company-8-assistant-1`) |
| Vectores en el índice | 297 | **87** |
| Vectores huérfanos | 179 | **0** |
| Documentos | 13 (4 invisibles + 1 duplicado) | **8, todos alcanzables** |
| Fragmentación | 82 % por caracteres | **100 % por oraciones** |
| Base de datos ↔ Pinecone | 150 vs 118 | **87 = 87** |

**Verificación funcional**, con recuperación directa sobre el índice saneado:

| Consulta | Resultado |
|---|---|
| *"¿qué es geometría semántica?"* | 5 de 5 fragmentos superan el umbral, de **dos documentos distintos** (0,574 – 0,456) |
| *"¿cuál es la capital de Francia?"* | **0 de 5** superan el umbral (máximo 0,139) |

La segunda fila es la primera comprobación empírica del control de
alucinaciones: sin fragmentos por encima del umbral, el modelo no recibe
contexto y responde que no encontró información.

**Lo que se perdió, y por qué:** cuatro documentos de EBIS y uno de VCD tenían el
archivo original ausente en S3, de modo que no eran reindexables. Se eliminaron
junto con sus vectores huérfanos. Dos de ellos (`Resumen Clase 2 - Tema 1.pdf` y
`Resumen de Clase 3 - Tema 1.pdf`) se conservan en `docs/Test-Documentos/` y
pueden volver a subirse.

### 0.1 Cuatro documentos eran invisibles para el asistente

El índice contenía tres generaciones de nomenclatura conviviendo:

| Namespace | Vectores | Formato de id | Estado |
|---|---|---|---|
| `__default__` | 142 | `7_chunk_0` | Documentos ya borrados de la base (ids 7, 8, 11…) |
| `knowledgespace-demo--ebis` | 32 | `knowledgespace-demo--ebis_31_chunk_7` | **4 documentos vivos, inalcanzables** |
| `knowledgespace-demo--vcd` | 5 | — | Residuo del mismo esquema antiguo |
| `company-8-assistant-1` | 118 | `doc-36-chunk-0` | El único que consulta el sistema |

`RAGService` busca exclusivamente en el namespace que construye
`PineconeService.construir_namespace`, es decir `company-8-assistant-1`. Los 32
vectores del esquema antiguo corresponden a cuatro documentos que la interfaz
muestra como `completed`:

```
Resumen Clase 1 - Tema 1.pdf         6 fragmentos
Resumen Clase 2 - Tema 1.pdf         7
Resumen de Clase 3 - Tema 1.pdf      9
Resumen de Clase 2 - Tema 2.pdf     10
```

**Consecuencia: el asistente EBIS no puede responder nada sobre el Tema 1.** Se
confirma en la prueba del 8 de octubre: a la pregunta *"dame un resumen de la
documentación disponible"* las cinco fuentes fueron de Tema 3 y Tema 4,
ninguna de Tema 1.

Es además un fallo de corrección visible para el usuario: la interfaz afirma que
el documento está procesado y es buscable, y no lo es.

### 0.2 El 82 % del índice usaba la fragmentación antigua

| Fragmentación | Fragmentos |
|---|---|
| Por caracteres (anterior al 2026-10-03) | **123** |
| Por oraciones (actual) | 27 |

Once de los trece documentos se indexaron entre junio y agosto, antes del cambio
a división por oraciones. **La memoria afirma que el sistema fragmenta por
oraciones: es cierto del código y falso del 82 % de lo indexado.**

Hay evidencia de que la distribución de similitudes se movió: en una consulta
real del 8 de octubre el quinto fragmento puntuó **0,37**, por debajo del
`0,389` que la medición original del umbral fijó como mínimo legítimo.

### 0.3 Un documento duplicado — eliminado

`Diapositivas Tema 6 - Sesión 1.pdf` está subido dos veces, con el mismo tamaño
de archivo: `id=42` (agosto, 23 fragmentos, por caracteres) e `id=44` (9 de
octubre, 21 fragmentos, por oraciones). **44 fragmentos del mismo contenido
compitiendo entre sí**, lo que reduce la diversidad de las cinco fuentes
recuperadas y distorsionaría cualquier medición de precisión del contexto.

### 0.3b La causa raíz: tres migraciones simultáneas

Al intentar reindexar los cuatro documentos huérfanos, los cuatro fallaron con
`NoSuchKey` de S3. Sus rutas seguían un esquema anterior:

```
id=28  (junio)   uploads\8_Resumen Clase 1 - Tema 1.pdf        archivo ausente
id=36  (agosto)  company-8/71724cb604b44144bc634c40ca335be3.pdf  correcto
```

Entre junio y agosto cambiaron **tres esquemas a la vez**, y los documentos
anteriores no se migraron en ninguno de los tres:

| | Antes | Después |
|---|---|---|
| Ruta en S3 | `uploads\{company}_{nombre}.pdf` | `company-{id}/{uuid}.pdf` |
| Namespace de Pinecone | `knowledgespace-demo--{asistente}` | `company-{id}-assistant-{id}` |
| Identificador de vector | `{namespace}_{doc}_chunk_{i}` | `doc-{id}-chunk-{i}` |

Obsérvese además que la ruta antigua usaba la barra invertida de Windows como
separador de clave de S3, donde la convención es la barra normal.

**El sistema siguió funcionando con normalidad durante cuatro meses.** La
interfaz mostraba los documentos como `completed`, el chat respondía sin error, y
simplemente nunca recuperaba nada de ellos. El fallo solo se hizo visible al
auditar el índice contra la base de datos.

El asistente VCD estaba en la misma situación: su único documento, invisible.

### 0.4 Reprocesar no era idempotente — corregido

Los identificadores de vector son `doc-{id}-chunk-{i}`, es decir, dependen de la
**posición** del fragmento. `_procesar_documento_background` subía los vectores
nuevos sin borrar los anteriores: un `upsert` sobrescribe las posiciones que
vuelve a generar y deja vivas las sobrantes. Como la división por oraciones
produce un 12,5 % menos de fragmentos, cada reindexado dejaba huérfanas las
posiciones finales, con el texto de la versión anterior.

**Corregido el 9 de octubre:** se llama a `eliminar_por_documento` —que borra por
filtro de metadatos, no por lista de identificadores— antes del `upsert`, y
después de generar los *embeddings*, para que un fallo en la extracción o en la
llamada a OpenAI deje el índice como estaba.

### Lo que esto aporta a la memoria

No es solo una tarea de mantenimiento. Es un hallazgo con nombre propio para el
capítulo 7: **el índice vectorial se desincroniza del código y nada lo detecta.**
Ocurrió dos veces por motivos distintos —un cambio de esquema de nombres y un
cambio de estrategia de fragmentación— y en ambos casos el sistema siguió
respondiendo con normalidad, sin error visible. Es un problema real de los
sistemas RAG en producción, documentado aquí con cifras propias.

---

## 1. Arquitectura y recuperación

| Pieza | Estado | Evidencia |
|---|---|---|
| Recuperación densa, similitud coseno, `top_k=5` | 🟡 | `pinecone_service.py` (`metric="cosine"`), `rag_service.py:76` |
| Umbral de relevancia `0.30` | ✅ | `rag_service.py`, `resultados/umbral_2026-10-09.json` |
| Fragmentación por oraciones, sin solapamiento | ✅ | `pdf_service.py`, `resultados/chunking_2026-10-07.json` |
| Conversación multiturno (20 mensajes) | ✅ | `chat.py:61`; límite de preguntas compuestas medido en `resultados/preguntas_compuestas_2026-10-09.json` |
| Metadatos para citar fuentes | 🟡 | `documents.py:134` |
| Aislamiento multi-tenant por *namespace* | 🟡 | `pinecone_service.py`, `tests/test_pinecone_namespace.py` |
| Reescritura o expansión de consulta | ❌ | La pregunta se vectoriza tal cual |
| Reranking | ❌ | Evaluado y descartado, sin medición que lo respalde |
| RAG híbrido (denso + BM25) | ❌ | — |

**El umbral, revalidado el 2026-10-09.** Estaba medido sobre un índice
fragmentado por caracteres, de junio, lo que creaba una incoherencia: los
capítulos 3 y 4 afirmaban que el valor estaba justificado por medición mientras
el capítulo 5 defendía otra estrategia de fragmentación. Repetida la medición
sobre el índice actual, el `0.30` sigue dentro de la banda vacía, aunque esta se
estrechó de 0.160 a 0.135 y el margen frente al ruido cayó de 0.071 a 0.042.

Ese estrechamiento **es en sí mismo un resultado**: demuestra que el umbral
depende de la configuración de fragmentación y no es una constante del dominio.
Comparativa completa en `RAG_PIPELINE.md` §6.

---

## 2. Evaluación

| Pieza | Estado |
|---|---|
| Calidad estructural de la fragmentación | ✅ Medida el 2026-10-07, reproducida idéntica el 2026-10-09 |
| Coste por consulta | ✅ Medido el 2026-10-08, registros 71-80 |
| Dataset de evaluación | ❌ |
| Langfuse | ✅ Instrumentado el 2026-10-09 |
| RAGAS | ❌ |
| Métricas de recuperación (`hit@k`, MRR) | ❌ |
| Latencia p50 / p95 | ❌ |
| Umbral de relevancia | ✅ Revalidado el 2026-10-09 |
| Degradación en preguntas compuestas | ✅ Medida el 2026-10-09 |

**Este es el bloque que decide la nota, y es el más vacío.** Dos mediciones
hechas, cinco por hacer.

---

## 3. Control de alucinaciones

Hay **tres mecanismos implementados y ninguno medido**. Es exactamente lo que el
tutor señaló.

| Mecanismo | Implementado | Medido | Con test |
|---|---|---|---|
| Umbral de relevancia descarta contexto pobre | Sí | **No** | **No** |
| *Prompt* obliga a responder solo con el contexto | Sí | **No** | **No** |
| Registro de *knowledge gaps* | Sí | **No** | — |

El *prompt* exige responder literalmente *"No encontré información sobre este
tema en los documentos de la empresa"* cuando el contexto no basta
(`rag_service.py:24`). **Nunca se ha verificado que lo haga.**

### Una alucinación real, detectada el 8 de octubre

A la pregunta *"dame un resumen de la documentación disponible"*, el sistema
respondió *"la documentación disponible se compone de varios resúmenes de
clases…"* habiendo visto **únicamente cinco fragmentos**.

No inventó contenido: **sobredeclaró su cobertura**. Es una alucinación de
alcance, es real, es del propio corpus, y es justo el tipo de fallo que RAGAS
mide con la métrica de *faithfulness*. Debe entrar en el capítulo 5 como caso
analizado.

---

### Un segundo modo: cobertura parcial en preguntas compuestas

Medido el 9 de octubre sobre seis parejas de preguntas. El pipeline vectoriza el
**mensaje entero**, de modo que una pregunta doble produce un vector que no
representa bien a ninguno de los dos temas.

| | |
|---|---|
| Cobertura conjunta media | **48 %** (mínimo 40 %, máximo 60 %) |
| Fragmentos sobre el umbral en las compuestas | **30 de 30** |
| Parejas donde la compuesta puntúa más que alguna separada | **6 de 6** |

Lo peligroso no es la pérdida de evidencia, sino que **nada la señala**. El
umbral mide parecido, no cobertura: los cinco fragmentos lo superan siempre. Y
la puntuación llega a subir, porque un texto más largo genera un *embedding* más
rico que se acerca más a los fragmentos. El usuario recibe una respuesta de
aspecto confiado construida sobre la mitad de la evidencia.

Es un modo de alucinación distinto al que protege el umbral, y ninguno de los
tres mecanismos actuales lo cubre.

**Hipótesis no confirmada:** se esperaba que las parejas de temas alejados se
degradaran más que las de temas vecinos. La dirección es ligeramente esa (45 %
frente a 55 %), pero con n=4 y n=2 el dato no sostiene la conclusión. Se deja
constancia porque condicionaba el diseño del experimento.

---

## 4. Observabilidad

| Pieza | Estado |
|---|---|
| Seguimiento de coste por solicitud | ✅ |
| Trazas del pipeline RAG | ✅ Cinco observaciones por consulta |
| Langfuse | ✅ Instrumentado, dependencia opcional |

**Dato de la auditoría:** `rag_service.py`, `chat.py` y `pinecone_service.py`
tienen **0 llamadas a `logger`**. En toda la aplicación hay 5.

Esto significa que, cuando una respuesta sale mal, no hay forma de saber qué se
recuperó, con qué puntuaciones ni qué contexto recibió el modelo. Es la razón
de fondo por la que el tutor preguntó por Langfuse.

---

## 5. Pruebas

21 tests en verde, repartidos en 5 archivos. Pero:

| Qué cubren | |
|---|---|
| Formato del contexto construido | 4 tests |
| Cálculo de costes | 5 tests |
| Métricas del panel | 4 tests |
| Períodos de *knowledge gaps* | 4 tests |
| Construcción de *namespaces* | 4 tests |
| **Umbral de relevancia** | **0** |
| **Abstención ("no encontré información")** | **0** |
| **Recuperación de extremo a extremo** | **0** |

La aportación central del trabajo no tiene ni una prueba que la respalde.

---

# Plan

El orden importa: **dataset → medición → mejoras**. Sin línea base, reranking e
híbrido solo se pueden afirmar, no demostrar — y afirmar sin medir es
precisamente lo que hay que dejar de hacer en este proyecto.

## Bloque A0 — Sanear el índice ✅ *completado el 2026-10-09*

Coste total estimado: **menos de un céntimo** en *embeddings*.

- [x] **A0.1. Reproceso idempotente.** Borrado previo en
      `_procesar_documento_background`. *Hecho el 2026-10-09.*
- [x] **A0.2. Los 4 documentos huérfanos** resultaron irreindexables (archivo
      ausente en S3) y se eliminaron junto con el de VCD. *2026-10-09.*
- [x] **A0.3. Duplicado `id=42` de Tema 6 eliminado.** *2026-10-09.*
- [x] **A0.4. Reindexados** los 6 que seguían fragmentados por caracteres:
      95 → 87 fragmentos. *2026-10-09.*
- [x] **A0.5. Namespaces muertos eliminados**: 179 vectores. *2026-10-09.*
- [x] **A0.6. Verificado**: 87 vectores en Pinecone = 87 de `chunk_count`, y
      recuperación comprobada con consulta cubierta y consulta ajena.
      *2026-10-09.*

## Bloque A — Instrumentar y medir *(prioridad máxima)*

- [ ] **A1. Dataset de evaluación.** 15-20 preguntas con respuesta de
      referencia, frase ancla y tipo. Repartidas según la taxonomía de
      `TUTORIAS.md`, **incluyendo preguntas sin respuesta en el corpus y al
      menos una compuesta**.
- [x] **A2. Langfuse instrumentado.** Cada consulta genera una traza con cinco
      observaciones; el paso de recuperación guarda cada fragmento con su
      puntuación y si supera el umbral, y las consultas sin contexto se
      etiquetan aparte. Dependencia opcional: con `LANGFUSE_ENABLED=false` el
      sistema funciona igual. Ver `OBSERVABILIDAD.md`. *2026-10-09.*
- [ ] **A3. Dataset cargado en Langfuse** y apuntado contra el RAG.
- [ ] **A4. RAGAS — línea base.** *Faithfulness*, *answer relevancy*, *context
      precision* y *context recall* sobre la configuración actual.
- [ ] **A5. Latencia p50/p95**, que sale gratis de las trazas de A2.

## Bloque B — Cerrar los huecos del núcleo

- [x] **B1. Umbral revalidado** sobre el índice por oraciones. Sigue dentro de
      la banda, pero esta se estrechó un 16 % (0.160 → 0.135) y el margen sobre
      el ruido cayó un 41 % (0.071 → 0.042). Automatizado en
      `experimentos/medir_umbral.py`; resultados en `umbral_2026-10-09.json`.
      `RAG_PIPELINE.md` §6 y el comentario de `rag_service.py` actualizados.
      *2026-10-09.*
- [x] **B2. Tests del umbral y de la abstención.** 14 tests nuevos en
      `tests/test_rag_service_umbral.py` (de 21 a 35 en total). Verificado que
      detectan un cambio del umbral: bajándolo a 0.10, fallan 3. *2026-10-09.*
- [x] **B3. Preguntas compuestas medidas.** 6 parejas: la compuesta recupera
      de media el **48 %** de la evidencia (mínimo 40 %, máximo 60 %), y el
      umbral no lo detecta en **30/30** fragmentos. En 6 de 6 la compuesta
      puntúa más alto que alguna de las separadas.
      `experimentos/medir_preguntas_compuestas.py`. *2026-10-09.*
- [ ] **B4. Llevar a la memoria** los dos modos de alucinación documentados
      aquí (alcance sobredeclarado y cobertura parcial en preguntas compuestas)
      como casos analizados del capítulo 5.

## Bloque C — Mejoras, cada una medida contra la línea base

- [ ] **C1. Reranking**, medido contra A4 sobre el mismo dataset.
- [ ] **C2. RAG híbrido** (denso + BM25), o decisión documentada de dejarlo como
      trabajo futuro con el argumento de cuándo haría falta: siglas, códigos,
      nombres propios, referencias normativas.

## El entregable del bloque C

Una tabla con una fila por configuración. **Esa tabla es el capítulo 5.**

| Configuración | Faithfulness | Context precision | Answer relevancy | Latencia p95 |
|---|---|---|---|---|
| Base | | | | |
| + reranking | | | | |
| + híbrido | | | | |

---

## Qué cambia en la próxima tutoría

Hoy, a las siete preguntas del tutor, el proyecto respondía *"implementado, sin
medir"* en casi todas. Cerrados los bloques A y B, las respuestas pasan a ser:

| Pregunta | Respuesta después |
|---|---|
| ¿Control de alucinaciones? | "Tres mecanismos, medidos con RAGAS. *Faithfulness* de X sobre un dataset de 20 preguntas." |
| ¿Pruebas con Langfuse y dataset? | "Sí. Dataset de 20 preguntas apuntado contra el RAG, con trazas de cada recuperación." |
| ¿Qué tipos de preguntas admite? | "Estos tres, y estos cinco no. Lo tengo medido, incluidas las compuestas." |
| ¿Reranking? ¿Híbrido? | "Medido contra la línea base. Mejora X, cuesta Y." |

Esa es la diferencia entre un proyecto que funciona y un proyecto que se
defiende.
