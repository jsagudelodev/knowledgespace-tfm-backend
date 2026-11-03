# Arquitecturas RAG — qué son, qué resuelven y cuáles aplican aquí

Material de estudio y de defensa. Complementa a `RAG_PIPELINE.md`, que
describe **el pipeline concreto de este proyecto**; aquí se describe el abanico
de arquitecturas existentes para poder situar el nuestro y justificar la
elección.

> **Para citar en la memoria:** este documento es una guía de estudio, no una
> fuente. Si una de estas técnicas va al capítulo 2, localiza el trabajo
> original, ábrelo y cítalo tú. Ver la regla en `practica-tfm/GLOSARIO.md`.

---

## 1. El pipeline base y sus cuatro puntos de intervención

Todo sistema RAG hace lo mismo en el fondo:

```
   PREGUNTA
      |
      v
   [1] PRE-RECUPERACIÓN      ¿qué se busca exactamente?
      |
      v
   [2] RECUPERACIÓN          ¿cómo se encuentra?
      |
      v
   [3] POST-RECUPERACIÓN     ¿qué se le pasa al modelo y en qué orden?
      |
      v
   [4] GENERACIÓN            ¿cómo se responde, y qué se hace si no hay base?
      |
      v
   RESPUESTA
```

**Casi todas las arquitecturas que vas a oír nombrar son una intervención en
uno de esos cuatro puntos.** Esa es la clave para entenderlas: no son sistemas
rivales, son mejoras colocadas en sitios distintos de la misma tubería, y en
general se pueden combinar.

---

## 2. RAG básico (*naive RAG*)

El punto de partida: trocear, indexar, recuperar los `k` más similares, meterlos
en el prompt y generar. Sin intervención en ninguno de los cuatro puntos.

| Ventajas | Inconvenientes |
|---|---|
| Simple de implementar y de explicar | Si la recuperación falla, no hay segunda oportunidad |
| Latencia mínima: una búsqueda y una generación | La consulta se usa tal cual la escribió el usuario |
| Coste mínimo y predecible | El orden lo decide la similitud, que no siempre acierta |
| Comportamiento determinista y auditable | No detecta que la evidencia es insuficiente |

**Es la línea base de este proyecto** (`RAGService`), el término de comparación
de todas las mejoras medidas. La configuración activa añade sobre ella una
intervención previa a la recuperación; ver la sección 7.

---

## 3. Intervenciones en PRE-RECUPERACIÓN

Transforman la pregunta antes de buscar. Parten de una observación incómoda: la
pregunta del usuario suele ser un mal vector de búsqueda.

### 3.1 Reescritura de consulta (*query rewriting*)

Un LLM reformula la pregunta antes de buscar: corrige, desambigua y añade
terminología del dominio. Útil cuando el usuario no conoce el vocabulario de los
documentos — justo el caso de alguien que se está capacitando.

- **Ventaja:** acerca el lenguaje del usuario al de los documentos.
- **Coste:** una llamada al LLM antes de buscar (latencia y dinero).
- **Riesgo:** una reescritura mala estropea una consulta que iba bien.

### 3.2 Consulta múltiple y fusión (*multi-query*, *RAG-Fusion*)

Se generan varias reformulaciones de la pregunta, se busca con cada una y se
fusionan los resultados por posición (RRF, el mismo mecanismo del ejercicio 9.0).

- **Ventaja:** no depende de que una única formulación acierte.
- **Coste:** N búsquedas en lugar de una.

### 3.3 Descomposición de consultas ✅ **la configuración activa**

Si la pregunta contiene varias intenciones, se parte en subpreguntas, se busca
por separado y se unen los contextos.

**Esta es la respuesta arquitectónica al problema medido en
`../api/experimentos/medir_preguntas_compuestas.py`:** con preguntas compuestas la
cobertura cae a ~50% porque el mensaje entero se convierte en un único vector
que no representa bien a ninguno de los dos temas. La descomposición ataca
exactamente esa causa.

Implementada en dos variantes. `RAGServiceAvanzado` une todos los fragmentos de
las subpreguntas y sube la cobertura al 88 %, pero manda hasta el doble de
contexto. `RAGServiceCompleto` —la activa, `descomposicion_acotada`— mantiene
los cinco fragmentos de siempre y los reparte por turnos entre subpreguntas:
la cobertura llega al 52 % y el desequilibrio entre temas baja de 1,83 a 0,83,
al mismo coste de contexto que la línea base. Detalle en `NUCLEO_RAG.md` §8 y
§10.

### 3.4 HyDE (*Hypothetical Document Embeddings*)

El LLM redacta primero una respuesta **hipotética** a la pregunta, y se busca
usando el vector de esa respuesta en lugar del de la pregunta.

La intuición: una respuesta se parece más a un párrafo de respuesta que una
pregunta. Pregunta y respuesta tienen formas lingüísticas distintas, y eso
separa sus vectores aunque hablen de lo mismo.

- **Ventaja:** mejora la recuperación cuando pregunta y documento se expresan de
  forma muy distinta.
- **Coste:** una generación antes de buscar.
- **Riesgo:** si el modelo alucina la respuesta hipotética, busca en la
  dirección equivocada con total confianza.

### 3.5 Enrutado de consultas (*query routing*) ✅ **ya presente aquí**

Decidir **a qué índice** va la pregunta antes de buscar.

Este proyecto lo hace de forma explícita: cada asistente tiene su propio
*namespace* y la consulta se resuelve dentro del dominio que le corresponde. No
es un enrutado automático por clasificación, sino declarado por el usuario al
elegir asistente — pero el efecto arquitectónico es el mismo: reducir el espacio
de búsqueda antes de buscar.

---

## 4. Intervenciones en RECUPERACIÓN

### 4.1 Recuperación densa

La de este proyecto: embeddings y similitud coseno. Capta el significado;
falla con lo literal (códigos, siglas, referencias normativas).

### 4.2 Recuperación híbrida (densa + léxica)

Se combina la búsqueda vectorial con una léxica tipo BM25 y se fusionan los
rankings. Desarrollado en el ejercicio `practica-tfm/9.0_rag_hibrido.py`.

- **Ventaja:** cubre el punto ciego del denso con identificadores literales.
- **Coste medido en el 9.0:** puede degradar consultas semánticas, al arrastrar
  coincidencias de palabras comunes poco informativas.
- **En este proyecto:** el modo híbrido nativo de Pinecone exige `dotproduct` y
  el índice usa `cosine`, así que se evitó reindexar: BM25 se calcula en memoria
  (`indice_lexico.py`) y se fusiona con la búsqueda densa por posición (RRF).
  Implementado como `RAGServiceHibrido` y medido el 2026-10-19: hit@1 de 0,25 a
  0,42 y fidelidad de 0,939 a 0,965, pero la cobertura de preguntas de dos
  temas cae del 48 % al 30 %. Combinado con el reparto equilibrado
  (`RAGServiceDescomposicionHibrida`) llega al 37 % y es la configuración más
  lenta. **Medido, no activo.** Detalle en `NUCLEO_RAG.md` §11 y §12.

### 4.3 Recuperación jerárquica (*small-to-big*, *parent document*)

Se indexan fragmentos pequeños, porque dan más precisión al buscar, pero al
recuperar uno se devuelve el fragmento **padre**, más grande, para que el modelo
tenga contexto suficiente.

- **Ventaja:** resuelve la tensión entre precisión al buscar y contexto al
  responder, sin tener que elegir un único tamaño de chunk.
- **Relación con este proyecto:** es la alternativa a la decisión de
  `target_size` que se midió en `../api/experimentos/medir_chunking.py`. Merece una mención en
  trabajo futuro.

### 4.4 Recuperación contextual

Antes de generar el embedding de cada fragmento, se le antepone una frase que
lo sitúa dentro de su documento. Ataca un defecto conocido del troceado: un
fragmento aislado pierde sus referentes — "este régimen", "dicho procedimiento"
—, y sin saber de qué documento viene, su vector es ambiguo.

- **Ventaja:** fragmentos más distinguibles entre sí.
- **Coste:** una llamada al LLM por fragmento **en la ingesta** (no en consulta,
  así que no afecta a la latencia percibida).

---

## 5. Intervenciones en POST-RECUPERACIÓN

### 5.1 Reordenamiento (*reranking*)

Un segundo modelo reordena los `k` recuperados por relevancia real, no por
similitud vectorial. Implementado como ejercicio en `practica-tfm/7.0_reranking_con_llm.py`.

- **Ventaja:** la similitud coseno aproxima la relevancia, no la mide. Un
  reordenador la juzga directamente.
- **Coste:** una llamada extra por consulta, en el camino crítico de la latencia.
- **Decisión en este proyecto:** implementado como `RAGServiceReranking` y
  medido: hit@3 de 0,500 a 0,667 y MRR de 0,394 a 0,447, pero las métricas de
  generación no mejoran fuera del ruido del evaluador y cada consulta cuesta
  3,7 veces más. **Medido, no activo.** Detalle en `NUCLEO_RAG.md` §9.

### 5.2 Compresión de contexto

Se filtran o resumen los fragmentos recuperados para quedarse solo con las
frases que responden a la pregunta.

- **Ventaja:** menos tokens de entrada, menos coste, y menos ruido que distraiga
  al modelo.
- **Riesgo:** comprimir es decidir qué sobra, y esa decisión se delega en otro
  modelo.

---

## 6. Intervenciones en GENERACIÓN, y arquitecturas con bucle

Las anteriores son tuberías rectas. Estas introducen decisiones y repetición.

### 6.1 Self-RAG

El modelo decide **si hace falta recuperar**, y después critica su propia
respuesta para comprobar que está respaldada por el contexto.

- **Ventaja:** evita recuperar cuando no es necesario y añade autocrítica.
- **Coste:** varias llamadas por consulta; comportamiento menos predecible.

### 6.2 RAG correctivo (*CRAG*)

Se evalúa la calidad de lo recuperado y, si es pobre, se dispara una
alternativa: reformular, ampliar la búsqueda o declarar que no hay respuesta.

- **Relación con este proyecto:** el umbral de relevancia de 0.30 es una versión
  mínima y determinista de esta idea — evalúa la evidencia y, si no llega,
  provoca la abstención. CRAG lo generaliza añadiendo vías de recuperación
  alternativas en lugar de rendirse.

### 6.3 RAG agéntico

Un agente decide en bucle qué buscar, con qué herramienta y cuándo parar.

- **Ventaja:** resuelve preguntas que exigen varios pasos encadenados.
- **Coste:** latencia y gasto poco acotados, y mucho más difícil de auditar.
- **Decisión en este proyecto:** fuera de alcance, y explícitamente descartado
  también como trabajo futuro.

### 6.4 GraphRAG

Se construye un grafo de entidades y relaciones a partir del corpus, y se
responde recorriéndolo. Su fuerte son las preguntas globales — *"¿cuáles son los
temas principales?"* — que la recuperación por fragmentos no cubre bien, porque
ningún fragmento concreto contiene la respuesta.

- **Coste:** una fase de construcción del grafo cara y que hay que rehacer
  cuando cambia el corpus. Con documentación normativa que se actualiza a
  menudo, ese coste recurrente es el argumento decisivo en contra.

---

## 7. Dónde está este proyecto

**RAG avanzado** en la taxonomía de Gao et al. (2023): la línea base con una
intervención previa a la recuperación —descomposición de consultas con reparto
equilibrado del contexto—, y aislamiento multi-tenant como restricción
estructural. Configuración activa: `RAG_CONFIGURACION=descomposicion_acotada`
(`RAGServiceCompleto`).

| Punto | Qué se hace aquí |
|---|---|
| Pre-recuperación | Enrutado por asistente (*namespace* propio por dominio); preguntas sobre el catálogo completo respondidas con metadatos (`alcance_global.py`); **descomposición de la pregunta en subpreguntas** |
| Recuperación | Densa, `top_k=5`, `text-embedding-3-small`, similitud coseno |
| Post-recuperación | **Filtro por umbral de relevancia (0.30)**; reparto por turnos de los cinco fragmentos entre subpreguntas |
| Generación | `gpt-4o-mini`, *system prompt* restrictivo + abstención explícita |

Sobre esa base hay tres refuerzos medidos: el **troceado por oraciones**
(`../api/experimentos/medir_chunking.py`: elimina el 79% de cortes a mitad de
palabra), el **umbral de relevancia** (revalidado en
`../api/experimentos/medir_umbral.py`: sigue dentro de la banda vacía entre
ruido 0.258 y señal 0.393) y la **descomposición acotada** (cobertura de
preguntas compuestas del 48 % al 52 %, desequilibrio de 1,83 a 0,83, sin
aumentar el contexto).

Las seis configuraciones conviven en el código y se eligen con una variable de
entorno, sin tocarlo:

| Configuración | Estado |
|---|---|
| `base` — RAG básico con umbral | Línea base de comparación |
| `descomposicion` — sin tope | Medida, no activa: duplica el contexto |
| **`descomposicion_acotada`** | **✅ Activa** |
| `reranking` | Medida, no activa: ×3,7 de coste sin mejora medible en las respuestas |
| `hibrido` — densa + BM25 | Medida, no activa: compuestas del 48 % al 30 % |
| `descomposicion_hibrida` | Medida, no activa: compuestas al 37 %, la más lenta |

### Por qué esta arquitectura y no una más sofisticada

Cuatro argumentos, en orden de fuerza:

1. **Auditabilidad.** Cada respuesta es trazable: estos fragmentos, estas
   puntuaciones, este umbral. Self-RAG, CRAG o un agente introducen decisiones
   tomadas por un modelo, que no se pueden justificar ante un usuario que
   pregunta por qué el sistema contestó eso.
2. **Latencia y coste acotados.** Una búsqueda y una generación por consulta;
   solo si un filtro de texto detecta varias preguntas se añaden una llamada
   para descomponer y una búsqueda por subpregunta, alrededor de 1,2 s más en
   la mediana. Las arquitecturas con bucle no permiten prometer un límite.
3. **Un corpus que cambia.** Todo lo que exija una fase de preproceso costosa
   —GraphRAG, recuperación contextual— se vuelve a pagar con cada actualización
   normativa. En comercio exterior eso es a menudo.
4. **Lo medido sostiene lo elegido.** Las decisiones de este pipeline tienen
   número detrás. Añadir etapas sin medirlas habría cambiado afirmaciones
   verificables por complejidad sin respaldo.

### La respuesta de 30 segundos para la defensa

> *"Es un RAG avanzado: recuperación densa con filtro por umbral, y antes de
> buscar, descomposición de la pregunta en subpreguntas con reparto equilibrado
> del contexto, para que una pregunta con dos temas no pierda uno. Implementé y
> medí también el reordenado y la búsqueda híbrida con BM25. No los activé: el
> reordenado multiplica el coste por 3,7 sin mejorar las respuestas de forma
> medible, y el híbrido encuentra mejor el fragmento pero empeora justo las
> preguntas compuestas. Las seis configuraciones se cambian con una variable de
> entorno, y cada decisión tiene una cifra detrás."*

---

## 8. Resumen

| Arquitectura | Interviene en | Resuelve | Aquí |
|---|---|---|---|
| RAG básico | — | — | ✅ base |
| Reescritura de consulta | Pre | Vocabulario distinto | ❌ |
| Multi-query / Fusion | Pre | Formulación poco afortunada | ❌ |
| **Descomposición** | Pre | **Preguntas compuestas** | ✅ activa, con reparto equilibrado |
| HyDE | Pre | Distancia pregunta-respuesta | ❌ |
| Enrutado | Pre | Espacio de búsqueda | ✅ por asistente, y preguntas de catálogo a metadatos |
| Híbrida | Recuperación | Códigos y siglas | 🟠 implementada y medida, no activa |
| Jerárquica | Recuperación | Precisión frente a contexto | 🔵 trabajo futuro |
| Contextual | Recuperación | Fragmentos sin referente | ❌ coste en ingesta |
| Reranking | Post | Orden por relevancia real | 🟠 implementado y medido, no activo |
| Compresión | Post | Tokens y ruido | ❌ |
| Self-RAG | Generación | Autocrítica | ❌ no auditable |
| CRAG | Generación | Evidencia insuficiente | 🟡 versión mínima: el umbral |
| Agéntico | Generación | Varios pasos | ❌ fuera de alcance |
| GraphRAG | Todo | Preguntas globales | ❌ corpus cambiante |
