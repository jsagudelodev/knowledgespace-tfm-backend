# Experimento 1: Fragmentación por caracteres o por oraciones

En la memoria es el **primer experimento** del capítulo 5.

## EXP-01 (07-10)

**Pregunta:** ¿Qué le hace cada estrategia de troceado al texto?

**Resultado:** Cortes a mitad de palabra del 79,2 % al 0 %; 19 % menos de texto indexado

**Decisión:** Troceado por oraciones

**Dónde está en la memoria:** 5.3, 4.2

## Archivos

- `chunking_2026-10-07.json`: métricas de cada estrategia de fragmentación, por documento.
- `chunking_2026-10-09.json`: métricas de cada estrategia de fragmentación, por documento.

## Cómo se reproduce

Con medir_chunking.py, desde `api/`. Los comandos exactos y la explicación de cada métrica están en [`GUIA_PRUEBAS.md`](../GUIA_PRUEBAS.md); el índice de todos los experimentos, en [`REGISTRO.md`](../REGISTRO.md).
