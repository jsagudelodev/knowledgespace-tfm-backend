# Núcleo RAG — auditoría y plan

Qué está implementado, qué está implementado pero sin medir, y qué falta.
Auditado contra el código el **9 de octubre de 2026**, tras la primera tutoría
(ver [`TUTORIAS.md`](TUTORIAS.md)). **Actualizado el 19 de octubre** tras
incorporar el reordenado (§9), el reparto equilibrado (§10), cerrar el híbrido
(§11) y medir una sexta configuración que combina ambos (§12).

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

## Guía rápida — las seis clases, en lenguaje llano

Antes del detalle técnico de más abajo: qué es cada clase, por qué existe y si
está activa. Las seis heredan lo mismo —el filtro de relevancia 0,30, el
*prompt* que impide inventar, el registro de coste, las trazas— y solo cambian
**cómo se recuperan los fragmentos** (el método `_recuperar`).

**1. `RAGService` — la línea base (*naive RAG*).** Convierte la pregunta en un
vector, busca los 5 fragmentos más parecidos por significado, descarta los que
no llegan a 0,30 de relevancia y, si no queda ninguno, se abstiene. Es el punto
de comparación de todo lo demás: sin ella, ninguna mejora se puede demostrar,
solo afirmar. Su límite: un vector no representa bien una pregunta con dos
temas, y puede no encontrar un término técnico poco frecuente aunque esté en
el corpus.

**2. `RAGServiceAvanzado` — descomposición sin tope.** Si detecta varios temas
en la pregunta, la parte en subpreguntas, busca cada una por separado y junta
**todos** los fragmentos encontrados. Sube la cobertura de preguntas con dos
temas del 48 % al 88 %, pero sin control de cuánto crece el contexto: con dos
subpreguntas puede mandar 9-10 fragmentos al modelo en vez de 5, casi el doble
de costo en esa consulta. Medida, no activa — superada por la #3.

**3. `RAGServiceCompleto` — descomposición acotada / reparto equilibrado — ✅
la activa hoy.** Igual que la anterior, pero mantiene el límite de siempre (5
fragmentos): en vez de quedarse con "los 5 mejores en general" —que suele
dejar a un tema con 4 y al otro con 1—, reparte por turnos, el mejor fragmento
de cada subpregunta por ronda, hasta llenar los 5 huecos. Ningún tema se queda
sin representación, al mismo costo que la base. Si la pregunta es simple, se
comporta exactamente como la base. Resuelve la pregunta del tutor sobre varias
preguntas a la vez sin pagar el costo doble de la #2.

**4. `RAGServiceReranking` — reordenado.** Busca entre más candidatos (20 en
vez de 5), filtra por el mismo umbral, y un modelo reordena los que quedan por
utilidad real, no por parecido vectorial. Mejora el acierto en encontrar el
fragmento correcto, pero una llamada extra que debe leer el texto completo de
cada candidato multiplica el costo por consulta ×3,7, y las respuestas
generadas no mejoran de forma medible. Medida, no activa.

**5. `RAGServiceHibrido` — densa + léxica (BM25).** A la búsqueda por
significado le suma una búsqueda por palabra exacta (BM25), y combina los dos
rankings por posición. Rescata fragmentos que el significado pasa por alto por
usar un término técnico poco frecuente. Da el mejor acierto medido en el
dataset de 18 preguntas, pero empeora las preguntas de dos temas (cobertura de
48 % a 30 %, peor que no hacer nada) porque no descompone: busca con la
pregunta completa. Medida, no activa — retrocede justo en lo que el tutor
preguntó.

**6. `RAGServiceDescomposicionHibrida` — la combinación de la #3 y la #5.**
Descompone y reparte en turnos como la #3, pero dentro de cada subpregunta
aplica también BM25 como la #5. La intención: que ninguna subpregunta se quede
sin representación y que cada una rescate lo que el significado pasa por
alto. Da el mejor hit@3 y MRR medidos y el mejor reparto de las seis, pero no
recupera del todo la cobertura que la #5 pierde (37 %, todavía por debajo del
48 % de la base) y es la más lenta de las seis. Medida, no activa.

### Cifras completas, lado a lado

| Configuración | hit@1 | hit@3 | MRR | Fidelidad (RAGAS) | Cobertura compuestas | Desequilibrio | p95 latencia |
|---|---|---|---|---|---|---|---|
| 1. Base | 0,25 | 0,50 | 0,394 | 0,939 | 48 % | 1,83 | 4,92 s |
| 2. Descomposición sin tope | 0,25 | 0,50 | 0,394 | sin medir | 88 % | 0,83 | 5,28 s |
| **3. Descomposición acotada (activa)** | 0,25 | 0,50 | 0,394 | sin medir | **52 %** | **0,83** | 5,33 s |
| 4. Reordenado | 0,25 | 0,67 | 0,447 | 0,946 | — | — | 6,40 s |
| 5. Híbrido (BM25) | 0,42 | 0,58 | 0,537 | 0,965 | 30 % | 1,00 | 6,97 s |
| 6. Descomposición + híbrida | 0,42 | 0,67 | 0,544 | 0,913* | 37 % | 0,67 | 8,77 s |

\* *Incluye ruido del evaluador: comprobado pregunta por pregunta, para varios
casos el contexto recuperado y la respuesta generada son idénticos a los de la
#5, y aun así el juez de RAGAS dio notas distintas. Detalle en §12.*

**Por qué la activa es la #3 y no la #5 o la #6, que sacan mejor nota en el
dataset de 18 preguntas:** el tutor preguntó explícitamente si el sistema
admite varias preguntas a la vez, y la #3 es la única, de las tres medidas en
ese terreno, que lo resuelve sin empeorar nada ni disparar el costo. La #5 lo
rompe (30 %) y la #6 no termina de arreglarlo (37 %), a cambio de ser la más
lenta de las seis.

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
| Reescritura o expansión de consulta | ❌ | La pregunta se vectoriza tal cual (la descomposición de §8 es un caso distinto: no reescribe, separa) |
| Descomposición de consultas | ✅ | `RAGServiceAvanzado`, cobertura 48 %→88 %. §8 |
| Descomposición con tope de contexto (reparto equilibrado) | ✅ | `RAGServiceCompleto`, **configuración activa por defecto**. §10 |
| Reranking | ✅ medido, **no activo** | `RAGServiceReranking`, hit@3 0,50→0,667; decisión de no desplegar documentada. §9 |
| RAG híbrido (denso + BM25) | ✅ medido, **no activo** | `RAGServiceHibrido`, hit@1 0,25→0,42, pero empeora preguntas compuestas (48 %→30 %). §11 |
| Descomposición + híbrida | ✅ medido, **no activo** | `RAGServiceDescomposicionHibrida`, mejor hit@3/MRR medidos, no recupera del todo la cobertura perdida por el híbrido. §12 |

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
| Dataset de evaluación | ✅ 18 preguntas, cerrado el 2026-10-11 (§6) |
| Langfuse | ✅ Instrumentado el 2026-10-09; dataset enlazado el 2026-10-18 |
| RAGAS | ✅ Línea base el 2026-10-12 (§7); reranking el 2026-10-14 (§9) |
| Métricas de recuperación (`hit@k`, MRR) | ✅ Por frase ancla, 2026-10-11 (§6.2) |
| Latencia p50 / p95 | ✅ 2,41 s / 4,26 s, medida el 2026-10-11 (§6.3) |
| Umbral de relevancia | ✅ Revalidado el 2026-10-09 |
| Degradación en preguntas compuestas | ✅ Medida el 2026-10-09; corregida con descomposición el 2026-10-12 |

**Este bloque, que decide la nota, ya está cerrado.** Las nueve piezas están
medidas, incluida la comparación del híbrido y de la sexta configuración
contra la línea base (§11, §12).

---

## 3. Control de alucinaciones

> **Esta sección describe el diagnóstico del 9 de octubre.** Al 19 de octubre
> los tres mecanismos **ya están medidos** — ver §6.1 (abstención, 6/6
> correctas en las seis configuraciones donde se ha ejecutado el dataset) y §7
> en adelante (`faithfulness` por configuración: 0,939 en la base, hasta 0,965
> con el híbrido). Se conserva el texto original porque el hallazgo de la
> alucinación de alcance (más abajo) sigue vigente tal cual se detectó.

Había **tres mecanismos implementados y ninguno medido**. Es exactamente lo que
el tutor señaló.

| Mecanismo | Implementado | Medido | Con test |
|---|---|---|---|
| Umbral de relevancia descarta contexto pobre | Sí | **Sí**, §6.1 y §7 | Sí, `test_rag_service_umbral.py` |
| *Prompt* obliga a responder solo con el contexto | Sí | **Sí**, abstención 6/6 en §6.1 | Sí |
| Registro de *knowledge gaps* | Sí | No es una métrica de calidad, es un registro operativo | — |

El *prompt* exige responder literalmente *"No encontré información sobre este
tema en los documentos de la empresa"* cuando el contexto no basta
(`rag_service.py:24`). Verificado en §6.1: 6 de 6 abstenciones correctas sobre
el dataset de 18 preguntas, sin ninguna abstención indebida.

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

**Dato de la auditoría original, 9 de octubre:** `rag_service.py`, `chat.py` y
`pinecone_service.py` tenían **0 llamadas a `logger`**. En toda la aplicación
había 5. Eso significaba que, cuando una respuesta salía mal, no había forma de
saber qué se recuperó, con qué puntuaciones ni qué contexto recibió el modelo.
Es la razón de fondo por la que el tutor preguntó por Langfuse.

**Verificado de nuevo el 19 de octubre:** `chat.py` y `pinecone_service.py`
siguen sin ninguna llamada a `logger`, pero ya no es el diagnóstico que importa
— `rag_service.py` tiene ahora 7 (una por cada configuración que descompone,
reparte o fusiona: `[RAG*]`, `[RAG~]`, `[RAG#]`…) y, sobre todo, **Langfuse ya
está instrumentado** (§11 de esta sección en su momento, hoy integrado en el
flujo normal): cada consulta genera cinco observaciones, y el paso de
recuperación guarda cada fragmento con su puntuación y si superó el umbral.
Esa es la observabilidad real que responde a la pregunta del tutor —no el
conteo de `logger.info`, que para este proyecto resultó ser la señal
equivocada—. Detalle completo en `OBSERVABILIDAD.md`. En toda la aplicación hay
hoy 44 llamadas a `logger`.

---

## 5. Pruebas

**Actualizado el 19 de octubre: 117 tests en verde, 18 archivos** (`pytest -q`,
verificado). La tabla original de esta sección, del 9 de octubre, decía 21
tests sin ninguno sobre el umbral ni la abstención — la aportación central del
trabajo no tenía ni una prueba. Eso cambió en el bloque B del plan (ver más
abajo) y creció de nuevo con cada configuración añadida después.

| Qué cubren | Tests |
|---|---|
| Las seis configuraciones del pipeline RAG y la construcción de contexto (`rag_factory`, `avanzado`, `completo`, `reranking`, `híbrido`, `descomposición+híbrida`, `context`) | 56 |
| Umbral de relevancia y abstención (`test_rag_service_umbral.py`) | 14 |
| Parámetros configurables del pipeline (`TOP_K`, umbral, etc. por variable de entorno) | 9 |
| Índice léxico BM25 (soporte del híbrido) | 8 |
| Namespaces y listado de Pinecone | 13 |
| Observabilidad (cliente Langfuse, trazabilidad de *embeddings*) | 4 |
| Resto de la aplicación: costes, panel, *knowledge gaps* | 13 |

**Sigue sin existir ningún test de integración**: ninguno levanta la
aplicación ni toca una base de datos real — ver la limitación declarada en
`ALCANCE_TFM.md`. Lo que sí cambió es que la aportación central —las seis
estrategias de recuperación, el umbral y la abstención— concentra la mayoría
de los 117 tests.

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

> **Nota añadida el 20 de octubre: esta no es la única medición de la línea
> base, y conviene saber cuál citar en cada caso.** Esta tabla es la del
> `ragas_2026-10-12.json`. Al volver a medir el 14 de octubre para comparar
> con el reordenado (§9), con la temperatura fijada explícitamente en 0
> (`ragas_2026-10-14_base_temp0.json`), la base dio `faithfulness` **0,939** y
> `answer_relevancy` 0,839 — distinto, pese a ser "la misma" configuración.
> `context_recall` sale **idéntico** en los dos archivos (0,895833... hasta el
> último decimal), lo que confirma la causa: esa métrica depende solo de qué
> se recupera —determinista, no cambia con la temperatura—, mientras que
> `faithfulness` y `answer_relevancy` dependen de la respuesta generada, que
> sí varía entre ejecuciones. Es la misma clase de ruido que §12 documenta
> para el juez de RAGAS, aquí observado un nivel antes, en la propia
> generación. **Para comparar contra otra configuración medida el mismo día
> con la misma temperatura fija (reordenado, híbrido, la sexta clase), cita
> 0,939** —es el valor que usan las tablas comparativas de §9, §11 y §12—,
> no el 0,888 de esta tabla, que viene de una ejecución distinta sin
> temperatura fijada.

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

## 9. Reordenado de fragmentos (reranking) — 2026-10-14

Segunda mejora implementada y medida contra la línea base. Ensancha la
búsqueda a 20 candidatos, filtra por el mismo umbral de 0,30 antes de
reordenar —para que la abstención no cambie— y un modelo reordena los
supervivientes por utilidad real, no por similitud coseno.

### El resultado

| | Base | Con reordenado |
|---|---|---|
| hit@3 | 0,500 | **0,667** |
| MRR | 0,394 | **0,447** |
| `context_precision` (RAGAS) | 0,877 | 0,920 |
| `context_recall` (RAGAS) | 0,896 | 0,896 |
| `faithfulness` (RAGAS) | 0,939 | 0,946 |
| `answer_relevancy` (RAGAS) | 0,839 | 0,813 |

**La recuperación mejora de forma clara; la generación no.** Las cuatro
métricas de RAGAS se mueven dentro del margen de ruido del propio modelo
evaluador —ninguna cruza una diferencia que se pueda llamar mejora real—, así
que no está demostrado que las respuestas finales sean mejores, solo que los
fragmentos llegan mejor ordenados.

### El coste

La llamada del reordenador consume unos 4.600 tokens de entrada por consulta
—necesita ver el texto completo de cada candidato para no repetir el error
que motivó subir el recorte de 400 a 1.000 caracteres (ver
`reordenador.py`)—, lo que multiplica por **3,7** el coste de la consulta.

### Decisión

**Disponible, medida y documentada; no activa por defecto.** Mejora la
recuperación de forma consistente, pero pagar 3,7 veces más por consulta sin
que se demuestre una respuesta mejor es pagar sin cobrar. La clase
(`RAGServiceReranking`) y el mixin que comparte con `RAGServiceCompleto`
(`MezclaReordenado` en `reordenador.py`) quedan activables por
`RAG_CONFIGURACION=reranking`. Razonamiento completo en el docstring de
`rag_factory.py`.

---

## 10. Reparto equilibrado de contexto — 2026-10-16

Tercera mejora, construida sobre la descomposición de consultas (§8) para
cerrar el defecto que esta dejaba abierto: **ensancha sin recortar**. Con dos
subpreguntas, la descomposición sin tope manda 9-10 fragmentos al modelo en
vez de 5 — casi el doble de coste de contexto por consulta.

### Por qué no se recortó con el reordenador

El primer intento recortó pidiendo al modelo que ordenara los fragmentos por
utilidad y conservando los cinco primeros. **Se midió y empeoró**, sobre las
seis parejas de preguntas compuestas:

| | Cobertura | Desequilibrio |
|---|---|---|
| Base | 48 % | 1,83 |
| Reordenado y recorte | 52 % | **2,17** — peor reparto |
| Reparto en turnos (la solución adoptada) | ~52 % | **0,83** |

El reordenador elige los fragmentos "más útiles" en conjunto y tiende a
concentrarse en una de las dos subpreguntas — justo lo que la descomposición
venía a evitar — y además cobra una llamada al modelo por hacerlo.

### La solución: reparto en turnos, sin coste de llamada

`RAGServiceCompleto._repartir` toma por rondas el mejor fragmento aún no
incluido de cada subpregunta, garantizando que ninguna se queda sin
representación, sin decidir cuál es "mejor" en conjunto. Con el presupuesto
fijo en `TOP_K=5`, el techo de cobertura es matemáticamente ~50 % — por eso
esta variante no persigue el 88 % de la descomposición sin tope (§8), que solo
es alcanzable enviando el doble de fragmentos.

**Lo que sí logra, medido:** el desequilibrio cae de 1,83 a 0,83 —casi el
mismo valor que la descomposición sin tope (0,9)— al mismo coste de contexto
que la línea base. Es, de las cinco configuraciones, la única que mejora el
reparto de evidencia sin pagar ni en tokens ni en llamadas adicionales de
reordenado.

### Decisión

**Es la configuración activa por defecto** (`RAG_CONFIGURACION=descomposicion_acotada`).
Resuelve el mismo problema que la descomposición sin tope —ninguna subpregunta
se queda sin representación— sin su coste de contexto. Detalle completo en
`rag_service_completo.py`.

---

## 11. RAG híbrido (denso + BM25) — 2026-10-19, cerrado

Cuarta mejora, implementada para cerrar la pregunta 4 del tutor (*"¿es un RAG
híbrido?"*), que hasta ahora se respondía "no, y no está medido por qué no".

### El problema que resuelve

La recuperación densa compara significado y es ciega a la forma: un código de
régimen, una partida arancelaria o un acrónimo poco frecuente puede no tener
una representación vectorial distintiva, y la similitud coseno lo trata como
ruido. BM25 es la operación inversa — ciega al significado, precisa con la
letra. El híbrido combina ambas para que lo que una descarta, la otra pueda
rescatarlo.

### El diseño: el umbral protege primero, la fusión opera después

BM25 y la similitud coseno no viven en la misma escala, y mezclarlas sin
cuidado abre dos modos de fallo: que el sistema deje de abstenerse nunca (BM25
casi siempre encuentra alguna coincidencia léxica) o que se abstenga siempre
(si la fusión diluye la señal densa por debajo del umbral). La solución,
coherente con el patrón ya usado en reranking y en el reparto equilibrado:

```
1. búsqueda densa ensanchada
2. filtro por umbral 0,30 — IDÉNTICO al de la línea base
3. si no sobrevive nada → abstención, igual que la base
   (BM25 no tiene voto sobre si el sistema responde)
4. si sobrevive algo → se busca también por BM25 y se fusiona
   por POSICIÓN (Reciprocal Rank Fusion), nunca por puntuación
5. se devuelven los TOP_K mejores de la fusión
```

Un fragmento rescatado solo por BM25 puede entrar a la fusión, pero nunca
puede ser la única señal que sostiene una respuesta — el paso 3 ya decidió que
hay evidencia suficiente antes de que BM25 participe. Detalle completo en
`rag_service_hibrido.py`.

### Estado de la medición

Primera ejecución del dataset completo (18 preguntas) el 19 de octubre:

| | |
|---|---|
| Abstención correcta | **6/6** |
| Falsa abstención | **0/12** |
| Latencia | entre 1,66 s y 7,96 s |

Coincide con el comportamiento de la línea base en abstención, que es
exactamente lo que el diseño garantiza por construcción (paso 3).

### RAGAS contra la línea base

| Métrica | Base | Híbrido |
|---|---|---|
| hit@1 (frase ancla) | 0,25 | **0,42** |
| hit@3 (frase ancla) | 0,50 | 0,58 |
| MRR (frase ancla) | 0,394 | **0,537** |
| `faithfulness` | 0,939 | **0,965** |
| p95 latencia | 4,92 s | 6,97 s |

El híbrido rescata evidencia real que la base pasaba por alto: ante *"¿qué
diferencias hay entre las GAN y los VAE?"* —el fallo de recuperación
confirmado en §7.3—, BM25 sí encuentra el fragmento que explica el mecanismo
competitivo ("si el discriminador acierta, el generador mejora") que la
búsqueda densa dejaba fuera.

### El efecto secundario: empeora las preguntas compuestas

Medido con el mismo experimento del §3 y el §8 (seis parejas, solo
*embeddings*):

| | Base | Descomposición acotada | Híbrido solo |
|---|---|---|---|
| Cobertura conjunta | 48 % | 52 % | **30 %** |
| Desequilibrio | 1,83 | 0,83 | 1,00 |

El híbrido busca con la consulta completa, sin descomponer, así que arrastra
el mismo problema de vector único que la base — y al fusionar con BM25 sobre
ese vector único, desplaza algunos de los fragmentos que la base sí recuperaba
bien. Es una medición puramente de *embeddings*, sin modelo juez de por medio,
así que no está sujeta al ruido que sí afecta a la comparación de
`faithfulness` del §12.

### Decisión

**Disponible, medida y documentada; no activa por defecto**
(`RAG_CONFIGURACION=hibrido`). Mejora el acierto de recuperación y la
fidelidad medida sobre el dataset de 18 preguntas, pero el tutor preguntó
explícitamente si el sistema admite varias preguntas a la vez, y esta
configuración retrocede justo ahí (48 %→30 %). Activar una mejora que rompe un
problema ya resuelto no se justifica sin resolver antes esa regresión — lo que
se intentó en §12. `RAGServiceHibrido` queda con test propio
(`test_rag_service_hibrido.py`, 8 tests) y el índice léxico probado por
separado (`test_indice_lexico.py`, 8 tests).

---

## 12. Descomposición + híbrida — 2026-10-19, cerrado

Quinta mejora, construida para responder una pregunta concreta: ¿se puede
combinar el reparto equilibrado (§10) con la búsqueda léxica (§11) sin que una
estropee lo que la otra resuelve? No compiten en principio: el reparto decide
**cuántos** fragmentos le tocan a cada subpregunta; el híbrido decide
**cuáles** fragmentos concretos rescata dentro de una búsqueda.

### El diseño

Una clase nueva, `RAGServiceDescomposicionHibrida`, hereda de
`RAGServiceCompleto` y del mismo *mixin* de fusión léxica que usa
`RAGServiceHibrido` (`fusion_lexica.MezclaLexica`), sin modificar ninguna de
las cinco clases existentes:

```
1. descompone la consulta                    (como §8/§10)
2. para CADA subpregunta:
     a. búsqueda densa ensanchada
     b. filtro por umbral                    (como §10)
     c. fusión con BM25, con el texto de      (como §11, pero una vez
        ESA subpregunta, no el de la          por subpregunta)
        consulta completa
3. si ninguna subpregunta tiene evidencia → abstención, igual que la base
4. si hay más fragmentos que el presupuesto → reparto en turnos (§10)
```

Con una sola subpregunta este flujo se reduce exactamente al comportamiento de
`RAGServiceHibrido` — no hay un caso especial para ello, es la misma secuencia
sobre una lista de longitud uno.

**Dos errores de diseño reales, encontrados antes de medir contra el índice
real**, mediante tests con sabotaje deliberado (revertir la corrección,
confirmar que el test falla, restaurar):

1. Un fragmento rescatado solo por BM25 no tiene puntuación densa. Asignarle
   `None` habría producido un `TypeError` más adelante, en el filtro heredado
   de la línea base. Corregido usando el propio umbral de relevancia como
   valor centinela explícito, nunca como medición real.
2. El orden de combinación de los rankings densos y léxicos podía hacer que
   ese valor centinela **sobrescribiera** la puntuación densa real de un
   fragmento presente en ambos rankings, perdiendo la medición real. Corregido
   invirtiendo el orden de combinación.

### El resultado

| | Base | Híbrido solo | Descomposición + híbrida |
|---|---|---|---|
| hit@3 | 0,50 | 0,58 | **0,67** |
| MRR | 0,394 | 0,537 | **0,544** |
| Abstención correcta | 6/6 | 6/6 | 6/6 |
| `faithfulness` (RAGAS) | 0,939 | 0,965 | 0,913 |
| Cobertura compuestas | 48 % | 30 % | 37 % |
| Desequilibrio compuestas | 1,83 | 1,00 | **0,67** |
| p95 latencia | 4,92 s | 6,97 s | **8,77 s** |

**La caída de `faithfulness` frente al híbrido solo no es una regresión
real.** Verificado pregunta por pregunta: de las 12 evaluadas, en 6 el
contexto recuperado y la respuesta generada son **idénticos carácter por
carácter** entre esta clase y el híbrido solo (con una sola subpregunta, el
flujo se reduce al mismo comportamiento). Aun así el juez de RAGAS dio notas
distintas sobre el mismo insumo —1,0 frente a 0,6 en el caso más extremo,
sobre *"¿qué es un LLM?"*—, lo que por sí solo explica el 64 % de la
diferencia observada en el promedio. El resto son variaciones de redacción sin
diferencia de contenido, verificadas a mano en dos casos más, consistentes con
la falta de reproducibilidad exacta de `temperature=0`. Es la misma limitación
del modelo juez que ya documenta el §7.5, aquí confirmada con evidencia
directa en vez de inferida.

**Lo que sí mejora, de forma real y verificable sin modelo juez:** el reparto
entre subpreguntas — el mejor de las seis configuraciones (desequilibrio
0,67, frente a 0,83 de la descomposición acotada sola).

**Lo que no logra:** recuperar la cobertura de preguntas compuestas que el
híbrido solo pierde. Sube del 30 % al 37 %, pero sigue por debajo del 48 % de
la base y del 52 % de la configuración activa — atenúa el problema, no lo
resuelve.

### Decisión

**Disponible, medida y documentada; no activa por defecto**
(`RAG_CONFIGURACION=descomposicion_hibrida`). No hay ganancia limpia que
compense su costo: es la configuración más lenta de las seis, y el problema
que la motivó —la pérdida de cobertura en preguntas compuestas del híbrido—
sigue sin resolverse del todo. Se documenta con el mismo criterio que el
reordenado y el híbrido: una mejora medida y descartada con razones es tan
defendible como una activada. Test propio en
`test_rag_service_descomposicion_hibrida.py` y
`test_pinecone_listar_namespace.py`.

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

- [x] **C1. Reranking**, medido contra la línea base con RAGAS. hit@3 de 0,50 a
      0,667 y MRR de 0,394 a 0,447, pero las cuatro métricas de generación
      dentro del margen de ruido del juez y coste ×3,7. **Decisión: no
      activo.** Ver §9. *2026-10-14.*
- [x] **C2. RAG híbrido** (denso + BM25), medido contra la línea base: hit@1 de
      0,25 a 0,42, `faithfulness` de 0,939 a 0,965, pero empeora la cobertura
      de preguntas compuestas (48 %→30 %). **Decisión: no activo** — rompe
      justo el problema que el tutor preguntó explícitamente. Ver §11.
      *2026-10-19.*
- [x] **C5 (no planificada). Descomposición + híbrida**, combinando C4 y C2 en
      una clase nueva. Mejor hit@3/MRR medidos (0,67 / 0,544) y mejor reparto
      de las seis (desequilibrio 0,67), pero no recupera del todo la cobertura
      de compuestas que C2 pierde (37 %, bajo el 48 % de la base) y es la
      configuración más lenta medida (p95 8,77 s). **Decisión: no activa.**
      Ver §12. *2026-10-19.*
- [x] **C3. Descomposición de consultas implementada y medida.** Cobertura
      conjunta del 48 % al 88 % sobre las mismas seis parejas; las seis mejoran.
      `RAGServiceAvanzado` redefine solo `_recuperar`. Coste: +1,2 s de latencia
      mediana y el doble de contexto en las consultas que se descomponen.
      Ver §8. *2026-10-12.*
- [x] **C4 (no planificada). Reparto equilibrado de contexto**, construida
      sobre C3 para quitarle el coste de contexto sin perder el reparto entre
      subpreguntas. Desequilibrio de 1,83 a 0,83 al mismo coste que la base.
      **Es la configuración activa por defecto.** Ver §10. *2026-10-16.*

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

El 9 de octubre, a las siete preguntas del tutor, el proyecto respondía
*"implementado, sin medir"* en casi todas. Al 19 de octubre, con los bloques A,
B y C cerrados o en curso, las respuestas son:

| Pregunta | Respuesta al 19 de octubre |
|---|---|
| ¿Control de alucinaciones? | Tres mecanismos, medidos con RAGAS. *Faithfulness* 0,888 en la línea base y 0,946 con reordenado, sobre 12 preguntas con respuesta en el corpus. Abstención 6/6 correcta, 0 indebidas. |
| ¿Pruebas con Langfuse y dataset? | Sí. 18 preguntas viven como *dataset* dentro de Langfuse y se ejecutaron contra el RAG como una *run* enlazada a sus trazas. |
| ¿Qué tipos de preguntas admite? | Tres categorías medidas —literal, compuesta, sin respuesta— y una taxonomía explícita de lo que no admite por diseño. |
| ¿Reranking? | Medido contra la línea base: mejora hit@3 y MRR, no mejora RAGAS, cuesta ×3,7. Disponible, no activo. |
| ¿Híbrido? | Medido contra la línea base: mejora hit@1 y *faithfulness*, pero empeora la cobertura de preguntas compuestas (48 %→30 %). Se probó además una sexta configuración que lo combina con el reparto equilibrado: mejora el reparto pero no recupera del todo esa cobertura. Disponibles ambas, ninguna activa. |
| ¿Varias preguntas a la vez? | Resuelto: descomposición sin tope (cobertura 48 %→88 %, coste doble) y reparto equilibrado (cobertura 52 %, desequilibrio 1,83→0,83, sin coste extra) — esta última es la activa. El híbrido, evaluado como alternativa, retrocede aquí al 30 %. |

Esa es la diferencia entre un proyecto que funciona y un proyecto que se
defiende.
