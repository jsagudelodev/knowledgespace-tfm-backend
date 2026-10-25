# Cómo funciona el RAG — explicación desde cero

Este documento existe para una sola cosa: **entender el sistema sin mirar
código**, de modo que si el tutor pregunta "¿y esto por qué funciona así?" la
respuesta salga de haberlo entendido, no de haberlo memorizado.

Para la referencia técnica con nombres de archivo y líneas exactas, ver
`RAG_PIPELINE.md`. Para la taxonomía de arquitecturas y por qué se eligió esta,
ver `ARQUITECTURAS_RAG.md`. Para el diagrama visual, ver `DIAGRAMA_FLUJO_RAG.md`.
Este documento es el paso anterior a los tres: la intuición.

---

## El problema, antes que la solución

Hay miles de palabras repartidas en documentos PDF. Alguien pregunta algo en
lenguaje natural. El sistema tiene que encontrar, entre todo ese texto, el
trocito exacto que responde — y redactar una respuesta usando **solo** ese
trocito, sin inventar nada.

Dos preguntas escondidas ahí:

1. ¿Cómo se encuentra el trocito correcto sin leer todo el documento cada vez?
2. ¿Cómo se sabe que ese trocito es realmente sobre lo preguntado, y no algo
   que solo se parece por casualidad?

Todo lo que sigue es la respuesta a esas dos preguntas.

---

## 1. Convertir palabras en números — el embedding

Imagina que cada frase, en vez de texto, fuera un **punto en un mapa**. Un mapa
con 1536 direcciones a la vez en lugar de dos (norte/sur, este/oeste) — pero la
idea es la misma si se piensa en dos.

En ese mapa, las frases que **significan cosas parecidas** quedan **cerca**, y
las que no tienen relación quedan **lejos**:

```
                    "qué es un VAE"  ●
                                      \
                           ● "autoencoder variacional"

                                                    ● "cuál es la capital de Francia"
```

"Qué es un VAE" y "autoencoder variacional" caen cerca aunque no compartan ni
una palabra, porque hablan de lo mismo. "Capital de Francia" cae lejísimos.

Ese mapa no se dibuja a mano: lo calcula un modelo de OpenAI,
**`text-embedding-3-small`**. Le entra una frase, le salen 1536 números — sus
coordenadas en el mapa. A esa lista de números se le llama **embedding**, y a
las coordenadas, **vector**. El modelo no entiende nada ni razona: solo calcula
dónde cae esa frase en el mapa del significado.

---

## 2. Por qué vectores y no buscar por palabras (Ctrl+F)

Si se buscara por coincidencia exacta de texto, la pregunta *"¿por qué los
modelos de difusión son más estables que las GAN?"* solo encontraría frases que
contuvieran literalmente "modelos de difusión" o "estables". Si la respuesta
real dice *"no hay dos redes compitiendo, lo que elimina el colapso de modo"* —
sin usar la palabra "estable"— **Ctrl+F no la encuentra nunca**.

Con el mapa de significados sí se encuentra, porque esa frase cae cerca en el
mapa aunque no comparta palabras. Eso es lo que permite preguntar con palabras
propias y encontrar la respuesta aunque el documento la diga de otra forma.

**El precio de esto:** el mapa de significados confunde entre sí cosas que se
parecen en forma pero no en contenido — típicamente, códigos y números
("régimen 3040" vs "régimen 3050"). Ese es el hueco que una recuperación
híbrida (vectores + búsqueda léxica) vendría a tapar — ver
`ARQUITECTURAS_RAG.md` §4.2 y el ejercicio `practica-tfm/9.0_rag_hibrido.py`.

---

## 3. Trocear el documento — chunking

No se mete el PDF entero como un solo punto en el mapa: sería un punto
"borroso", mezclando veinte temas a la vez. Por eso se trocea en
**fragmentos** (chunks), cada uno convertido en su propio punto:

```
Documento completo
   │
   ├── Fragmento 1 (habla de VAE)         → su propio punto en el mapa
   ├── Fragmento 2 (habla de GAN)         → su propio punto en el mapa
   ├── Fragmento 3 (habla de difusión)    → su propio punto en el mapa
   └── ...
```

**Cómo se trocea importa, y está medido.** Cortar por caracteres fijos puede
partir una frase a la mitad; ese fragmento mutilado cae en un punto raro del
mapa que no representa bien ninguna idea completa. Por eso el troceado respeta
los finales de oración: cada punto del mapa es una idea completa, no una idea
cortada. Medido en `api/experimentos/medir_chunking.py`: el troceado por
caracteres cortaba el 79 % de los fragmentos a mitad de palabra; por oraciones,
el 0 %.

---

## 4. Guardar los puntos — Pinecone

Con miles de fragmentos ya convertidos en puntos del mapa, hace falta un sitio
donde guardarlos y poder preguntar rápido: *"¿cuáles son los puntos más
cercanos a este otro punto?"*

Ese sitio es **Pinecone**: una base de datos que, en vez de buscar por texto
exacto o por un identificador, busca por **cercanía en el mapa**. Se le da un
vector y devuelve los vectores guardados más cercanos a él.

---

## 5. La pregunta entra en el mismo mapa

Aquí está el mecanismo central de todo el sistema:

**La pregunta del usuario se convierte en un punto del mismo mapa**, con el
mismo modelo de embeddings que se usó para los documentos.

```
Usuario pregunta: "qué es un VAE"
            │
            ▼
   [mismo modelo de embeddings]
            │
            ▼
   Un punto en el mapa: [0.21, -0.05, 0.88, ... 1536 números]
```

El sistema le pide a Pinecone los puntos de documentos guardados más cercanos
a ese punto. Toda la "inteligencia" de la búsqueda es, literalmente, medir
distancias entre puntos en un mapa de 1536 dimensiones.

**Cómo se mide esa cercanía — similitud coseno.** En vez de la distancia en
línea recta, se mide el **ángulo** entre dos puntos vistos desde el origen del
mapa. Ángulo pequeño → direcciones parecidas → significado parecido. El
resultado es un número entre 0 y 1: cuanto más cerca de 1, más parecidos.

```
pregunta ●
          \  ángulo pequeño
           \
            ● fragmento sobre VAE        → similitud alta, ej. 0.58


pregunta ●
          \
           \                    ángulo grande
            \
             ·  ·  ·  ·  ·  ·  ● fragmento sobre capital de Francia
                                            → similitud baja, ej. 0.14
```

Ese número es el **score** que aparece en el código y en las trazas de
Langfuse.

---

## 6. Cuántos fragmentos traer — el `top_k`

Pinecone no da solo el punto más cercano: da los **N más cercanos**, ordenados
de más a menos parecido. Ese N es el `top_k`, y vale **5 por defecto**
(`RAG_TOP_K` en `app/core/config.py`).

**Por qué 5 y no 1, ni 50.** Con 1, si la respuesta está repartida en dos
párrafos y el primero no basta, el sistema se queda corto. Con 50, se le manda
al modelo generativo demasiado texto — más caro, más lento, con más ruido
mezclado entre lo bueno. 5 es un punto intermedio: margen para encontrar la
evidencia aunque no sea el fragmento número 1, sin inflar coste ni latencia. Es
una decisión de ingeniería, no una ley matemática — por eso es configurable, y
por eso en el reordenado (§9) se sube a 20 temporalmente.

---

## 7. El problema: Pinecone siempre contesta, tenga o no algo bueno

Pinecone **siempre** devuelve 5 fragmentos, aunque ninguno tenga que ver con la
pregunta — como un bibliotecario al que se le pide "tráeme los 5 libros más
parecidos a esto": si no hay nada parecido, trae los 5 *menos distintos*, que
pueden seguir sin relación alguna.

Si esos 5 fragmentos irrelevantes se le pasaran tal cual al modelo generativo,
es probable que inventara algo con tono convincente. Eso es una alucinación.

---

## 8. El umbral — la línea entre "sirve" y "no sirve"

La solución es una **línea de corte** en el score de similitud. Si un
fragmento no la supera, se descarta, aunque sea el mejor de los 5.

Esa línea es **0.30** (`RAG_UMBRAL_RELEVANCIA`), y no se inventó: se midió.

```
Se lanzaron preguntas de tres tipos contra los documentos reales:

  AJENA ("capital de Francia")    → similitud más alta lograda:  0.258
  CUBIERTA ("qué son las GANs")   → similitud más baja de una buena: 0.393

              0.258                              0.393
  ruido  ◄────────┤        ZONA VACÍA        ├────────►  señal
              máximo                            mínima

                         0.30 ← el umbral, justo en medio
```

Cualquier valor entre 0.258 y 0.393 funciona igual de bien: no hay nada ahí en
medio, es tierra de nadie entre "esto es ruido" y "esto es señal real". 0.30
cae en esa banda vacía. Medido en `api/experimentos/medir_umbral.py`, y
**revalidado** después de cambiar el troceado — el umbral se midió antes del
cambio de chunking y había que confirmar que seguía valiendo con la nueva
distribución de similitudes. Seguía.

**Qué hace en la práctica.** De los 5 fragmentos que trae Pinecone, se
descartan los que no llegan a 0.30. Si ninguno llega, no hay con qué responder
— y en vez de inventar, el sistema dice *"No encontré información sobre este
tema en los documentos de la empresa"*. Medido: 6 de 6 preguntas fuera del
corpus produjeron esa abstención, y 0 de 12 preguntas con respuesta real
produjeron una abstención incorrecta (`api/experimentos/resultados/` — dataset
con dos conjuntos, uno de control y otro fuera de corpus; un único conjunto no
demuestra nada, porque un sistema que se callara siempre sacaría el mismo
100 % de "abstención correcta" sin haber aprendido nada).

---

## 9. Construir el contexto y preguntarle al modelo generativo

Los fragmentos que sobrevivieron al umbral se pegan en un bloque de texto — el
**contexto**. Se arma un mensaje para el modelo generativo (`gpt-4o-mini`) así:

```
1. "Eres un asistente. Responde SOLO con el contexto. Si no hay
    información suficiente, di que no la encontraste."      ← las reglas
2. "Contexto: [fragmentos que pasaron el umbral]"            ← la evidencia
3. [historial de la conversación, si lo hay]                 ← memoria
4. "Pregunta: qué es un VAE"                                 ← lo pedido
```

El modelo no busca nada por su cuenta: solo lee ese paquete y redacta una
respuesta basándose en él. Si el contexto no tiene la respuesta, sus propias
instrucciones (punto 1) lo obligan a admitirlo.

---

## El viaje completo, de un tirón

```
"¿Qué es un VAE?"
       │
       ▼
Se convierte en un punto del mapa (embedding)
       │
       ▼
Pinecone busca los 5 puntos más cercanos (top_k = 5)
       │
       ▼
Se descartan los que no llegan a 0.30 de similitud (umbral)
       │
       ├── Si no sobrevive ninguno → "No encontré información..."
       │
       └── Si sobrevive alguno →
                │
                ▼
         Se arma el contexto con esos fragmentos
                │
                ▼
         gpt-4o-mini redacta la respuesta, usando SOLO ese contexto
                │
                ▼
         Respuesta + las fuentes citadas (qué documentos la respaldan)
```

Todo lo que viene después (§10) son variaciones sobre **un único paso** de este
viaje: cómo se eligen los 5 fragmentos. El resto nunca cambia — ver
`DIAGRAMA_FLUJO_RAG.md` para el porqué de diseño (patrón Template Method).

---

## 10. Las cuatro variantes, ya con el viaje base entendido

- **`base`** — el viaje tal cual se acaba de contar. Un embedding, un
  `top_k = 5`, listo.
- **`descomposicion`** — si la pregunta en realidad son dos preguntas pegadas
  ("qué es un VAE y qué son las GAN"), un modelo las separa primero, y se hace
  el viaje completo una vez por cada una, trayendo 5 fragmentos de cada lado.
  Riesgo: puede acabar mandando 10 fragmentos en vez de 5.
- **`descomposicion_acotada`** (la activa hoy) — igual, pero al final se queda
  solo con 5 en total, repartidos de forma equilibrada entre las subpreguntas,
  en vez de dejar que una se lleve todo el espacio.
- **`reranking`** — en vez de traer 5, trae 20 candidatos, los descarta por el
  umbral igual que siempre, y antes de quedarse con los 5 mejores, le pide a un
  modelo que los **reordene** por utilidad real — porque "parecido en el mapa"
  no siempre coincide con "lo más útil para responder esta pregunta concreta".

---

## Respuestas de una frase, por si preguntan algo suelto

| Pregunta | Respuesta corta |
|---|---|
| ¿Por qué vectores y no texto? | Para encontrar significado aunque no se compartan palabras |
| ¿Qué mide la similitud coseno? | El ángulo entre dos puntos, no la distancia — qué tan parecida es la *dirección* del significado |
| ¿Por qué `top_k = 5`? | Equilibrio entre margen para encontrar la evidencia y no encarecer/ensuciar la respuesta con ruido |
| ¿De dónde sale el umbral `0.30`? | Medido: cae en la banda vacía entre el ruido máximo (0.258) y la señal mínima (0.393) |
| ¿Qué pasa si nada supera el umbral? | Se abstiene en vez de inventar — medido: 6/6 correcto, con conjunto de control de 12 preguntas sin falsas abstenciones |
| ¿Por qué importa cómo se trocea? | Un fragmento cortado a mitad de frase cae en un punto "borroso" del mapa que no representa bien ninguna idea |
| ¿Qué hace el modelo generativo exactamente? | Redacta con el contexto dado, nunca busca por su cuenta; sus propias instrucciones le prohíben usar conocimiento externo |

---

## Para seguir, en código

Con esta intuición ya construida, el siguiente paso es leer `rag_service.py` —
ahí vive el viaje base completo, método por método, con los mismos nombres que
aparecen aquí (`_recuperar`, `RELEVANCE_THRESHOLD`, `TOP_K`). `RAG_PIPELINE.md`
tiene la referencia técnica completa con rutas de archivo y línea exacta de
cada pieza.
