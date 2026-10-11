# Dataset de evaluación — preguntas

Borrador de trabajo. **Las preguntas están escritas a mano, leyendo los
documentos del corpus**, no generadas por un modelo: es lo que evita que
hereden la redacción de los fragmentos e inflen artificialmente los resultados
de recuperación.

Metodología y formato en [`../api/experimentos/GUIA_DATASET.md`](../api/experimentos/GUIA_DATASET.md).
Corpus en `Test-Documentos/corpus-indexado/` (8 documentos, 87 fragmentos).

**Estado:** ✅ **completo** — 18 preguntas · 16 frases ancla verificadas · 12
respuestas de referencia escritas. Listo para pasar a CSV.

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
- [ ] Pasar a CSV en `api/experimentos/` con el formato de la guía

### Reparto actual

```
literal         8    ✔ dentro del objetivo (~7)
multi           4    ✔ casi (~5)
sin_respuesta   6    ✔ en el objetivo (~6)
                ──
                18
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
