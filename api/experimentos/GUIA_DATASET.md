# Guía para construir el dataset de evaluación

Qué es, qué problema resuelve, y cómo se escribe cada fila.

---

## 1. El problema que resuelve

Hasta ahora este proyecto ha medido tres cosas, y las tres son **estructurales**:

| Medición | Qué dice |
|---|---|
| Calidad del *chunking* | Qué le hace cada estrategia al texto |
| Coste por consulta | Cuánto cuesta responder |
| Banda del umbral | Dónde se separa el ruido de la señal |

Todas son ciertas y defendibles. Pero **ninguna dice si el sistema responde
bien**.

Para afirmar que una respuesta es correcta hace falta saber de antemano qué es
lo correcto, y eso no está escrito en ninguna parte. Es un examen sin hoja de
respuestas: se puede verificar que está bien impreso y cuánto costó el papel,
pero no se puede corregir.

**El dataset es la hoja de respuestas.**

### Las cuatro preguntas que desbloquea

1. **¿Encuentra el fragmento correcto?** Se anota de antemano qué frase del
   documento responde cada pregunta, y se comprueba si el sistema la recuperó.
2. **¿La respuesta se apoya en lo recuperado, o inventa?** Es la *faithfulness*
   de RAGAS. El proyecto declara tres mecanismos anti-alucinación y ninguno
   está medido.
3. **¿Se abstiene cuando debe?** Hoy se sabe que funciona en un caso aislado.
   Con el dataset se sabe en qué proporción.
4. **¿Una mejora mejora de verdad?** Sin dataset, "el reranking mejora el
   sistema" es una opinión. Con dataset, es una fila de una tabla.

### Por qué lo tiene que escribir una persona

Porque hay que **leer los documentos** y decidir qué pregunta tiene respuesta
ahí y cuál no.

Generarlo con un modelo a partir de los mismos documentos invalida la medición:
se estaría evaluando el sistema contra preguntas que otro modelo se inventó de
los mismos textos. Y las preguntas **sin respuesta en el corpus** no se pueden
generar desde los documentos, por definición — y son precisamente las que miden
el control de alucinaciones.

---

## 2. Los tipos de pregunta

No es burocracia: cada tipo mide algo distinto. La explicación detallada de cada tipo y de cada métrica está en `docs/DATASET_PREGUNTAS.md`, sección «Tipos de pregunta y cómo se mide cada uno». Los tres primeros forman el
dataset original (preguntas 1–18); los demás se añadieron a partir del
2026-10-22 para cubrir comportamientos que esos tres no medían.

| Tipo | Qué mide | Cómo se evalúa |
|---|---|---|
| `literal` | ¿Sabe encontrar un dato que está en un fragmento? | RAGAS + anclas |
| `multi` | ¿Sabe juntar piezas separadas? ← **aquí se nota la fragmentación** | RAGAS + anclas |
| `sin_respuesta` | ¿Sabe cuándo callarse? ← **aquí está la aportación del trabajo** | Tasa de abstención |
| `parafrasis` | ¿Recupera cuando la pregunta no usa las palabras del documento? | RAGAS + anclas |
| `otro_idioma` | ¿Recupera si preguntan en inglés sobre documentos en español? | RAGAS + anclas |
| `comparativa` | ¿Contrasta dos conceptos de partes distintas del corpus? | RAGAS + anclas en ambos lados |
| `alcance_global` | ¿Qué hace ante una pregunta sobre todo el corpus? (defecto declarado en 5.4) | RAGAS |
| `dato_exacto` | ¿Da cifras, fechas y nombres sin redondear ni inventar? | RAGAS + comparación con la referencia |
| `premisa_falsa` | ¿Corrige la premisa en vez de seguirle la corriente? | Criterio sí/no con juez (RAGAS se calcula, pero solo orientativo) |
| `parcial` | ¿Responde la parte que está y se abstiene en la que no? | Criterio sí/no con juez (RAGAS se calcula, pero solo orientativo) |
| `ambigua` | ¿Reconoce que la pregunta admite varias lecturas? | Criterio sí/no con juez |
| `seguimiento` | ¿Usa el historial para entender la pregunta? (necesita columna de historial) | RAGAS con historial |
| `inyeccion` | ¿Resiste instrucciones metidas en la pregunta? (sin guardrails: se espera que falle) | Criterio sí/no |

**Estado (2026-10-22):** el dataset tiene 27 preguntas. Además de los tres
tipos originales (1–18), se escribieron y validaron tres tipos nuevos:
`parafrasis` (19–21), `premisa_falsa` (22–24) y `parcial` (25–27). Los demás
tipos de la tabla quedan **propuestos, no incluidos**. Si se añaden, las
comparativas no deben repetir las que ya existen como `multi` o `literal`
(preguntas 5, 8 y 11), que conservan su tipo original porque ya están medidas
con él.

Reglas que salieron al validar las preguntas nuevas:

- **Paráfrasis:** no nombrar el concepto ni copiar sus términos clave; una
  paráfrasis inversa (describe y pide el nombre) necesita una referencia que
  nombre el concepto.
- **Premisa falsa:** presuponer lo falso («¿por qué…?»), no preguntarlo («¿es
  cierto que…?»); lo falso contradice algo explícito del corpus.
- **Parcial:** la parte ausente se verifica con búsquedas en todo el corpus;
  mejor si es algo que el modelo sabe por su cuenta.
- **Respuesta de referencia:** le habla al usuario (nada de «según el
  documento»), no afirma más que el corpus («estrictamente», «exclusivamente») y,
  si la pregunta compara, la referencia compara.

El tercero es el menos habitual y el más importante. La mayoría de los datasets
de evaluación solo contienen preguntas con respuesta, y por eso solo miden
recuperación. Este mide además **abstención**, que es lo que el tutor llamó
"control mínimo de alucinaciones".

### Reparto recomendado (15-20 preguntas)

```
~7 literales
~5 multi
~6 sin_respuesta
```

---

## 3. El formato

```
id,pregunta,tipo,documento,respuesta_referencia,ancla,ancla_2,notas
```

| Columna | Quién la rellena |
|---|---|
| `pregunta` | **Tú** |
| `respuesta_referencia` | **Tú** |
| `tipo` | **Tú** |
| `documento` | **Tú** |
| `ancla`, `ancla_2` | **Tú** |
| lo que respondió el sistema | se genera al ejecutar |
| qué fragmentos recuperó | se genera al ejecutar |

Las dos últimas son las que RAGAS necesita y no se escriben a mano: salen de
lanzar el dataset contra el RAG.

---

## 4. Una fila de cada tipo, con texto real del corpus

### `literal` — la respuesta está en un fragmento

> **Fragmento** (`Resumen Clase 2 - Tema 3.pdf`):
> *"A diferencia de los autoencoders simples, los VAE utilizan ruido gaussiano
> en el espacio latente para generar variaciones aleatorias pero coherentes de
> los datos originales."*

| Campo | Valor |
|---|---|
| `pregunta` | ¿Qué utilizan los VAE para generar variaciones de los datos originales? |
| `respuesta_referencia` | Ruido gaussiano en el espacio latente, que les permite generar variaciones aleatorias pero coherentes de los datos originales, a diferencia de los autoencoders simples. |
| `tipo` | `literal` |
| `documento` | Resumen Clase 2 - Tema 3.pdf |
| `ancla` | `ruido gaussiano en el espacio latente` |

La respuesta de referencia **se escribe leyendo el fragmento**; no es copiar y
pegar. Es la respuesta correcta, y RAGAS la comparará con la que dé el sistema.

### `multi` — hace falta juntar dos partes

> **Fragmento A:** *"El generador es uno de los dos componentes principales de
> las GANs. Su objetivo es tomar una entrada de ruido aleatorio y convertirlo en
> una imagen que parezca lo más real posible."*
>
> **Fragmento B:** *"El discriminador actúa como un 'crítico' que intenta
> distinguir entre las imágenes… A través de este proceso competitivo, el
> generador mejora sus habilidades hasta que el discriminador ya no puede
> distinguir los datos falsos de los reales."*

| Campo | Valor |
|---|---|
| `pregunta` | ¿Cómo compiten entre sí los dos componentes de una GAN? |
| `respuesta_referencia` | El generador crea datos falsos a partir de ruido aleatorio y el discriminador actúa como crítico intentando distinguirlos de los reales. En ese proceso competitivo el generador mejora hasta que el discriminador ya no puede distinguirlos. |
| `tipo` | `multi` |
| `documento` | Clase 2 – Modelos Autoregresivos, VAEs y GANs.pdf |
| `ancla` | `El generador crea datos falsos` |
| `ancla_2` | `el discriminador ya no puede distinguir` |

**Dos anclas, y el acierto exige las dos** entre los fragmentos recuperados. Si
solo se exigiera una, se estaría midiendo lo mismo que una `literal`.

### `sin_respuesta` — no está en el corpus

| Campo | Valor |
|---|---|
| `pregunta` | ¿Cuánto cuesta entrenar un modelo de difusión en AWS? |
| `respuesta_referencia` | No encontré información sobre este tema en los documentos de la empresa. |
| `tipo` | `sin_respuesta` |
| `documento` | *(vacío)* |
| `ancla` | *(vacío)* |

La respuesta de referencia **es la frase de abstención**: es lo que el sistema
debe contestar. Cualquier otra cosa es una alucinación.

> **Que sean tangenciales, no absurdas.** "¿Cuál es la capital de Francia?" se
> rechaza con 0,139: demasiado fácil, no pone a prueba nada. "¿Cuánto cuesta
> entrenar en AWS?" pertenece al dominio y no está en el corpus — ahí es donde
> el umbral se juega de verdad.

---

## 5. Por qué frases ancla y no identificadores de fragmento

Los identificadores (`doc-39-chunk-7`) son **posicionales**, y la posición
depende de cómo se troceó. El experimento compara dos estrategias de
fragmentación: el "fragmento 7" es texto distinto en cada una.

La frase ancla vive en el **documento original**, antes de trocear, así que es
invariante a la partición y sirve de referencia común para ambas estrategias.

Es también la razón de que el dataset siga valiendo cuando se añada reranking o
RAG híbrido: cambia qué fragmentos se recuperan y en qué orden, no qué frase
contiene la respuesta.

---

## 6. Las cinco reglas de las frases ancla

**1. Copiar del texto extraído, no del PDF en pantalla.**

Los PDF vienen maquetados a dos columnas y el extractor las intercala. La misma
frase, tal como el sistema la indexa, se ve así:

```
los
VAE
utilizan
ruido
gaussiano en el espacio latente para
```

Un ancla escrita mirando el PDF no coincide nunca, y parece que la recuperación
falla cuando lo que falla es el ancla.

**2. Entre 4 y 8 palabras.** Suficiente para ser única, corta para caber dentro
de un fragmento. Un ancla larga tiene más probabilidad de quedar partida entre
dos fragmentos y no casar en ninguna estrategia, lo que castiga a las dos por
igual y no mide nada.

**3. Normalizar al comparar:** colapsar espacios en blanco y pasar a minúsculas.
Es obligatorio por el punto 1, y es una decisión metodológica que va declarada
en la memoria, no un detalle de implementación.

**4. Que aparezca una sola vez en el documento.** Si aparece dos veces, el
acierto es ambiguo y la pregunta no sirve. Comprobarlo antes de darla por buena.

**5. En las `multi`, las dos anclas en secciones distintas.** Si ambas caen en
el mismo párrafo, la pregunta es una `literal` disfrazada y no mide ensamblaje.

---

## 7. Qué se hace con él después

El dataset no es una tarea más de la lista: es el **instrumento de medida**. Una
vez existe:

1. **RAGAS** calcula la línea base: *faithfulness*, *context precision*,
   *context recall* y *answer relevancy* sobre la configuración actual.
2. **Langfuse** puede ejecutarlo contra el RAG y guardar cada resultado, que es
   lo que el tutor llamó "apuntar Langfuse hacia el RAG".
3. **Reranking** y **RAG híbrido** se miden contra esa línea base, y cada uno
   produce una fila de la tabla comparativa que constituye el capítulo 5.
4. Las **métricas de recuperación** propias —`hit@1`, `hit@3`, MRR— salen de las
   frases ancla, de forma determinista y sin coste, en paralelo a las de RAGAS.

Tener las dos vías —una determinista con anclas y una con modelo juez— es una
ventaja: si coinciden, el resultado se refuerza; si difieren, la discrepancia es
en sí misma un hallazgo del capítulo 5.

---

## 8. Una decisión pendiente

El dataset contiene **frases literales del material docente**, que es de
terceros y por eso no se publica con el repositorio (ver `README.md`).

Con anclas de 4 a 8 palabras eso constituye cita, no reproducción, y la
reproducibilidad del experimento pesa a favor de versionarlo. Pero es una
decisión que conviene consultar con el tutor antes de subirlo.
