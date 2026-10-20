# Registro de tutorías

Acta de cada sesión con el tutor, las observaciones recibidas y el plan de
acción derivado. Se actualiza el mismo día de cada reunión, mientras está
fresca, y cada vez que se cierra alguno de los puntos pendientes.

*Última actualización: 12 de octubre de 2026.* El acta de cada reunión se
conserva tal como se escribió; lo que se actualiza es el estado de resolución,
la ficha técnica y el plan.

> **Fecha límite de entrega: `⟨PENDIENTE — confirmar⟩`.** El calendario de más
> abajo está anclado al 9 de octubre de 2026 y asume unas seis semanas. Si la
> fecha real es otra, hay que recalcularlo.

---

## Tutoría 1 — viernes 9 de octubre de 2026

**Formato:** primera reunión, 15 minutos. Resolución de dudas y muestra de
avances. No era entrega ni evaluación.

**Qué se mostró:** el chat en funcionamiento con el asistente EBIS. Una pregunta
real (*"¿qué es geometría semántica?"*), las cinco fuentes consultadas con su
porcentaje de relevancia (59 %, 58 %, 58 %, 50 %, 49 %) y el coste de la
consulta (0,000261 USD).

### Observación principal

El tutor tiene experiencia en RAG y orientó la conversación a la arquitectura y
la evaluación, no a la funcionalidad. **La aplicación funciona, pero el proyecto
no sabía describirse con el vocabulario del campo ni demostrar su calidad con
métricas.** Esa es la brecha a cerrar.

### Preguntas que el proyecto no pudo responder

1. ¿Qué tipos de preguntas admite este RAG?
2. ¿Se pueden hacer varias preguntas?
3. ¿Qué arquitectura RAG se implementó?
4. ¿Es un RAG híbrido?
5. ¿Qué técnica de recuperación se aplicó?
6. ¿Se hicieron pruebas con Langfuse, con un dataset de 10-20 preguntas
   apuntado contra el RAG?
7. ¿Se aplica un control mínimo de alucinaciones?

### Estado de resolución de las siete — al 12 de octubre de 2026

| # | Pregunta | Estado | Dónde queda respondida |
|---|---|---|---|
| 1 | Tipos de preguntas | **Resuelta y medida** | `DATASET_PREGUNTAS.md`; memoria 5.1. Tres categorías —literal, distribuida y sin respuesta—, con métricas desglosadas por categoría. |
| 2 | Varias preguntas a la vez | **Resuelta e implementada** | Memoria 5.3; `NUCLEO_RAG.md` §8. Era un defecto medido (48 % de cobertura); con descomposición de consultas sube al 88 %. |
| 3 | Arquitectura RAG | **Resuelta** | `ARQUITECTURAS_RAG.md`. Naive RAG con filtro por umbral, más una intervención previa a la recuperación en la clase avanzada. |
| 4 | ¿Híbrido? | **Respondida: no** | Ficha técnica de abajo. Sin implementar; pendiente de que el tutor aclare si es obligatorio. |
| 5 | Técnica de recuperación | **Resuelta** | `RAG_PIPELINE.md` §6. Densa por coseno, `top_k=5`, umbral 0,30 revalidado sobre el índice vigente. |
| 6 | Langfuse + dataset apuntado al RAG | **Resuelta** | `OBSERVABILIDAD.md` y `experimentos/langfuse_dataset.py`. Las 18 preguntas viven como *dataset* dentro de Langfuse y se ejecutaron contra el RAG como una *run* enlazada, no solo trazas sueltas. *2026-10-18.* |
| 7 | Control de alucinaciones | **Resuelta y medida** | Memoria 5.3 y 5.4. `faithfulness` 0,888, abstención correcta 6/6 y ninguna abstención indebida. |

**El hallazgo que no se esperaba.** Al medir la abstención se vio que el umbral
de relevancia solo produjo **2 de las 6** abstenciones correctas. En las otras
cuatro la búsqueda devolvió cinco fragmentos por encima de 0,30 —uno a 0,534,
más alto que el de varias preguntas legítimas— y fue el *prompt* restrictivo el
que se abstuvo. Los dos mecanismos se reparten el trabajo: un sistema que
confiara solo en el umbral habría respondido a las tres preguntas tangenciales.
La puntuación de similitud mide proximidad temática, no capacidad de responder.

---

### Las respuestas correctas — ficha técnica del proyecto

Verificadas contra el código. Deben poder recitarse en cualquier reunión. La
columna de la derecha señala lo que ha cambiado desde la reunión.

| Pregunta | Respuesta al 12 de octubre de 2026 | Cambio |
|---|---|---|
| **Arquitectura** | Naive RAG con filtro post-recuperación por umbral. Existe además `RAGServiceAvanzado`, que añade una intervención previa a la recuperación. | ⬆ |
| **Técnica de recuperación** | Densa, por similitud coseno (`metric="cosine"` en Pinecone), `top_k=5`, con descarte por umbral de 0,30 **revalidado** sobre el índice por oraciones. | ⬆ |
| **¿Híbrido?** | No. Densa pura, sin componente léxico (BM25). | = |
| **¿Reranking?** | No implementado. Descartado por coste por consulta. | = |
| **¿Reescritura de consulta?** | **Sí, en la clase avanzada:** descomposición de consultas (*multi-query*). La básica sigue vectorizando el mensaje tal cual. Sin expansión ni HyDE. | ⬆ |
| **Fragmentación** | Por oraciones, objetivo de 1.000 caracteres, **sin solapamiento**. | = |
| **Conversación** | Multiturno: se envían los 20 últimos mensajes al modelo. | = |
| **Evaluación** | Chunking, umbral, preguntas compuestas, recuperación por frase ancla y generación con RAGAS. **Cinco experimentos, todos reproducibles.** | ⬆ |
| **Control de alucinaciones** | Los mismos tres mecanismos, ahora **medidos**: `faithfulness` 0,888 y abstención correcta 6/6, sin abstenciones indebidas. | ⬆ |
| **Observabilidad** | Langfuse sobre OpenTelemetry, cinco observaciones por consulta. Dependencia opcional. | ✚ |

> La versión de esta ficha verificada el 9 de octubre decía «sin multi-query»,
> «la evaluación de recuperación y alucinaciones, pendientes» y «ninguno está
> medido». Las tres han dejado de ser ciertas.

### Taxonomía de preguntas del sistema

**Admite:** definiciones y explicaciones; hechos concretos contenidos en un
fragmento; síntesis de varios fragmentos sobre un mismo tema.

**No admite, por diseño:**

- Conteos y agregaciones ("¿cuántos documentos hay sobre X?"): el sistema no ve
  el corpus, ve cinco fragmentos.
- Comparaciones exhaustivas entre documentos.
- Preguntas sobre el conjunto de la documentación.
- Preguntas por la ausencia ("¿qué temas no se cubren?").
- Aritmética o razonamiento temporal sobre los datos.

### Dos limitaciones detectadas el mismo día

**Preguntas compuestas.** El mensaje completo se convierte en un único vector.
Ante *"¿qué es un VAE y cómo se entrena un transformer?"*, el vector resultante
no se aproxima bien a ninguno de los dos temas y la recuperación se degrada.
No estaba documentado. **Cerrada el 12 de octubre:** medido el defecto
(48 % de cobertura conjunta) e implementada la descomposición de consultas,
que lo lleva al 88 % sin que ninguna de las seis parejas empeore.

**Alucinación de alcance.** A la pregunta *"dame un resumen de la documentación
disponible"*, el sistema respondió *"la documentación disponible se compone
de…"* habiendo visto únicamente cinco fragmentos. No inventó contenido, pero
sobredeclaró su cobertura. **Documentada en la memoria 5.4** como primero de
los dos modos de alucinación analizados. **Sigue sin corregirse:** exigiría
reconocer las preguntas de alcance global y responderlas con metadatos del
corpus en lugar de con fragmentos recuperados.

### Preguntas abiertas para el tutor

> ⚠️ **Al 12 de octubre el correo sigue sin enviarse.** Las preguntas 1 y 2
> bloquean las dos únicas mejoras que quedan del plan —reranking y RAG
> híbrido—, porque de su respuesta depende si hay que implementarlas o basta
> con conocerlas y justificar su ausencia.

Enviar por correo mientras la reunión esté reciente:

1. La lista de temas (Langfuse, RAGAS, reranking, híbrido), ¿es de
   implementación obligatoria o de conocimiento y mención en la memoria?
2. ¿Hay alguno imprescindible frente a los demás?
3. ¿Se pueden citar frases literales del material docente de EBIS en un anexo?
   (Bloquea el dataset.)
4. ¿Qué capítulos pesan más en la rúbrica?
5. ¿La demo de la defensa es en vivo o grabada?

---

## Plan de acción

**Principio que ordena el resto:** RAGAS no es un punto más de la lista, es el
instrumento de medida. Sin línea base, ni el reranking ni el híbrido son
demostrables, solo afirmables. El orden **dataset → medición → mejoras** no es
negociable.

**Regla de reparto:** cada implementación se documenta el mismo día en que se
cierra, aunque sea en borrador. No se acumula código para escribir al final.

### Inmediato — fin de semana del 10-11 de octubre

- [x] **Dataset de evaluación.** 18 preguntas —8 literal, 4 distribuida, 6 sin
      respuesta—, 17 frases ancla verificadas como únicas en el corpus y 12
      respuestas de referencia. Redactado a mano, no generado por un modelo.
      *2026-10-11.*
- [ ] Correo al tutor con las cinco preguntas abiertas.

### Semana 1 — 12 al 18 de octubre

- [x] **Langfuse** instrumentado sobre el pipeline RAG, como dependencia
      opcional: con `LANGFUSE_ENABLED=false` el sistema funciona igual.
      *2026-10-09.*
- [x] **Dataset cargado en Langfuse y apuntado contra el RAG.** Las 18
      preguntas viven ahora como *dataset* dentro de Langfuse
      («knowledgespace-conjunto-referencia») y se ejecutaron contra la
      configuración base como una *run* con nombre, 18 ítems enlazados a sus
      trazas. Script: `experimentos/langfuse_dataset.py`. El coste de esa
      corrida no queda en `cost_tracking` —decisión deliberada, ver
      `OBSERVABILIDAD.md`— pero sí en la propia interfaz de Langfuse.
      *2026-10-18.*
- [x] **RAGAS: línea base.** `context_precision` 0,912, `context_recall` 0,896,
      `faithfulness` 0,888 y `answer_relevancy` 0,822 sobre 12 preguntas, en un
      entorno aislado del de la aplicación. *2026-10-12.*
- [x] Redactadas **5.2 Métricas empleadas** y **6.3 Observabilidad**.
      *2026-10-12.*

### Semana 2 — 19 al 25 de octubre

- [ ] **Reranking** implementado y medido contra la misma línea base.
- [x] Experimento de **preguntas compuestas**: 6 parejas, cobertura conjunta
      del 48 %. *2026-10-09.* Y la mejora que lo corrige, medida: 88 %.
      *2026-10-12.*
- [x] **Umbral de relevancia revalidado** sobre el índice por oraciones. Sigue
      dentro de la banda, pero esta se estrechó un 16 % y el margen frente al
      ruido cayó un 41 %. *2026-10-09.*
- [x] Redactado **5.3 Resultados**, con los cinco experimentos y sus tablas.
      El capítulo 5 queda cerrado: 5.709 palabras, sin marcadores pendientes.
      *2026-10-12.*

### Semana 3 — 26 de octubre al 1 de noviembre

- [ ] **RAG híbrido**, o decisión documentada de dejarlo como trabajo futuro.
- [ ] Redactar los capítulos **3** (arquitectura, selección tecnológica y
      análisis de costes) y **4** (implementación).

### Semanas 4 a 6 — 2 de noviembre en adelante

- [ ] Capítulo **2** (estado del arte).
- [ ] Capítulos **6, 7 y 8**.
- [ ] Capítulo **9 — bibliografía**. *Abrir el archivo ya: es lo único que no se
      puede acelerar al final, y hoy tiene cero referencias.*
- [ ] Anexos y manual de usuario.
- [ ] Ensayo de la defensa.

---

## Estado

| | 9 de octubre | 12 de octubre |
|---|---|---|
| Memoria | 3.331 palabras | **8.692** de las ~15.000-20.000 necesarias |
| Escrito | Capítulo 1; secciones 5.1, 5.3 y 5.4 | Capítulo 1; **capítulo 5 completo**; 6.3 y 7.1 |
| Vacío | Capítulos 2, 3, 4, 6, 7, 8, 9 y 10 | Capítulos 2, 3, 4, 8 y 9; parte de 6, 7 y 10 |
| Bibliografía | 0 referencias | **0 referencias** de las 15-25 requeridas |
| Tests | 21, en verde | **35**, en verde |
| Índice vectorial | 4 espacios de nombres, 297 vectores, desincronizado | **1 espacio, 87 vectores**, coincidiendo con la base de datos |

**Medido y defendible al 12 de octubre** —cinco experimentos, todos
reproducibles desde `api/experimentos/`:

| | Resultado |
|---|---|
| Calidad estructural del *chunking* | Cortes a mitad de palabra del 79,2 % al 0 %; 19 % menos de texto indexado |
| Umbral de relevancia | Ruido 0,258 / señal 0,393; el 0,30 sigue dentro de la banda |
| Preguntas compuestas | Cobertura conjunta del 48 %, con los 30 fragmentos por encima del umbral |
| Recuperación por frase ancla | hit@3 0,50 y MRR 0,394; literal 0,525 frente a distribuida 0,133 |
| Abstención | 6/6 correctas, 0 indebidas; el umbral produjo 2 y el *prompt* 4 |
| Generación (RAGAS) | `faithfulness` 0,888, `context_precision` 0,912 |
| Latencia | p50 2,41 s, p95 4,26 s |
| Coste por consulta | 0,000431 USD |
| Descomposición de consultas | Cobertura del 48 % al 88 %; +1,2 s de latencia mediana |

**Lo que falta, por orden de urgencia:**

1. **El correo al tutor.** Bloquea reranking y RAG híbrido, las dos únicas
   mejoras que quedan del plan.
2. **La memoria.** Faltan los capítulos 2, 3, 4, 8 y 9. El código ya no es el
   cuello de botella.
3. **La bibliografía.** Cero referencias desde el 9 de octubre. Es lo único que
   no se puede acelerar al final.
