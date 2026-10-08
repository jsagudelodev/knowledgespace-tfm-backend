# Funcionalidades del TFM — Inventario completo

**Documento:** Registro de todas las funcionalidades implementadas, en progreso y planificadas.  
**Última actualización:** 2026-10-03  
**Responsable:** Estudiante TFM

---

## 📊 Estado actual

| Completadas | En progreso | Planificadas | Total |
|---|---|---|---|
| **10** | **0** | **3** | **13** |

---

## ✅ Funcionalidades Completadas

### **F1: RAG Pipeline completo (5.0)**
- **Descripción:** Implementación de punta a punta: documento → chunks → embeddings → búsqueda → filtro → prompt → LLM
- **Componentes:**
  - Extracción de documentos (PDF/DOCX/TXT)
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
- **Valor típico:** 0.222 (antes), 0.289 (después de optimización)
- **Uso:** Validar calidad de recuperación
- **Estado:** ✅ Implementado y medido
- **Código:** `docs/practica-tfm/5.1_precision_recall.py`

---

### **F3: Métrica Recall@k**
- **Descripción:** Mide cobertura: de los chunks relevantes que existen, ¿cuántos encontramos?
- **Fórmula:** aciertos / total_relevantes
- **Valor típico:** 1.000 (100% — encontramos todo lo que existe)
- **Uso:** Validar no dejamos cosas afuera
- **Estado:** ✅ Implementado y medido
- **Código:** `docs/practica-tfm/5.1_precision_recall.py`

---

### **F4: Métrica MRR (Mean Reciprocal Rank)**
- **Descripción:** Mide orden: ¿en qué posición encontramos el primer chunk relevante?
- **Fórmula:** 1 / posición_del_primero_bueno
- **Valor típico:** 0.389 (antes), 0.456 (después)
- **Uso:** Validar que lo bueno aparece arriba (importante para LLM)
- **Estado:** ✅ Implementado y medido
- **Código:** `docs/practica-tfm/5.2_mrr.py`

---

### **F5: Métrica Latencia (p50, p95)**
- **Descripción:** Mide velocidad: ¿cuánto tarda una consulta?
- **p50:** Mediana (mitad de queries ≤ este tiempo)
- **p95:** Percentil 95 (95% de queries son más rápidas)
- **Valor típico:** p50=510ms (antes), p50=650ms (después)
- **Uso:** Validar SLA y aceptabilidad
- **Estado:** ✅ Implementado y medido
- **Código:** `docs/practica-tfm/5.3_latencia.py`

---

### **F6: LLM-as-Judge (Faithfulness)**
- **Descripción:** Usa un LLM como juez para detectar si la respuesta del RAG alucina
- **Entrada:** pregunta + contexto + respuesta
- **Salida:** True/False (¿es fiel al contexto?)
- **Uso:** Validar sin alucinaciones
- **Valor típico:** 100% faithful
- **Estado:** ✅ Implementado y validado
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
- **Mejora:** Precision +30% (0.222 → 0.289), MRR +17% (0.389 → 0.456)
- **Trade-off:** Latencia +140ms (510ms → 650ms), aceptable
- **Estado:** ✅ Implementado en producción
- **Código:** `api/app/services/pdf_service.py` (función `dividir_en_chunks_semantico()`)

---

### **F9: Tabla Comparativa de Configuraciones (6.2)**
- **Descripción:** Mide 4 configuraciones de chunking en la misma tabla
- **Configuraciones:**
  1. Antiguo (1000/200): 0.222 precision, 510ms latencia
  2. Semántico (1000/200): 0.289 precision, 650ms latencia ← **ELEGIDO**
  3. Agresivo (500/100): 0.311 precision, 920ms latencia
  4. Conservador (1500/300): 0.178 precision, 420ms latencia
- **Uso:** Validar decisión de qué usar
- **Estado:** ✅ Implementado y analizado
- **Código:** `docs/practica-tfm/6.2_tabla_comparativa.py`

---

### **F10: Harness Completo (6.3)**
- **Descripción:** Ejecuta todas las métricas (precision, recall, MRR, faithfulness, latencia) sobre el mismo dataset
- **Entrada:** 9 preguntas con ground truth
- **Salida:** tabla con todas las métricas + promedio final
- **Uso:** Validación final integrada
- **Resultado:** Precision 0.267, Recall 1.0, MRR 1.0, Faithfulness 100%, Latencia 1.4s
- **Estado:** ✅ Implementado y ejecutado
- **Código:** `docs/practica-tfm/6.3_harness_completo.py`

---

### **F11: Documentación Estrategia de Rendimiento**
- **Descripción:** Documento que explica cómo se midió, optimizó y validó el RAG
- **Secciones:**
  1. Línea base (métricas iniciales)
  2. Problema identificado (chunking rompe oraciones)
  3. Hipótesis (respetando oraciones mejorará)
  4. Intervención (chunking semántico)
  5. Validación (resultados +30%)
  6. Decisión final (por qué lo elegimos)
  7. Cómo reproducir (pasos exactos)
  8. Implicaciones en producción
- **Estado:** ✅ Completo
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

---

## ⏳ Funcionalidades en Progreso

Ninguna actualmente.

---

## 📋 Funcionalidades Planificadas

### **F14: Reranking con LLM** (Baja prioridad, alta valor)
- **Descripción:** Después de recuperar top-5 por similitud, un LLM los reordena por relevancia semántica
- **Componentes:**
  - Función `reranquear(pregunta, chunks)` 
  - LLM evalúa cada chunk
  - Devuelve chunks reordenados
  - Integración en `rag_service.py`
- **Mejora esperada:** Precision +10% (estimado)
- **Costo:** +200-300ms latencia, +0.0001 USD/query
- **Esfuerzo:** 2-3 horas
- **Decisión:** ⏳ PENDIENTE (ver BACKLOG_TFM.md)

---

### **F15: Memoria Conversacional en RAG** (Baja prioridad, UX)
- **Descripción:** Integrar historial de conversación en el contexto del RAG
- **Uso:** Preguntas multi-turn coherentes ("siguiente pregunta" entiende contexto)
- **Componentes:**
  - Pasar `conversation_history` a `generate_response()`
  - Incluir en el prompt del LLM
- **Mejora esperada:** UX +50% (subjetivo)
- **Costo:** +0 (solo llena contexto)
- **Esfuerzo:** 1 hora
- **Decisión:** ⏳ DESPUÉS DE DEFENSA

---

### **F16: Fine-tuning de Embeddings** (Baja prioridad, producción)
- **Descripción:** Entrenar embeddings custom en el corpus de la empresa
- **Uso:** Mejorar precision en el dominio específico
- **Mejora esperada:** Precision +5-15% (estimado)
- **Costo:** $100+ training, +0 inferencia
- **Esfuerzo:** 8 horas (dataset + training)
- **Decisión:** ⏳ DESPUÉS DE DEFENSA, para producción

---

## 🎯 Roadmap por fase

### **Fase 1: Completada (Hoy)**
- ✅ F1-F13: Todas las funcionalidades críticas para defensa
- ✅ Código integrado en producción
- ✅ Documentación completa

### **Fase 2: PRE-DEFENSA (Próximos días)**
- ⏳ F14 (Reranking): **DECIDIR AHORA** si se implementa
- 📖 Practicar SIMULACRO_DEFENSA.md
- 🎯 Preparar presentación

### **Fase 3: POST-DEFENSA (Después de pasar)**
- 🟢 F15 (Memoria conversacional): UX improvement
- 🟢 F16 (Fine-tuning embeddings): Para producción real

---

## 📊 Matriz de priorización

| Feature | Para defensa | Para usuarios | Esfuerzo | Recomendación |
|---|---|---|---|---|
| F1-F13 | ✅ Críticas | ✅ Esencial | ✅ Done | **DONE** |
| F14 (Reranking) | ⭐⭐⭐ Fortalece | ⭐⭐ Mejora | 2-3h | 🎯 **SÍ, AHORA** |
| F15 (Memoria) | ⭐ Bonus | ⭐⭐⭐ Mejora | 1h | ⏳ Después |
| F16 (Fine-tune) | ⭐ Bonus | ⭐⭐ Mejora | 8h | ⏳ Después |

---

## ✋ Próximas decisiones

**¿Implementamos F14 (Reranking) ahora?**

- **SÍ:** +10% precision, fortalece defensa, 2-3h, bajo riesgo
- **NO:** primero defensa, luego optimizaciones

**Recomendación:** **SÍ**, porque es bajo riesgo y fortalece la defensa.

---

**Documento mantenido por:** Estudiante TFM  
**Última revisión:** 2026-10-03
