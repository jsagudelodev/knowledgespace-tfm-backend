# Diagrama de flujo — pipeline RAG

Material de defensa. Dos vistas complementarias del mismo sistema:

1. **El recorrido completo de una consulta**: lo que el chat hace siempre,
   igual en todas las configuraciones. Es el diagrama de la memoria (3.2).
2. **El único punto de extensión** — qué hace cada configuración dentro de
   `_recuperar()`, que es lo único que cambia entre ellas.

Los valores (`TOP_K=5`, umbral `0.30`, etc.) son los **valores por defecto**
de `app/core/config.py`; los cuatro son parametrizables por variable de
entorno. Ver `COMO_ARRANCAR.md` para cómo seleccionar la configuración activa.

---

## 1. El recorrido completo de una consulta

Este es el diagrama del apartado 3.2 de la memoria. Todo lo que no sea
`_recuperar()` vive **una sola vez** en `routers/v1/chat.py` y en
`RAGService` (`_preparar_generacion` y `_build_messages`) y es común a todas
las configuraciones. El único paso que varía es la recuperación, resaltado en
amarillo; la sección 2 lo detalla.

```mermaid
flowchart TB
    subgraph P1 ["1 · Petición"]
        direction LR
        A([Pregunta]) --> B["Usuario, empresa<br/>e historial"]
        B --> D{"¿Alcance<br/>global?"}
        D -- Sí --> E(["Listado de documentos<br/>sin pasar por el RAG"])
    end

    subgraph P2 ["2 · Recuperación"]
        direction LR
        G{{"Búsqueda en Pinecone<br/>← único paso que varía"}} --> I{"¿Score<br/>≥ 0,30?"}
        I -- Sí --> J["Fragmentos"]
        I -- No --> K["Aviso<br/>«sin contexto»"]
    end

    subgraph P3 ["3 · Generación"]
        direction LR
        L["Prompt:<br/>reglas + contexto"] --> M["Respuesta con fuentes<br/>o abstención"]
        M --> Q([Costo, traza<br/>y respuesta])
    end

    P1 -- "No es de alcance global" --> P2
    P2 --> P3

    style G fill:#fff3cd,stroke:#997404,stroke-width:2px
    style K fill:#f8d7da,stroke:#842029
    style Q fill:#d1e7dd,stroke:#0f5132
```

**Lo que hay que señalar si preguntan por la abstención:** cuando ningún
fragmento supera el umbral, el sistema **no se salta el modelo**. Le envía un
aviso explícito de que no hay contexto, y es el modelo el que se abstiene,
porque las reglas del prompt se lo ordenan. Se hace así porque un contexto
vacío y silencioso invita al modelo a rellenarlo con conocimiento propio. El
filtro del umbral (rombo «¿Score ≥ 0,30?») es **posterior** a la recuperación y **común** a todas las
configuraciones: ninguna estrategia de recuperación puede saltárselo.

---

## 2. Dentro de `_recuperar()` — las seis configuraciones

Esto es lo que cambia. `rag_factory.py` instancia una de las seis clases
según `RAG_CONFIGURACION`; cada una reimplementa `_recuperar` de forma
distinta y el resto del pipeline (sección 1) no se entera de cuál está activa.

```mermaid
flowchart TD
    Q([Pregunta]) --> SEL{RAG_CONFIGURACION}

    %% ── base ─────────────────────────────────────────────
    SEL -- base --> B1[Vectorizar la pregunta\ntal cual]
    B1 --> B2["Buscar en Pinecone\ntop_k = 5"]
    B2 --> B3([5 fragmentos])

    %% ── descomposicion ───────────────────────────────────
    SEL -- descomposicion --> D1{"¿El LLM detecta\nvarias preguntas?\n(máx. 3 subpreguntas)"}
    D1 -- "No (1 sola)" --> D2["Recuperación estándar\ntop_k = 5\n← igual que 'base', sin coste extra"]
    D1 -- "Sí (N ≥ 2)" --> D3["Buscar top_k = 5\nPOR CADA subpregunta"]
    D3 --> D4["Fusionar sin duplicados\n(mejor score de cada fragmento)"]
    D4 --> D5(["Hasta N × 5 fragmentos\n↑ el contexto crece sin tope"])
    D2 --> D6([5 fragmentos])

    %% ── descomposicion_acotada (por defecto) ─────────────
    SEL -- "descomposicion_acotada\n(valor por defecto)" --> A1{"¿Varias preguntas?"}
    A1 -- No --> A2["Recuperación estándar\ntop_k = 5"]
    A1 -- Sí --> A3["Buscar top_k = 5\nPOR CADA subpregunta"]
    A3 --> A4["Filtrar por umbral\nPOR SUBPREGUNTA"]
    A4 --> A5["Repartir en turnos:\nel mejor fragmento aún no\nincluido de cada subpregunta"]
    A5 --> A6(["Tope: 5 fragmentos\nrepartidos equilibradamente"])
    A2 --> A7([5 fragmentos])

    %% ── reranking ─────────────────────────────────────────
    SEL -- reranking --> R1["Buscar en Pinecone\ntop_k = 20  ← se ensancha"]
    R1 --> R2["Filtrar por umbral\n(antes de reordenar)"]
    R2 --> R3{"¿Algún candidato\nsupera el umbral?"}
    R3 -- No --> R4([Lista vacía → se abstiene\nigual que 'base'])
    R3 -- Sí --> R5["El LLM reordena los\nsupervivientes por utilidad"]
    R5 --> R6["Conservar los\n5 primeros del nuevo orden"]
    R6 --> R7([5 fragmentos reordenados])

    %% ── hibrido ───────────────────────────────────────────
    SEL -- hibrido --> H1["Búsqueda densa en Pinecone\n+ búsqueda léxica BM25"]
    H1 --> H2["Fusionar ambas listas\n(Reciprocal Rank Fusion)"]
    H2 --> H3([5 fragmentos])

    %% ── descomposicion_hibrida ────────────────────────────
    SEL -- descomposicion_hibrida --> X1{"¿Varias preguntas?"}
    X1 -- No --> X2["Búsqueda híbrida\n(densa + BM25)"]
    X1 -- Sí --> X3["Búsqueda híbrida\nPOR CADA subpregunta"]
    X3 --> X4["Repartir en turnos\ncomo la acotada"]
    X4 --> X5(["Tope: 5 fragmentos"])
    X2 --> X6([5 fragmentos])

    style SEL fill:#fff3cd,stroke:#997404,stroke-width:2px
    style A1 fill:#d1e7dd,stroke:#0f5132
    style A5 fill:#d1e7dd,stroke:#0f5132
    style A6 fill:#d1e7dd,stroke:#0f5132,stroke-width:2px
    style D5 fill:#f8d7da,stroke:#842029
```

**Las frases que hay que tener listas si preguntan "¿por qué esa y no
otra?":**

- **`base`** es la línea base: el término de comparación de todo el
  capítulo 5. Nunca se modifica, para que la comparación siga siendo posible.
- **`descomposicion`** demuestra el techo de la mejora (cobertura del 48 % al
  88 % sobre las seis parejas medidas), pero **sin tope**: con 2 subpreguntas
  ya duplica el contexto y el coste.
- **`descomposicion_acotada`** es la que está activa. Resuelve el mismo
  problema — ninguna subpregunta se queda sin representación (desequilibrio de
  1,83 a 0,83) — **sin** aumentar el presupuesto de 5 fragmentos.
- **`reranking`** mejora la recuperación de forma medible (hit@3 de 0,50 a
  0,67), pero las métricas de generación no se movieron fuera del margen de
  ruido del juez, y multiplica el coste ×3,7. Queda medido y documentado, no
  activo.
- **`hibrido`** es la que mejor encuentra el fragmento correcto (hit@1 de 0,25
  a 0,42), pero busca con la pregunta completa y baja la cobertura de las
  preguntas de dos temas del 48 % al 30 %. **`descomposicion_hibrida`** la
  sube al 37 %, sin llegar a la base, y es la más lenta. Ninguna está activa:
  retroceden justo en las preguntas compuestas.

---

## 3. Cómo se seleccionan en producción

```mermaid
flowchart LR
    ENV[".env\nRAG_CONFIGURACION"] --> FAC["rag_factory.clase_de()"]
    FAC -->|nombre válido| CLS["Instancia la clase\ncorrespondiente"]
    FAC -->|nombre desconocido| BASE["Cae a 'base'\n+ warning en el log"]
    CLS --> CHAT["routers/v1/chat.py\nno sabe cuál está activa"]
    BASE --> CHAT

    style FAC fill:#fff3cd,stroke:#997404,stroke-width:2px
    style BASE fill:#f8d7da,stroke:#842029
```

El router de chat llama a `crear_rag_service()` y usa el resultado como un
`RAGService` cualquiera — no necesita saber cuál de las seis clases recibió.
Cambiar de configuración es cambiar una variable de entorno, nunca tocar
código.
