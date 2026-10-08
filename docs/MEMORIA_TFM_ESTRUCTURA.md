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

## Cap. 5 — Evaluación y experimentos (9 págs) 🔒

**Bloqueado hasta ejecutar el harness real.** No se redacta antes.

### 5.1 Metodología de evaluación (2)
Corpus, construcción del ground truth con frases ancla, y por qué no se usaron
identificadores de chunk. Base conceptual: `GLOSARIO.md` §5.

### 5.2 Métricas empleadas (1,5)
Precision@k, Recall@k, MRR, latencia p50/p95, faithfulness — y **por qué cada
una**, no solo su fórmula.

### 5.3 Resultados (3)
Tabla comparativa de configuraciones con los números que salgan del harness.
Gráficas. Enlace al JSON de resultados versionado.

### 5.4 Análisis de errores y limitaciones (2,5)
Ground truth pequeño, un solo corpus, emparejamiento literal de la frase ancla,
el LLM juez como evaluador imperfecto.

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
