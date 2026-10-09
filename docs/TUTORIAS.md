# Registro de tutorías

Acta de cada sesión con el tutor, las observaciones recibidas y el plan de
acción derivado. Se actualiza el mismo día de cada reunión, mientras está
fresca.

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

### Las respuestas correctas — ficha técnica del proyecto

Verificadas contra el código el 9 de octubre de 2026. Deben poder recitarse en
cualquier reunión.

| Pregunta | Respuesta |
|---|---|
| **Arquitectura** | Naive RAG con filtro post-recuperación por umbral de relevancia. |
| **Técnica de recuperación** | Densa, por similitud coseno (`metric="cosine"` en Pinecone), `top_k=5`, con descarte por umbral de 0,30. |
| **¿Híbrido?** | No. Densa pura, sin componente léxico (BM25). |
| **¿Reranking?** | No implementado. Evaluado y descartado por coste por consulta. |
| **¿Reescritura de consulta?** | No. La pregunta del usuario se vectoriza tal cual: sin expansión, sin multi-query, sin HyDE. |
| **Fragmentación** | Por oraciones, objetivo de 1.000 caracteres, **sin solapamiento**. |
| **Conversación** | Multiturno: se envían los 20 últimos mensajes al modelo. |
| **Evaluación** | Medida la calidad estructural del chunking. La de recuperación y la de alucinaciones, pendientes. |
| **Control de alucinaciones** | Tres mecanismos —umbral, *prompt* restrictivo que obliga a responder "No encontré información sobre este tema en los documentos de la empresa", y registro de *knowledge gaps*—. **Ninguno está medido.** |

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
No estaba documentado. Es un experimento de diez minutos.

**Alucinación de alcance.** A la pregunta *"dame un resumen de la documentación
disponible"*, el sistema respondió *"la documentación disponible se compone
de…"* habiendo visto únicamente cinco fragmentos. No inventó contenido, pero
sobredeclaró su cobertura. Es el tipo de fallo que RAGAS detecta y debe entrar
en el capítulo 5.

### Preguntas abiertas para el tutor

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

- [ ] **Dataset de evaluación**, 15-20 preguntas, con las columnas que RAGAS
      necesita: pregunta, respuesta de referencia, frase ancla, tipo.
      Repartidas entre los tipos de la taxonomía, **incluidas las que el
      sistema no debería poder responder**.
- [ ] Correo al tutor con las cinco preguntas abiertas.

### Semana 1 — 12 al 18 de octubre

- [ ] **Langfuse** instrumentado sobre el pipeline RAG.
- [ ] Dataset cargado en Langfuse y apuntado contra el RAG.
- [ ] **RAGAS: línea base.** Faithfulness, answer relevancy, context precision
      y context recall sobre la configuración actual.
- [ ] Redactar **5.2 Métricas empleadas** y la sección **6.3 Observabilidad**.

### Semana 2 — 19 al 25 de octubre

- [ ] **Reranking** implementado y medido contra la misma línea base.
- [ ] Experimento de **preguntas compuestas**.
- [ ] **Revalidación del umbral de relevancia** sobre el índice con división por
      oraciones (el 0,30 se midió con chunking por caracteres).
- [ ] Redactar **5.3 Resultados** con la tabla comparativa.

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

## Estado al 9 de octubre de 2026

| | |
|---|---|
| Memoria | 3.331 palabras de las ~15.000-20.000 necesarias |
| Escrito | Capítulo 1 completo; secciones 5.1, 5.3 y 5.4 |
| Vacío | Capítulos 2, 3, 4, 6, 7, 8, 9 y 10 |
| Bibliografía | 0 referencias de las 15-25 requeridas |
| Tests | 21, en verde |
| Medido y defendible | Calidad estructural del chunking (2026-10-07, reproducido idéntico el 2026-10-09) y coste por consulta (2026-10-08) |
