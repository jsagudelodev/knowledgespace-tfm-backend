# Guía de las pruebas realizadas

Para preparar la defensa. Por cada decisión del sistema, el tribunal puede
preguntar **«¿por qué esto y no aquello?»**. Esta guía recoge, experimento por
experimento, qué se preguntó, cómo se midió, qué salió, qué se decidió y cómo
responderlo en voz alta.

El índice con los archivos de evidencia está en [`REGISTRO.md`](REGISTRO.md).
Las cifras salen de [`resultados/`](resultados/); si un número no está ahí, no
se cita.

*Última actualización: 3 de noviembre de 2026.*

---

## 1. Las métricas, en una línea cada una

Hay que poder explicarlas sin mirar.

| Métrica | Qué mide | Cómo se calcula aquí |
|---|---|---|
| **hit@k** | ¿Está el fragmento correcto entre los *k* primeros? | Se busca la frase ancla (una cadena literal del documento) en los *k* fragmentos recuperados |
| **MRR** | ¿En qué posición aparece el correcto? | Media de 1/posición: 1 si está primero, 0,5 si está segundo… (Voorhees, 1999) |
| **Cobertura conjunta** | En una pregunta con dos temas, ¿cuánta evidencia de ambos llega? | Porcentaje de las frases ancla de las dos subpreguntas presentes en el contexto |
| **Desequilibrio** | ¿Un tema se come el contexto del otro? | Diferencia entre los fragmentos que recibe cada subpregunta |
| **Fidelidad** (RAGAS) | ¿La respuesta se apoya en el contexto o inventa? | Un modelo juez descompone la respuesta en afirmaciones y comprueba cada una (Es et al., 2024) |
| **Pertinencia** (RAGAS) | ¿La respuesta contesta lo preguntado? | Modelo juez |
| **Precisión / exhaustividad del contexto** (RAGAS) | ¿Lo recuperado sirve y está completo? | Modelo juez contra la respuesta de referencia |
| **Abstención correcta** | Ante una pregunta sin respuesta, ¿dice que no sabe? | Conteo directo, sin juez |
| **Criterio sí/no** | ¿Corrigió la premisa falsa? ¿Inventó la parte que falta? | Una pregunta concreta a un juez gpt-4.1 |

**La idea clave para la defensa:** las métricas de recuperación (hit@k, MRR,
cobertura, abstención) se calculan comparando texto y son exactamente
reproducibles. Las de RAGAS dependen de un modelo juez y tienen ruido,
estimado en unos 3,5 puntos (EXP-07). Por eso **ninguna decisión se apoya solo
en RAGAS**.

---

## 2. Experimento por experimento

### EXP-01 — Troceado: por caracteres o por oraciones

- **Pregunta:** ¿qué le hace cada estrategia al texto?
- **Cómo:** los mismos tres PDF troceados con las dos estrategias: 1.000
  caracteres con 200 de solapamiento, frente a oraciones agrupadas hasta unos
  1.000 caracteres sin solapamiento. No llama a ningún modelo.
- **Resultado:** los fragmentos cortados a mitad de palabra bajan del 79,2 % al
  0 %. Se indexa un 19 % menos de texto, porque desaparece el solapamiento, que
  duplicaba un 23 %.
- **Decisión:** troceado por oraciones.
- **Si te preguntan «¿por qué sin solapamiento?»:** «El solapamiento existe
  para compensar un corte a ciegas: si partes una idea, repites 200 caracteres
  para que un fragmento la tenga entera. Si cortas por oraciones, no partes
  ideas y el remedio sobra. Lo medí: un 23 % de texto duplicado que dejé de
  pagar.»
- **Límite honesto:** se comparó la **estrategia**, no el **tamaño**. Los 1.000
  caracteres no están justificados por ninguna medición (ver §3).

### EXP-02 — El umbral de relevancia 0,30

- **Pregunta:** el 0,30 se fijó en junio sobre el índice antiguo; ¿sigue
  valiendo con el troceado por oraciones?
- **Cómo:** nueve consultas de tres familias (cubiertas por el corpus,
  tangenciales y ajenas). Se mide la puntuación más alta de una consulta que no
  debería encontrar nada (ruido) y la más baja de un fragmento legítimo (señal).
- **Resultado:** ruido máximo 0,258, señal mínima 0,393. El 0,30 queda dentro
  de esa banda vacía. Pero la banda se estrechó un 16 % y el margen sobre el
  ruido cayó un 41 %.
- **Decisión:** se mantiene 0,30.
- **Si te preguntan «¿por qué 0,30 y no 0,35, que está más centrado?»:**
  «Dentro de la banda, perder evidencia válida es peor que dejar pasar un
  fragmento mediocre, porque de lo mediocre ya protege el prompt. Por eso
  queda más cerca del ruido que de la señal, a propósito.»
- **Límite honesto:** nueve consultas. Y el umbral mide parecido, no si el
  fragmento responde (EXP-04 lo demuestra).

### EXP-03 — Preguntas compuestas, línea base

- **Pregunta:** ¿qué pasa si el mensaje trae dos preguntas de temas distintos?
- **Cómo:** seis parejas de preguntas. Se mide cuánta evidencia de cada una
  llega a los 5 fragmentos.
- **Resultado:** cobertura conjunta del 48 %; desequilibrio 1,83. Típicamente
  un tema recibe 4 fragmentos y el otro 1.
- **Decisión:** defecto confirmado. Motiva EXP-05 y EXP-08.
- **Si te preguntan «¿por qué falla?»:** «El mensaje entero se convierte en un
  solo vector, que queda a medio camino entre los dos temas y no se parece
  bien a ninguno.»

### EXP-04 — La línea base, de punta a punta

- **Pregunta:** ¿cómo recupera y responde el RAG básico?
- **Cómo:** las 18 preguntas del conjunto de referencia (8 literales, 4
  distribuidas, 6 sin respuesta) y RAGAS sobre las 12 que tienen respuesta.
- **Resultado:** hit@3 0,50 y MRR 0,394 (literales 0,525, distribuidas 0,133).
  Fidelidad 0,888. Abstención correcta 6/6, sin abstenciones indebidas. Latencia
  p50 2,41 s y p95 4,26 s.
- **El hallazgo:** de las 6 abstenciones, el umbral solo produjo 2. Las otras 4
  las frenó el prompt, porque los fragmentos superaron el 0,30.
- **Si te preguntan «¿cómo controla las alucinaciones?»:** «Con dos mecanismos,
  y medí que hacen falta los dos: el umbral descarta lo que no se parece, y el
  prompt obliga a abstenerse cuando lo que se parece no responde. Solo con el
  umbral habría contestado tres preguntas tangenciales.»
- **Nota:** se hizo con temperatura 0,7, la de entonces.

### EXP-05 — Descomposición sin tope

- **Pregunta:** si se parte la pregunta en subpreguntas y se busca cada una por
  separado, ¿se arregla EXP-03?
- **Resultado:** cobertura del 48 % al 88 %; las seis parejas mejoran. Pero se
  mandan entre 8 y 10 fragmentos al modelo en vez de 5, y la latencia mediana
  pasa de 2,41 s a 3,65 s.
- **Decisión:** superada por EXP-08, que consigue el reparto sin duplicar el
  contexto.

### EXP-06 — Temperatura

- **Pregunta:** el modelo generaba con temperatura 0,7 desde el principio; ¿es
  correcto para un sistema que no debe inventar?
- **Cómo:** el mismo conjunto con temperatura 0. La temperatura no afecta a la
  búsqueda, y se comprobó que las dos pasadas recuperan exactamente los mismos
  fragmentos, así que la diferencia es solo de la generación.
- **Resultado:** fidelidad de 0,888 a 0,939; fidelidad mínima de 0,538 a 0,750;
  pertinencia de 0,822 a 0,839.
- **Decisión:** temperatura 0 para todos los asistentes. La interfaz la muestra
  bloqueada.
- **Si te preguntan «¿por qué 0 y no 0,2?»:** «La temperatura controla cuánto
  se aleja el modelo de la palabra más probable. Para redactar con creatividad
  eso ayuda; para responder con lo que dice un documento, solo añade
  variación. Además el sistema era incoherente: la descomposición ya usaba 0 y
  la respuesta, que es la que no debe inventar, usaba 0,7.»
- **Límite honesto:** solo se probaron dos valores. Falta literatura (ver §4).

### EXP-07 — Reordenado (reranking)

- **Pregunta:** la línea base tiene hit@1 0,25 y hit@5 0,67: encuentra la
  evidencia pero la deja abajo. ¿Un reordenador mejora las respuestas?
- **Cómo:** se recuperan 20 candidatos, se filtran por el umbral y un modelo
  los reordena por utilidad real.
- **Resultado:** hit@3 de 0,50 a 0,667 y MRR de 0,394 a 0,447. Pero las cuatro
  métricas de RAGAS se mueven dentro del ruido del juez. El coste por consulta
  sube de 0,000265 a 0,000974 USD (×3,7) y la latencia 1,26 s.
- **Decisión:** medido, no activo.
- **Si te preguntan «¿por qué no lo activas si recupera mejor?»:** «Porque el
  modelo recibe los cinco fragmentos y los lee todos: da igual en qué orden
  lleguen. El reordenado solo serviría si después recortara el contexto a tres.
  Pagar 3,7 veces más para cambiar un orden que no importa no tiene sentido.»
- **Lección registrada:** en una primera versión, el reordenador mejoraba hit@5
  y empeoraba las respuestas. Optimizar una métrica aislada llevó a un sistema
  peor.

### EXP-08 — Reparto equilibrado (la configuración activa)

- **Pregunta:** ¿se puede dar contexto a cada subpregunta sin pagar el doble?
- **Cómo:** se mantienen los 5 fragmentos, pero se llenan por turnos: el mejor
  de cada subpregunta en cada ronda.
- **Resultado:** cobertura 52 %, desequilibrio de 1,83 a 0,83, mismo volumen de
  contexto que la base. Latencia p95 5,33 s.
- **Decisión:** **activa** (`RAG_CONFIGURACION=descomposicion_acotada`).
- **Si te preguntan «¿por qué te quedas con 52 % y no con el 88 %?»:** «Porque
  lo medí generando las respuestas (EXP-13). En las preguntas compuestas, la
  acotada responde las dos partes en 18 de 18 y la sin tope en 15 de 18. En el
  caso donde fallan, la sin tope tenía los mismos cinco fragmentos más otros
  cinco de ruido, y con ese ruido el modelo se abstuvo. Recuperar más no es
  responder mejor.»
- **⚠️ No está en la memoria.** Ver §5.

### EXP-09 — Híbrido (densa + BM25)

- **Pregunta:** el tutor preguntó si era híbrido. ¿Sumar búsqueda por palabra
  exacta mejora la recuperación?
- **Cómo:** BM25 calculado en memoria y fusionado con la búsqueda densa por
  posición (RRF). No se usó el modo híbrido de Pinecone porque exige otra
  métrica de índice y habría que reindexar.
- **Resultado:** hit@1 de 0,25 a 0,42, MRR 0,537, fidelidad 0,965 (la mejor).
  Pero la cobertura de compuestas cae del 48 % al 30 %, peor que no hacer nada.
- **Decisión:** medido, no activo.
- **Si te preguntan «¿por qué no usas el híbrido, que da la mejor fidelidad?»:**
  «Porque busca con la pregunta entera y empeora justo las preguntas de dos
  temas, que es lo que usted me preguntó en la primera tutoría. Una mejora se
  activa cuando no rompe otra cosa.»
- **Límite honesto:** BM25 sin lematizar: «modelo» y «modelos» cuentan como
  palabras distintas.
- **⚠️ No está en la memoria.** Ver §5.

### EXP-10 — Reparto + híbrido

- **Resultado:** el mejor hit@3 (0,67), MRR (0,544) y desequilibrio (0,67) de
  los medidos, pero compuestas al 37 % y la más lenta (p95 8,77 s). La
  fidelidad de 0,913 incluye ruido del juez: hay casos con contexto y respuesta
  idénticos a EXP-09 y nota distinta.
- **Decisión:** medido, no activo.
- **⚠️ No está en la memoria.**

### EXP-11 — Tipos de pregunta nuevos

- **Pregunta:** ¿cómo responde a paráfrasis, premisas falsas y preguntas
  parciales?
- **Cómo:** 9 preguntas nuevas, 3 por tipo, sobre la configuración activa. Para
  las de premisa falsa y parcial se añadió un criterio sí/no, porque RAGAS no
  mide si se corrigió la premisa. El juez gpt-4o-mini rechazó dos respuestas
  correctas, así que se cambió a gpt-4.1, que coincidió con la revisión manual.
- **Resultado:** paráfrasis 1/3, premisa falsa 0/3, parcial 2/3. Abstención
  excesiva en las preguntas 22, 24 y 26: tenía la información y no respondió.
- **Decisión:** limitación declarada en la memoria.
- **Si te preguntan «¿cuál es el fallo más grave?»:** «La premisa falsa.
  Abstenerse de más es seguro, el usuario solo pierde una respuesta. Aceptar
  una premisa falsa le enseña algo incorrecto con la apariencia de venir de su
  propia documentación.»

### EXP-12 — Reglas en el prompt contra las premisas falsas

- **Resultado:** premisa falsa de 0/3 a 1/3, pero la pertinencia cae de 0,698 a
  0,583 porque el modelo empieza a abstenerse a medias sin motivo.
- **Decisión:** revertido. Los resultados se conservan como evidencia.
- **Si te preguntan:** «Probé a corregirlo en el prompt y empeoró más de lo que
  arregló. Lo dejo como limitación medida, no escondida.»

### EXP-13, EXP-14 y EXP-15

Tienen su propia carpeta, con un `LEEME.md` que explica qué se midió, el
resultado y la decisión:

- **EXP-13** — descomposición con tope o sin tope:
  [`EXP-13_descomposicion-con-o-sin-tope/LEEME.md`](EXP-13_descomposicion-con-o-sin-tope/LEEME.md).
- **EXP-14** — `text-embedding-3-small` frente a `3-large`:
  [`EXP-14_modelo-embedding/LEEME.md`](EXP-14_modelo-embedding/LEEME.md).
- **EXP-15** — fragmentos de 500, 1.000 y 1.500, y el defecto del recorte:
  [`EXP-15_tamano-fragmento/LEEME.md`](EXP-15_tamano-fragmento/LEEME.md).

---

## 3. Lo que pidió el tutor y lo que queda sin medir

Lo pidió el tutor el 3 de noviembre. Lo medido tiene su cifra; lo que no, la
respuesta honesta de la tercera columna.

| Decisión | Por qué se tomó | Respuesta honesta hoy | Experimento previsto |
|---|---|---|---|
| Modelo de embedding `text-embedding-3-small` | Coste y simplicidad | ✅ **Medido en EXP-14:** «`3-large` mejora el MRR de 0,36 a 0,44, pero gana en 6 preguntas y pierde en 3: no es concluyente, y cambiar obliga a reindexar y repetir las mediciones. El umbral seguiría valiendo.» | Hecho |
| Fragmentos de ~1.000 caracteres | Valor heredado del troceado anterior | ✅ **Medido en EXP-15:** «500, 1.000 y 1.500 dan el mismo hit@3; las diferencias no son concluyentes y con 500 el umbral quedaría casi en el ruido.» Además destapó que producción recortaba a 1.000 el texto que lee el modelo (corregido el 4 de noviembre) | Hecho |
| `top_k = 5` | Valor habitual; no se midió | «No lo medí; con más fragmentos sube el coste y el modelo atiende peor el centro del contexto.» | No se hará: la serie se cerró con EXP-15 |
| Generador `gpt-4o-mini` | Coste: `gpt-4o` cuesta 16,7 veces más (memoria 3.3) | Medido en coste, no en calidad | Opcional |
| Pinecone frente a pgvector | Espacios de nombres para el aislamiento | La memoria ya declara que no se comparó y que pgvector habría bastado | No se hará |

**Por qué el embedding y el tamaño no se pueden cambiar «en vivo»:** los
vectores de los documentos se calcularon con un modelo concreto y con unos
fragmentos concretos. Consultar con otro modelo compara vectores de espacios
distintos, y cambiar el tamaño cambia los propios fragmentos. Cada variante
exige reindexar el corpus en su propio espacio de nombres. Saber explicar esto
vale tanto como el resultado del experimento.

---

## 4. Literatura que respalda cada decisión

**Ya en la bibliografía de la memoria (verificadas):**

| Decisión | Referencia |
|---|---|
| RAG como arquitectura | Lewis et al. (2020); Gao et al. (2023) para la taxonomía básico / avanzado / modular |
| Recuperación densa | Karpukhin et al. (2020) |
| Similitud coseno entre frases | Reimers y Gurevych (2019) |
| BM25 | Robertson y Zaragoza (2009) |
| Reordenado | Nogueira y Cho (2019) |
| Reescritura y descomposición de consultas | Ma et al. (2023) |
| MRR | Voorhees (1999) |
| RAGAS | Es et al. (2024) |
| Alucinaciones | Ji et al. (2023) |

**Candidatas para lo que falta.** Hay que localizar cada una, abrirla y
comprobar que dice lo que se le atribuye antes de citarla (regla de
`docs/TFM/BIBLIOGRAFIA.md`):

| Decisión | Candidata |
|---|---|
| Comparar modelos de embedding | Muennighoff et al. (2023), *MTEB: Massive Text Embedding Benchmark*, EACL |
| Temperatura | Holtzman et al. (2020), *The Curious Case of Neural Text Degeneration*, ICLR; Renze y Guven (2024), sobre el efecto de la temperatura |
| Tamaño de fragmento | Chen et al. (2023), *Dense X Retrieval: What Retrieval Granularity Should We Use?* |
| Descomposición | Press et al. (2023), *self-ask*; Zhou et al. (2023), *least-to-most prompting* |
| `top_k` y contexto largo | Liu et al. (2024), *Lost in the Middle*, TACL |

---

## 5. Diferencias entre la memoria y el código

**Corregidas el 4 de noviembre** (respaldo previo en
`docs/Memoria_TFM_respaldo_2026-11-04.docx`). La memoria habla ahora de seis
configuraciones (2.1, 3.2 y 4.1), presenta la descomposición acotada y EXP-13
dentro del quinto experimento, añade la híbrida como octavo y declara activa
la acotada. También se corrigió el desequilibrio de la sin tope en la tabla del
quinto experimento: decía 0,9 y la media de las seis parejas es 0,83. El
documento tiene 57 páginas.

Lo que se encontró el 3 de noviembre, antes de corregir:

- Habla de **«tres clases»** y **«tres configuraciones»** (apartados 3.2 y 5.3).
  En el código hay seis.
- Dice que **«la descomposición de consultas está activa»** y presenta el 88 %
  de EXP-05. Lo activo es la descomposición **acotada** de EXP-08, que da el
  52 %. Si el tribunal ejecuta el sistema, verá la acotada.
- **No presenta la medición del híbrido** (EXP-09 y EXP-10), que es una de las
  siete preguntas del tutor. Solo aparece en el estado del arte y en la tabla
  de pruebas.
- Dice **«siete experimentos»**. Con EXP-08 a EXP-12 son doce, aunque EXP-11
  ya figura en 5.3 como «Ampliación del conjunto de evaluación».

Esto se corrige en la memoria, no en el código.

---

## 6. Cómo reproducir

Desde `api/`, con el entorno de la aplicación (`.venv`), salvo RAGAS, que va en
su entorno aislado (`.venv-eval`) porque arrastra más de sesenta dependencias.

```bash
# Troceado (EXP-01) — no llama a ningún modelo
.venv/Scripts/python.exe experimentos/medir_chunking.py <carpeta-con-PDFs>

# Umbral (EXP-02)
.venv/Scripts/python.exe experimentos/medir_umbral.py --empresa 8 --asistente 1

# Preguntas compuestas (EXP-03, 05, 08, 09, 10)
.venv/Scripts/python.exe experimentos/medir_preguntas_compuestas.py --empresa 8 --asistente 1 --configuracion descomposicion_acotada

# Conjunto de referencia completo (EXP-04, 06, 07, 09, 10, 11)
.venv/Scripts/python.exe experimentos/ejecutar_dataset.py --empresa 8 --asistente 1 --configuracion descomposicion_acotada --temperatura 0

# RAGAS sobre el último resultado
.venv-eval/Scripts/python.exe experimentos/evaluar_ragas.py
```

`--configuracion` acepta `base`, `descomposicion`, `descomposicion_acotada`,
`reranking`, `hibrido` y `descomposicion_hibrida`. Cada ejecución completa del
conjunto de referencia cuesta céntimos de dólar en OpenAI.
