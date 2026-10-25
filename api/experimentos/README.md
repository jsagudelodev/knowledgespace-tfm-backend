# Experimentos

Mediciones que respaldan las afirmaciones de la memoria. Cada una se puede
reproducir con un comando, y su salida queda en `resultados/` con la fecha.

> La regla del proyecto es que toda afirmación sobre el sistema debe poder
> verificarse en el código. Estos scripts son esa verificación: si la memoria
> dice "el chunking semántico elimina los cortes a mitad de palabra", aquí está
> el número y cómo se obtuvo.

**Todos los experimentos miden el código de producción, nunca una copia.**
Importan los servicios de `app/` y usan sus métodos tal cual. Un experimento que
reimplementara la lógica estaría midiendo otro sistema.

---

## 1. Calidad estructural del chunking

```bash
cd api
python experimentos/medir_chunking.py <carpeta-con-PDFs>
```

Compara las dos estrategias que conviven en `PDFService` sobre los mismos
documentos. **No llama a ningún modelo: no cuesta nada ejecutarlo.**

> **El corpus no está en el repositorio.** Los documentos usados son material
> docente de terceros y este repositorio se entrega con el TFM, así que no se
> publican. Lo que sí está versionado son las cifras que produjeron, en
> `resultados/`, y la descripción del corpus más abajo. El script funciona con
> cualquier carpeta de PDFs.

| Métrica | Qué responde |
|---|---|
| Nº de chunks | Cuántos embeddings habrá que pagar al indexar |
| Tamaño medio, desviación, mín, máx | Cómo de regulares son los fragmentos |
| % que cortan una palabra | El defecto que la división por oraciones promete arreglar |
| % que cortan una frase | Lo mismo a nivel de idea completa |
| % que exceden el objetivo | Detecta oraciones más largas que `target_size` |
| Cobertura | Por encima del 100% hay texto duplicado; por debajo, texto perdido |
| Densidad de puntos | Distingue prosa de material esquemático sin clasificarlo a mano |

### Cómo se miden los cortes

Criterios deliberadamente simples, para que cualquiera pueda comprobarlos:

- **Corta palabra:** el chunk termina en un carácter alfanumérico.
- **Corta frase:** el chunk no termina en `.`, `!`, `?`, `:` o `;`.
- En ambos casos **se excluye el último chunk** de cada documento: ahí el texto
  se acabó de verdad, no hay corte. Sin esa exclusión, todo documento sumaría un
  falso positivo.

Un análisis sintáctico real daría cifras más finas, pero introduciría una
dependencia que el sistema no tiene: se estaría midiendo otra cosa.

### El corpus medido

Tres documentos de un mismo curso, elegidos para cubrir dos formatos distintos:

| Documento | Págs | Tamaño | Puntos por mil | Formato |
|---|---|---|---|---|
| Diapositivas, Tema 1 Clase 1 | 31 | 2,7 MB | 15,6 | esquemático |
| Resumen, Clase 2 Tema 1 | 2 | 134 KB | 6,7 | prosa |
| Resumen, Clase 3 Tema 1 | 2 | 131 KB | 4,9 | prosa |

La densidad de puntos importa porque la división por oraciones usa el punto como
único separador: un documento con pocos puntos le da pocos sitios donde cortar.

### Resultados del 2026-10-07

Sobre esos 3 documentos:

| Estrategia | Chunks | Cortan palabra | Cortan frase | Cobertura |
|---|---|---|---|---|
| Por caracteres | 24 | **79,2 %** | 83,3 % | ~123 % |
| Por oraciones | 21 | **0,0 %** | 0,0 % | ~100 % |

Tres lecturas:

1. La división por oraciones **elimina por completo** los cortes a mitad de
   palabra y de frase.
2. El solapamiento de 200 caracteres **duplica cerca de una cuarta parte** del
   texto: se paga dos veces en embeddings.
3. Se generan un **12,5 % menos de chunks**, con el ahorro correspondiente.

A cambio, los fragmentos son menos regulares, tal como advierte el docstring del
método: en las diapositivas la desviación de tamaño pasa de 107 a 228.

**Limitaciones de esta medición, para no sobreinterpretarla:**

- Muestra pequeña: 3 documentos, 24 chunks. La diferencia es lo bastante grande
  para ser clara, pero no autoriza a generalizar a cualquier corpus.
- La división por oraciones no conserva el texto exactamente (99,1 % a 100,4 %
  de cobertura): `split(".")` reconstruye los separadores y eso altera alrededor
  del 1 % del contenido.
- Una hipótesis previa resultó falsa: se esperaba que las diapositivas tuvieran
  *menos* puntos que la prosa y resultó que tienen **más** (15,6 por mil frente
  a 4,9 y 6,7), probablemente por numeraciones y abreviaturas.

---

## Pendientes

**2. Calidad de recuperación.** Requiere un conjunto de preguntas con el
fragmento correcto anotado a mano. Mediría `hit@1`, `hit@3` y MRR con cada
estrategia. Es el experimento que de verdad dice cuál recupera mejor; el primero
solo dice qué le hace cada uno al texto.

**3. Revalidación del umbral de relevancia.** El `0.30` de
`RAGService.RELEVANCE_THRESHOLD` se midió **antes** de que existiera la división
por oraciones. Como el chunking cambia la distribución de similitudes, hay que
repetir la medición de `docs/TFM/RAG_PIPELINE.md` §6 y confirmar o corregir el valor.
