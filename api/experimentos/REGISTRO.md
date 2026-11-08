# Registro de experimentos

Índice de todas las mediciones del proyecto: qué pregunta respondía cada una,
qué se obtuvo, qué se decidió y en qué archivo está la evidencia. La
explicación de cada experimento, pensada para la defensa, está en
[`GUIA_PRUEBAS.md`](GUIA_PRUEBAS.md).

*Última actualización: 8 de noviembre de 2026.*

## Los nueve experimentos de la memoria

La memoria (capítulo 5) cuenta **nueve experimentos**, del primero al noveno.
Aquí cada medición se guardó con su propio número según se hizo, **EXP-01 a
EXP-15**, así que algunos experimentos de la memoria reúnen varios registros.
Esta tabla es la equivalencia, en el orden de la memoria (es la Tabla 30).
**Cada experimento tiene su carpeta** con un `LEEME.md` y los archivos de
resultados que respaldan sus cifras:

| Memoria | Qué mide | Registros | Carpeta |
|---|---|---|---|
| **1** | Fragmentación por caracteres o por oraciones | EXP-01 | [`1-fragmentacion/`](1-fragmentacion/LEEME.md) |
| **2** | Si el umbral 0,30 sigue valiendo | EXP-02 | [`2-umbral/`](2-umbral/LEEME.md) |
| **3** | Preguntas compuestas, sin corregir | EXP-03 | [`3-preguntas-compuestas/`](3-preguntas-compuestas/LEEME.md) |
| **4** | Línea base: recuperación y generación | EXP-04 | [`4-linea-base/`](4-linea-base/LEEME.md) |
| **5** | Descomposición de consultas: sin límite y acotada | EXP-05, EXP-08, EXP-13 | [`5-descomposicion/`](5-descomposicion/LEEME.md) |
| **6** | Temperatura 0,7 frente a 0 | EXP-06 | [`6-temperatura/`](6-temperatura/LEEME.md) |
| **7** | Reordenado | EXP-07 | [`7-reordenado/`](7-reordenado/LEEME.md) |
| **8** | Recuperación híbrida, sola y con la acotada | EXP-09, EXP-10 | [`8-hibrida/`](8-hibrida/LEEME.md) |
| **9** | Modelo de representaciones y tamaño de fragmento | EXP-14, EXP-15 | [`9-embeddings-y-tamano/`](9-embeddings-y-tamano/LEEME.md) |
| *Ampliación* | Paráfrasis, premisas falsas y parciales; reglas del prompt | EXP-11, EXP-12 | [`ampliacion/`](ampliacion/LEEME.md) |

Los guiones están en esta carpeta raíz porque varios experimentos usan el mismo
(por ejemplo, `ejecutar_dataset.py`). Una ejecución nueva guarda su salida en
`resultados/`, que el guion crea si no existe; los resultados que cita la
memoria están ya en la carpeta de su experimento.

La **ampliación** no lleva número en la memoria porque no compara
configuraciones: añade nueve preguntas al conjunto de referencia (de 18 a 27) y
prueba unas reglas en el prompt que se descartaron. Está en el apartado 5.3
(«Ampliación del conjunto de referencia») y en el 5.4.

En `GUIA_PRUEBAS.md`, cada registro indica entre paréntesis a qué experimento
de la memoria pertenece.

Desde EXP-02, todos se ejecutaron contra el corpus de producción: empresa 8,
asistente 1, espacio `company-8-assistant-1` (8 documentos, 87 fragmentos).
EXP-01 no usa el índice: trocea en local tres PDF del mismo curso. El de 9-10
es una segunda ejecución sobre los mismos tres documentos y parámetros.

---

## Resumen

| ID | Pregunta que responde | Fecha | Resultado | Decisión | Memoria |
|---|---|---|---|---|---|
| EXP-01 | ¿Qué le hace cada estrategia de troceado al texto? | 07-10 | Cortes a mitad de palabra del 79,2 % al 0 %; 19 % menos de texto indexado | Troceado por oraciones | 5.3, 4.2 |
| EXP-02 | ¿Sigue valiendo el umbral 0,30 con el troceado por oraciones? | 09-10 | Ruido máx. 0,258, señal mín. 0,393: el 0,30 sigue en la banda, con un 41 % menos de margen | Se mantiene 0,30 | 5.3 |
| EXP-03 | ¿Cuánto se degrada la búsqueda con dos preguntas en un mensaje? | 09-10 | Cobertura conjunta del 48 %; desequilibrio 1,83 | Defecto confirmado | 5.3 |
| EXP-04 | ¿Cómo recupera y responde la línea base? | 11 y 12-10 | hit@3 0,50, MRR 0,394; fidelidad 0,888; abstención 6/6 (2 por umbral, 4 por prompt) | Línea base de comparación | 5.3 |
| EXP-05 | ¿La descomposición corrige las preguntas compuestas? | 12-10 | Cobertura del 48 % al 88 %, pero hasta el doble de contexto | Superada por EXP-08 | 5.3 |
| EXP-06 | ¿Qué efecto tiene la temperatura en la fidelidad? | 14-10 | Fidelidad de 0,888 a 0,939; mínima de 0,538 a 0,750 | Temperatura 0 para todos | 5.3 |
| EXP-07 | ¿El reordenado mejora las respuestas? | 14-10 | hit@3 de 0,50 a 0,667, pero respuestas sin mejora medible y coste ×3,7 | Medido, no activo | 5.3 |
| EXP-08 | ¿Se puede repartir el contexto sin pagar el doble? | 16-10 | Cobertura 52 %, desequilibrio 0,83, mismo coste que la base | **Activa** (`descomposicion_acotada`) | 5.3, dentro del quinto |
| EXP-09 | ¿La búsqueda híbrida (densa + BM25) recupera mejor? | 19-10 | hit@1 de 0,25 a 0,42, fidelidad 0,965, pero cobertura de compuestas al 30 % | Medido, no activo | 5.3, octavo |
| EXP-10 | ¿Combinar reparto e híbrido suma lo mejor de ambos? | 19-10 | Mejor hit@3 (0,67) y MRR (0,544), pero compuestas al 37 % y la más lenta | Medido, no activo | 5.3, octavo |
| EXP-11 | ¿Cómo responde a paráfrasis, premisas falsas y preguntas parciales? | 23-10 | Paráfrasis 1/3, premisa falsa 0/3, parcial 2/3; abstención excesiva en 22, 24 y 26 | Limitación declarada | 5.1, 5.3, 5.4 |
| EXP-12 | ¿Unas reglas en el prompt corrigen las premisas falsas? | 25-10 | Premisa falsa de 0/3 a 1/3, pero la pertinencia baja de 0,698 a 0,583 | Revertido | 5.4 |
| [EXP-13](5-descomposicion/EXP-13_descomposicion-con-o-sin-tope/LEEME.md) | ¿Qué descomposición da mejores respuestas, con tope o sin tope? | 03-11 | 27 preguntas: indistinguibles dentro del ruido. Compuestas: la acotada responde las dos partes en 18/18 y la sin tope en 15/18; con la misma evidencia más ruido, la sin tope se abstiene | Se mantiene la acotada, ahora con evidencia de respuesta | 5.3, dentro del quinto |
| [EXP-14](9-embeddings-y-tamano/EXP-14_modelo-embedding/LEEME.md) | ¿Recupera mejor `text-embedding-3-large` que `3-small`? | 04-11 | MRR de 0,362 a 0,443, pero 6 preguntas a favor y 3 en contra: no concluyente. El umbral 0,30 seguiría valiendo | Se mantiene `3-small` | 5.3, noveno |
| [EXP-15](9-embeddings-y-tamano/EXP-15_tamano-fragmento/LEEME.md) | ¿Qué tamaño de fragmento recupera mejor: 500, 1.000 o 1.500? | 04-11 | hit@3 idéntico (0,52) en los tres; diferencias de posición no concluyentes; con 500 el umbral queda casi en el ruido. **Destapó un defecto:** producción guardaba solo 1.000 caracteres por fragmento y eso causaba la abstención indebida de la pregunta 26. Corregido y reindexado: la 26 responde, pero añade de memoria un dato que no está en los documentos | Se mantiene 1.000; recorte corregido | 5.3, noveno; 5.4 |

**Lo que pidió el tutor el 3 de noviembre** (modelo de embedding y tamaño de
fragmento) está medido en EXP-14 y EXP-15. Con EXP-15 se cerró la serie:
`top_k` queda sin medir y declarado como tal. Ver
[`GUIA_PRUEBAS.md`](GUIA_PRUEBAS.md) §3.

---

## Archivos de evidencia por experimento

Cada uno en la carpeta de su experimento.

| ID | Script | Archivos |
|---|---|---|
| EXP-01 | `medir_chunking.py` | `1-fragmentacion/chunking_2026-10-07.json`, `1-fragmentacion/chunking_2026-10-09.json` |
| EXP-02 | `medir_umbral.py` | `2-umbral/umbral_2026-10-09.json` |
| EXP-03 | `medir_preguntas_compuestas.py` | `3-preguntas-compuestas/preguntas_compuestas_2026-10-09.json`; repetición de control: `3-preguntas-compuestas/preguntas_compuestas_2026-10-12.json` |
| EXP-04 | `ejecutar_dataset.py` + `evaluar_ragas.py` | `4-linea-base/dataset_ejecutado_2026-10-11.json`, `4-linea-base/ragas_2026-10-12.json` |
| EXP-05 | `medir_preguntas_compuestas.py` + `ejecutar_dataset.py` | `5-descomposicion/preguntas_compuestas_2026-10-12_avanzado.json`, `5-descomposicion/dataset_ejecutado_2026-10-12_avanzado.json` |
| EXP-06 | `ejecutar_dataset.py --temperatura 0` + `evaluar_ragas.py` | `6-temperatura/dataset_ejecutado_2026-10-14_temp0.0.json`, `6-temperatura/ragas_2026-10-14_base_temp0.json` |
| EXP-07 | `ejecutar_dataset.py` + `evaluar_ragas.py` | `7-reordenado/dataset_ejecutado_2026-10-14_reranking_temp0.0.json`, `7-reordenado/ragas_2026-10-14_reranking_temp0.json` |
| EXP-08 | `medir_preguntas_compuestas.py` + `ejecutar_dataset.py` | `5-descomposicion/preguntas_compuestas_2026-10-16_completo.json`, `5-descomposicion/dataset_ejecutado_2026-10-16_completo_temp0.0.json` |
| EXP-09 | los tres anteriores | `8-hibrida/preguntas_compuestas_2026-10-19_hibrido.json`, `8-hibrida/dataset_ejecutado_2026-10-19_hibrido_temp0.0.json`, `8-hibrida/ragas_2026-10-19_avanzado_hibrido_bm25_temp0.0.json` |
| EXP-10 | los tres anteriores | `8-hibrida/preguntas_compuestas_2026-10-19_descomposicion_hibrida.json`, `8-hibrida/dataset_ejecutado_2026-10-19_descomposicion_hibrida_temp0.0.json`, `8-hibrida/ragas_2026-10-19_avanzado_descomposicion_hibrida_temp0.0.json` |
| EXP-11 | `ejecutar_dataset.py` + `evaluar_ragas.py` (con `criterios.py`) | `ampliacion/dataset_ejecutado_2026-10-23_descomposicion_acotada_temp0.0.json`, `ampliacion/ragas_2026-10-23_avanzado_descomposicion_acotada_temp0.0.json` |
| EXP-12 | igual que EXP-11, con el prompt modificado | `ampliacion/dataset_ejecutado_2026-10-25_descomposicion_acotada_temp0.0_prompt_v2.json`, `ampliacion/ragas_2026-10-25_avanzado_descomposicion_acotada_temp0.0_prompt_v2.json` |
| EXP-15 | `comparar_tamano_fragmento.py` | `9-embeddings-y-tamano/EXP-15_tamano-fragmento/resultados/2026-11-04.json`; espacios `exp-chunk-500/1000/1500` |
| EXP-14 | `comparar_embeddings.py` | `9-embeddings-y-tamano/EXP-14_modelo-embedding/resultados/2026-11-04.json`; espacio `exp-emb-3-large` en Pinecone |
| EXP-13 | parte A: `ejecutar_dataset.py` + `evaluar_ragas.py`; parte B: `responder_compuestas.py` | A: los cuatro `*_2026-11-03_descomposicion*` de `resultados/`; B: `5-descomposicion/EXP-13_descomposicion-con-o-sin-tope/resultados/2026-11-03_parte-b.json` y `.md` |

Las 27 preguntas de EXP-11 también se ejecutaron como *dataset* en Langfuse
(`knowledgespace-conjunto-referencia`, 24-10), con `langfuse_dataset.py`. Ver
`docs/TFM/OBSERVABILIDAD.md`.

### Nombres heredados

Los archivos anteriores a este registro usan nombres distintos para la misma
configuración. **No se renombran**, porque la memoria y la documentación citan
esas rutas. Equivalencias:

| En los archivos aparece | Es la configuración | Clase |
|---|---|---|
| `naive`, `naive_rag_umbral_0.30`, `base`, o sin sufijo | `base` | `RAGService` |
| `avanzado`, `avanzado_descomposicion` | `descomposicion` (sin tope) | `RAGServiceAvanzado` |
| `completo`, `avanzado_completo`, `descomposicion_acotada` | `descomposicion_acotada` (la activa) | `RAGServiceCompleto` |
| `reranking`, `avanzado_reranking` | `reranking` | `RAGServiceReranking` |
| `hibrido`, `avanzado_hibrido_bm25` | `hibrido` | `RAGServiceHibrido` |
| `descomposicion_hibrida` | `descomposicion_hibrida` | `RAGServiceDescomposicionHibrida` |

Dos avisos al leer estos archivos:

- Los JSON de este periodo **no registran el commit** del código ni una huella
  del dataset. Las fechas y `docs/trabajo/NUCLEO_RAG.md` permiten situarlos,
  pero no prueban por sí solos que dos ejecuciones sean comparables.
- `4-linea-base/dataset_ejecutado_2026-10-11.json` y `4-linea-base/ragas_2026-10-12.json` se hicieron con
  temperatura 0,7, que era la de entonces. Desde EXP-06 todo es con
  temperatura 0.

---

## Convención para los experimentos nuevos (EXP-13 en adelante)

Cada experimento nuevo es una carpeta con nombre que se lee solo:

```
experimentos/
  9-embeddings-y-tamano/EXP-14_modelo-embedding/
    experimento.toml      la definición: qué se varía y qué queda fijo
    LEEME.md              pregunta, hipótesis, resultado, decisión
    resultados/
      2026-11-04_control.json
      2026-11-04_large.json
```

Reglas:

1. **Una pregunta por experimento**, escrita en el `LEEME.md`.
2. **Siempre hay una variante `control`**, que es la configuración de
   producción.
3. **Un solo parámetro cambia por variante.** Si cambian dos, la diferencia no
   se puede atribuir a ninguno.
4. **Cada JSON registra:** experimento, variante, fecha, commit, huella del
   dataset, todos los parámetros (no solo el que cambia), corpus y espacio de
   nombres, métricas, detalle por pregunta y coste.
5. **El embedding y el tamaño de fragmento se fijan al indexar.** Cada variante
   que los cambie se indexa en su propio espacio de nombres (`exp-…`); nunca
   se toca `company-8-assistant-1`.
6. **Al cerrar el experimento se añade su fila a la tabla de arriba**, con la
   decisión tomada.

EXP-13 se corrió con los scripts existentes, antes de que exista el programa
común: tiene su `LEEME.md`, pero sus JSON siguen en `resultados/` con el
nombre de los scripts.
