# Registro de tutorías

Acta de cada sesión con el tutor, las observaciones recibidas y el plan de
acción derivado. Se actualiza el mismo día de cada reunión, mientras está
fresca, y cada vez que se cierra alguno de los puntos pendientes.

*Última actualización: 19 de octubre de 2026.* El acta de cada reunión se
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
| 2 | Varias preguntas a la vez | **Resuelta e implementada** | Memoria 5.3; `NUCLEO_RAG.md` §8 y §10. Era un defecto medido (48 % de cobertura). La descomposición sin tope lo sube al 88 %, pero enviando el doble de contexto; la configuración realmente activa (reparto equilibrado) llega al 52 %, sin coste extra — es la cifra que corresponde citar si preguntan por el sistema en producción, no el 88 %. |
| 3 | Arquitectura RAG | **Resuelta** | `ARQUITECTURAS_RAG.md`. Naive RAG con filtro por umbral, más una intervención previa a la recuperación en la clase avanzada. |
| 4 | ¿Híbrido? | **Resuelta** | `NUCLEO_RAG.md` §11. Implementado y medido el 19-10: mejora hit@1 (0,25→0,42) y *faithfulness* (0,939→0,965), pero empeora la cobertura de preguntas compuestas (48 %→30 %). Se probó también combinarlo con el reparto equilibrado (§12): mejora el reparto pero no recupera del todo esa cobertura (37 %). **Decisión: ninguna de las dos variantes se activa**, documentadas como alternativa. |
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

| Pregunta | Respuesta al 19 de octubre de 2026 | Cambio |
|---|---|---|
| **Arquitectura** | Naive RAG con filtro post-recuperación por umbral como línea base, y **cinco variantes más** conviviendo con ella, seleccionables por variable de entorno sin tocar código (patrón Factory sobre Template Method): descomposición sin tope, descomposición con reparto equilibrado (la activa por defecto), reordenado, densa+léxica, y una combinación de las dos últimas. | ⬆ |
| **Técnica de recuperación** | Densa, por similitud coseno (`metric="cosine"` en Pinecone), `top_k=5`, con descarte por umbral de 0,30 **revalidado** sobre el índice por oraciones. La variante híbrida añade BM25 fusionado por posición (RRF), filtrando por el mismo umbral antes de fusionar. | ⬆ |
| **¿Híbrido?** | **Medido y descartado por ahora.** `RAGServiceHibrido`, hit@1 0,25→0,42 y *faithfulness* 0,939→0,965, pero empeora la cobertura de preguntas compuestas (48 %→30 %). Combinado con el reparto equilibrado (`RAGServiceDescomposicionHibrida`) mejora el reparto pero no recupera esa cobertura del todo (37 %) y es la configuración más lenta medida. Ninguna de las dos activa. | ⬆ |
| **¿Reranking?** | **Implementado y medido el 14-10.** Mejora la recuperación (hit@3 de 0,50 a 0,667, MRR de 0,394 a 0,447), pero las cuatro métricas de generación de RAGAS se mueven dentro del margen de ruido del juez, y multiplica el coste por consulta ×3,7. Disponible, **no activo por defecto**. | ⬆ |
| **¿Reescritura de consulta?** | **Sí, en dos variantes:** descomposición de consultas (*multi-query*) sin tope, y con reparto equilibrado entre subpreguntas (la activa). La línea base sigue vectorizando el mensaje tal cual. Sin expansión ni HyDE. | ⬆ |
| **Fragmentación** | Por oraciones, objetivo de 1.000 caracteres, **sin solapamiento**. | = |
| **Conversación** | Multiturno: se envían los 20 últimos mensajes al modelo. | = |
| **Evaluación** | Chunking, umbral, preguntas compuestas, recuperación por frase ancla, generación con RAGAS (línea base, reordenado, híbrido y la combinación de híbrido con reparto equilibrado). **Ocho experimentos, todos reproducibles.** | ⬆ |
| **Control de alucinaciones** | Los mismos tres mecanismos, medidos: `faithfulness` 0,888 en la base y 0,946 con reordenado; abstención correcta 6/6 en las cinco configuraciones donde se ha medido, sin abstenciones indebidas. | = |
| **Observabilidad** | Langfuse sobre OpenTelemetry, cinco observaciones por consulta. Dependencia opcional. El dataset de 18 preguntas vive dentro de Langfuse como *run* enlazada a sus trazas. | ⬆ |
| **Pruebas** | 117 tests en verde, 18 archivos. La mayoría apunta directamente a la aportación central: las seis estrategias de recuperación, el umbral y la abstención. | ⬆ |

> La versión de esta ficha verificada el 9 de octubre decía «sin multi-query»,
> «la evaluación de recuperación y alucinaciones, pendientes» y «ninguno está
> medido». La del 12 de octubre daba el reranking y el híbrido por no
> implementados. Ninguna de las dos sigue siendo cierta.

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
(48 % de cobertura conjunta) e implementada la descomposición de consultas, que
lo lleva al 88 % sin que ninguna de las seis parejas empeore, aunque enviando
el doble de contexto al modelo. **La configuración que de verdad queda activa
el 16 de octubre** (reparto equilibrado, sin ese coste extra) llega al 52 % —
la cifra a citar si preguntan por el sistema en producción, no el 88 %, que
corresponde a la variante sin tope.

**Alucinación de alcance.** A la pregunta *"dame un resumen de la documentación
disponible"*, el sistema respondió *"la documentación disponible se compone
de…"* habiendo visto únicamente cinco fragmentos. No inventó contenido, pero
sobredeclaró su cobertura. **Documentada en la memoria 5.4** como primero de
los dos modos de alucinación analizados. **Sigue sin corregirse:** exigiría
reconocer las preguntas de alcance global y responderlas con metadatos del
corpus en lugar de con fragmentos recuperados.

### Preguntas abiertas para el tutor

> 🟡 **Aclarado el 22 de octubre — no es una autorización institucional
> explícita, es una circunstancia.** El máster describe el TFM como "de
> desarrollo grupal", pese a lo cual este se hace en solitario. Lo que
> ocurrió: la asesora del máster indicó vincularse al grupo de WhatsApp
> para formar equipo; nadie respondió ni apareció; ante eso, decidió
> continuar solo. No hay una confirmación explícita y por escrito de que
> EBIS acepte la entrega individual por esta razón — es una decisión propia
> ante la falta de respuesta del canal oficial.
>
> **Recomendación: dejarlo documentado, no solo decidido.** Conviene (a)
> mandar un correo breve a la asesora o al tutor dejando constancia de que
> se intentó formar grupo por el canal indicado y nadie respondió, aunque
> sea después de los hechos, para tener un rastro escrito; y (b) mencionarlo
> en una línea de la introducción o los preliminares de la memoria, para que
> el corrector no se pregunte por qué no hay reparto de responsabilidades
> entre varios integrantes sin que nadie se lo haya explicado.
>
> ⚠️ **Al 12 de octubre el correo con las otras cinco preguntas seguía sin
> enviarse.** Las preguntas 1 y 2 bloquean las dos únicas mejoras que quedan
> del plan —reranking y RAG híbrido—, porque de su respuesta depende si hay
> que implementarlas o basta con conocerlas y justificar su ausencia. Ambas
> ya se implementaron y midieron de todos modos (ver §11 y §12 de
> `NUCLEO_RAG.md`), así que esta pregunta concreta perdió urgencia; las
> demás siguen abiertas.

Enviar por correo mientras la reunión esté reciente:

0. ~~El TFM es de desarrollo grupal y se está entregando en solitario por no
   haber encontrado grupo. ¿Es aceptable así?~~ — **aclarado el 2026-10-22,
   pero sin confirmación institucional por escrito.** Se intentó formar
   grupo vía el canal que indicó la asesora (grupo de WhatsApp); nadie
   respondió; se decidió continuar solo. Pendiente, si no se ha hecho ya:
   un correo breve dejando constancia de esto por escrito.
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

- [x] **Reranking** implementado y medido contra la misma línea base: hit@3
      0,50→0,667, MRR 0,394→0,447; RAGAS dentro del margen de ruido; coste
      ×3,7. Decisión: disponible, no activo. *2026-10-14.*
- [x] **Reparto equilibrado de contexto** (no planificada): cierra el coste de
      contexto que dejaba abierto la descomposición sin tope. Desequilibrio de
      1,83 a 0,83 al mismo coste que la base. **Es la configuración activa por
      defecto.** *2026-10-16.*
- [x] Experimento de **preguntas compuestas**: 6 parejas, cobertura conjunta
      del 48 %. *2026-10-09.* Y la mejora que lo corrige, medida: 88 %.
      *2026-10-12.*
- [x] **Umbral de relevancia revalidado** sobre el índice por oraciones. Sigue
      dentro de la banda, pero esta se estrechó un 16 % y el margen frente al
      ruido cayó un 41 %. *2026-10-09.*
- [x] Redactado **5.3 Resultados**, con los cinco experimentos y sus tablas.
      El capítulo 5 queda cerrado. *2026-10-12.*

### Semana 3 — 26 de octubre al 1 de noviembre

- [x] **RAG híbrido**: implementado y medido el 19-10 contra la línea base.
      Mejora hit@1 y *faithfulness*, pero empeora la cobertura de preguntas
      compuestas (48 %→30 %). Se probó además combinarlo con el reparto
      equilibrado: mejora el reparto pero no recupera esa cobertura del todo
      (37 %). **Decisión: ninguna de las dos variantes se activa.**
      `NUCLEO_RAG.md` §11 y §12.
- [x] Redactados los capítulos **3** (requisitos, arquitectura, selección
      tecnológica y análisis de costes — 3.557 palabras) y **4**
      (implementación — 2.524 palabras). *Verificado en el documento al
      19-10; no estaba previsto cerrarlos hasta esta semana y ya lo están.*

### Semanas 4 a 6 — 2 de noviembre en adelante

- [ ] Capítulo **2** (estado del arte). El hueco más grande que queda en la
      memoria; exige lectura, no redacción sobre código existente.
- [ ] **6.2** (UX y usabilidad) y **7.2** (riesgos, ética y mitigaciones) — 6.1,
      6.3 y 7.1 ya están escritos.
- [ ] Capítulo **8** (conclusiones y trabajo futuro).
- [ ] Capítulo **9 — bibliografía**. 22-23 referencias ya compuestas en
      `BIBLIOGRAFIA.md`; **falta verificarlas una a una y transferirlas** al
      documento. El capítulo sigue vacío en el `.docx`.
- [ ] Anexos y manual de usuario — el manual no existe todavía en ningún repo.
- [ ] Ensayo de la defensa.

---

## Estado

| | 9 de octubre | 12 de octubre | 19 de octubre |
|---|---|---|---|
| Memoria | 3.331 palabras | 8.692 de las ~15.000-20.000 necesarias | **17.445**, dentro del rango objetivo |
| Escrito | Capítulo 1; secciones 5.1, 5.3 y 5.4 | Capítulo 1; capítulo 5 completo; 6.3 y 7.1 | **Capítulos 1, 3, 4 y 5 completos**; 6.1, 6.3 y 7.1 |
| Vacío | Capítulos 2, 3, 4, 6, 7, 8, 9 y 10 | Capítulos 2, 3, 4, 8 y 9; parte de 6, 7 y 10 | **Capítulos 2, 8, 9 y 10; 6.2 y 7.2** |
| Bibliografía | 0 referencias | 0 referencias de las 15-25 requeridas | **22-23 referencias compuestas** en `BIBLIOGRAFIA.md`, **ninguna verificada ni transferida** al capítulo 9 del documento |
| Tests | 21, en verde | 35, en verde | **117**, en verde, 18 archivos |
| Índice vectorial | 4 espacios de nombres, 297 vectores, desincronizado | 1 espacio, 87 vectores, coincidiendo con la base de datos | Sin cambios desde el 9-10 |

**Medido y defendible al 19 de octubre** —ocho experimentos, todos
reproducibles desde `api/experimentos/`:

| | Resultado |
|---|---|
| Calidad estructural del *chunking* | Cortes a mitad de palabra del 79,2 % al 0 %; 19 % menos de texto indexado |
| Umbral de relevancia | Ruido 0,258 / señal 0,393; el 0,30 sigue dentro de la banda |
| Preguntas compuestas (línea base) | Cobertura conjunta del 48 %, con los 30 fragmentos por encima del umbral |
| Recuperación por frase ancla | hit@3 0,50 y MRR 0,394; literal 0,525 frente a distribuida 0,133 |
| Abstención (línea base) | 6/6 correctas, 0 indebidas; el umbral produjo 2 y el *prompt* 4 |
| Generación, línea base (RAGAS) | `faithfulness` 0,888, `context_precision` 0,912 |
| Latencia (línea base) | p50 2,41 s, p95 4,26 s |
| Coste por consulta | 0,000431 USD |
| Descomposición de consultas (sin tope) | Cobertura del 48 % al 88 %; +1,2 s de latencia mediana; coste doble de contexto |
| Reparto equilibrado (activo por defecto) | Cobertura 52 %, desequilibrio de 1,83 a 0,83, mismo coste que la base |
| Reordenado (reranking) | hit@3 0,50→0,667; RAGAS dentro del margen de ruido; coste ×3,7 — no activo |
| Híbrido (denso + BM25) | hit@1 0,25→0,42, *faithfulness* 0,939→0,965; empeora preguntas compuestas (48 %→30 %) — no activo |
| Descomposición + híbrida | Mejor hit@3/MRR medidos (0,67 / 0,544) y mejor reparto (0,67); no recupera del todo la cobertura perdida por el híbrido (37 %); la más lenta de las seis — no activa |

**Lo que falta, por orden de urgencia:**

0. **Dejar constancia por escrito de por qué el TFM se entrega en
   solitario.** Aclarado el 22 de octubre: se intentó formar grupo por el
   canal que indicó la asesora (WhatsApp), nadie respondió, se decidió
   continuar solo — pero eso no es lo mismo que una autorización
   institucional explícita. Un correo breve dejando esto documentado, más
   una línea en la introducción de la memoria, cierra el riesgo de que el
   corrector se lo pregunte sin que quede una respuesta ya dada.
1. ~~Verificar la bibliografía~~ — **resuelto el 20 de octubre.** 22
   referencias verificadas, formato y las dos citas con *venue* dudoso
   decididos. Ver `BIBLIOGRAFIA.md`. Queda pendiente solo el trabajo mecánico
   de transcribirla al capítulo 9 del `.docx`.
2. **Confirmar el estado del correo al tutor** (las preguntas 1-5 de la lista
   de abajo). Al 12 de octubre seguía sin enviarse y bloqueaba la decisión
   sobre reranking e híbrido. Ambos se implementaron y midieron igualmente
   desde entonces; falta registrar aquí si el tutor llegó a responder y qué
   dijo.
3. **La memoria.** Faltan los capítulos 2, 8, 9 y 10, y las secciones 6.2 y
   7.2. El capítulo 2 se empezó el 20 de octubre con el método de
   pregunta-respuesta (no generado de una sola vez, por la advertencia de la
   rúbrica contra texto sin adaptación propia) y quedó pausado en la sección
   2.1, a la espera de una lectura activa del paper de Vaswani et al. El
   código ya no es el cuello de botella — lleva varios días siéndolo cada vez
   menos.

El bloque C del plan —mejoras del pipeline RAG, cada una medida contra la
línea base— **queda completo el 19 de octubre**: reordenado, híbrido,
descomposición con reparto equilibrado y la combinación de las dos últimas,
las cuatro medidas y con decisión documentada.
