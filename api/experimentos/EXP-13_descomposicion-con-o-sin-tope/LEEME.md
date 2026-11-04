# EXP-13 — Descomposición con tope o sin tope

**Pregunta:** ¿cuál de las dos descomposiciones da mejores respuestas, la que
une todos los fragmentos de las subpreguntas (`descomposicion`, EXP-05) o la
que mantiene cinco y los reparte por turnos (`descomposicion_acotada`, EXP-08,
la activa)?

**Por qué hacía falta:** EXP-05 y EXP-08 solo midieron qué fragmentos llegan.
La sin tope recupera más evidencia (88 % frente a 52 %) con el mismo equilibrio
entre temas (0,83), y la acotada manda menos contexto y sin ruido (0 fragmentos
ajenos frente a 6). Cuál responde mejor no se había medido: la única ejecución
de la sin tope era del 12 de octubre, con temperatura 0,7, y no es comparable.

**Hipótesis:** la acotada responde igual o mejor, porque el contexto extra de
la sin tope trae ruido.

**Qué se fija:** temperatura 0, `top_k` 5, umbral 0,30, `text-embedding-3-small`,
`gpt-4o-mini`, el mismo día y el mismo código.
**Qué se varía:** solo `--configuracion`.

- Código: commit `842554f`, con cambios locales sin subir en las preguntas sin
  respuesta, las notificaciones, los documentos y la valoración. Ninguno toca
  el pipeline RAG: en `app/services` y `app/core` solo cambian
  `knowledge_gap_index_service.py` y `notification_service.py`, y el chat no
  usa ninguno de los dos para responder.
- Dataset: `dataset_evaluacion.csv`, 27 preguntas, SHA-256
  `776050faa0916b2f339ac61c66698fc61e8dc3a7c7e2138c5dd8c1745c393361`.
- Corpus: empresa 8, asistente 1, `company-8-assistant-1`.

---

## Parte A — las 27 preguntas del conjunto de referencia (3 de noviembre)

| Métrica | Sin tope | Acotada (activa) |
|---|---|---|
| hit@1 / hit@3 / hit@5 | 0,24 / 0,43 / 0,62 | 0,24 / 0,48 / 0,62 |
| MRR | 0,363 | 0,362 |
| Abstención correcta | 6/6 | 6/6 |
| Abstención indebida | 22, 24, 26 | 22, 24, 26 |
| Fidelidad (RAGAS) | 0,783 | 0,773 |
| Pertinencia (RAGAS) | 0,650 | 0,696 |
| Precisión del contexto (RAGAS) | 0,745 (n=18)* | 0,753 |
| Exhaustividad del contexto (RAGAS) | 0,893 | 0,925 |
| Premisa falsa / parcial (juez gpt-4.1) | 0/3 / 2/3 | 0/3 / 2/3 |
| Latencia p50 / p95 | 3,45 s / 6,32 s | 3,74 s / 5,79 s |
| Tokens totales | 45.874 | 39.363 |

\* RAGAS no pudo puntuar tres preguntas de la sin tope.

**El ruido entre ejecuciones.** La acotada se había medido ya el 23 de octubre
con la misma configuración. Entre aquel día y hoy, 8 de las 27 preguntas
recuperaron otros fragmentos y 9 cambiaron de respuesta, y la precisión del
contexto pasó de 0,810 a 0,753 sin cambiar nada. **Cualquier diferencia de menos
de unos 6 puntos entre configuraciones está dentro de lo que varía la misma
configuración de un día para otro.** La causa no está aislada; la candidata es
la llamada que decide si se descompone, que no da siempre la misma salida.

**Lectura:**

- En las preguntas de este conjunto **las dos son indistinguibles**: todas las
  diferencias caen dentro de ese ruido. 20 de las 27 recibieron exactamente el
  mismo contexto.
- La sin tope gasta un **17 % más de tokens** y no es por las preguntas
  compuestas: descompuso también dos paráfrasis de un solo tema (20 y 21), que
  pasaron de 5 fragmentos a 11 y 14. Es el riesgo de no tener tope: un falso
  positivo de la descomposición multiplica el contexto.
- Este conjunto tiene **una sola** pregunta con dos temas de verdad (la 9). Las
  `multi` son comparaciones entre dos conceptos. Por eso la parte A no puede
  decidir entre las dos: donde se diferencian es en las preguntas compuestas.

**Archivos** (en `resultados/`, con el nombre de los scripts actuales):

- `dataset_ejecutado_2026-11-03_descomposicion_temp0.0.json`
- `dataset_ejecutado_2026-11-03_descomposicion_acotada_temp0.0.json`
- `ragas_2026-11-03_avanzado_descomposicion_temp0.0.json`
- `ragas_2026-11-03_avanzado_descomposicion_acotada_temp0.0.json`

**Incidencia registrada.** Al recalcular los criterios con gpt-4.1,
`evaluar_ragas.py --solo-criterios` juzgó las respuestas de la sin tope y
escribió los veredictos en el JSON de la acotada, porque tomaba la entrada del
`dataset_ejecutado` más reciente. Se corrigió el script, que ahora usa la
entrada que figura en el propio JSON de RAGAS y se niega si se le indica otra,
y se repitió el juicio. La cifra no cambió (0/3 y 2/3), pero el veredicto
equivocado queda en `criterios_anteriores` del JSON de la acotada, como
entrada del 2026-11-03 con juez gpt-4.1. Se comprobó que las cifras del 23 de
octubre no se vieron afectadas: sus justificaciones corresponden a las
respuestas de ese día.

---

## Parte B — las 6 parejas compuestas, con respuesta generada (3 de noviembre)

Las seis preguntas compuestas de EXP-03 («que es un VAE y que es la geometria
semantica»…), respondidas por las dos configuraciones con el pipeline del chat
y temperatura 0, **tres veces cada una**, alternando configuraciones dentro de
cada repetición. Un juez gpt-4.1 lee las dos preguntas, el contexto que recibió
el sistema y la respuesta, y clasifica cada parte como RESPONDE, ABSTIENE u
OMITE, y si la respuesta afirma algo que no está en el contexto. El criterio
está en `juez_compuestas.py` y sus tests en `tests/test_juez_compuestas.py`.

```
.venv\Scripts\python.exe experimentos\responder_compuestas.py --empresa 8 --asistente 1
```

| | Sin tope | Acotada (activa) |
|---|---|---|
| **Responde las dos partes** | **15/18** | **18/18** |
| Partes respondidas / abstenidas / omitidas | 30 / 6 / 0 | 36 / 0 / 0 |
| Afirma algo fuera del contexto | 1/18* | 0/18 |
| Fragmentos por respuesta | 9,7 | 5 |
| Tokens por respuesta | 2.943 | 1.639 (un 44 % menos) |
| Latencia p50 | 6,27 s | 6,32 s |
| Parejas con las dos partes en las 3 repeticiones | 5 de 6 (falla la 4) | 6 de 6 |

\* Es la misma respuesta de abstención de la pareja 4: el juez considera falso
decir «no encontré información» cuando el contexto la tiene. No añade ningún
dato inventado.

**El caso que decide, la pareja 4** («que es el test de Turing y que es la
geometria semantica»). Revisado a mano en la repetición 1:

- La acotada recibe 5 fragmentos y responde bien las dos partes.
- La sin tope recibe 10, **entre ellos los mismos 5 de la acotada**, más cinco
  que no tratan de ninguna de las dos preguntas: los axiomas de una métrica de
  distancia, dos tablas comparativas de modelos y la celda de una LSTM.
- Con esos 10, el modelo responde «No encontré información sobre este tema en
  los documentos de la empresa». Igual en las tres repeticiones.

Es decir, **con la misma evidencia más ruido, el sistema dejó de responder**.
No es un fallo de recuperación, porque la evidencia estaba: el exceso de
contexto hizo que el modelo no reconociera la respuesta y se abstuviera.

**Límites:**

- Seis parejas, y la diferencia viene de una sola. Es sistemática (3 de 3),
  así que no es casualidad de una ejecución, pero no permite estimar una tasa.
- El juez es un modelo. Las 36 respuestas están en `2026-11-03_parte-b.md`
  para revisarlas a mano.
- No se aisló por qué el ruido provoca la abstención y no una respuesta
  incompleta. Es coherente con lo que describe la literatura sobre contextos
  largos (Liu et al., 2024, *Lost in the Middle*, pendiente de verificar),
  pero aquí solo se observó, no se explicó.

**Archivos:** `resultados/2026-11-03_parte-b.json` (todo, con commit,
parámetros, contextos y la salida literal del juez) y
`resultados/2026-11-03_parte-b.md` (las respuestas para leer).

---

## Decisión

**Se mantiene la descomposición acotada.** Ahora con evidencia de respuesta,
no solo de recuperación:

1. En las preguntas normales, las dos son indistinguibles (parte A).
2. En las compuestas, la acotada responde las dos partes en 18 de 18 y la sin
   tope en 15 de 18 (parte B).
3. Donde se diferencian, la sin tope tenía la misma evidencia más ruido y se
   abstuvo: recuperar más fragmentos no significó responder mejor.
4. La acotada gasta un 44 % menos de tokens en las compuestas y un 17 % menos
   en el conjunto general, sin perder latencia.

**Cómo defenderlo:** «La sin tope recupera más evidencia, el 88 % frente al
52 %, y por eso la medí también generando respuestas. En las compuestas, la
acotada responde las dos partes en 18 de 18 y la sin tope en 15 de 18. En el
caso donde fallan, la sin tope tenía los mismos cinco fragmentos más otros
cinco de ruido, y con ese ruido el modelo se abstuvo. Recuperar más no es
responder mejor, y esa es la razón de tener tope.»

**Consecuencia para la memoria:** el capítulo 5 presenta el 88 % de la sin
tope como el resultado de la configuración activa. Debe presentar la acotada
(52 % de cobertura, desequilibrio 0,83) y este experimento como la razón de
elegirla.
