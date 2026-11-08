# Dataset de evaluación — preguntas

**Las preguntas están escritas a mano, leyendo los
documentos del corpus**, no generadas por un modelo: es lo que evita que
hereden la redacción de los fragmentos e inflen artificialmente los resultados
de recuperación.

Metodología y formato en [`../api/experimentos/GUIA_DATASET.md`](../../api/experimentos/GUIA_DATASET.md).
Corpus en `Test-Documentos/corpus-indexado/` (8 documentos, 87 fragmentos).

**Estado:** ✅ **27 preguntas** en `api/experimentos/dataset_evaluacion.csv`.
Las 18 originales (1–18) más 9 de tipos nuevos añadidas el 2026-10-22 (19–27),
escritas y validadas una a una: ver [Ampliación](#ampliación-2026-10-22-tres-tipos-nuevos).

---

## Tipos de pregunta y cómo se mide cada uno

### Qué es cada tipo y para qué se usa

Los tres primeros prueban la **búsqueda**: si el sistema encuentra la
información. Los otros tres prueban el **control de alucinaciones**: si sabe qué
hacer cuando no debe responder tal cual.

| Tipo | Qué es | Comportamiento correcto | Para qué se usa | Preguntas |
|---|---|---|---|---|
| `literal` | La respuesta está en un solo fragmento y la pregunta usa sus palabras | Responder con ese fragmento | Comprobar que la búsqueda encuentra un dato en el caso más directo | 2–4, 6–10 |
| `multi` | La respuesta está repartida en dos partes del corpus, a veces en dos documentos | Recuperar las dos partes y unirlas | Medir si la fragmentación deja la información demasiado repartida | 1, 5, 11, 12 |
| `parafrasis` | La misma pregunta sin los términos del documento; la variante inversa describe el concepto y pide su nombre | Encontrar el mismo fragmento y responder igual | Medir si la búsqueda entiende el significado y no solo la coincidencia de palabras | 19–21 |
| `sin_respuesta` | Lo preguntado no está en ningún documento (tangencial o claramente fuera) | Abstenerse: «No encontré información…» | Medir el control de alucinaciones en su caso básico | 13–18 |
| `premisa_falsa` | La pregunta da por cierto algo que el corpus contradice | Corregir la premisa con lo que dice el documento | Medir si el sistema resiste a un usuario que lo empuja hacia un error teniendo el contexto que lo refuta | 22–24 |
| `parcial` | Una parte de la pregunta está en el corpus y la otra no | Responder la parte que está y decir que la otra no aparece, sin aportarla | Medir si sabe abstenerse a medias sin completar con el conocimiento propio del modelo | 25–27 |

### Qué mide cada métrica y a qué tipos se aplica

| Métrica | Qué pregunta responde | Cómo se calcula | Se aplica a | Por qué |
|---|---|---|---|---|
| **hit@1, hit@3, hit@5 y MRR** (anclas) | ¿Se recuperó el fragmento correcto, y en qué posición? | Busca la frase ancla en los fragmentos recuperados; determinista, sin juez y sin costo | Todos los tipos con ancla | Es la medida directa de la búsqueda. En `multi` exige las dos anclas |
| **Context precision** (RAGAS) | De lo que se recuperó, ¿cuánto servía? | Juez LLM, contra la respuesta de referencia | Todos menos `sin_respuesta` | Mide el ruido de la recuperación |
| **Context recall** (RAGAS) | De lo que hacía falta, ¿cuánto se recuperó? | Juez LLM, contra la respuesta de referencia | Todos menos `sin_respuesta` | Mide si falta información en el contexto |
| **Faithfulness** (RAGAS) | ¿Cada afirmación de la respuesta está respaldada por los fragmentos? | Juez LLM: descompone la respuesta en afirmaciones y verifica cada una | Todos menos `sin_respuesta` | Es el control mínimo de alucinaciones que pidió el tutor |
| **Answer relevancy** (RAGAS) | ¿La respuesta trata de lo que se preguntó? | Juez LLM y embeddings | Todos menos `sin_respuesta` | Detecta respuestas que se van por las ramas |
| **Tasa de abstención correcta** | ¿Dijo «No encontré información» cuando debía? | Busca la frase de abstención; determinista | `sin_respuesta` | RAGAS no sabe puntuar una abstención (ver Hallazgos, punto 4) |
| **Criterio sí/no** (`experimentos/criterios.py`) | ¿Hizo lo que debía en este tipo de pregunta? | Juez LLM (gpt-4.1) con una pregunta concreta por tipo | `premisa_falsa`, `parcial` | RAGAS no comprueba si se corrigió la premisa ni si se inventó la parte ausente |

En `premisa_falsa` y `parcial` las métricas de RAGAS se calculan, pero son
**orientativas**: el veredicto lo da el criterio sí/no. Además, el script avisa
cuando el sistema se abstiene del todo en una pregunta que sí tenía respuesta,
que es el fallo de abstención excesiva.

---

## Con respuesta en el corpus (12)

| # | Pregunta | Tipo | Doc | Ancla | Resp. ref. |
|---|---|---|---|---|---|
| 1 | ¿Qué tipos de IA generativa existen? | `multi` | 39 + 40 | ☑ | ☐ |
| 2 | ¿Cómo se presentan los vectores en la IA? | `literal` | **43** | ☑ | ☐ |
| 3 | ¿Qué es la similitud coseno? | `literal` | 43 | ☑ | ☐ |
| 4 | ¿Por qué es óptima la similitud coseno en la semántica direccional? | `literal` | 44 | ☑ | ☐ |
| 5 | ¿Qué diferencias hay entre las GAN y los VAE? | `multi` | **38** | ☑ | ☐ |
| 6 | ¿Qué es un LLM? | `literal` | 40 | ☑ | ☐ |
| 7 | ¿Qué tipos de datos procesa GPT-4o? | `literal` | 40 | ☑ | ☐ |
| 8 | ¿Qué diferencias hay entre GPT-4o y Gemini 2.0? | `literal` | 40 | ☑ | ☐ |
| 9 | ¿Qué son los hiperparámetros? ¿Y los parámetros? | `literal` | 36 | ☑ | ☐ |
| 10 | ¿Qué es el *learning rate* en *deep learning*? | `literal` | 36 | ☑ | ☐ |
| 11 | ¿En qué se diferencian la distancia Euclídea y la de Manhattan? | `multi` | 44 | ☑ | ☐ |
| 12 | ¿En qué teorema se basa la distancia Euclídea (L2) y para qué tipo de datos es ideal? | `multi` | 44 | ☑ | ☐ |

### Notas por pregunta

**1.** Los modelos autoregresivos, VAE y GAN están en `doc39`; la difusión, en
`doc40`. De ahí que sea `multi`: hace falta recuperar de dos documentos.

**2.** Reformulada. La versión original —*"¿qué es un espacio vectorial?"*—
pedía algo que **el corpus nunca define**. Lo menciona (*"Fundamentos de los
Espacios Vectoriales en la IA"*, *"este espacio vectorial permite manipular
imágenes"*) pero no lo define, y tampoco hay un *"¿qué es un vector?"* ni un
*"un vector es…"*. Lo que sí define con rigor es el **espacio métrico**, en el
`doc44` posición 4.537, con sus tres axiomas.

La pregunta se reorientó a lo que sí responde el pasaje que señala el ancla, que
ya estaba verificada. Quedaba también la opción de preguntar por el espacio
métrico; se descartó por no rehacer el trabajo hecho.

> Lección: comprobar que el corpus **define** el concepto, no solo que lo
> menciona. Una palabra que aparece diez veces puede no estar definida ni una.

**4.** La mejor planteada de todas. Es un *por qué*, no un *qué es*, de modo que
obliga a recuperar la justificación y no una definición. Conviene tener más de
este estilo.

**5.** ⚠️ **GAN y VAE aparecen en dos documentos**, el resumen `doc38` y las
diapositivas `doc39`. Antes de fijar el ancla, comprobar que esa frase literal
solo está en uno:

```powershell
Select-String -Path *.txt -Pattern "la frase ancla"
```

**7.** Reformulada. La versión original —*"¿puede un modelo multimodal procesar
audio?"*— era de sí/no, y una respuesta de una palabra no deja evaluar nada. La
respuesta está literal en `doc40`: *"entrada y salida de texto, imagen y audio
en tiempo real"*.

**8.** Parece `multi` y no lo es: ambos modelos están en la **misma tabla
comparativa** de `doc40`, con toda probabilidad en el mismo fragmento.

**9.** Es una **pregunta compuesta**, justo el patrón que degrada la
recuperación a la mitad. Pero los dos conceptos están definidos en el mismo
bloque de `doc36`, así que previsiblemente funcione. Se mantiene a propósito: si
acierta, refina el hallazgo del experimento de preguntas compuestas — el
problema no es que sean dos preguntas, sino que los temas estén **separados**.

**11.** Apunta al `doc44`, no al `doc43`. El resumen solo las nombra de pasada
—una mención de *"Distancia Euclidia"* y dos de Manhattan, en viñetas
consecutivas, es decir, el mismo fragmento—, mientras que las diapositivas las
desarrollan con catorce y doce menciones repartidas, además de Minkowski. Por
eso ahí sí es `multi`.

> ⚠️ **Los dos documentos escriben el término distinto:** el resumen usa
> *"Euclidia"* y las diapositivas *"Euclídea"*, con tilde. La normalización del
> sistema colapsa espacios y pasa a minúsculas, **pero no quita tildes**. Al
> buscar el ancla, probar ambas grafías.

Se reformuló desde *"¿cuál es la distancia Manhattan (L1) y la distancia
Euclídea (L2)?"*, que era una pregunta compuesta. La versión actual exige
recuperar ambas definiciones para responder —que es lo que mide una `multi`—
sin ser dos preguntas pegadas.

**12.** Las dos anclas están **verificadas**: únicas en todo el corpus y
separadas por **siete fragmentos** dentro del `doc44`, lo que la convierte en
una `multi` sólida —no en dos viñetas contiguas—.

| Mitad | Ancla | Posición | Fragmento |
|---|---|---|---|
| El teorema | `Basada en el teorema de Pitágoras` | 5.060 | ~5 |
| Los datos | `es ideal para datos como imágenes` | 10.744 | ~12 |

Texto de origen: *"Distancia Euclídea (L2). Basada en el teorema de Pitágoras,
mide la línea recta entre dos puntos"* y *"La distancia Euclídea (L2) es ideal
para datos como imágenes, señales o coordenadas físicas donde la magnitud
absoluta tiene significado real"*.

> Ojo al evaluarla: el `doc44` dice también que la similitud coseno es *"ideal
> para textos y embeddings semánticos"*. Si el sistema contesta eso, no ha
> entendido por cuál métrica se le preguntaba — y es un fallo interesante, no
> un error del dataset.

---

## Respuestas de referencia

Se escriben **mirando el fragmento**, no de memoria: cada afirmación debe poder
señalarse en el `.txt`. Escribir lo que uno sabe del tema, en vez de lo que el
documento dice, mide si el sistema coincide con el conocimiento general del
autor — no si usa los documentos, que es lo que se quiere evaluar.

Es además la misma regla que el *prompt* le impone al sistema: la hoja de
respuestas debe cumplir lo que se le exige al examinado.

| # | Respuesta de referencia |
|---|---|
| 1 | Los modelos autoregresivos predicen el siguiente token a partir de los anteriores, generando token a token en orden, y son la base de modelos como GPT. Los autoencoders variacionales (VAE) comprimen los datos en un espacio latente y usan ruido gaussiano para generar variaciones. Las redes generativas antagónicas (GAN) enfrentan un generador y un discriminador. Y la difusión generativa parte de una imagen aleatoria y aprende a convertir ese ruido en una imagen coherente. |
| 2 | No solo como entidades matemáticas, sino como contenedores de características multidimensionales. Un embedding es una proyección de un objeto —texto, imagen o audio— en un espacio continuo donde la cercanía geométrica equivale a la similitud conceptual. |
| 3 | Es la técnica predilecta para embeddings de texto, porque mide el ángulo entre vectores y resulta invariante a la magnitud o longitud de los documentos. |
| 4 | Es óptima para embeddings semánticos porque en ellos la dirección del vector captura el significado, con independencia de su magnitud, como ocurre en Word2Vec o BERT. |
| 5 | Los VAE comprimen los datos en un espacio latente para luego reconstruirlos, y usan ruido gaussiano en ese espacio para generar variaciones aleatorias pero coherentes. Las GAN funcionan con una dinámica de juego de suma cero entre dos redes: un generador que crea imágenes falsas y un discriminador que intenta detectarlas. |
| 6 | Son modelos entrenados para procesar, entender y generar lenguaje natural. Predicen el siguiente token en una secuencia dada, y con ello pueden responder preguntas, resumir textos, traducir o razonar. |
| 7 | Texto, imagen y audio, tanto de entrada como de salida, y en tiempo real. |
| 8 | GPT-4o procesa texto, imagen y audio, con razonamiento rápido y conversación multimodal fluida. Gemini 2.0 Flash añade vídeo a esas modalidades y destaca por una ventana de contexto de hasta un millón de tokens y generación multimodal nativa. |
| 9 | Los hiperparámetros son todo aquello que se puede configurar antes de entrenar y no se aprende automáticamente; su ajuste correcto es clave para el éxito. Los parámetros, en cambio, son los valores matemáticos que se ajustan durante el entrenamiento. |
| 10 | Es el factor de aprendizaje del modelo: lo rápido o despacio que cambia internamente para aprender la tarea. Con un valor bajo, como 0,01, los pesos cambian poco en cada iteración; con uno alto, como 0,5, cambian mucho. |
| 11 | La distancia de Manhattan resulta especialmente útil con datos dispersos, como representaciones de texto basadas en conteo de palabras, y es menos sensible a los valores atípicos porque no eleva al cuadrado las diferencias. Sus curvas de iso-distancia forman rombos en 2D, frente a los círculos de la Euclídea, y además se calcula de forma más eficiente. |
| 12 | Se basa en el teorema de Pitágoras y mide la línea recta entre dos puntos, por lo que es la distancia natural en el espacio físico. Resulta ideal para datos como imágenes, señales o coordenadas físicas, donde la magnitud absoluta tiene significado real y los datos siguen una distribución aproximadamente normal. |

**Las 12 completas.** Las 6 `sin_respuesta` comparten la frase de abstención.

### Redactar, no recortar

Las respuestas se escriben como frases completas, no como fragmentos copiados
del documento. El motivo es práctico: si la referencia es idéntica al texto del
fragmento, no se puede distinguir si el sistema **entendió** la respuesta o
simplemente **copió** el contexto que recibió.

La fidelidad se mantiene igual —cada afirmación sigue siendo señalable en el
`.txt`—; lo que cambia es la redacción.

### Tres errores reales cometidos al redactarlas

**Escribir de memoria.** El primer borrador de la 6 decía *"entrenado con
grandes cantidades de texto para aprender patrones del lenguaje"* — cierto sobre
los LLM, pero ausente del `doc40`. Y omitía la predicción del siguiente token,
que es justo el contenido del ancla. Ancla y referencia habrían medido cosas
distintas.

**Responder desde el fragmento equivocado.** Para la 7 se propuso *"permiten
razonamiento más humano, entienden contexto visual y auditivo"*, que está
literal en el `doc40` — pero en la sección de modelos multimodales en general,
unas 5.000 posiciones después de donde se responde qué datos procesa GPT-4o. La
frase era verificable y aun así no respondía a la pregunta.

> Que una frase esté en el documento no basta: tiene que estar **en el pasaje
> que responde a esa pregunta**, el mismo que señala el ancla.

El mismo tropiezo se repitió en la pregunta 1, con *"procesan texto token por
token, manteniendo un estado interno (memoria)"*. Está literal en el `doc39`,
posición 1.382 — pero describe **las RNN**, en la sección de arquitecturas de
red, mil caracteres después del pasaje sobre tipos de modelo generativo que
señalan las anclas (posiciones 352 y 388).

El mismo error se repitió una tercera vez en la pregunta 5, con *"fundamental
para entender la especialización de la IA según el tipo de dato (texto vs.
imagen)"*. Está literal en el `doc38`, posición 3.238 — pero en la
**conclusión**, mientras las anclas están en 1.988 y 2.392. Y, sobre todo, no
responde a la pregunta: dice que conocer esas arquitecturas es útil, no en qué
se diferencian.

> **El patrón:** las frases de resumen y conclusión están bien escritas y por
> eso resultan atractivas, pero son generalizaciones y casi nunca responden
> preguntas concretas.

> **La comprobación que lo evita, en una línea:** si tu respuesta no contiene el
> contenido de tus anclas, estás en el pasaje equivocado. En la 5 las anclas
> hablaban de ruido gaussiano y de juego de suma cero, y la respuesta propuesta
> no mencionaba ninguna de las dos.

### La respuesta de referencia es la ideal, no la que encaja con las anclas

La pregunta 1 pide los tipos de IA generativa, y el corpus describe **cuatro**:
autoregresivos, VAE, GAN y difusión. Las dos anclas solo cubren dos de ellos.

La respuesta de referencia los recoge los cuatro de todos modos. Si el sistema
recupera solo dos, el `context_recall` bajará — y **está bien que baje**, porque
efectivamente no recuperó la respuesta completa. Ajustar la referencia para que
encaje con lo que se espera recuperar sería falsear la medición.

### Una `multi` descartada

Se evaluó añadir *"¿Qué tipos de datos procesa un modelo multimodal y qué le
permite eso?"*. Sus dos anclas candidatas —`Modelo que puede procesar diferentes
tipos de input` y `Permiten razonamiento más "humano"`— son únicas, pero están a
**509 caracteres**: mismo fragmento o contiguo. Sería una `literal` disfrazada.

El dataset se cierra en 18 preguntas con 4 `multi`. Forzar una quinta que no
mide ensamblaje sería peor que no tenerla.

---

## Frases ancla — verificadas

Las doce comprobadas el 11 de octubre de 2026 contra los ocho `.txt` del corpus:
**cada una aparece exactamente una vez en todo el corpus**, en el documento
indicado. Copiadas del texto extraído, no del PDF.

| # | Doc | Ancla | Pos. | Pal. |
|---|---|---|---|---|
| 1 | 39 | `Predice el siguiente token a partir de los anteriores` | 352 | 9 |
| 1 | 40 | `convertir ruido en una imagen coherente` | 388 | 6 |
| 2 | 43 | `contenedores de características multidimensionales` | 901 | 4 |
| 3 | 43 | `invariante a la magnitud` | 3.631 | 4 |
| 4 | 44 | `la dirección del vector captura el significado` | 11.254 | 7 |
| 5 | 38 | `ruido gaussiano en el espacio latente` | 1.988 | 6 |
| 5 | 38 | `dinámica de "juego de suma cero"` | 2.392 | 6 |
| 6 | 40 | `Predicen el siguiente token en una secuencia dada` | 3.262 | 8 |
| 7 | 40 | `imagen y audio en tiempo real` | 5.819 | 6 |
| 8 | 40 | `Ventana de contexto de hasta 1 millón de tokens` | 11.387 | 9 |
| 9 | 36 | `configurar antes de entrenar` | 1.244 | 4 |
| 9 | 36 | `se ajustan durante el entrenamiento` | 1.407 | 5 |
| 10 | 36 | `el factor de aprendizaje del modelo` | 2.804 | 6 |
| 11 | 44 | `útil al trabajar con datos dispersos` | 7.135 | 6 |
| 12 | 44 | `Basada en el teorema de Pitágoras` | 5.060 | 6 |
| 12 | 44 | `es ideal para datos como imágenes` | 10.744 | 6 |

### Cambios de documento al verificar

**Pregunta 2** pasa del `doc44` al **`doc43`**. El resumen define el vector como
*"contenedores de características multidimensionales"*, una frase breve y única;
las diapositivas desarrollan el concepto a lo largo de varios fragmentos sin una
definición compacta que sirva de ancla.

**Pregunta 5** se fija en el **`doc38`**, el resumen. Tanto él como el `doc39`
tratan VAE y GAN, pero el resumen los define de forma concisa y en secciones
separadas, que es lo que necesita una `multi`. Usar el `doc39` habría obligado a
vigilar que la frase no apareciera también en el `doc38`.

### Avisos sobre pares de la misma pregunta

**Pregunta 9.** Las dos anclas están a **163 caracteres**: caen con seguridad en
el mismo fragmento. Es coherente con lo previsto —los dos conceptos se definen
en el mismo bloque— y por eso sigue clasificada como `literal` pese a estar
formulada como pregunta compuesta.

**Pregunta 5.** A **404 caracteres**: probablemente fragmentos contiguos. Es una
`multi` débil. Si al medir resulta que siempre se recuperan juntos, conviene
anotarlo: significa que mide poco más que una `literal`.

**Pregunta 12.** A **5.684 caracteres**, unos siete fragmentos. Es la `multi`
mejor construida del conjunto.

### Descartada por ambigua

`mide el ángulo entre vectores` era el candidato natural para la pregunta 3,
pero aparece **dos veces**, en el `doc43` y en el `doc44`. Si el sistema
recuperase el fragmento equivocado se contaría un acierto falso. Sustituida por
`invariante a la magnitud`, que solo está en el `doc43`.

Es el fallo que más fácil se cuela, y la razón de comprobar la unicidad una a
una.

---

## Sin respuesta en el corpus (6)

| # | Pregunta | Dificultad | Por qué no está |
|---|---|---|---|
| 13 | En una arquitectura RAG, ¿qué problema resuelve el uso de un *reranker* tras recuperar documentos? | **tangencial** | El corpus explica RAG pero nunca el reordenado |
| 14 | ¿Qué ocurre cuando la temperatura de un LLM aumenta, manteniendo iguales los demás parámetros? | **tangencial** | Cubre hiperparámetros de entrenamiento, no de inferencia |
| 15 | En *fine-tuning* con LoRA, ¿cuál es la idea principal? | **tangencial** | Menciona *fine-tuning* en `doc37`, nunca LoRA ni adaptadores |
| 16 | ¿Qué es el sistema aduanero? | ajena (control) | Ningún documento trata comercio exterior |
| 17 | ¿Qué hora es? | ajena (control) | No es respondible desde documentos |
| 18 | ¿Cuál es la capital de Francia? | ajena (control) | — |

Para todas: `respuesta_referencia` = **la frase exacta de abstención**, y
`documento` y `ancla` vacíos.

### Por qué hay dos grupos

**Las tangenciales son las que miden de verdad.** El sistema va a recuperar
fragmentos con puntuación por encima de 0,30 —habla de RAG, de hiperparámetros,
de *fine-tuning*— y aun así debe abstenerse. **Ahí no lo salva el umbral: lo
salva el *prompt* restrictivo**, que es precisamente lo que nunca se ha medido.

**Las ajenas son el control negativo.** Se descartan por el umbral sin esfuerzo
(la de Francia puntuó 0,139 en la última medición). Si el sistema fallara en
estas, habría un problema grave y conviene detectarlo.

Con tres de cada clase basta: el trabajo fino está en las tangenciales.

### Dos matices que merecen nota

**17 y 18 no prueban lo mismo.** La de Francia comprueba si el modelo **filtra
conocimiento de su entrenamiento** —sabe que es París y el *prompt* le prohíbe
usarlo—. La de la hora comprueba si **se inventa** algo que no puede saber de
ninguna manera, ni por los documentos ni por el entrenamiento. La segunda es la
prueba más limpia de abstención.

**La 18 tiene historia.** Aparece en las dos mediciones del umbral, de junio y
de octubre, sobre dos estrategias de fragmentación distintas. Incluyéndola aquí
suma un tercer punto de medición: es la única consulta con continuidad a lo
largo del proyecto, y eso respalda que la abstención es estable y no un
resultado afortunado.

---

## Descartada

> *"¿Qué vino a resolver la IA generativa en 2026?"*

Por dos motivos. **No tiene respuesta verificable:** `doc40` tiene una sección
de estado del arte con modelos de 2025-2026, pero no afirma qué vino a resolver
la IA generativa ese año. Habría que inventar la respuesta de referencia, y
entonces no se mide el sistema sino si coincide con una opinión. Y **el fallo
no sería interpretable:** si contesta algo, no hay forma de decidir si acertó.

> **La regla:** si no puedes escribir la respuesta de referencia señalando una
> frase concreta del documento, la pregunta no sirve.

Alternativa verificable sobre esa misma zona del corpus:

> *"¿Qué arquitectura usa LLaMA 4 y cuál es su contexto máximo?"*

Respuesta literal en `doc40`: *"Mixture of Experts (MoE), modelo multimodal con
arquitectura eficiente y contexto de hasta 10M tokens"*.

---

## Lo que falta

- [x] **Frases ancla** de las 12 con respuesta — verificadas el 2026-10-11
- [x] **Respuestas de referencia** — las 12, escritas el 2026-10-11
- [x] Verificar la unicidad del ancla de la 5 — resuelta fijándola en el `doc38`
- [x] Pasar a CSV en `api/experimentos/` con el formato de la guía

### Reparto actual

```
literal         8    ✔ dentro del objetivo (~7)
multi           4    ✔ casi (~5)
sin_respuesta   6    ✔ en el objetivo (~6)
parafrasis      3    añadidas el 2026-10-22
premisa_falsa   3    añadidas el 2026-10-22
parcial         3    añadidas el 2026-10-22
                ──
                27
```

Siguen faltando una o dos `multi`, que son las que miden si el sistema sabe
**juntar piezas separadas** — donde más se nota la estrategia de fragmentación.
Los documentos grandes, `doc39`, `doc40` y `doc44`, son los que tienen secciones
suficientemente separadas para ello.

**Un patrón que funciona para construirlas:** buscar un concepto que el
documento **define en un sitio y aplica o critica en otro**. Las GAN, por
ejemplo, se definen al principio de `doc39` y sus limitaciones aparecen mucho
después — *"¿para qué sirven las GAN y en qué casos no conviene usarlas?"*
obliga a recuperar ambas secciones.

---

## Ampliación 2026-10-22: tres tipos nuevos

El dataset original medía encontrar un dato, juntar piezas y callarse cuando no
hay nada. No medía tres comportamientos que también deciden si un RAG es fiable,
así que se añadieron 9 preguntas, escritas a mano leyendo el corpus y validadas
una a una. Criterios de cada tipo en `GUIA_DATASET.md` §2.

| # | Tipo | Pregunta (resumida) | Documento | Qué se espera |
|---|---|---|---|---|
| 19 | `parafrasis` | Técnica de medición entre vectores inmune a la extensión de los documentos | `doc43` | Similitud coseno, sin que la pregunta la nombre |
| 20 | `parafrasis` (inversa) | Sistema que entiende y escribe textos adivinando la palabra siguiente | `doc40` | Nombrar el LLM |
| 21 | `parafrasis` (inversa) | Sistema de OpenAI que procesa voz, imagen y texto en tiempo real | `doc40` | GPT-4o, no los otros modelos de OpenAI de la misma tabla |
| 22 | `premisa_falsa` | Por qué las GAN generan texto tan bien | `doc38` | Corregir: no son adecuadas para texto |
| 23 | `premisa_falsa` | Por qué hay que reducir el learning rate al subir el batch size | `doc36` | Corregir: se aumenta, no se reduce |
| 24 | `premisa_falsa` | Por qué GET es el estándar para enviar datos e inferir | `doc41` | Corregir: es POST |
| 25 | `parcial` | Características de FastAPI y quién lo creó | `doc41` | Responder las características; el creador no está |
| 26 | `parcial` | En qué se diferencia StyleGAN de otras GAN y qué empresa lo hizo | `doc39` | Responder la diferencia; la empresa no está |
| 27 | `parcial` | Qué hito marcó *Attention Is All You Need* y quién lo publicó | `doc37`, `doc40` | Responder el hito; los autores no están |

Las tres `parcial` piden un dato que el modelo conoce por su entrenamiento, y en
la 26 y la 27 el nombre que lo delataría (NVIDIA, Google) aparece en el corpus en
otro contexto: si lo menciona, usó conocimiento externo o mezcló fragmentos.

### Primera medición (2026-10-23, configuración activa)

`descomposicion_acotada`, temperatura 0. Resultados en
`ampliacion/dataset_ejecutado_2026-10-23_descomposicion_acotada_temp0.0.json` y
`ampliacion/ragas_2026-10-23_avanzado_descomposicion_acotada_temp0.0.json`.

| # | Respuesta del sistema | Criterio |
|---|---|---|
| 19 | «Similitud del coseno» | ✅ |
| 20 | «Un modelo generativo, como GPT»: no dice LLM y no recupera el fragmento esperado | ⚠️ |
| 21 | **«GPT-5»**: la otra fila multimodal de OpenAI de la tabla | ❌ |
| 22 | «No encontré información», con el fragmento recuperado en 3.ª posición | ❌ |
| 23 | **Acepta la premisa**: «es necesario reducir el learning rate», con el fragmento correcto en 1.ª posición | ❌ |
| 24 | «No encontré información» | ❌ |
| 25 | Características correctas; «no encontré información sobre el creador» | ✅ |
| 26 | «No encontré información», sin responder la parte que sí estaba (ver la nota tras los hallazgos) | ❌ |
| 27 | Hito correcto; «no encontré información sobre los autores» | ✅ |

**Criterios sí/no** (juez gpt-4.1): `premisa_falsa` 0/3 · `parcial` 2/3.

**RAGAS por tipo** (juez gpt-4o-mini; precisión de contexto, recall, fidelidad y
relevancia):

| Tipo | n | Precisión | Recall | Fidelidad | Relevancia |
|---|---|---|---|---|---|
| `literal` | 8 | 0,877 | 0,938 | 0,919 | 0,816 |
| `multi` | 4 | 0,774 | 0,812 | 0,975 | 0,855 |
| `parafrasis` | 3 | 0,962 | 1,000 | 0,694 | 0,803 |
| `premisa_falsa` | 3 | 0,444 | 0,722 | 0,111 | 0,247 |
| `parcial` | 3 | 0,889 | 0,889 | 0,869 | 0,518 |

La media sobre las 21 preguntas (0,810 · 0,885 · 0,775 · 0,698) **no es
comparable** con las líneas base de 12 preguntas: baja porque se añadieron tipos
más difíciles, no porque el sistema empeorara.

### Hallazgos

1. **El sistema no sabe corregir una premisa falsa.** Falla en las tres, de dos
   formas: se abstiene (22 y 24) o la acepta y la justifica (23). La 23 es el
   caso más grave: con la respuesta correcta en el primer fragmento, construye
   una explicación contraria al documento, arrastrado por la justificación que
   trae la pregunta («para evitar inestabilidad»).
2. **Abstención excesiva.** El 100 % de abstención correcta de las 6
   `sin_respuesta` tiene un reverso que el dataset original no podía ver: el
   sistema también se calla cuando sí tiene información (22, 24 y 26; la 26
   tenía otra causa, ver la nota de EXP-15 más abajo). El prompt
   le pide abstenerse si el contexto no responde la pregunta, y ante una premisa
   falsa o una pregunta compuesta interpreta que no la responde.
3. **La abstención parcial sí funciona** cuando el sistema responde (25 y 27):
   dice qué no sabe y no completa con conocimiento externo. No nombró ni al
   creador de FastAPI ni a Google. (Tras el arreglo de EXP-15 apareció un caso
   que sí completa: ver la nota más abajo.)
4. **RAGAS no sabe juzgar estos dos tipos.** La misma respuesta —«No encontré
   información sobre este tema en los documentos de la empresa»— recibió una
   fidelidad de 0,00 en la 22 y la 24, y de 1,00 en la 26: ante una abstención,
   la cifra no significa nada. Y aceptar la premisa falsa de la 23 obtuvo una
   relevancia de 0,74, porque la respuesta sí trata de lo que se preguntó. La
   fidelidad baja avisa de que algo va mal (0,33 en la 23, 0,25 en la 21, que
   nombra un modelo equivocado), pero no dice qué. Por eso estos tipos se
   juzgan además con el criterio sí/no.
5. **El juez también se equivoca.** Con gpt-4o-mini, el criterio `parcial`
   rechazó las respuestas correctas de la 25 y la 27. Se cambió a gpt-4.1 para
   los criterios, y los veredictos descartados quedan en `criterios_anteriores`
   del JSON de RAGAS.

### Experimento: corregir la premisa desde el prompt (2026-10-25, descartado)

Hipótesis: los fallos de `premisa_falsa` y la abstención excesiva se deben a que
el prompt de sistema no dice qué hacer cuando el contexto **contradice** la
pregunta. Se añadieron dos reglas al `DEFAULT_SYSTEM_PROMPT`: corregir la
suposición en vez de aceptarla o abstenerse, y responder la parte disponible de
una pregunta parcial indicando qué falta. Se midió con las 27 preguntas
(`dataset_ejecutado_2026-10-25_…_prompt_v2.json`,
`ragas_2026-10-25_…_prompt_v2.json`).

| | Prompt original (23 oct) | Prompt con las dos reglas (25 oct) |
|---|---|---|
| `premisa_falsa` (criterio, juez gpt-4.1) | 0/3 | 1/3 |
| `parcial` (criterio, juez gpt-4.1) | 2/3 | 2/3 |
| Abstención correcta en `sin_respuesta` | 6/6 | 6/6 |
| Relevancia media (RAGAS) | 0,698 | 0,583 |

- La única mejora es la 22, y a medias: empieza con «No encontré información…»
  y a continuación corrige la premisa, de modo que la respuesta se contradice.
- La 23 sigue aceptando la premisa. Ahora cita primero el dato correcto (el
  learning rate aumenta) y después concluye lo contrario.
- La 24 y la 26 siguen abstenciéndose.
- **Efecto secundario:** la regla de las parciales hizo que el modelo añadiera
  «No encontré información sobre otros…» a respuestas que estaban completas
  (preguntas 1, 5 y 8). En la 8, RAGAS bajó la relevancia de 0,94 a 0,00 al
  leer la respuesta como evasiva.

**Decisión:** se revirtió el prompt a su versión original. Ajustar el prompt no
basta para este fallo: arregla poco y degrada respuestas que estaban bien. Las
vías que quedan como trabajo futuro son un paso explícito de detección de
contradicciones entre pregunta y contexto antes de generar, o una verificación
posterior de la respuesta (LLM-as-judge), medidas con este mismo conjunto.

### Nota sobre la pregunta 26 (EXP-15, 2026-11-04)

La abstención de la 26 no se debía al prompt. Producción guardaba solo los
primeros 1.000 caracteres de cada fragmento, y el dato que responde la 26 estaba
en el carácter 1.028 de un fragmento de 1.673: el modelo nunca lo leía. Corregido
el recorte y reindexado el corpus, la 26 ya responde la parte documentada, pero
añade de memoria que StyleGAN es de NVIDIA, un dato que no está en los
fragmentos. El criterio `parcial` sigue en 2/3, ahora por completar con
conocimiento propio en lugar de por callarse. Tras el arreglo, la abstención
indebida queda en la 22 y la 24. Detalle en
`api/experimentos/9-embeddings-y-tamano/EXP-15_tamano-fragmento/LEEME.md`.
