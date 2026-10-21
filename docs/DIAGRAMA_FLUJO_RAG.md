# Diagrama de flujo — pipeline RAG

Material de defensa. Dos vistas complementarias del mismo sistema:

1. **El esqueleto compartido** — lo que `generate_response()` hace siempre,
   igual en las cuatro configuraciones.
2. **El único punto de extensión** — qué hace cada configuración dentro de
   `_recuperar()`, que es lo único que cambia entre ellas.

Los valores (`TOP_K=5`, umbral `0.30`, etc.) son los **valores por defecto**
de `app/core/config.py`; los cuatro son parametrizables por variable de
entorno. Ver `COMO_ARRANCAR.md` para cómo seleccionar la configuración activa.

---

## 1. El esqueleto compartido (Template Method)

Todo lo de aquí vive **una sola vez** en `RAGService.generate_response()` y se
hereda sin modificar. El único rombo que varía por configuración es
`_recuperar()` — ver la sección 2.

```mermaid
flowchart TD
    A([Pregunta del usuario]) --> B[Generar embedding de la consulta]
    B --> C{{"_recuperar(query, namespace)\n← ÚNICO PUNTO DE EXTENSIÓN"}}
    C --> D[Filtrar por umbral de relevancia\n0.30]
    D --> E{"¿Algún fragmento\nsupera el umbral?"}
    E -- No --> F(["Abstención:\n'No encontré información\nsobre este tema...'"])
    E -- Sí --> G[Construir contexto\ncon los fragmentos supervivientes]
    G --> H[Construir mensajes:\nsystem + contexto + historial + pregunta]
    H --> I[Llamada al modelo generativo\ngpt-4o-mini]
    I --> J[Registrar coste\ntokens de entrada/salida]
    J --> K([Respuesta + fuentes citadas])

    style C fill:#fff3cd,stroke:#997404,stroke-width:2px
    style F fill:#f8d7da,stroke:#842029
    style K fill:#d1e7dd,stroke:#0f5132
```

**Lo que hay que señalar si preguntan por el umbral:** el filtro (paso D) es
**posterior** a `_recuperar` y **común** a las cuatro configuraciones. Ninguna
estrategia de recuperación puede saltárselo — es la garantía de que la
abstención se comporta igual sin importar cuál esté activa.

---

## 2. Dentro de `_recuperar()` — las cuatro configuraciones

Esto es lo que cambia. `rag_factory.py` instancia una de las cuatro clases
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

    style SEL fill:#fff3cd,stroke:#997404,stroke-width:2px
    style A1 fill:#d1e7dd,stroke:#0f5132
    style A5 fill:#d1e7dd,stroke:#0f5132
    style A6 fill:#d1e7dd,stroke:#0f5132,stroke-width:2px
    style D5 fill:#f8d7da,stroke:#842029
```

**Las tres frases que hay que tener listas si preguntan "¿por qué esa y no
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
`RAGService` cualquiera — no necesita saber cuál de las cuatro clases recibió.
Cambiar de configuración es cambiar una variable de entorno, nunca tocar
código.
