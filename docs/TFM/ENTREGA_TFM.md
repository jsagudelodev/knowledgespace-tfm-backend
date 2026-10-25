# Entrega del TFM — índice central

Todo lo que exige la guía oficial del TFM
([`[MID] Orientaciones y pautas TFM.pdf`](%5BMID%5D%20Orientaciones%20y%20pautas%20TFM.pdf)),
dónde está cada cosa y qué falta. Última revisión: 2026-10-25.

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

## 1. Lo que exige la guía y dónde se cumple

### Aplicación

| Exigencia | Dónde | Estado |
|---|---|---|
| Backend y lógica de IA en Python | `api/` (FastAPI) | ✅ |
| Frontend en otro lenguaje (permitido) | repositorio del frontend (Angular) | ✅ |
| Solución reproducible, con instrucciones de despliegue | [`DEPLOYMENT.md`](DEPLOYMENT.md) | ✅ |
| Credenciales externalizadas y cómo reconstruir el archivo | `api/.env.example` y [`DEPLOYMENT.md`](DEPLOYMENT.md) §2 | ✅ |
| Qué servicios usa la aplicación | [`DEPLOYMENT.md`](DEPLOYMENT.md) §1 | ✅ |
| Calidad de código y gestión de excepciones | `ruff` y ESLint sin avisos; excepciones tipadas; tests en ambos repos | ✅ |
| Latencia y escalabilidad | Latencia medida en `api/experimentos/`; Cloud Run escala solo | ✅ |
| Aplicación funcional y desplegada | Vercel + Cloud Run | ✅ |
| `README` al día | `README.md` de cada repositorio | ⚠️ El del backend aún dice que el despliegue quedó fuera de alcance y que no hay Alembic |

### Memoria (PDF, 50–60 páginas como máximo)

| Exigencia | Capítulo | Estado |
|---|---|---|
| Introducción: por qué, para quién, dónde aplica | 1 | ✅ |
| Estado del arte y fundamentos, con bibliografía citada | 2 y 9 ([`BIBLIOGRAFIA.md`](BIBLIOGRAFIA.md)) | ❌ Pendiente |
| Metodología: cómo se coordinó, implementó y testeó | 1 / 5 / 6 | ⚠️ Falta una frase: el TFM es grupal y se hizo de forma individual |
| Arquitectura y diagrama de flujo | 3.2 ([`DIAGRAMA_FLUJO_RAG.md`](DIAGRAMA_FLUJO_RAG.md)) | ⚠️ Queda un marcador `⟨PENDIENTE⟩` |
| Diseño de datos y pipelines | 3.4 ([`MODELO_DATOS.md`](MODELO_DATOS.md), [`RAG_PIPELINE.md`](RAG_PIPELINE.md)) | ✅ |
| Costes de inferencia y justificación frente a alternativas | 3.3 | ✅ |
| Métricas, resultados y análisis de errores | 5 ([`DATASET_PREGUNTAS.md`](DATASET_PREGUNTAS.md)) | ⚠️ Faltan los hallazgos del 23–25 de octubre en 5.3 y 5.4 |
| Observabilidad | 6.3 ([`OBSERVABILIDAD.md`](OBSERVABILIDAD.md)) | ✅ |
| **Capturas de pantalla de la interfaz** | 4, 5, 6 | ❌ La memoria no tiene imágenes (ver §3) |
| **Fragmentos de código críticos, comentados** | 3, 4 | ❌ Pendiente (ver §4) |
| **Dirección del repositorio** | 1 y anexo 10.1 | ❌ Pendiente (texto en §2) |
| Conclusiones y trabajo futuro | 8 | ❌ Pendiente |
| Anexo: despliegue y manual de usuario | 10.1 ([`DEPLOYMENT.md`](DEPLOYMENT.md) + `doc/MANUAL_USUARIO.md` del frontend) | ⚠️ Hecho en los repositorios; falta la versión corta en la memoria |
| Resultados completos de la evaluación | 10.3 ([`DATASET_PREGUNTAS.md`](DATASET_PREGUNTAS.md), `api/experimentos/resultados/`) | ⚠️ Falta en la memoria |

**Extensión:** la memoria tiene unas 18.100 palabras sin imágenes ni capítulo
2. Al añadirlos hay riesgo de superar las 60 páginas: el detalle debe ir a los
anexos.

### Defensa (10 minutos de exposición y 5 de preguntas)

| Exigencia | Estado |
|---|---|
| Presentación con apoyo visual | ❌ Pendiente |
| Vídeo demostrativo (recomendado) | ❌ Pendiente |
| Ensayo | Primer simulacro hecho el 2026-10-21 (5,7/10) |

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
`doc/MANUAL_USUARIO.md`. Para la memoria se eligen seis:

| Captura | Apartado | Pie de figura |
|---|---|---|
| `02-dashboard.jpg` | 4.1 | Panel principal de KnowledgeSpace para un usuario de empresa |
| `05-temperatura-fija.jpg` | 4.3 | Formulario de asistente: la temperatura se fija en 0 tras medir su efecto en la fidelidad |
| `08-chat-respuesta-con-fuentes.jpg` | 4.2 | Respuesta con las fuentes consultadas, su relevancia y el costo de la consulta |
| `09-chat-fragmento-citado.jpg` | 4.2 | Fragmento exacto del documento que sustenta la respuesta |
| `10-chat-abstencion.jpg` | 5.3 | Abstención ante una pregunta sin respuesta en la documentación |
| `12-preguntas-sin-respuesta.jpg` | 6.3 | Módulo de preguntas sin respuesta |

`16-usuarios.jpg` y `17-empresas.jpg` muestran correos y nombres reales:
difuminarlos antes de usarlos fuera del repositorio.

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

- [ ] Memoria: dirección de los repositorios, frase sobre el trabajo individual y el marcador `⟨PENDIENTE⟩` de 3.2
- [ ] Memoria: las seis capturas y los cuatro fragmentos de código
- [ ] Memoria: hallazgos en 5.3 y 5.4
- [ ] Memoria: capítulo 2 (estado del arte) y capítulo 8 (conclusiones y trabajo futuro)
- [ ] Memoria: versión corta del anexo 10.1 y resultados en 10.3
- [ ] Controlar la extensión (60 páginas como máximo)
- [ ] `README.md` del backend al día
- [ ] Vídeo demostrativo y presentación de la defensa
- [ ] Dar acceso de lectura al revisor en los dos repositorios
