# Experimento 8: Recuperación híbrida, sola y combinada con la acotada

En la memoria es el **octavo experimento** del capítulo 5.

## EXP-09 (19-10)

**Pregunta:** ¿La búsqueda híbrida (densa + BM25) recupera mejor?

**Resultado:** hit@1 de 0,25 a 0,42, fidelidad 0,965, pero cobertura de compuestas al 30 %

**Decisión:** Medido, no activo

**Dónde está en la memoria:** 5.3, octavo

## EXP-10 (19-10)

**Pregunta:** ¿Combinar reparto e híbrido suma lo mejor de ambos?

**Resultado:** Mejor hit@3 (0,67) y MRR (0,544), pero compuestas al 37 % y la más lenta

**Decisión:** Medido, no activo

**Dónde está en la memoria:** 5.3, octavo

## Archivos

- `preguntas_compuestas_2026-10-19_hibrido.json`: cobertura de cada pareja de preguntas, por separado y unidas.
- `preguntas_compuestas_2026-10-19_descomposicion_hibrida.json`: cobertura de cada pareja de preguntas, por separado y unidas.
- `dataset_ejecutado_2026-10-19_hibrido_temp0.0.json`: por pregunta: fragmentos recuperados, respuesta, tiempo y métricas de recuperación.
- `dataset_ejecutado_2026-10-19_descomposicion_hibrida_temp0.0.json`: por pregunta: fragmentos recuperados, respuesta, tiempo y métricas de recuperación.
- `ragas_2026-10-19_avanzado_hibrido_bm25_temp0.0.json`: métricas RAGAS por pregunta y medias.
- `ragas_2026-10-19_avanzado_descomposicion_hibrida_temp0.0.json`: métricas RAGAS por pregunta y medias.

## Cómo se reproduce

Con medir_preguntas_compuestas.py, ejecutar_dataset.py y evaluar_ragas.py, desde `api/`. Los comandos exactos y la explicación de cada métrica están en [`GUIA_PRUEBAS.md`](../GUIA_PRUEBAS.md); el índice de todos los experimentos, en [`REGISTRO.md`](../REGISTRO.md).
