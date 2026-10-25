# Estado del software de cara a la entrega — 2026-10-20

Evaluación honesta del software completo (backend + frontend), no solo del
pipeline RAG, para responder antes de la defensa: ¿está en condiciones de
entregarse? Cada afirmación de este documento fue verificada contra el código
real el 19-20 de octubre de 2026, no copiada de otro documento sin comprobar
— el proyecto ya tuvo casos de documentación desactualizada (ver
`NUCLEO_RAG.md` y `TUTORIAS.md`), así que esta vez cada punto cita dónde se
comprobó.

> **Veredicto corto:** el software está en estado defendible. Funciona de
> punta a punta, la arquitectura está razonada y medida, y las limitaciones
> reales están reconocidas en el propio código, no escondidas. Lo que falta
> es deuda técnica conocida, ninguna bloqueante para la entrega.

---

## ¿Resuelve un problema documental con RAG?

Sí. El flujo completo funciona de punta a punta: se sube un documento, se
trocea por oraciones, se indexa en Pinecone aislado por empresa y asistente
(multi-tenant real, verificado en `pinecone_service.py` y
`test_pinecone_namespace.py`), y el chat responde citando las fuentes con su
puntuación de relevancia, absteniéndose cuando no hay evidencia suficiente.

Verificado contra `docs/FUNCIONALIDADES.md`: las 14 funcionalidades marcadas
como completadas tienen código real detrás (rutas de código citadas y
comprobadas), y las 2 marcadas como fuera de alcance (reranking como
funcionalidad de producto, *fine-tuning*) están justificadas, no omitidas. El
propio documento se autocorrigió en el pasado cuando una funcionalidad quedó
mal etiquetada (memoria conversacional, F13) — es disciplina real, no un
documento aspiracional.

## ¿Está bien implementada la arquitectura?

Sí, en dos sentidos:

1. **Separación de capas real**, backend y frontend. Backend:
   `routers/v1/` → `services/` → `repositories/` → `db/models/`, con
   `schemas/` Pydantic aparte; inyección de dependencias de FastAPI bien
   usada (`Depends(get_db)`, `Depends(get_current_user)`); ningún router
   accede a SQLAlchemy saltándose el repositorio. Frontend: estructura por
   *features* (`assistants`, `chat`, `documents`, `companies`...), cada una
   con `pages/` y `services/` propios, más `core/` y `shared/` — patrón
   estándar de Angular, homogéneo en los módulos revisados.
2. **La decisión de arquitectura RAG está razonada, no improvisada.** Se
   eligió "RAG básico + dos refuerzos medidos" en vez de algo más vistoso
   (*self-RAG*, GraphRAG, agéntico) con argumentos explícitos: auditabilidad,
   latencia acotada, corpus que cambia. Detalle completo y las seis
   configuraciones medidas en `NUCLEO_RAG.md`.

## ¿Está el código limpio, organizado, mantenible, con buenas prácticas?

Mixto — y conviene no mezclar las cuatro preguntas, porque la respuesta no es
la misma:

| | Veredicto | Evidencia |
|---|---|---|
| **Organizado** | ✅ Sólido | Capas separadas sin mezclas, patrón por *features* homogéneo en los 10 módulos del frontend |
| **Limpio** | ✅ Bien | Sin código muerto relevante; sin `console.log` ni tipos `any` sueltos en el frontend (grep en 0 resultados); archivos de tamaño razonable (el router/servicio más grande fuera del RAG es `documents.py`, 443 líneas); decisiones comentadas explicando el *por qué*, no solo el qué, en los módulos críticos (`security.py`, `database.py`, `documents.py`) |
| **Mantenible** | ✅ Mejorado el 20 y 21-10 | Las 14 excepciones genéricas quedaron tipadas (`EmbeddingError`, `VectorStoreError`, `StorageError`, `DocumentExtractionError` en `app/core/exceptions.py`), la verificación de aislamiento multi-tenant —repetida en 17 sitios de 5 routers— se centralizó en `BaseRepository.get_of_company`, y **Alembic quedó implementado** (ver abajo) en lugar de los `migrate_*.sql` sueltos |
| **Buenas prácticas de ingeniería** | 🟡 Mejorado el 21-10 | **Backend: `ruff` configurado** (`api/ruff.toml`), 295 avisos iniciales reducidos a 0 — 61 arreglos mecánicos (imports sin usar y desordenados) y el resto revisado caso por caso, incluido un **bug real encontrado**: una clave de diccionario duplicada en `experimentos/medir_chunking.py` que descartaba en silencio el conteo de caracteres totales del documento (sin afectar ninguna cifra ya citada en la memoria). Sigue pendiente: cero tests en el frontend, y CI automatizado en ningún repo (sin `.github/workflows`) |

**Sobre las migraciones de base de datos — resuelto el 21-10.** Alembic
quedó implementado (`api/alembic/`), con una línea base vacía estampada
contra la base real (las tablas ya existían, no había nada que crear) y un
hallazgo real en el camino: al configurarlo apareció una tabla
`alembic_version` con una fila huérfana de un intento anterior y abandonado
(probablemente del producto comercial del que parte este proyecto), sin
ninguna migración real detrás — se limpió y se reemplazó por la línea base
propia. El autogenerate también sacó a la luz deuda real no documentada
antes (cuatro columnas huérfanas nuevas en `documents`, y varias columnas
`nullable` en la base real donde el modelo exige `NOT NULL`), que queda
señalada para reconciliar con calma, no corregida de golpe contra producción
— ver `MODELO_DATOS.md` §3.7 para el detalle completo. Los `migrate_*.sql`
anteriores (`migrate_cost_tracking.sql`, etc.) quedan como registro
histórico de cómo se llegó al esquema actual, no como el procedimiento
vigente.

**Sobre la autenticación:** JWT HS256 sin *refresh token* ni revocación,
decisión documentada y justificada en `api/app/core/security.py`. El
aislamiento multi-tenant se repite endpoint a endpoint
(`if doc.company_id != current_user.company_id: 404`) en vez de un
repositorio base con `get_scoped(id, company_id)` — funciona y es
consistente, pero es lógica duplicada que se podría centralizar.

**Un hallazgo que descarta una sospecha razonable:** el modelo `Widget` y su
router existieron y se retiraron deliberadamente (`git log`: *"Recorte de
alcance TFM: retira el router de widgets"*). No es código muerto accidental,
es un recorte de alcance consciente con rastro en el historial de git.

## ¿Están aplicadas correctamente las pruebas con Langfuse?

Sí. Instrumentado como dependencia opcional — con `LANGFUSE_ENABLED=false` el
sistema funciona igual (`OBSERVABILIDAD.md`). Cada consulta genera cinco
observaciones, con la puntuación de cada fragmento recuperado y si superó el
umbral. Las 18 preguntas del conjunto de evaluación viven como **dataset
real** de Langfuse (`knowledgespace-conjunto-referencia`), ejecutadas como
una *run* con nombre enlazada a sus trazas —no como trazas sueltas sin
agrupar—, mediante `experimentos/langfuse_dataset.py`. Decisión documentada y
deliberada: el coste de esos experimentos no se mezcla con `cost_tracking`
(que registra gasto real de cliente), para no contaminar esa métrica.

## ¿Y RAGAS?

También bien aplicado, con una práctica que no es habitual y vale la pena
destacar: entorno de evaluación aislado (`.venv-eval`) para no contaminar las
~20 dependencias de producción con las ~60 de RAGAS. Medición contra línea
base en cada una de las mejoras (`ragas_2026-10-*.json`), con cuatro métricas
estándar (`faithfulness`, `context_precision`, `context_recall`,
`answer_relevancy`).

La limitación del método —un modelo de lenguaje juzgando a otro— no solo está
declarada de oídas: se **demostró con evidencia propia** el 19 de octubre.
Comparando la sexta configuración de RAG contra el híbrido solo, se encontró
que para el mismo contexto recuperado y la misma respuesta generada,
carácter por carácter, el juez de RAGAS dio notas distintas (1,0 frente a
0,6) en dos ejecuciones distintas. Es un hallazgo metodológico legítimo para
el capítulo 5 — no un defecto del propio sistema, sino del instrumento de
medida. Detalle completo en `NUCLEO_RAG.md` §12.

## ¿Sabemos cuánto cuesta una llamada o una respuesta? ¿Está bien medido?

Sí, y está bien diseñado. Verificado en
`api/app/services/cost_tracking_service.py` y
`api/app/routers/v1/chat.py:107-149`:

- Se registra **por separado** la generación de la respuesta (`operation="chat"`),
  el *embedding* de la pregunta (`operation="embedding"`), **y cada llamada
  auxiliar** de las configuraciones avanzadas —descomposición, reordenado—
  con su propia etiqueta de operación. Así se puede saber cuánto cuesta cada
  mejora específicamente, no solo el total de la consulta.
- Un fallo al registrar el coste **nunca rompe la respuesta al usuario** — es
  un efecto secundario contable, con su propio `try/except` y *rollback*,
  documentado así explícitamente en el docstring de la clase.
- Coste medido en la línea base: **0,000431 USD por consulta**
  (`NUCLEO_RAG.md` §6).

**Única limitación real:** la tabla de precios (`PRICING` en
`cost_tracking_service.py`) está fija en el código, con los precios públicos
de OpenAI al momento de escribirla. No se sincroniza automáticamente si
OpenAI cambia tarifas — hay que actualizarla a mano.

## ¿Qué falta para completar la entrega?

**Nada que bloquee funcionalmente** — el producto funciona de punta a punta
y está medido. Lo que queda es deuda técnica reconocida, ninguna exige parar
la entrega:

| Pendiente | Impacto | Dónde |
|---|---|---|
| ~~Excepciones genéricas sin tipar~~ — **resuelto el 20-10** | Calidad de código | `app/core/exceptions.py` (nuevo), 4 servicios actualizados |
| ~~Verificación multi-tenant duplicada~~ — **resuelto el 20-10** | Mantenibilidad | `BaseRepository.get_of_company`, 17 sitios en 5 routers |
| ~~Cero tests en el frontend~~ — **resuelto el 23/24-10** | Buenas prácticas | 8 archivos `.spec.ts`, 34 tests (guards, interceptores, `AuthService`, `ChatService`, `ChunksDrawerComponent`) |
| ~~Sin *linting* en el backend~~ — **resuelto el 21-10** | Buenas prácticas | `api/ruff.toml`, `api/requirements-dev.txt` |
| ~~Sin *linting* en el frontend~~ — **resuelto el 23-10** | Buenas prácticas | `@angular-eslint`, `ng lint` |
| Sin CI en ningún repo | Buenas prácticas | Ambos repos |
| ~~Sin Alembic~~ — **resuelto el 21-10** | Mantenibilidad | `api/alembic/`, `MODELO_DATOS.md` §3.7 |
| Deuda de esquema encontrada al adoptar Alembic (columnas `nullable`, tipos) | Mantenibilidad, no bloqueante | `MODELO_DATOS.md` §3.7 |
| Método de ancla sin variantes equivalentes (`\|`) | Evaluación, no producto | `experimentos/ejecutar_dataset.py` |
| ~~Alucinación de alcance global~~ — **resuelto el 25-10** | Producto | `app/services/alcance_global.py` — detector por patrones + respuesta desde metadatos reales de `documents`, sin pasar por el RAG ni por el LLM |
| Corpus `.txt` de evaluación con extracción incompleta | Evaluación, no producto | `experimentos/dataset_evaluacion.csv` (caso P8) |

Para cada uno conviene tener lista la razón de por qué quedó así (tiempo y
alcance de un TFM individual), igual que ya está respondida la de Alembic y
la del JWT sin revocación — admitido con criterio es más defendible que
perfecto sin evidencia.

**Nota (2026-10-25):** la tabla de arriba se actualizó para marcar como
resueltos los tests/linting de frontend y la alucinación de alcance global
—verificado contra el código y contra el backend real en cada caso—, pero el
resto del documento sigue con la fecha de verificación original del 19-20 de
octubre. No se re-auditó todo de nuevo, solo estos puntos puntuales.
