# Funcionalidades del TFM — Inventario completo

**Documento:** Registro de las funcionalidades implementadas y de las que
quedaron fuera de alcance, con el motivo.  
**Última actualización:** 2026-10-21

> **Ejercicios frente a mediciones.** F2–F7 y F9–F12 son ejercicios de práctica
> de `docs/practica-tfm/`, carpeta que no se versiona. Usan datos didácticos
> —su propio código lo indica ("DATOS PRE-CALCULADOS", "Simula latencia")—, así
> que **sus valores no son mediciones del sistema** y este documento ya no los
> cita. Las mediciones reales, reproducibles con un comando, están en
> `api/experimentos/resultados/`.

---

## 📊 Estado actual

| Completadas | En progreso | Planificadas | Total |
|---|---|---|---|
| **15** | **0** | **1** | **16** |

---

## ✅ Funcionalidades Completadas

### **F1: RAG Pipeline completo (5.0)**
- **Descripción:** Implementación de punta a punta: documento → chunks → embeddings → búsqueda → filtro → prompt → LLM
- **Componentes:**
  - Extracción de documentos (PDF/DOCX/TXT/MD)
  - División en chunks
  - Generación de embeddings (OpenAI text-embedding-3-small)
  - Búsqueda en Pinecone
  - Filtrado por umbral (0.30)
  - Construcción de prompt RAG
  - Llamada a LLM (gpt-4o-mini)
- **Estado:** ✅ Completo y funcional
- **Código:** `api/app/services/rag_service.py`, `pdf_service.py`, `embedding_service.py`
- **Archivo educativo:** `docs/practica-tfm/5.0_rag_de_principio_a_fin.py`

---

### **F2: Métrica Precision@k**
- **Descripción:** Mide certeza: de los k chunks devueltos, ¿cuántos son relevantes?
- **Fórmula:** aciertos / k
- **Uso:** Validar calidad de recuperación
- **Estado:** Ejercicio de práctica con datos didácticos (sin valor medido)
- **Código:** `docs/practica-tfm/5.1_precision_recall.py`

---

### **F3: Métrica Recall@k**
- **Descripción:** Mide cobertura: de los chunks relevantes que existen, ¿cuántos encontramos?
- **Fórmula:** aciertos / total_relevantes
- **Uso:** Validar no dejamos cosas afuera
- **Estado:** Ejercicio de práctica con datos didácticos (sin valor medido)
- **Código:** `docs/practica-tfm/5.1_precision_recall.py`

---

### **F4: Métrica MRR (Mean Reciprocal Rank)**
- **Descripción:** Mide orden: ¿en qué posición encontramos el primer chunk relevante?
- **Fórmula:** 1 / posición_del_primero_bueno
- **Uso:** Validar que lo bueno aparece arriba (importante para LLM)
- **Estado:** Ejercicio de práctica con datos didácticos (sin valor medido).
  El MRR medido sobre el sistema real está en el apartado 5.3 de la memoria
  (comparación del reordenado, ver F14)
- **Código:** `docs/practica-tfm/5.2_mrr.py`

---

### **F5: Métrica Latencia (p50, p95)**
- **Descripción:** Mide velocidad: ¿cuánto tarda una consulta?
- **p50:** Mediana (mitad de queries ≤ este tiempo)
- **p95:** Percentil 95 (95% de queries son más rápidas)
- **Uso:** Validar SLA y aceptabilidad
- **Estado:** Ejercicio de práctica con latencia simulada (sin valor medido)
- **Código:** `docs/practica-tfm/5.3_latencia.py`

---

### **F6: LLM-as-Judge (Faithfulness)**
- **Descripción:** Usa un LLM como juez para detectar si la respuesta del RAG alucina
- **Entrada:** pregunta + contexto + respuesta
- **Salida:** True/False (¿es fiel al contexto?)
- **Uso:** Validar sin alucinaciones
- **Estado:** Ejercicio de práctica (sin valor medido). No está en el código
  productivo: no hay validación posterior de la respuesta (ver `ALCANCE_TFM.md`).
  La fidelidad medida del sistema es la de RAGAS (`faithfulness`), en
  `api/experimentos/resultados/ragas_*.json`
- **Código:** `docs/practica-tfm/5.5_llm_as_judge.py`

---

### **F7: Generación de Preguntas Sintéticas**
- **Descripción:** Genera preguntas automáticamente a partir de chunks (sin escribir a mano)
- **Entrada:** un chunk del documento
- **Salida:** una pregunta cuya respuesta es ese chunk
- **Uso:** Crear dataset de evaluación sin esfuerzo manual
- **Estado:** ✅ Implementado
- **Código:** `docs/practica-tfm/5.4_generar_preguntas_sinteticas.py`

---

### **F8: Chunking Semántico (6.1)**
- **Descripción:** Divide documentos respetando oraciones (no corta en mitad de frase)
- **Antes:** Corta por caracteres fijos → rompe oraciones
- **Ahora:** Agrupa oraciones hasta ~1000 caracteres → contexto coherente
- **Medición:** calidad estructural (cortes a mitad de palabra y de frase,
  regularidad, cobertura) con `api/experimentos/medir_chunking.py`; resultados en
  `api/experimentos/resultados/chunking_2026-10-07.json` y `chunking_2026-10-09.json`
- **Estado:** ✅ Implementado en producción
- **Código:** `api/app/services/pdf_service.py` (función `dividir_en_chunks_semantico()`)

---

### **F9: Tabla Comparativa de Configuraciones (6.2)**
- **Descripción:** Compara 4 configuraciones de chunking en la misma tabla
- **Uso:** Practicar cómo se justifica una decisión con una tabla comparativa
- **Estado:** Ejercicio de práctica con datos pre-calculados (sin valor medido).
  La comparación real de las dos estrategias de chunking es la de F8
- **Código:** `docs/practica-tfm/6.2_tabla_comparativa.py`

---

### **F10: Harness Completo (6.3)**
- **Descripción:** Ejecuta todas las métricas (precision, recall, MRR, faithfulness, latencia) sobre el mismo dataset
- **Salida:** tabla con todas las métricas + promedio final
- **Uso:** Practicar la validación integrada
- **Estado:** Ejercicio de práctica con recuperación y latencia simuladas (sin
  valor medido). La evaluación real del sistema usa el dataset de 18 preguntas
  de `api/experimentos/dataset_evaluacion.csv` y RAGAS
- **Código:** `docs/practica-tfm/6.3_harness_completo.py`

---

### **F11: Documentación Estrategia de Rendimiento**
- **Descripción:** Documento que explica cómo se midió, optimizó y validó el RAG
- **Secciones:**
  1. Línea base (métricas iniciales)
  2. Problema identificado (chunking rompe oraciones)
  3. Hipótesis (respetando oraciones mejorará)
  4. Intervención (chunking semántico)
  5. Validación
  6. Decisión final (por qué lo elegimos)
  7. Cómo reproducir (pasos exactos)
  8. Implicaciones en producción
- **Estado:** Material de práctica; sus tablas usan los datos didácticos de los
  ejercicios, no mediciones del sistema
- **Código:** `docs/practica-tfm/ESTRATEGIA_RENDIMIENTO_RAG.md`

---

### **F12: Simulacro de Defensa (Sección 8)**
- **Descripción:** Preguntas esperadas en la defensa sobre medición y optimización + respuestas modelo
- **Contenido:**
  - Cómo midió la calidad (métricas)
  - Cómo optimizó (chunking)
  - Cómo validó (harness)
  - Repreguntas probables
  - Respuestas defensibles
- **Estado:** ✅ Completo
- **Código:** `docs/practica-tfm/SIMULACRO_DEFENSA.md` (sección 8)

---

### **F13: Ambas Versiones de Chunking en Código**
- **Descripción:** El código productivo soporta ambas estrategias (antiguo + semántico)
- **Antiguo:** `dividir_en_chunks_caracteres()` — corta por caracteres fijos
- **Nuevo:** `dividir_en_chunks_semantico()` — agrupa oraciones
- **Parámetro:** `semantico=True/False` en `procesar()`
- **Defecto:** `semantico=True` (usa el nuevo)
- **Uso:** Compatible hacia atrás, permite comparativas
- **Estado:** ✅ Implementado y en producción
- **Código:** `api/app/services/pdf_service.py`
- **Matiz:** ningún llamador productivo pasa `semantico=False` — `documents.py`
  lo fija en `True`. La estrategia antigua se conserva para poder comparar las
  dos sobre los mismos documentos, que es lo que hace
  `api/experimentos/medir_chunking.py`.

---

### **F15: Memoria Conversacional en RAG**
- **Descripción:** El historial de la conversación entra en el contexto del RAG
- **Uso:** Preguntas encadenadas coherentes — "¿y eso cuánto cuesta?" entiende
  de qué se habla
- **Componentes:**
  - `chat.py` recupera los 20 mensajes previos **antes** de añadir el actual,
    para no duplicarlo en el prompt
  - `rag_service.generate_response()` lo recibe y `_build_messages()` lo coloca
    después del contexto y antes de la pregunta: lo más cercano a la pregunta
    es la conversación reciente, que es lo que da sentido a las referencias
- **Costo:** +0 llamadas; solo ocupa contexto
- **Estado:** ✅ Implementado
- **Código:** `api/app/routers/v1/chat.py:61-62,70`,
  `api/app/services/rag_service.py:56,82,165-166`

> Esta funcionalidad figuraba como planificada "después de la defensa" cuando
> ya estaba implementada. Se corrigió al revisar la coherencia entre el
> documento y el código.

---

### **F14: Reordenado de fragmentos con LLM**
- **Descripción:** Tras recuperar los candidatos por similitud, un LLM los
  reordena por relevancia antes de construir el contexto
- **Estado:** ✅ Implementado y medido el 2026-10-14, **no activo**
- **Medición:** mejora la recuperación —context precision de 0,877 a 0,920
  (`ragas_2026-10-14_reranking_temp0.json` frente a `ragas_2026-10-14_base_temp0.json`),
  hit@3 de 0,500 a 0,667 y MRR de 0,394 a 0,447—, pero las métricas de
  generación se mueven dentro del margen de ruido del modelo evaluador
- **Por qué no está activo:** la llamada del reordenador consume unos 4.600
  tokens de entrada y multiplica por 3,7 el coste de cada consulta sin haber
  demostrado mejores respuestas. Ver `api/app/services/rag_factory.py` y el
  apartado 5.3 de la memoria
- **Código:** `api/app/services/rag_service_reranking.py`, `api/app/services/reordenador.py`

> Esta funcionalidad figuraba como planificada y "fuera de alcance" cuando ya
> estaba implementada y medida. Se corrigió el 2026-10-21.

---

## ⏳ Funcionalidades en Progreso

Ninguna actualmente.

---

## 📋 Funcionalidades Planificadas

### **F16: Fine-tuning de Embeddings** (Baja prioridad, producción)
- **Descripción:** Entrenar embeddings custom en el corpus de la empresa
- **Uso:** Mejorar precision en el dominio específico
- **Mejora esperada:** Precision +5-15% (estimado)
- **Costo:** $100+ training, +0 inferencia
- **Esfuerzo:** 8 horas (dataset + training)
- **Decisión:** ⏳ DESPUÉS DE DEFENSA, para producción

---

## 🎯 Roadmap por fase

### **Fase 1: Completada**
- ✅ F1-F15: todas las funcionalidades críticas para la defensa (F14 medida pero no activa)
- ✅ Código integrado
- ✅ Documentación completa

### **Fase 2: Pre-defensa**
- 📖 Practicar el simulacro de defensa
- 🎯 Preparar la presentación

### **Fase 3: Post-defensa**
- 🟢 F16 (Fine-tuning de embeddings): para producción real

---

## 📊 Matriz de priorización

| Feature | Para la defensa | Para usuarios | Esfuerzo | Estado |
|---|---|---|---|---|
| F1-F13, F15 | ✅ Críticas | ✅ Esencial | — | **Implementadas** |
| F14 (Reordenado) | ⭐⭐⭐ Fortalece | ⭐⭐ Mejora | — | **Implementada y medida, no activa** |
| F16 (Fine-tuning) | ⭐ Extra | ⭐⭐ Mejora | 8 h | Fuera de alcance |

---

## Qué quedó fuera y por qué

**F16, fine-tuning de embeddings.** Requiere un conjunto de entrenamiento propio
y un coste de entrenamiento que no se justifica con el volumen actual de
documentos.

**Recomendación:** **SÍ**, porque es bajo riesgo y fortalece la defensa.

---

**Documento mantenido por:** Estudiante TFM  
**Última revisión:** 2026-10-21
