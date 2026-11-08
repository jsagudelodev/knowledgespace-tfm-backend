# Experimento 6: Temperatura 0,7 frente a 0

En la memoria es el **sexto experimento** del capítulo 5.

## EXP-06 (14-10)

**Pregunta:** ¿Qué efecto tiene la temperatura en la fidelidad?

**Resultado:** Fidelidad de 0,888 a 0,939; mínima de 0,538 a 0,750

**Decisión:** Temperatura 0 para todos

**Dónde está en la memoria:** 5.3

## Archivos

- `dataset_ejecutado_2026-10-14_temp0.0.json`: por pregunta: fragmentos recuperados, respuesta, tiempo y métricas de recuperación.
- `ragas_2026-10-14_base_temp0.json`: métricas RAGAS por pregunta y medias.

## Cómo se reproduce

Con ejecutar_dataset.py --temperatura 0 y evaluar_ragas.py, desde `api/`. Los comandos exactos y la explicación de cada métrica están en [`GUIA_PRUEBAS.md`](../GUIA_PRUEBAS.md); el índice de todos los experimentos, en [`REGISTRO.md`](../REGISTRO.md).
