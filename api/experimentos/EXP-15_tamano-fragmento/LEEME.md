# EXP-15 — Tamaño del fragmento: 500, 1.000 y 1.500 caracteres

**Pregunta:** ¿qué tamaño de fragmento recupera mejor, sobre los mismos
documentos?

**Por qué hacía falta:** EXP-01 comparó la *estrategia* de troceado (por
caracteres o por oraciones), pero el *tamaño*, 1.000 caracteres, venía
heredado y nunca se varió. Lo pidió el tutor el 3 de noviembre.

**Qué se fija:** los 8 documentos originales, extraídos de nuevo de S3 con los
extractores de producción; la función de troceado de producción
(`dividir_en_chunks_semantico`); `text-embedding-3-small`; las 27 preguntas y
las 9 consultas de EXP-02. La respuesta escrita a mano que hay en producción
se copia igual en las tres variantes.
**Qué se varía:** solo el tamaño objetivo. La variante de 1.000 se rehace con
el mismo procedimiento que las otras y es el control.

- Código: `842554f` con cambios locales ajenos al pipeline RAG.
- Dataset: SHA-256 `776050faa0916b2f339ac61c66698fc61e8dc3a7c7e2138c5dd8c1745c393361`.
- Espacios: `exp-chunk-500`, `exp-chunk-1000`, `exp-chunk-1500`.
- **Producción no se tocó:** 88 vectores antes y 88 después.

```
.venv\Scripts\python.exe experimentos\comparar_tamano_fragmento.py --empresa 8 --asistente 1
```

**Dos comparaciones.** Con cinco fragmentos fijos, los de 1.500 entregan el
triple de texto que los de 500. Se mide con los cinco de producción y con el
mismo volumen de texto, unos 5.000 caracteres (10, 5 y 3 fragmentos). Sin
umbral, como EXP-14. Ninguna frase ancla quedó partida entre dos fragmentos
en ninguna variante, así que la métrica no penaliza a los fragmentos pequeños.

---

## Resultado (4 de noviembre)

| Tamaño | Fragmentos | Longitud media | hit@1 (5) | hit@3 (5) | MRR (5) | MRR (mismo volumen) |
|---|---|---|---|---|---|---|
| 500 | 162 | 461 | 0,33 | 0,52 | 0,422 | 0,437 (k=10) |
| **1.000 (control)** | 88 | 850 | 0,24 | 0,52 | 0,386 | 0,386 (k=5) |
| 1.500 | 60 | 1.248 | 0,29 | 0,52 | 0,444 | 0,397 (k=3) |

**Lectura:**

- **hit@3 es idéntico en los tres tamaños (0,52).** Las diferencias están en
  la posición exacta del fragmento correcto, no en si se encuentra.
- Frente a 1.000, el de 500 mejora en 6 preguntas y empeora en 4; el de 1.500
  mejora en 8 y empeora en 4. Con 21 preguntas, ninguno de los dos repartos
  permite afirmar que un tamaño sea mejor.
- La ventaja aparente de 1.500 con cinco fragmentos se reduce a la mitad al
  igualar el volumen de texto (MRR 0,444 → 0,397): parte de su ventaja era
  recibir más texto.

**Banda de relevancia** (9 consultas de EXP-02, cinco fragmentos):

| Tamaño | Ruido máximo | Señal mínima | Margen del 0,30 sobre el ruido |
|---|---|---|---|
| 500 | 0,282 | 0,416 | 0,018 |
| 1.000 | 0,257 | 0,393 | 0,043 |
| 1.500 | 0,201 | 0,348 | 0,099 |

El 0,30 queda dentro de la banda en los tres casos, pero **con fragmentos de
500 caracteres quedaría casi pegado al ruido**: cuanto más corto es el
fragmento, más alto puntúa una consulta ajena. Cambiar el tamaño exigiría
recalibrar el umbral.

---

## El hallazgo principal: producción recorta el texto que lee el modelo

Al comparar el control con producción, que deberían coincidir, el control dio
mejores cifras (hit@3 de 0,52 frente a 0,48). La causa está en
`routers/v1/documents.py`: cada vector se calcula con el fragmento completo,
pero en sus metadatos se guarda `chunk[:1000]`, y **es ese texto recortado el
que `RAGService._build_context` entrega al modelo**.

- La función de troceado agrupa oraciones hasta unos 1.000 caracteres, pero
  una «oración» sin punto (habitual en diapositivas) puede ser más larga. En
  este corpus, **10 de los 87 fragmentos superan los 1.000 caracteres**, el
  mayor con 2.785, y el recorte les quita **5.021 caracteres en total**.
- **La pregunta 26** (en qué se diferencia StyleGAN de otras GAN): el fragmento
  correcto, `doc-39-chunk-13`, mide 1.673 caracteres y la frase que la
  responde empieza en el carácter 1.028. Producción lo recupera, pero el
  modelo solo lee los primeros 1.000 y responde que no encontró información.
  **La abstención indebida de la pregunta 26 que recoge el capítulo 5 no es un
  fallo del modelo: la causa este recorte.**
- Producción y control recuperan los mismos fragmentos en el mismo orden en
  26 de las 27 preguntas. La diferencia de cifras viene del texto, no de la
  búsqueda.

### Corrección aplicada (4 de noviembre)

1. **Código.** `routers/v1/documents.py` guarda ahora el fragmento completo
   (la construcción de los vectores pasó a `_vectores_de_documento`). El mismo
   recorte estaba en `knowledge_gap_index_service.py`, en las respuestas
   escritas a mano y en los alias, y también se quitó. Tres tests nuevos en
   `tests/test_texto_completo_en_metadatos.py`; se comprobó que fallan al
   volver a poner el recorte. Suite completa: 266 tests.
2. **Reindexado** de los 8 documentos con `reindexar.py --asistente 1`: los
   mismos fragmentos (8, 5, 5, 19, 18, 5, 6 y 21) y 88 vectores antes y
   después. `doc-39-chunk-13` tiene ahora sus 1.673 caracteres.
3. **Repetición del conjunto de referencia** con la configuración activa,
   temperatura 0, RAGAS y criterios con gpt-4.1.

| | Antes (3 de noviembre) | Después (4 de noviembre) |
|---|---|---|
| hit@1 / hit@3 / MRR | 0,24 / 0,48 / 0,362 | 0,29 / 0,52 / 0,409 |
| Abstención correcta | 6/6 | 6/6 |
| Abstención indebida | 22, 24 y **26** | 22 y 24 |
| Fidelidad / pertinencia (RAGAS) | 0,773 / 0,696 | 0,731 / 0,741 |
| Premisa falsa / parcial (gpt-4.1) | 0/3 / 2/3 | 0/3 / 2/3 |

**La pregunta 26 después del arreglo.** Ya no se abstiene: responde
correctamente en qué se diferencia StyleGAN, porque ahora el modelo lee esa
parte del fragmento. Pero añade «StyleGAN fue desarrollado por NVIDIA», y
**«NVIDIA» no aparece en ninguno de los cinco fragmentos recibidos**: el
modelo completó la otra mitad de la pregunta con su propio conocimiento. El
criterio `parcial` la sigue marcando como no cumplida, ahora por esa razón y
no por abstenerse.

**Lectura:**

- La corrección era necesaria: el modelo tiene que leer lo mismo que la
  búsqueda encontró. Una abstención indebida desaparece y la recuperación
  medida por ancla sube, porque las anclas que estaban en la parte recortada
  ahora llegan al modelo.
- El recorte **escondía otro fallo**. Mientras el modelo no veía la respuesta,
  se abstenía; al verla, aporta el dato que falta de memoria. Es el mismo
  límite de las premisas falsas: las reglas del prompt dicen qué hacer cuando
  no hay contexto, pero no frenan del todo que el modelo complete con lo que
  sabe cuando sí lo hay.
- Las cifras de RAGAS se mueven dentro del ruido entre ejecuciones (EXP-13),
  así que no se atribuyen al arreglo. La bajada de fidelidad es coherente con
  la frase sobre NVIDIA, pero no se puede separar del ruido.

**Archivos:** `resultados/dataset_ejecutado_2026-11-04_descomposicion_acotada_temp0.0_texto_completo.json`
y `resultados/ragas_2026-11-04_avanzado_descomposicion_acotada_temp0.0_texto_completo.json`.

**Para la defensa:** «Midiendo el tamaño de fragmento descubrí que el modelo
solo leía los primeros 1.000 caracteres de cada fragmento. Lo corregí, y la
pregunta 26 dejó de abstenerse. Pero al leer la respuesta completa, el modelo
añadió de memoria la empresa que creó StyleGAN, que no está en los
documentos. El recorte tapaba un segundo fallo, del mismo tipo que las
premisas falsas, y lo dejo declarado como limitación.»

---

## Decisión sobre el tamaño

**Se mantiene 1.000 caracteres.**

1. Ningún tamaño mejora de forma concluyente: hit@3 es idéntico y los
   repartos pregunta a pregunta (6–4 y 8–4) caben en el azar.
2. Al igualar el volumen de texto, la ventaja de 1.500 se reduce a la mitad.
3. Con 500, el umbral quedaría casi en el ruido y habría que recalibrarlo.
4. Cambiar obliga a reindexar y a repetir todas las mediciones del capítulo 5.

**Cómo defenderlo:** «Medí 500, 1.000 y 1.500 caracteres sobre los mismos
documentos, con cinco fragmentos y con el mismo volumen de texto. Los tres
encuentran el fragmento correcto entre los tres primeros igual de a menudo, y
las diferencias de posición no son concluyentes con 21 preguntas. Con 500, el
umbral quedaría casi pegado al ruido. Me quedo con 1.000. Y el experimento
destapó un defecto real: producción guardaba solo los primeros 1.000
caracteres de cada fragmento, y eso explicaba una de las abstenciones
indebidas.»

**Limitaciones:** 21 preguntas con ancla; un solo corpus; solo recuperación,
sin generar respuestas.
