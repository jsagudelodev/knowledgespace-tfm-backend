# EXP-14 — Modelo de embedding: `3-small` frente a `3-large`

**Pregunta:** ¿recupera mejor `text-embedding-3-large` que el modelo de
producción, `text-embedding-3-small`, sobre los mismos fragmentos?

**Por qué hacía falta:** el modelo de embedding se eligió por coste y nunca se
comparó con otro. Lo pidió el tutor el 3 de noviembre.

**Hipótesis:** `3-large` recupera mejor, sobre todo en paráfrasis, porque
representa con más finura el significado.

**Qué se fija:** los mismos 88 fragmentos (copiados del espacio de producción,
con sus identificadores y metadatos), `top_k` 5, las 27 preguntas del conjunto
de referencia y las 9 consultas de EXP-02.
**Qué se varía:** solo el modelo de embedding, de los fragmentos y de la
pregunta.

- Código: `842554f` con cambios locales ajenos al pipeline RAG (ver EXP-13).
- Dataset: SHA-256 `776050faa0916b2f339ac61c66698fc61e8dc3a7c7e2138c5dd8c1745c393361`.
- Espacio del candidato: `exp-emb-3-large`, en el mismo índice. El chat no
  puede llegar a él.
- **Producción no se tocó:** 88 vectores antes y 88 después.

```
.venv\Scripts\python.exe experimentos\comparar_embeddings.py --empresa 8 --asistente 1
```

**Dos decisiones de método:**

1. **Sin umbral.** El 0,30 se calibró para `3-small`. Aplicarlo a otro modelo,
   que puntúa en otra escala, podría descartar fragmentos válidos y perjudicar
   al candidato. Se comparan los cinco primeros resultados sin filtrar, con
   métricas por frase ancla: deterministas y sin juez.
2. **`3-large` reducido a 1.536 dimensiones.** Su tamaño nativo es 3.072, pero
   el índice es de 1.536 y la API permite pedir menos dimensiones. Se mide el
   modelo reducido, no el completo.

---

## Resultado (4 de noviembre)

| Métrica (21 preguntas con ancla) | `3-small` (control) | `3-large` (1.536) |
|---|---|---|
| hit@1 | 0,24 | 0,29 |
| hit@3 | 0,48 | 0,52 |
| hit@5 | 0,62 | 0,71 |
| MRR | 0,362 | 0,443 |

Por tipo de pregunta:

| Tipo | n | MRR `3-small` | MRR `3-large` |
|---|---|---|---|
| literal | 8 | 0,525 | 0,438 |
| multi | 4 | 0,133 | 0,200 |
| paráfrasis | 3 | 0,067 | 0,333 |
| premisa falsa | 3 | 0,555 | 0,833 |
| parcial | 3 | 0,333 | 0,500 |

**Pregunta por pregunta:** `3-large` mejora en 6 (5, 11, 19, 22, 24 y 27),
empeora en 3 (1, 4 y 6) y queda igual en 12. Gana sobre todo donde hay que
reunir dos fragmentos (5, 11 y 27 pasan a encontrar las dos anclas entre los
cinco primeros) y en la paráfrasis 19, que pasa del quinto puesto al primero.
Pierde en tres preguntas literales: en la 6 («¿Qué es un LLM?») el fragmento
correcto baja del primer puesto al segundo.

**¿Es una diferencia real?** No se puede afirmar. De las 9 preguntas que
cambian, 6 favorecen a `3-large` y 3 a `3-small`. Con tan pocos casos, un
reparto así aparece por azar con frecuencia: la prueba de signos da p ≈ 0,5.
La dirección favorece a `3-large`, pero la muestra no permite sostenerla.

**Banda de relevancia** (las 9 consultas de EXP-02):

| | Ruido máximo | Señal mínima | Banda vacía | Centro |
|---|---|---|---|---|
| `3-small` | 0,258 | 0,393 | 0,135 | 0,326 |
| `3-large` | 0,232 | 0,398 | 0,166 | 0,315 |

- El control reproduce **exactamente** las cifras de EXP-02 (0,258 y 0,393).
  La búsqueda es estable entre ejecuciones, a diferencia de lo que se mide con
  modelo juez.
- Con `3-large`, la banda es un 23 % más ancha y el **0,30 sigue dentro**: si
  se cambiara de modelo, el umbral no tendría que recalibrarse.

**Coste:** convertir el corpus con `3-large` consumió 21.399 tokens, unos
0,003 USD. En el uso real el modelo de embedding apenas pesa: convertir una
pregunta son unos 25 tokens, frente a los más de 1.300 que lee el modelo
generador.

**Archivo:** `resultados/2026-11-04.json` (posiciones, puntuaciones e
identificadores de cada pregunta con los dos modelos, la banda y el recuento
de vectores de producción antes y después).

---

## Decisión

**Se mantiene `text-embedding-3-small`.**

1. La mejora de `3-large` es modesta y no concluyente: 6 preguntas a favor y 3
   en contra, sobre 21.
2. Gana en los tipos donde la muestra es más pequeña (3 o 4 preguntas) y
   pierde en el más numeroso, el literal.
3. Cambiar exige reindexar todo el corpus, y todas las mediciones del capítulo
   5 se hicieron con `3-small`: activarlo obligaría a repetirlas para que la
   memoria siga describiendo el sistema que se entrega.
4. No se midió si recuperar mejor se traduce en mejores respuestas. EXP-07 y
   EXP-13 enseñan que no siempre es así.

**Cómo defenderlo:** «Comparé `3-small` con `3-large` sobre los mismos
fragmentos, sin umbral, para no favorecer a ninguno. `3-large` mejora el MRR de
0,36 a 0,44, pero pregunta por pregunta gana en 6 y pierde en 3, y con esa
muestra la diferencia no es concluyente. El umbral de 0,30 seguiría valiendo.
Lo dejo como trabajo futuro con un conjunto de evaluación más grande, porque
cambiar el modelo obliga a reindexar todo y a repetir las mediciones.»

**Limitaciones:** 21 preguntas con ancla; `3-large` medido a 1.536
dimensiones y no a 3.072; solo recuperación, sin generar respuestas.

**El espacio `exp-emb-3-large`** queda en el índice (88 vectores). Se puede
borrar cuando ya no haga falta; no afecta a la aplicación.
