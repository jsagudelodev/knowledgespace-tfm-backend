# Experimento 4: Línea base: recuperación y generación

En la memoria es el **cuarto experimento** del capítulo 5.

## EXP-04 (11 y 12-10)

**Pregunta:** ¿Cómo recupera y responde la línea base?

**Resultado:** hit@3 0,50, MRR 0,394; fidelidad 0,888; abstención 6/6 (2 por umbral, 4 por prompt)

**Decisión:** Línea base de comparación

**Dónde está en la memoria:** 5.3

## Archivos

- `dataset_ejecutado_2026-10-11.json`: por pregunta: fragmentos recuperados, respuesta, tiempo y métricas de recuperación.
- `ragas_2026-10-12.json`: métricas RAGAS por pregunta y medias.

## Cómo se reproduce

Con ejecutar_dataset.py y evaluar_ragas.py, desde `api/`. Los comandos exactos y la explicación de cada métrica están en [`GUIA_PRUEBAS.md`](../GUIA_PRUEBAS.md); el índice de todos los experimentos, en [`REGISTRO.md`](../REGISTRO.md).
