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

## 6. Primera ejecución del dataset — 2026-10-11

Las 18 preguntas de `dataset_evaluacion.csv` lanzadas contra el pipeline de
producción (`experimentos/ejecutar_dataset.py`). Resultados en
`resultados/dataset_ejecutado_2026-10-11.json`.

### 6.1 Abstención — la métrica que pidió el tutor

| | |
|---|---|
| Preguntas sin respuesta en el corpus | 6 |
| Abstenciones correctas | **6** |
| Abstenciones indebidas (en preguntas con respuesta) | **0** |
| **Tasa de abstención correcta** | **100 %** |

Incluye las tres tangenciales —*reranker*, *temperatura de un LLM*, *LoRA*—,
donde el sistema recuperó fragmentos con puntuación por encima del umbral y se
abstuvo de todos modos. En esos casos **no lo salva el umbral, lo salva el
prompt restrictivo**, que es precisamente lo que nunca se había medido.

### 6.2 Recuperación por frase ancla

Determinista, sin modelo juez y sin coste.

| Grupo | n | hit@1 | hit@3 | hit@5 | MRR |
|---|---|---|---|---|---|
| Todas | 12 | 0,25 | 0,50 | 0,67 | 0,394 |
| `literal` | 8 | 0,38 | 0,62 | 0,75 | **0,525** |
| `multi` | 4 | 0,00 | 0,25 | 0,50 | **0,133** |

En las `multi` el acierto exige **las dos anclas** entre los fragmentos
recuperados, y se toma la peor posición: la respuesta no está completa hasta
que aparece la segunda.

### 6.3 Latencia

```
p50 = 2,41 s     p95 = 4,26 s     máximo = 6,04 s
```

### 6.4 Las cuatro preguntas fallidas, analizadas una a una

Tres de los cuatro fallos **no son de recuperación**, y distinguirlo importa
porque de lo contrario las cifras del apartado 6.2 se malinterpretan.

**P3 — «¿Qué es la similitud coseno?»** El ancla `invariante a la magnitud`
está en el `doc43`, el resumen. El sistema recuperó en segunda posición, con un
score de 0,787, un fragmento del `doc44` que dice *"Es invariante a la longitud
del texto. Captura similitud semántica independientemente de la magnitud"*. Las
cuatro palabras del ancla están presentes, repartidas en dos viñetas. **El
sistema recuperó contenido correcto de un documento distinto del anotado.**

**P8 — «¿Qué diferencias hay entre GPT-4o y Gemini 2.0?»** Los fragmentos
recuperados mencionan *Claude Opus 4.6* y *Gemini 3 Pro*, que **no aparecen en
el `.txt` extraído del corpus**. El documento indexado contiene secciones que la
extracción local no recogió: las anclas se verificaron contra un texto que no
coincide del todo con lo indexado.

**P11 — «¿En qué se diferencian la Euclídea y la de Manhattan?»** El ancla
`Datos físicos, clustering` procede de una tabla comparativa, y la
fragmentación la partió: *"clustering"* quedó en el fragmento 3 y *"coordenadas
físicas"* en el 4.

**P5 — «¿Qué diferencias hay entre las GAN y los VAE?»** Este **sí es un fallo
real**. Ninguno de los cinco fragmentos menciona *suma cero*, *generador* ni
*discriminador*: la pregunta pedía contrastar ambas arquitecturas y el sistema
solo recuperó material sobre VAE.

### 6.5 Hallazgo metodológico: el límite de la frase ancla

> La medición por frase ancla presupone que la respuesta vive en **un único
> pasaje**. En un corpus con documentos redundantes —un resumen y unas
> diapositivas del mismo tema— esa premisa se rompe: el sistema puede recuperar
> evidencia válida de un pasaje distinto del anotado, y la métrica lo contabiliza
> como fallo.

Este corpus contiene dos pares redundantes: `doc43`↔`doc44` (Tema 6) y
`doc38`↔`doc39` (VAE y GAN). Tres de los cuatro fallos provienen de ahí.

Es la justificación de mantener **las dos vías de medición**: las anclas son
deterministas pero rígidas, mientras que RAGAS juzga el contenido y no la
posición, de modo que no sufre este problema. Si RAGAS otorga buen
`context_recall` a las mismas preguntas en que el ancla falló, la discrepancia
confirma el diagnóstico — y constituye en sí misma un resultado del capítulo 5.

**Corrección prevista:** admitir variantes equivalentes dentro de un ancla,
separadas por `|`, con semántica de alternativa. Los dos niveles no se mezclan:

| Nivel | Semántica | Para qué |
|---|---|---|
| `ancla` y `ancla_2` | **Y** — se exigen ambas | Preguntas `multi` |
| `\|` dentro de un campo | **O** — basta una | Pasajes redundantes |

---

## 7. Línea base con RAGAS — 2026-10-12

Evaluación de las 12 preguntas con respuesta en el corpus, con `gpt-4o-mini`
como modelo juez. Script: `experimentos/evaluar_ragas.py`. Resultados en
`resultados/ragas_2026-10-12.json`.

### 7.1 La línea base

| Métrica | Valor | Qué mide |
|---|---|---|
| `context_precision` | **0,912** | De lo recuperado, cuánto servía |
| `context_recall` | **0,896** | De lo necesario, cuánto se recuperó |
| `faithfulness` | **0,888** | La respuesta se apoya en el contexto |
| `answer_relevancy` | **0,822** | La respuesta contesta a la pregunta |

Junto con lo medido en la ejecución del dataset (§6), el cuadro completo de la
configuración actual queda así:

```
tasa de abstención correcta   100 %  (6/6)
hit@3 por frase ancla         0,50
MRR por frase ancla           0,394
latencia p50 / p95            2,41 s / 4,26 s
```

`faithfulness` es la métrica que el tutor pidió como control mínimo de
alucinaciones. Descompone cada respuesta en afirmaciones y verifica una a una
si el contexto recuperado las respalda.

### 7.2 Desglose por tipo de pregunta

| Tipo | n | `context_precision` | `context_recall` | `faithfulness` |
|---|---|---|---|---|
| `literal` | 8 | 0,929 | 0,938 | 0,900 |
| `multi` | 4 | **0,878** | **0,812** | **0,865** |

Las preguntas compuestas obtienen peores resultados en las tres métricas. Es la
**tercera medición independiente** que apunta en la misma dirección, tras el
experimento de preguntas compuestas (§3) y las métricas por frase ancla (§6.2).

Esa convergencia es lo que permite proponer la descomposición de consultas
(C3) con datos que la justifican, y no por recomendación bibliográfica.

### 7.3 Los dos métodos de medición, comparados

Las métricas por frase ancla y las de RAGAS **no miden lo mismo ni fallan por
lo mismo**, y contrastarlas resultó más informativo que cualquiera de las dos
por separado.

| Pregunta | Ancla | RAGAS | Diagnóstico |
|---|---|---|---|
| P5 — GAN vs VAE | falla | `faithfulness` **0,538** | **Fallo real.** Ambos métodos coinciden |
| P8 — GPT-4o vs Gemini | falla | `faithfulness` **0,615** | **Fallo real** |
| P3 — similitud coseno | falla | sin anomalía | **Artefacto del ancla** |
| P11 — Euclídea vs Manhattan | falla | sin anomalía | **Artefacto del ancla** |

El análisis preliminar de §6.4 conjeturaba que **tres** de los cuatro fallos
eran artefactos del método de anclas. RAGAS corrige esa conjetura: solo **dos**
lo son. La P8 arrastra además un fallo real de recuperación, independiente del
problema del texto extraído desactualizado.

**Lo que aporta cada método:**

| | Frase ancla | RAGAS |
|---|---|---|
| Determinismo | Total: la frase está o no está | Depende de un modelo juez |
| Coste | Nulo | Céntimos por ejecución |
| Qué evalúa | La **posición** de un pasaje concreto | El **contenido** de la respuesta |
| Punto ciego | Corpus redundante: penaliza evidencia válida de otro pasaje | El sesgo del propio juez |

Ninguno sustituye al otro. **Donde discrepan es donde está la información**: una
discrepancia señala o bien un límite del método de anclas, o bien un fallo que
el juez pasa por alto.

### 7.4 Notas de método

**El entorno aislado funcionó.** RAGAS se instaló en `.venv-eval`, separado del
de la aplicación, y la comunicación entre ambos es un fichero JSON. El servicio
mantiene sus veinte dependencias; la evaluación arrastra las suyas, más de
sesenta, sin contaminarlo.

**Una incompatibilidad que hubo que resolver.** RAGAS 0.4.3 importa
`langchain_community.chat_models.vertexai`, módulo que la versión 0.4 de
`langchain-community` ya no incluye —el paquete está siendo retirado— y que el
resolvedor de dependencias instala por defecto. Se corrige fijando
`langchain-community<0.4`. Conviene registrarlo en `requirements-eval.txt`.

**Un error de informe, no de medición.** La primera ejecución no mostró
`context_precision`. La métrica se había calculado y pagado: lo que falló fue el
filtro de columnas del resumen, que buscaba nombres exactos cuando RAGAS las
nombra según la clase de métrica (`LLMContextPrecisionWithReference` produce
`llm_context_precision_with_reference`). Se recalculó desde el JSON guardado,
sin volver a invocar al modelo, porque el detalle por pregunta estaba
almacenado. Es la razón de guardar siempre el desglose y no solo los promedios.

**Coste y duración:** 3 minutos y 16 segundos, 48 evaluaciones —12 preguntas por
4 métricas—, unos céntimos.

### 7.5 Limitación que debe declararse

RAGAS emplea **un modelo de lenguaje como juez**, es decir, un modelo evaluando
a otro. Es la práctica estándar del campo y responde a lo solicitado, pero
introduce su propio sesgo: el juez puede equivocarse, y lo hace de forma
sistemática, no aleatoria.

La medición determinista por frases ancla, aunque más rígida, no depende de
ningún juicio. Disponer de ambas es lo que permite detectar cuándo una de las
dos se equivoca.

---

## 8. Descomposición de consultas — 2026-10-12

Primera mejora implementada y medida contra la línea base. Resuelve el defecto
cuantificado en §3: las preguntas compuestas recuperaban de media el 48 % de la
evidencia necesaria, y ningún mecanismo del sistema lo señalaba.

### 8.1 El resultado

Mismo experimento, mismas seis parejas de preguntas, misma métrica
(`experimentos/medir_preguntas_compuestas.py`).

| | Base | Con descomposición |
|---|---|---|
| Cobertura conjunta media | 48 % | **88 %** |
| Mínimo observado | 40 % | **80 %** |
| Máximo observado | 60 % | **100 %** |
| Desequilibrio medio entre subpreguntas | 1,8 | **0,9** |

| Pareja | Base | Avanzado |
|---|---|---|
| lejanas 1 | 50 % | **100 %** |
| lejanas 2 | 40 % | 90 % |
| lejanas 3 | 50 % | 90 % |
| lejanas 4 | 40 % | 90 % |
| vecinas 1 | 50 % | 80 % |
| vecinas 2 | 60 % | 80 % |

**Las seis parejas mejoran y ninguna empeora.**

La caída del desequilibrio importa tanto como la subida de la cobertura, porque
describe un **cambio en el modo de fallo**. Con el pipeline base, repartos como
4/1 o 1/4 significaban que una de las dos preguntas se quedaba sin responder.
Con descomposición, los repartos son 5/5, 4/5 y 4/4: en el peor caso, a una de
las dos le falta un fragmento.

### 8.2 El coste

| | Base | Avanzado |
|---|---|---|
| Fragmentos enviados al modelo (compuestas) | 5 | 8-10 |
| Latencia mediana sobre el dataset completo | 2,41 s | **3,65 s** |
| Llamadas al modelo por consulta | 1 | **2** |

El peaje de latencia se paga en **todas** las consultas, no solo en las
compuestas: siempre hay que preguntar al modelo si procede descomponer. El
coste de contexto, en cambio, solo crece cuando efectivamente se descompone.

### 8.3 El diseño: dos clases, no una modificación

```
RAGService                    la línea base, sin modificar
   └── RAGServiceAvanzado     redefine únicamente `_recuperar`
```

`RAGServiceAvanzado` hereda `generate_response`, el filtro por umbral, el
*prompt* restrictivo, la construcción del contexto, el registro de coste, las
trazas y la abstención. Lo único que cambia es **cómo se obtienen los
fragmentos**.

Para hacerlo posible se extrajo previamente la recuperación de
`generate_response` a un método propio, `_recuperar`, sin alterar el
comportamiento: 35 tests en verde antes y después.

**Por qué dos clases y no un parámetro.** Modificar `RAGService` habría hecho
desaparecer la línea base: para volver a medir el «antes» habría que revertir el
cambio. Con ambas vivas, las dos configuraciones se relanzan sobre el mismo
material cuando convenga, y la comparación es reproducible en cualquier momento
—incluso durante la defensa—.

En este trabajo se descartaron deliberadamente otras abstracciones que habrían
tenido una sola implementación. Aquí hay dos reales, y existen precisamente para
ser comparadas.

### 8.4 Dos propiedades del diseño

**Si la pregunta no es compuesta, el comportamiento es idéntico al de la base.**
La descomposición devuelve una sola subpregunta y se delega en
`super()._recuperar`. Verificado: ante *«¿qué es la similitud coseno?»* ambas
configuraciones devuelven los mismos cinco fragmentos y los mismos 1.535 tokens.

**Un fallo de la descomposición nunca impide una respuesta.** Si el modelo no
responde, devuelve un formato inesperado o produce más de tres subpreguntas, se
recupera como el pipeline base. La mejora no puede convertirse en un punto de
fallo.

### 8.5 Un error de método que conviene registrar

La primera medición se hizo con el **instrumento equivocado**. Se lanzó el
dataset de evaluación completo con la clase avanzada y las métricas por frase
ancla salieron **idénticas** a las de la línea base, lo que parecía indicar que
la mejora no servía.

La causa fue una confusión conceptual entre dos cosas distintas:

| | Qué es | Ejemplo |
|---|---|---|
| **Pregunta compuesta** | Dos preguntas en un mismo mensaje | *«¿Qué es un VAE y cómo se entrena un transformer?»* |
| **Tipo `multi` del dataset** | **Una** pregunta que exige dos piezas de evidencia | *«¿Qué diferencias hay entre las GAN y los VAE?»* |

*«¿Qué diferencias hay entre X e Y?»* es una sola pregunta, y el descompositor
hizo bien en no partirla: dividirla produciría *«¿qué es X?»* y *«¿qué es Y?»*,
que no es lo que se preguntaba. **El dataset no contiene preguntas compuestas**,
salvo la número 9, que fue justamente la única que se descompuso.

La mejora se mide con el experimento que midió el defecto, no con el dataset
general. Es la misma disciplina aplicada al propio proceso de evaluación.

### 8.6 Efecto secundario detectado

La descomposición **reformula la consulta incluso cuando no la separa**. Ante
*«¿qué es la similitud coseno?»*, el pipeline base obtuvo una puntuación máxima
de 0,768 y el avanzado de 0,787 sobre los mismos fragmentos: el texto que llega
al vectorizador ha pasado por el modelo y no es idéntico al original.

El efecto es pequeño y favorable en este caso, pero es una diferencia real entre
ambas configuraciones que debe declararse: **el avanzado no es estrictamente la
base más una recuperación adicional**.

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

- [x] **A4. RAGAS — línea base.** `context_precision` 0,912, `context_recall`
      0,896, `faithfulness` 0,888 y `answer_relevancy` 0,822 sobre 12
      preguntas. En `.venv-eval`, aislado del entorno de la aplicación.
      *2026-10-12.*
- [x] **`requirements-eval.txt` creado** con `ragas==0.4.3` y
      `langchain-community<0.4`. La restricción está documentada en el propio
      fichero: la 0.4.2 retira el módulo que RAGAS importa. *2026-10-12.*

- [x] **A1. Dataset de evaluación.** 18 preguntas —8 `literal`, 4 `multi`, 6
      `sin_respuesta`—, 17 frases ancla verificadas como únicas en el corpus y
      12 respuestas de referencia. En `experimentos/dataset_evaluacion.csv`;
      razonamiento y errores de método en `DATASET_PREGUNTAS.md`. *2026-10-11.*
- [x] **A5. Latencia p50/p95** medida en la ejecución del dataset: 2,41 s y
      4,26 s. *2026-10-11.*
- [x] **Métricas de recuperación por ancla** (`hit@k`, MRR) y **tasa de
      abstención correcta**, calculadas en la misma pasada. *2026-10-11.*
- [ ] **Corregir el método de anclas**: admitir variantes equivalentes con `|`
      y volver a ejecutar, para separar los fallos reales de los artefactos del
      corpus redundante.
- [ ] **Regenerar los `.txt` del corpus**: el índice contiene secciones que la
      extracción local no recogió (ver §6.4, P8).

- [x] **A2. Langfuse instrumentado.** Cada consulta genera una traza con cinco
      observaciones; el paso de recuperación guarda cada fragmento con su
      puntuación y si supera el umbral, y las consultas sin contexto se
      etiquetan aparte. Dependencia opcional: con `LANGFUSE_ENABLED=false` el
      sistema funciona igual. Ver `OBSERVABILIDAD.md`. *2026-10-09.*
- [ ] **A3. Dataset cargado en Langfuse** y apuntado contra el RAG.

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
- [x] **B4. Los dos modos de alucinación llevados a la memoria**, en el
      apartado 5.4, como casos analizados y no como deficiencias. *2026-10-11.*
- [x] **Capítulo 5 cerrado.** 5.1 (conjunto de referencia), 5.2 (métricas,
      escrita entera), 5.3 (experimentos cuarto y quinto) y 5.4 (limitaciones
      del modelo juez y del método de anclas). Sin marcadores pendientes:
      5.709 palabras y nueve tablas. Se corrigió además el orden de lectura de
      tres bloques que habían quedado invertidos al insertarlos. *2026-10-12.*

## Bloque C — Mejoras, cada una medida contra la línea base

- [ ] **C1. Reranking**, medido contra A4 sobre el mismo dataset.
- [ ] **C2. RAG híbrido** (denso + BM25), o decisión documentada de dejarlo como
      trabajo futuro con el argumento de cuándo haría falta: siglas, códigos,
      nombres propios, referencias normativas.
- [x] **C3. Descomposición de consultas implementada y medida.** Cobertura
      conjunta del 48 % al 88 % sobre las mismas seis parejas; las seis mejoran.
      `RAGServiceAvanzado` redefine solo `_recuperar`. Coste: +1,2 s de latencia
      mediana y el doble de contexto en las consultas que se descomponen.
      Ver §8. *2026-10-12.*

### Por qué C3 es el mejor candidato de los tres

Es la **única mejora cuyo problema ya está medido**: la degradación del 48 % en
preguntas compuestas (§3) y el `MRR` de 0,133 frente a 0,525 de las `literal`
(§6.2). El reranking y el híbrido se implementarían a ciegas, esperando que
mejoren; esta se implementa sabiendo exactamente qué arregla y cuánto margen
hay.

Responde además de forma directa a una de las preguntas del tutor —*¿se pueden
hacer varias preguntas?*—, permitiendo pasar de *«no, y lo he medido»* a *«no lo
hacía, lo medí, lo implementé y mejoró un X %»*.

**El diseño: una clase nueva, no una modificación.**

Modificar `RAGService` haría desaparecer la línea base, que habría que revertir
para volver a medirla. Con dos clases, ambas configuraciones se pueden relanzar
sobre el mismo dataset en cualquier momento, y la comparación es reproducible.

Requiere un refactor mínimo: extraer la recuperación de `generate_response` a un
método propio, de modo que la subclase solo redefina ese punto. El umbral, el
*prompt*, el contexto, el registro de coste y las trazas se heredan sin tocar
nada.

```
RAGService              _recuperar  →  1 embedding, 1 búsqueda
RAGServiceAvanzado      _recuperar  →  descompone, N búsquedas, deduplica
```

Si la descomposición devuelve una sola subpregunta —porque la pregunta no era
compuesta— el comportamiento es idéntico al de la base: la mejora solo actúa
cuando hace falta.

**Coste:** una llamada adicional al LLM por consulta (unas 5·10⁻⁵ USD) y en
torno a un segundo de latencia.

**Nota sobre la abstracción:** en este trabajo se descartó deliberadamente
abstraer otras piezas que habrían tenido una sola implementación. Aquí hay dos
reales, y existen precisamente para ser comparadas.

### Orden de ejecución

```
1. RAGAS sobre el código actual     la línea base queda fijada
2. extraer _recuperar               refactor sin cambio de comportamiento
3. RAGServiceAvanzado               la descomposición
4. RAGAS de nuevo                   el después
```

RAGAS **antes** de tocar nada: así los números de la base proceden de código sin
modificar. El paso 2 se verifica con los 35 tests y relanzando el dataset; si da
exactamente los mismos resultados, el refactor es correcto.

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
