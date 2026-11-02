# Entrega del TFM — índice central

Todo lo que pide la guía oficial del TFM —separando lo exigido de lo sugerido
y de lo que es decisión propia—
([`[MID] Orientaciones y pautas TFM.pdf`](%5BMID%5D%20Orientaciones%20y%20pautas%20TFM.pdf)),
dónde está cada cosa y qué falta. Última revisión: 2026-11-02.

La documentación de esta carpeta es la de la entrega. El material de trabajo
(preparación de la defensa, tutorías, auditorías internas) está en
[`docs/trabajo/`](../trabajo/) y en `doc/trabajo/` del frontend.

**Repositorios** (privados; se da acceso de lectura al revisor desde
*Settings → Collaborators*):

- Backend: https://github.com/jsagudelodev/knowledgespace-tfm-backend
- Frontend: https://github.com/jsagudelodev/knowledgespace-tfm-frontend
- Aplicación desplegada: https://knowledgespace-tfm-frontend.vercel.app

Las credenciales del usuario de demostración **no se escriben en ningún
repositorio**: van en la memoria (anexo 10.1).

---

## 1. Lo que pide la guía y dónde se cumple

La columna **Tipo** distingue tres cosas que no hay que confundir:

- **Exigido**: la guía lo escribe como obligación. Se cita la página.
- **Sugerido**: aparece en el índice «a modo de ejemplo» (pág. 4) o como
  recomendación. No es obligatorio, pero seguirlo ayuda a cumplir los
  criterios de evaluación (págs. 5–7).
- **Propio**: decisión del proyecto; la guía no lo pide. Se justifica porque
  la memoria se puntúa por «rigor metodológico», «análisis crítico» y
  «justificación de las decisiones» (pág. 6), no porque sea un requisito.

### Aplicación

| Qué | Tipo | Dónde | Estado |
|---|---|---|---|
| Backend y lógica de IA en Python | Exigido (pág. 2) | `api/` (FastAPI) | ✅ |
| Frontend en otro lenguaje | Permitido (pág. 2) | repositorio del frontend (Angular) | ✅ |
| Solución reproducible, con instrucciones para desplegar y probar | Exigido (pág. 2) | [`DEPLOYMENT.md`](DEPLOYMENT.md) | ✅ |
| Credenciales externalizadas y cómo reconstruir el archivo | Exigido (pág. 2) | `api/.env.example` y [`DEPLOYMENT.md`](DEPLOYMENT.md) §2 | ✅ |
| Qué servicios usa la aplicación | Exigido (pág. 2) | [`DEPLOYMENT.md`](DEPLOYMENT.md) §1 | ✅ |
| Repositorio privado con acceso al corrector | Exigido el repositorio; privado, recomendado (pág. 3) | GitHub | ⚠️ Falta dar acceso al revisor |
| Calidad de código, excepciones, latencia, escalabilidad | Criterio de evaluación (pág. 5) | `ruff` y ESLint; excepciones tipadas; tests; latencia medida; Cloud Run | ✅ |
| Aplicación desplegada en la nube | Propio: la guía pide que sea ejecutable, no que esté desplegada | Vercel + Cloud Run | ✅ |
| `README` al día | Criterio «Documentación» (pág. 5) | `README.md` de cada repositorio | ✅ El del backend se corrigió el 2026-10-28 (despliegue continuo, Alembic, tests) |

### Memoria (PDF, 50–60 páginas como máximo)

| Qué | Tipo | Capítulo | Estado |
|---|---|---|---|
| Extensión máxima de 60 páginas | Exigido (pág. 3) | — | ⚠️ Controlar al añadir imágenes |
| Introducción: por qué, para quién, dónde aplica | Exigido (pág. 3) | 1 | ✅ |
| Metodología: coordinación, implementación, testeo y métricas | Exigido (pág. 3) | 1 / 5 / 6 | ⚠️ Falta la frase del trabajo individual; la pág. 8 evalúa «la contribución individual de cada miembro» |
| **Capturas de pantalla de la interfaz** | Exigido (pág. 3) | 4, 5, 6 | ❌ La memoria no tiene imágenes (ver §3) |
| **Fragmentos de código críticos, comentados** | Exigido (pág. 3) | 3, 4 | ❌ Pendiente (ver §4) |
| Conclusión, evaluación de resultados y trabajo futuro | Exigido (pág. 3) | 5 y 8 | ⚠️ 5 hecho; 8 pendiente |
| **Dirección del repositorio** | Exigido (pág. 3) | 1 y anexo 10.1 | ❌ Pendiente (texto en §2) |
| Desglose del costo de inferencia y justificación frente a alternativas | Exigido: «se exige» (pág. 7) | 3.3 | ✅ Tokens y comparación gpt-4o-mini / gpt-4o |
| Costo de alojamiento (hosting, APIs) y retorno de la inversión | Exigido: «se exige» (pág. 7) | 3.3 | ⚠️ Redactado el 2026-11-01 con el gasto real de octubre; falta pegarlo |
| Utilidad diferencial frente a soluciones existentes | Criterio de evaluación (pág. 7) | 2 | ❌ Un párrafo dentro del capítulo 2 |
| Optimización de latencia y escalabilidad | Criterio de evaluación (pág. 5) | 3.2 y 4.5 | ⚠️ El streaming va en el párrafo de la figura 3.2; falta una frase de escalabilidad en 4.5 |
| Prompts relevantes y bien diseñados | Criterio de evaluación (pág. 7) | 4.3 | ✅ |
| Estado del arte y bibliografía citada | Sugerido (índice); criterio de nota «fundamentación teórica» (pág. 5) | 2 y 9 ([`BIBLIOGRAFIA.md`](BIBLIOGRAFIA.md)) | ❌ Pendiente, versión corta: 3–4 páginas (LLM, RAG, RGPD y Reglamento de IA) |
| Diagrama de flujo de la arquitectura | Sugerido (índice, 3.2) | 3.2 ([`figuras/figura-3.2-flujo-consulta.png`](figuras/figura-3.2-flujo-consulta.png), fuente en [`DIAGRAMA_FLUJO_RAG.md`](DIAGRAMA_FLUJO_RAG.md) §1) | ⚠️ Figura hecha; falta insertarla con su párrafo en lugar del `⟨PENDIENTE⟩` |
| Diseño de datos y pipelines | Sugerido (índice, 3.4) | 3.4 ([`MODELO_DATOS.md`](MODELO_DATOS.md), [`RAG_PIPELINE.md`](RAG_PIPELINE.md)) | ✅ |
| Análisis de errores y limitaciones | Sugerido (índice, 5.3) | 5.3 y 5.4 | ⚠️ Redactados el 2026-10-28; falta pasarlos a la memoria |
| Observabilidad | Sugerido, «si aplica» (índice, 6.3) | 6.3 ([`OBSERVABILIDAD.md`](OBSERVABILIDAD.md)) | ✅ |
| Anexo: despliegue y manual de usuario | Sugerido (índice, 10.1) | 10.1 ([`DEPLOYMENT.md`](DEPLOYMENT.md) + `doc/MANUAL_USUARIO.md` del frontend) | ⚠️ Hecho en los repositorios; falta la versión corta en la memoria |
| Resultados completos de la evaluación | Sugerido (índice, anexos) | 10.3 ([`DATASET_PREGUNTAS.md`](DATASET_PREGUNTAS.md), `api/experimentos/resultados/`) | ⚠️ Falta en la memoria |
| Dataset ampliado (de 18 a 27 preguntas, con 3 tipos nuevos), RAGAS, juez con criterios sí/no, Langfuse | Propio: la guía pide métricas, no cuáles | 5 y 6.3 | ✅ Cerrado: no ampliar más |
| Documentos técnicos de esta carpeta (`DATASET_PREGUNTAS`, `RAG_PIPELINE`, `MODELO_DATOS`…) y este índice | Propio: material de apoyo del repositorio | `docs/TFM/` | ✅ |

**Extensión:** la copia del 19-10 ya tiene unas 18.700 palabras sin imágenes
ni capítulo 2. Al añadirlos se superarían las 60 páginas: el detalle por
experimento del 5.3 (3.350 palabras) pasa al anexo 10.3, y en el cuerpo queda
la tabla resumen con sus conclusiones.

### Defensa (10 minutos de exposición y 5 de preguntas)

| Qué | Tipo | Estado |
|---|---|---|
| Ajustarse a 10 + 5 minutos | Exigido (pág. 5) | ❌ Pendiente de ensayar con reloj |
| Presentación con apoyo visual | Criterio de evaluación (pág. 7) | ❌ Pendiente |
| Vídeo demostrativo | Recomendado (pág. 3) | ❌ Pendiente |
| Ensayo | Propio | Primer simulacro hecho el 2026-10-21 (5,7/10) |

---

## 2. Texto para la memoria: repositorios

> El código fuente de la solución está disponible en dos repositorios privados,
> a los que se dará acceso al tribunal evaluador:
> - Backend (Python, FastAPI): https://github.com/jsagudelodev/knowledgespace-tfm-backend
> - Frontend (Angular): https://github.com/jsagudelodev/knowledgespace-tfm-frontend
>
> La aplicación desplegada puede probarse en
> https://knowledgespace-tfm-frontend.vercel.app con el usuario de demostración
> indicado en el anexo 10.1.

---

## 3. Capturas para la memoria

Las 18 capturas están en `doc/capturas/` del frontend y se usan en
`doc/MANUAL_USUARIO.md`. Para la memoria se eligen cinco (revisado el
2026-11-01):

| Captura | Apartado | Pie de figura |
|---|---|---|
| `02-dashboard.jpg` | 4.1 | Panel principal de KnowledgeSpace para un usuario de empresa |
| `09-chat-fragmento-citado.jpg` | 4.2 | Respuesta con las fuentes consultadas, su relevancia, el fragmento citado y el costo de la consulta |
| `05-temperatura-fija.jpg` | 5.3 (sexto experimento) | Formulario de asistente: la temperatura queda fijada en 0 tras medir su efecto en la fidelidad |
| `10-chat-abstencion.jpg` | 5.3 | Abstención ante una pregunta cuya respuesta no está en la documentación |
| [`figuras/figura-objetivo4-respuesta-indexada.jpg`](figuras/figura-objetivo4-respuesta-indexada.jpg) | 8 (objetivo 4) | El chat responde con una respuesta redactada manualmente desde «Preguntas sin respuesta» (fuente «Respuesta directa», 89 %) |

Descartadas:

- `08-chat-respuesta-con-fuentes.jpg`: repite lo que muestra la 09.
- `12-preguntas-sin-respuesta.jpg`: muestra el indicador «9,4 % de las
  consultas encuentran fuente», calculado sobre meses de consultas de prueba,
  que choca con los resultados del capítulo 5 sin explicación.
- La figura del objetivo 4 se recorta al panel del chat: al fondo aparece una
  pregunta de prueba personal.
- `16-usuarios.jpg` y `17-empresas.jpg` muestran correos y nombres reales; no
  se usan.

---

## 4. Fragmentos de código para la memoria

Cuatro fragmentos, uno por idea central. Están en el código; antes de pegarlos
en la memoria, copiarlos de nuevo desde el archivo por si cambiaron.

| # | Idea | Archivo | Qué copiar | Apartado |
|---|---|---|---|---|
| 1 | Umbral de relevancia y contexto vacío explícito | `api/app/services/rag_service.py` | El filtro `relevant_docs = [...] >= RELEVANCE_THRESHOLD` y el mensaje «No se encontró contexto relevante…» de `_build_messages` | 4.2 |
| 2 | Reglas contra alucinaciones que la personalidad no puede anular | `api/app/services/rag_service.py` | `construir_prompt_de_sistema` | 4.3 |
| 3 | Aislamiento entre empresas | `api/app/services/pinecone_service.py` y `api/app/repositories/base.py` | `construir_namespace` y `get_of_company` | 4.4 |
| 4 | Costo de cada consulta | `api/app/services/cost_tracking_service.py` | `calculate_cost` | 3.3 |

Cada fragmento lleva debajo una o dos frases que expliquen por qué importa: la
guía pide que no sean elementos aislados.

---

## 5. Contenido de esta carpeta

| Archivo | Para qué |
|---|---|
| `[MID] Orientaciones y pautas TFM.pdf` | La guía oficial |
| [`DEPLOYMENT.md`](DEPLOYMENT.md) | Guía de despliegue (anexo 10.1) |
| [`DATASET_PREGUNTAS.md`](DATASET_PREGUNTAS.md) | Dataset de evaluación: tipos, métricas, resultados y hallazgos (capítulo 5) |
| [`RAG_PIPELINE.md`](RAG_PIPELINE.md) | El pipeline RAG y la justificación del umbral |
| [`DIAGRAMA_FLUJO_RAG.md`](DIAGRAMA_FLUJO_RAG.md) | Diagrama de flujo del pipeline (3.2) |
| [`MODELO_DATOS.md`](MODELO_DATOS.md) | Modelo de datos (3.4) |
| [`OBSERVABILIDAD.md`](OBSERVABILIDAD.md) | Langfuse, trazas y costes (6.3) |
| [`BIBLIOGRAFIA.md`](BIBLIOGRAFIA.md) | Bibliografía de trabajo (capítulo 9) |

Fuera de esta carpeta, pero parte de la entrega:

- `ALCANCE_TFM.md` (raíz de cada repositorio): qué entra en la entrega y qué no.
- `COMO_ARRANCAR.md`: arranque local del backend paso a paso.
- `api/experimentos/`: los scripts de evaluación, la guía del dataset y los
  resultados con fecha.
- Frontend `doc/MANUAL_USUARIO.md` y `doc/capturas/`: manual de usuario.

---

## 6. Pendientes, por orden

Criterio acordado el 2026-11-01: hacer lo que pide la guía, sin ampliar, y
dedicar el tiempo restante a pulir el código.

### Lo que falta (al 2026-11-02)

Estado: el contenido que exige la guía ya está escrito. La memoria tiene 55
páginas y 23.832 palabras.

**Urgente:**

- [ ] Subir el arreglo del registro público (`api/app/routers/v1/auth.py`, `api/tests/test_auth_router.py`). Mientras no se suba, la ruta sigue abierta en producción

**Lo hace el autor (nadie puede hacerlo por él):**

- [ ] Leer el capítulo 2 completo y adaptarlo a su voz, sobre todo la comparación con ChatGPT y NotebookLM
- [ ] Leer en voz alta el 5.3 y el 5.4 y ajustarlos a su forma de hablar
- [ ] Concretar en el trabajo futuro (cap. 8) qué significa «nuevas interfaces adaptadas a cada perfil de usuario»
- [ ] Revisar el 6.2 y el 7.2 y prepararse para defender el hallazgo del registro
- [ ] Comprobar que los objetivos de 1.2 coinciden con la propuesta aprobada
- [ ] Revisar `ALCANCE_TFM.md` (lo modificó él)

**Lo redacta Claude y lo revisa el autor:**

- [ ] Resumen y abstract (media página cada uno)
- [ ] Anexo 10.1 corto: usuario de demostración y enlaces (credenciales solo aquí, nunca en los repos)
- [ ] Anexo 10.3: parte del detalle del 5.3, para no pasar de 60 páginas
- [ ] Portada (solo el autor) e índice automático de Word

**Cierre:**

- [ ] Exportar a PDF y comprobar que no pasa de 60 páginas
- [ ] Dar acceso de lectura al revisor en los dos repositorios
- [ ] Subir `docs/TFM/figuras/figura-objetivo4-respuesta-indexada.jpg` y este archivo
- [ ] Reactivar Supabase (plan gratuito: se pausa tras una semana sin uso) antes de la entrega y de la defensa

**Defensa (10 minutos de exposición y 5 de preguntas):**

- [ ] Presentación
- [ ] Vídeo demostrativo
- [ ] Ensayo cronometrado (primer simulacro, del 21-10: 5,7/10)

### Hecho

**Pegar (ya redactado):**

Hecho el 2026-11-01 directamente en `docs/Memoria_TFM.docx` (respaldo del
original en `docs/Memoria_TFM_respaldo_2026-11-01.docx`; ambos fuera de git):

- [x] Figura del flujo de consulta en 3.2 (Figura 1), con un párrafo corto que completa la descripción y la frase «el umbral mide parecido, no si responde» añadida a «El punto en el que se decide todo»
- [x] Dirección de los repositorios (final de 1.3) y trabajo individual (3.3)
- [x] Costo de alojamiento y retorno (final de 3.3) y la frase de la temperatura corregida
- [x] Las cinco capturas: Figuras 2 (4.1), 3 (4.2), 4 (5.3, abstención), 5 (5.3, temperatura) y 6 (capítulo 8)
- [x] Capítulo 8: apertura y tabla de objetivos
- [x] Despliegue de demostración y escalabilidad (4.5)
- [x] Coherencia: formatos PDF/DOCX/TXT/Markdown en 1.3 y RF-1; despliegue continuo sin integración continua (1.3); despliegue propio del TFM (1.3)

- [x] 5.1 (ampliación del conjunto y criterio binario), 5.3 (tabla por tipo) y 5.4 (premisas falsas, prompt en dos capas, tamaño de la muestra)
- [x] Los cuatro fragmentos de código, comentados: costo (3.3), prompt en dos capas y umbral (4.3), aislamiento (4.4)
- [x] Coherencia: la personalidad ya no sustituye las reglas (4.3, texto y tabla); el aislamiento usa `get_of_company` y se quitó la cifra de «45 veces en 13 enrutadores» (4.4); el alcance global aparece como corregido (5.4)

Resultado verificado abriendo el archivo con Word: 50 páginas, 21.187
palabras, 6 figuras y 4 fragmentos de código.

**Redactar (versión corta):**

- [x] Capítulo 2: unas 1.340 palabras (2.1, 2.2 con la comparación con soluciones existentes, 2.3 solo RGPD y Reglamento de IA); cita las 21 fuentes de la bibliografía y ninguna más (2026-11-01). Pendiente que el autor lo lea y lo adapte a su voz
- [x] Capítulo 8: trabajo futuro (2026-11-01; cubre las cinco remisiones al trabajo futuro que hace el resto de la memoria)
- [x] 6.2 UX (tres párrafos, con la falta de evaluación con usuarios declarada) y 7.2 Riesgos (tabla Riesgo / Mitigación / Riesgo residual y el hallazgo del registro público) (2026-11-02)
- [x] 6.1 actualizado: de 66 a 207 pruebas, con la tabla por ámbito rehecha (2026-11-02)
- [x] Eliminado `POST /api/v1/auth/register`: era público y tomaba `company_id` del cuerpo, lo que contradecía el 4.4. Hay un test que comprueba que ya no existe (2026-11-02)

Resultado verificado con Word el 2026-11-02: 55 páginas y 23.832 palabras.
Respaldo en `docs/Memoria_TFM_respaldo_2026-11-02.docx`.
