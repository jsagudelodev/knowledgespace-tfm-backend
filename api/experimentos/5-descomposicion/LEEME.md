# Experimento 5: Descomposición de consultas, sin límite y acotada

En la memoria es el **quinto experimento** del capítulo 5.

## EXP-05 (12-10)

**Pregunta:** ¿La descomposición corrige las preguntas compuestas?

**Resultado:** Cobertura del 48 % al 88 %, pero hasta el doble de contexto

**Decisión:** Superada por EXP-08

**Dónde está en la memoria:** 5.3

## EXP-08 (16-10)

**Pregunta:** ¿Se puede repartir el contexto sin pagar el doble?

**Resultado:** Cobertura 52 %, desequilibrio 0,83, mismo coste que la base

**Decisión:** **Activa** (`descomposicion_acotada`)

**Dónde está en la memoria:** 5.3, dentro del quinto

## EXP-13 (03-11)

**Pregunta:** ¿Qué descomposición da mejores respuestas, con tope o sin tope?

**Resultado:** 27 preguntas: indistinguibles dentro del ruido. Compuestas: la acotada responde las dos partes en 18/18 y la sin tope en 15/18; con la misma evidencia más ruido, la sin tope se abstiene

**Decisión:** Se mantiene la acotada, ahora con evidencia de respuesta

**Dónde está en la memoria:** 5.3, dentro del quinto

## Archivos

- `preguntas_compuestas_2026-10-12_avanzado.json`: cobertura de cada pareja de preguntas, por separado y unidas.
- `dataset_ejecutado_2026-10-12_avanzado.json`: por pregunta: fragmentos recuperados, respuesta, tiempo y métricas de recuperación.
- `preguntas_compuestas_2026-10-16_completo.json`: cobertura de cada pareja de preguntas, por separado y unidas.
- `dataset_ejecutado_2026-10-16_completo_temp0.0.json`: por pregunta: fragmentos recuperados, respuesta, tiempo y métricas de recuperación.
- `dataset_ejecutado_2026-11-03_descomposicion_acotada_temp0.0.json`: por pregunta: fragmentos recuperados, respuesta, tiempo y métricas de recuperación.
- `dataset_ejecutado_2026-11-03_descomposicion_temp0.0.json`: por pregunta: fragmentos recuperados, respuesta, tiempo y métricas de recuperación.
- `ragas_2026-11-03_avanzado_descomposicion_acotada_temp0.0.json`: métricas RAGAS por pregunta y medias.
- `ragas_2026-11-03_avanzado_descomposicion_temp0.0.json`: métricas RAGAS por pregunta y medias.
- [`EXP-13_descomposicion-con-o-sin-tope/`](EXP-13_descomposicion-con-o-sin-tope/LEEME.md): EXP-13: con tope o sin tope, en la generación, con su propio LEEME.

## Cómo se reproduce

Con medir_preguntas_compuestas.py, ejecutar_dataset.py, evaluar_ragas.py y responder_compuestas.py, desde `api/`. Los comandos exactos y la explicación de cada métrica están en [`GUIA_PRUEBAS.md`](../GUIA_PRUEBAS.md); el índice de todos los experimentos, en [`REGISTRO.md`](../REGISTRO.md).
