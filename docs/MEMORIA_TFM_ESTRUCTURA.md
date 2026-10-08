# Memoria del TFM — estructura de trabajo

Guion para escribir la memoria. **No es la memoria**: es el mapa que dice, en
cada sección, qué va, cuántas páginas y de qué material sale.

- **Formato de entrega:** PDF, 50-60 páginas (presupuesto aquí: ~57)
- **Índice:** el sugerido por EBIS, respetado en orden y numeración
- **Regla:** cada afirmación sobre el sistema debe poder verificarse en el código

---

## Presupuesto de páginas

| Cap. | Título | Págs | Estado |
|---|---|---|---|
| 0 | Preliminares | 4 | ❌ |
| 1 | Introducción | 5 | 🟡 |
| 2 | Estado del arte y fundamentos | 9 | ❌ |
| 3 | Requisitos y diseño | 8 | 🟢 |
| 4 | Implementación | 10 | 🟢 |
| 5 | Evaluación y experimentos | 9 | 🔒 bloqueado |
| 6 | Pruebas y validación | 4 | 🟡 |
| 7 | Discusión | 3 | ❌ |
| 8 | Conclusiones y trabajo futuro | 3 | 🟡 |
| 9 | Bibliografía | 2 | ❌ |
| 10 | Anexos | ~3 | 🟡 |

🟢 el material existe, es redactar · 🟡 hay base parcial · ❌ de cero ·
🔒 bloqueado hasta tener medición real

**Los capítulos 4 y 5 se llevan 19 páginas entre los dos.** Es deliberado: son
donde el proyecto es fuerte y donde la rúbrica pone el peso (calidad del
código, rigor metodológico, aportación personal).

---

## Cap. 0 — Preliminares (4 págs)

Portada, agradecimientos, resumen (castellano e inglés, ~250 palabras cada uno),
índice, y el **enlace al repositorio** — exigido explícitamente.

El resumen se escribe **al final**, cuando ya sabes qué contaste.

---

## Cap. 1 — Introducción (5 págs)

### 1.1 Contexto y motivación (2)
Qué problema real resuelve KnowledgeSpace: el conocimiento de una empresa vive
disperso en documentos que nadie encuentra. Por qué importa y a quién.

> La rúbrica pide *"una situación real que necesite solución, justificando por
> qué es importante abordarla"*. No empieces por la tecnología: empieza por el
> problema. El RAG aparece en el 1.2, no aquí.

### 1.2 Objetivos (1,5)
Un objetivo general y 4-6 específicos. **Medibles** — es la palabra que usa la
rúbrica. Un objetivo específico bien formulado se puede declarar cumplido o no
al llegar al capítulo 8.

### 1.3 Alcance de la solución (1,5)
Qué entra y qué no, y **por qué**. Sale casi entero de `ALCANCE_TFM.md`.
Incluye aquí que es un MVP con alcance recortado del producto comercial: esa
honestidad puntúa.

---

## Cap. 2 — Estado del arte y fundamentos (9 págs) ❌

El capítulo que hay que construir de cero y el que exige lectura. **Empieza ya,
30 min diarios.**

### 2.1 Modelos y arquitecturas (4)
Transformer y mecanismo de atención; qué es un LLM; qué son los embeddings y
por qué la similitud coseno mide significado.

### 2.2 Técnicas de adaptación (3)
Prompting, RAG, fine-tuning, LoRA — y **por qué este proyecto eligió RAG**.
Ese "por qué" es la bisagra con el capítulo 3: conocimiento que cambia a diario,
sin coste de reentrenamiento, y con trazabilidad de la fuente.

### 2.3 Marco legal y ético (2)
Más fácil de lo que parece, porque ya está implementado:
- **RGPD**: documentos corporativos que viajan a un tercero (OpenAI)
- **Aislamiento**: `company_id` del JWT y namespaces de Pinecone
- **Alucinaciones** como riesgo ético, y el umbral de 0.30 como mitigación

> ⚠️ La rúbrica penaliza *"la simple reproducción de texto generado por
> herramientas automáticas sin adaptación propia"*. Este capítulo se escribe
> leyendo fuentes y citándolas, no pidiéndoselo a un modelo.

---

## Cap. 3 — Requisitos y diseño (8 págs) 🟢

### 3.1 Requisitos funcionales y no funcionales (2)
Los no funcionales son los que distinguen: latencia, coste por consulta,
aislamiento entre empresas. Deberían poder cruzarse con el capítulo 5.

### 3.2 Arquitectura (2,5)
**Necesita un diagrama de flujo.** Fuente: `docs/RAG_PIPELINE.md`.

### 3.3 Selección tecnológica y costes (2)
Por qué FastAPI, Pinecone, OpenAI, S3, Angular. Fuente:
`docs/DEFENSA_TECNICA_AMPLIADA.md`, que ya tiene la comparativa Pinecone vs
pgvector.

> Aquí va el **análisis de coste e inferencia**, que la rúbrica *exige*:
> desglose por tokens y servicios, y justificación frente a alternativas más
> caras (p. ej. `gpt-4o-mini` frente a `gpt-4o`). Se sostiene con datos reales
> de `cost_tracking_service.py` — no con estimaciones.

### 3.4 Diseño de datos y pipelines (1,5)
Ingesta, chunking, embeddings, almacenamiento. Fuentes: `MODELO_DATOS.md`,
`PINECONE_VECTORES.md`.

---

## Cap. 4 — Implementación (10 págs) 🟢

El capítulo más largo. La rúbrica pide **capturas de pantalla y fragmentos de
código comentados** que expliquen decisiones, no que decoren.

### 4.1 Estructura del código y componentes (2)
La arquitectura por capas: router → service → repository. Y por qué ningún
router consulta la base directamente.

### 4.2 Integración con modelos (2)
Embeddings en lote, elección de modelos, gestión de errores de API.

### 4.3 Gestión de prompts (2)
El `DEFAULT_SYSTEM_PROMPT` y **por qué el contexto va como segundo mensaje de
system** y no dentro del mensaje del usuario. Ese razonamiento ya está escrito
en `rag_service.py::_build_messages` y es exactamente el tipo de decisión
justificada que buscan.

### 4.4 Seguridad y multi-tenancy (3)
JWT, `company_id`, namespaces, el 404-en-vez-de-403. Es una de las partes más
sólidas del proyecto: dale espacio.

### 4.5 Despliegue (1)
Docker y el procedimiento de arranque.

---

## Cap. 5 — Evaluación y experimentos (9 págs) 🟡

**Parcialmente desbloqueado.** El experimento de calidad estructural del
chunking ya está ejecutado (`api/experimentos/resultados/chunking_2026-10-07.json`)
y su lectura está redactada en `api/experimentos/README.md`. Con ese material se
pueden escribir ya 5.1 y 5.4. Solo 5.3 espera números nuevos.

### 5.1 Metodología de evaluación (2)
Corpus, construcción del ground truth con frases ancla, y por qué no se usaron
identificadores de chunk. Base conceptual: `practica-tfm/GLOSARIO.md` §5.

> El argumento central: se comparan **dos estrategias de chunking**, y el chunk
> nº 3 de una no tiene contraparte en la otra. Un identificador de chunk solo
> valdría para una de las dos y haría imposible el A/B. La frase ancla es
> invariante a la partición, porque es un fragmento literal del documento
> origen. Hay que declarar aquí la normalización aplicada al comparar
> (colapsado de espacios en blanco y paso a minúsculas), obligada porque la
> extracción del PDF introduce saltos de línea dentro de las frases.

### 5.2 Métricas empleadas (1,5)

Cuatro familias, y **por qué cada una**, no solo su fórmula:

| Métrica | Qué mide | Coste |
|---|---|---|
| `hit@1`, `hit@3`, MRR | Calidad de recuperación | Céntimos |
| Latencia p50/p95 | Rendimiento percibido | Gratis |
| Tasa de abstención correcta | **Mitigación de alucinaciones** | Gratis |
| Fidelidad al contexto (rúbrica manual de 3 niveles) | Calidad de la respuesta | Tiempo |

**Precision@k y Recall@k se declaran y se descartan**, con el motivo escrito:
con un único chunk relevante por pregunta son degeneradas — `precision@5` no
puede superar 0,2 y `recall@5` solo toma los valores 0 o 1. `hit@k` dice lo
mismo sin el artefacto.

**La tasa de abstención correcta es la métrica que evalúa la contribución
principal del trabajo.** Sobre las preguntas de tipo `sin_respuesta`, mide
cuántas veces el sistema respondió "No encontré información..." en lugar de
inventar. Es objetiva, no necesita juez, y es la verificación directa del umbral
de relevancia y de las capas de validación — es decir, de la mitigación de
alucinaciones que el proyecto declara como aportación.

**La fidelidad se valora a mano, no con un LLM juez.** Sobre una muestra de este
tamaño, una rúbrica de tres niveles (sostenida / parcialmente sostenida / no
sostenida por el contexto recuperado) aplicada por una persona es más defendible
que un modelo evaluando a otro modelo. El criterio de cada nivel se escribe
aquí, antes de puntuar, no se improvisa al puntuar.

### 5.3 Resultados (3)
Tabla comparativa de las dos estrategias de chunking con los números del
harness. Gráficas. Enlace al JSON versionado en `experimentos/resultados/`.

Incluye la **revalidación del umbral de relevancia**: el `0.30` de
`rag_service.py` se midió sobre un índice construido con chunking por
caracteres, antes de que existiera `dividir_en_chunks_semantico`. Repetir las
tres familias de consultas de `RAG_PIPELINE.md` §6 sobre el índice reconstruido
y confirmar o corregir el valor. Si no se hace, los capítulos 3 y 4 afirman que
el umbral está justificado por medición mientras el capítulo 5 defiende la otra
estrategia de chunking: una incoherencia que un revisor cruza en un minuto.

### 5.4 Análisis de errores y limitaciones (2,5)
Ground truth pequeño, un solo corpus, emparejamiento literal de la frase ancla.

Material ya escrito en `api/experimentos/README.md` que va aquí:

- Muestra pequeña: 3 documentos, 24 chunks. La diferencia medida es grande, pero
  no autoriza a generalizar a cualquier corpus.
- La división por oraciones no conserva el texto exactamente (cobertura entre
  99,1 % y 100,4 %): `split(".")` altera alrededor del 1 % del contenido.
- **La hipótesis previa que resultó falsa**: se esperaba que las diapositivas
  tuvieran menos puntos que la prosa y tienen más (15,6 por mil frente a 4,9 y
  6,7). Darle párrafo propio — una hipótesis fallida reportada es la señal más
  difícil de fingir de que se midió de verdad.

Y la que nace de la decisión del 5.2:

- **Evaluador único y no ciego.** Al valorar la fidelidad a mano, el autor juzga
  su propio sistema. Se gana en interpretabilidad lo que se pierde en
  independencia; la alternativa, un LLM juez, cambia un sesgo por otro y además
  es más atacable en la defensa.

> Un resultado modesto medido con rigor vale más que una mejora grande sin
> respaldo. Si el chunking semántico mejora un 12%, se defiende el 12%.

---

## Cap. 6 — Pruebas y validación (4 págs) 🟡

Tests unitarios existentes, el test funcional pendiente, UX del frontend, y qué
observabilidad hay (logs, tracking de coste) y cuál falta.

---

## Cap. 7 — Discusión (3 págs) ❌

Lecciones aprendidas y riesgos. **El sitio más valioso de toda la memoria para
ser honesto.** Lo que de verdad costó, lo que se descartó y por qué —
el reranking evaluado y no implementado encaja aquí.

---

## Cap. 8 — Conclusiones y trabajo futuro (3 págs) 🟡

Objetivo por objetivo del 1.2, declarado cumplido o no. Trabajo futuro sale de
`BACKLOG_TFM.md`.

---

## Cap. 9 — Bibliografía (2 págs) ❌

**15-25 referencias**, formato consistente (APA o IEEE, elige uno).
Imprescindibles: Vaswani et al. sobre Transformer, Lewis et al. sobre RAG,
documentación de OpenAI y Pinecone, y fuentes sobre evaluación de recuperación.

> Es lo único que no se puede acelerar al final. Abre el archivo hoy.

---

## Cap. 10 — Anexos (~3 págs) 🟡

1. Guía de despliegue y **manual de usuario** (el manual no existe todavía)
2. Prompts completos y esquema de datos
3. Salida del harness

---

## Orden de escritura recomendado

No es el orden del índice. Se empieza por donde hay material:

1. **Cap. 5** — en cuanto haya medición real. Calibra tu ritmo de escritura.
2. **Caps. 3, 4 y 10** — redactar sobre documentación existente
3. **Cap. 2 y 9** — en paralelo desde el día 1, a 30 min diarios
4. **Caps. 1, 6, 7 y 8** — se escriben solos cuando el resto está
5. **Cap. 0** — el resumen, al final

Empezar por el capítulo 1 es la trampa clásica: es el que menos material tiene
y el más difícil en frío.
