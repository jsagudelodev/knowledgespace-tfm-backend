# Experimento 9: Modelo de representaciones y tamaño de fragmento

En la memoria es el **noveno experimento** del capítulo 5.

## EXP-14 (04-11)

**Pregunta:** ¿Recupera mejor `text-embedding-3-large` que `3-small`?

**Resultado:** MRR de 0,362 a 0,443, pero 6 preguntas a favor y 3 en contra: no concluyente. El umbral 0,30 seguiría valiendo

**Decisión:** Se mantiene `3-small`

**Dónde está en la memoria:** 5.3, noveno

## EXP-15 (04-11)

**Pregunta:** ¿Qué tamaño de fragmento recupera mejor: 500, 1.000 o 1.500?

**Resultado:** hit@3 idéntico (0,52) en los tres; diferencias de posición no concluyentes; con 500 el umbral queda casi en el ruido. **Destapó un defecto:** producción guardaba solo 1.000 caracteres por fragmento y eso causaba la abstención indebida de la pregunta 26. Corregido y reindexado: la 26 responde, pero añade de memoria un dato que no está en los documentos

**Decisión:** Se mantiene 1.000; recorte corregido

**Dónde está en la memoria:** 5.3, noveno; 5.4

## Archivos

- `dataset_ejecutado_2026-11-04_descomposicion_acotada_temp0.0_texto_completo.json`: por pregunta: fragmentos recuperados, respuesta, tiempo y métricas de recuperación.
- `ragas_2026-11-04_avanzado_descomposicion_acotada_temp0.0_texto_completo.json`: métricas RAGAS por pregunta y medias.
- [`EXP-14_modelo-embedding/`](EXP-14_modelo-embedding/LEEME.md): EXP-14: text-embedding-3-small frente a 3-large, con su propio LEEME.
- [`EXP-15_tamano-fragmento/`](EXP-15_tamano-fragmento/LEEME.md): EXP-15: fragmentos de 500, 1.000 y 1.500 caracteres, con su propio LEEME.

## Cómo se reproduce

Con comparar_embeddings.py y comparar_tamano_fragmento.py, desde `api/`. Los comandos exactos y la explicación de cada métrica están en [`GUIA_PRUEBAS.md`](../GUIA_PRUEBAS.md); el índice de todos los experimentos, en [`REGISTRO.md`](../REGISTRO.md).
