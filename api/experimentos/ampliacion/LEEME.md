# Ampliación: Ampliación del conjunto de referencia y reglas del prompt

En la memoria no lleva número: no compara configuraciones, añade nueve preguntas al conjunto de referencia (de 18 a 27) y prueba unas reglas en el prompt que se descartaron. Está en el apartado 5.3 («Ampliación del conjunto de referencia») y en el 5.4.

## EXP-11 (23-10)

**Pregunta:** ¿Cómo responde a paráfrasis, premisas falsas y preguntas parciales?

**Resultado:** Paráfrasis 1/3, premisa falsa 0/3, parcial 2/3; abstención excesiva en 22, 24 y 26

**Decisión:** Limitación declarada

**Dónde está en la memoria:** 5.1, 5.3, 5.4

## EXP-12 (25-10)

**Pregunta:** ¿Unas reglas en el prompt corrigen las premisas falsas?

**Resultado:** Premisa falsa de 0/3 a 1/3, pero la pertinencia baja de 0,698 a 0,583

**Decisión:** Revertido

**Dónde está en la memoria:** 5.4

## Archivos

- `dataset_ejecutado_2026-10-23_descomposicion_acotada_temp0.0.json`: por pregunta: fragmentos recuperados, respuesta, tiempo y métricas de recuperación.
- `ragas_2026-10-23_avanzado_descomposicion_acotada_temp0.0.json`: métricas RAGAS por pregunta y medias.
- `dataset_ejecutado_2026-10-25_descomposicion_acotada_temp0.0_prompt_v2.json`: por pregunta: fragmentos recuperados, respuesta, tiempo y métricas de recuperación.
- `ragas_2026-10-25_avanzado_descomposicion_acotada_temp0.0_prompt_v2.json`: métricas RAGAS por pregunta y medias.

## Cómo se reproduce

Con ejecutar_dataset.py y evaluar_ragas.py (con criterios.py), desde `api/`. Los comandos exactos y la explicación de cada métrica están en [`GUIA_PRUEBAS.md`](../GUIA_PRUEBAS.md); el índice de todos los experimentos, en [`REGISTRO.md`](../REGISTRO.md).
