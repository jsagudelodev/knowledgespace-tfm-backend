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

## 1. Arquitectura y recuperación

| Pieza | Estado | Evidencia |
|---|---|---|
| Recuperación densa, similitud coseno, `top_k=5` | 🟡 | `pinecone_service.py` (`metric="cosine"`), `rag_service.py:76` |
| Umbral de relevancia `0.30` | 🟡 | `rag_service.py:18,79` |
| Fragmentación por oraciones, sin solapamiento | ✅ | `pdf_service.py`, `resultados/chunking_2026-10-07.json` |
| Conversación multiturno (20 mensajes) | 🟡 | `chat.py:61` |
| Metadatos para citar fuentes | 🟡 | `documents.py:134` |
| Aislamiento multi-tenant por *namespace* | 🟡 | `pinecone_service.py`, `tests/test_pinecone_namespace.py` |
| Reescritura o expansión de consulta | ❌ | La pregunta se vectoriza tal cual |
| Reranking | ❌ | Evaluado y descartado, sin medición que lo respalde |
| RAG híbrido (denso + BM25) | ❌ | — |

**Por qué el umbral está en 🟡 y no en ✅.** El `0.30` sí se midió, pero sobre un
índice construido con **fragmentación por caracteres**, antes de que existiera
la división por oraciones. Al cambiar la fragmentación cambia la distribución de
similitudes. Hay evidencia de que se movió: en una consulta real del 8 de
octubre, el quinto fragmento puntuó **0,37**, por debajo del `0,389` que la
medición original fijó como mínimo de un fragmento legítimo.

Mientras no se revalide, los capítulos 3 y 4 afirman que el umbral está
justificado por medición mientras el capítulo 5 defiende la otra estrategia de
fragmentación. Es una incoherencia que un revisor cruza en un minuto.

---

## 2. Evaluación

| Pieza | Estado |
|---|---|
| Calidad estructural de la fragmentación | ✅ Medida el 2026-10-07, reproducida idéntica el 2026-10-09 |
| Coste por consulta | ✅ Medido el 2026-10-08, registros 71-80 |
| Dataset de evaluación | ❌ |
| Langfuse | ❌ |
| RAGAS | ❌ |
| Métricas de recuperación (`hit@k`, MRR) | ❌ |
| Latencia p50 / p95 | ❌ |

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

## 4. Observabilidad

| Pieza | Estado |
|---|---|
| Seguimiento de coste por solicitud | ✅ |
| Trazas del pipeline RAG | ❌ **Cero** |
| Langfuse | ❌ |

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

## Bloque A — Instrumentar y medir *(prioridad máxima)*

- [ ] **A1. Dataset de evaluación.** 15-20 preguntas con respuesta de
      referencia, frase ancla y tipo. Repartidas según la taxonomía de
      `TUTORIAS.md`, **incluyendo preguntas sin respuesta en el corpus y al
      menos una compuesta**.
- [ ] **A2. Langfuse.** Instrumentar el pipeline: la consulta, el vector, los
      fragmentos recuperados con su puntuación, el contexto construido y la
      respuesta. Resuelve a la vez la carencia de trazas.
- [ ] **A3. Dataset cargado en Langfuse** y apuntado contra el RAG.
- [ ] **A4. RAGAS — línea base.** *Faithfulness*, *answer relevancy*, *context
      precision* y *context recall* sobre la configuración actual.
- [ ] **A5. Latencia p50/p95**, que sale gratis de las trazas de A2.

## Bloque B — Cerrar los huecos del núcleo

- [ ] **B1. Revalidar el umbral `0.30`** sobre el índice reconstruido con
      división por oraciones. Repetir las tres familias de consultas de
      `RAG_PIPELINE.md` §6. Cierra la incoherencia entre capítulos.
- [ ] **B2. Tests del umbral y de la abstención.** Que el sistema devuelva la
      frase exacta cuando ningún fragmento supera el umbral, y que descarte los
      que no llegan. Son tests de lógica pura: rápidos y sin coste.
- [ ] **B3. Experimento de preguntas compuestas.** Comparar la recuperación de
      una pregunta doble frente a las dos por separado. Diez minutos, y
      documenta una limitación real.
- [ ] **B4. Documentar la alucinación de alcance** como caso analizado del
      capítulo 5.

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
