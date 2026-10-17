"""RAG avanzado: descomposición de consultas.

Extiende `RAGService` cambiando **únicamente cómo se recuperan los fragmentos**.
El umbral de relevancia, el prompt restrictivo, la construcción del contexto, el
registro de coste, las trazas y la abstención se heredan sin modificación.

## El problema que resuelve

El pipeline base convierte el MENSAJE COMPLETO en un único vector antes de
buscar. Si el mensaje contiene dos preguntas sobre temas distintos, ese vector
no representa bien a ninguna de las dos: queda en un punto intermedio del
espacio de representaciones que puede no estar cerca de ningún fragmento.

Medido sobre seis parejas de preguntas (`experimentos/medir_preguntas_compuestas.py`,
2026-10-09):

    cobertura conjunta media              48 %   (mínimo 40 %, máximo 60 %)
    fragmentos sobre el umbral            30/30
    parejas donde la compuesta puntúa
    más que alguna separada                6/6

Lo grave no es perder evidencia, sino que **nada lo señala**: el umbral mide
parecido, no cobertura, de modo que los cinco fragmentos lo superan igualmente y
el usuario recibe una respuesta de apariencia completa construida sobre la mitad
del material.

## La estrategia

    "¿Qué es un VAE y cómo se entrena un transformer?"
                       │
                       ├── el modelo la descompone
                       │
              ┌────────┴────────┐
              ▼                 ▼
      "¿Qué es un VAE?"   "¿Cómo se entrena un transformer?"
              │                 │
          búsqueda          búsqueda          ← dos vectores, no uno
              │                 │
              └────────┬────────┘
                       ▼
            fragmentos unidos, sin duplicados

Cada subpregunta se vectoriza por separado, que es precisamente lo que el
pipeline base no hace.

## Dos propiedades que conviene conocer

**Si la pregunta no es compuesta, el comportamiento es idéntico al de la base.**
La descomposición devuelve una sola subpregunta, se hace una sola búsqueda y se
llama a `super()._recuperar`. La mejora solo actúa cuando hace falta.

**El contexto crece con el número de subpreguntas.** Se recuperan `TOP_K`
fragmentos por cada una, de modo que una pregunta doble envía aproximadamente el
doble de contexto al modelo y cuesta en torno al doble. Es el precio de la
cobertura, y queda acotado por dos vías: el límite de subpreguntas y el umbral
de relevancia, que sigue descartando lo que no llega a 0,30.

## Coste

Una llamada adicional al modelo por consulta para descomponer —con `max_tokens`
reducido y temperatura 0, en torno a 5·10⁻⁵ USD— más una búsqueda vectorial por
subpregunta. La latencia sube alrededor de un segundo.

Si la descomposición falla por cualquier motivo, se recupera como el pipeline
base: nunca debe impedir una respuesta.
"""
import logging
from typing import Any, List, Tuple

from app.core import observabilidad
from app.core.config import settings
from app.services.rag_service import TOP_K, RAGService

logger = logging.getLogger("uvicorn.error")

# Más de tres subpreguntas suele indicar que el modelo está desmenuzando una
# pregunta simple en matices, no separando temas. Y cada una añade contexto que
# se paga en todas las consultas.
MAX_SUBPREGUNTAS = settings.RAG_MAX_SUBPREGUNTAS

PROMPT_DESCOMPOSICION = """Tu tarea es decidir si un mensaje contiene VARIAS preguntas independientes sobre temas distintos.

Reglas estrictas:
- Si el mensaje contiene una sola pregunta, devuélvelo TAL CUAL, sin cambiar nada.
- Si contiene varias sobre temas distintos, devuelve cada una en su propia línea, reformulada para que se entienda por sí sola.
- NUNCA inventes preguntas que no estén en el mensaje original.
- NUNCA devuelvas más de {maximo} líneas.
- No añadas numeración, viñetas, explicaciones ni comentarios: solo las preguntas, una por línea.

Mensaje: {mensaje}"""


class RAGServiceAvanzado(RAGService):
    """RAG con descomposición de consultas.

    Se mantiene como clase aparte y no como una modificación de `RAGService`
    para que ambas configuraciones puedan ejecutarse sobre el mismo conjunto de
    evaluación y la comparación sea reproducible. Modificar la base habría
    hecho desaparecer el punto de referencia.
    """

    def _descomponer(self, query: str) -> List[str]:
        """Separa un mensaje en subpreguntas independientes.

        Devuelve siempre al menos una. Ante cualquier fallo —del modelo, de la
        red o del formato de la respuesta— devuelve la consulta original: la
        descomposición es una mejora, nunca un punto de fallo.
        """
        try:
            respuesta = self.client.chat.completions.create(
                model=settings.OPENAI_CHAT_MODEL,
                messages=[{
                    "role": "user",
                    "content": PROMPT_DESCOMPOSICION.format(
                        maximo=MAX_SUBPREGUNTAS, mensaje=query
                    ),
                }],
                temperature=0,
                max_tokens=200,
            )
            self._anotar_llamada("descomposicion", respuesta)
            texto = (respuesta.choices[0].message.content or "").strip()
        except Exception as e:  # noqa: BLE001
            logger.warning("[RAG+] Falló la descomposición, se usa la consulta original: %s", e)
            return [query]

        subs = [l.strip() for l in texto.splitlines() if l.strip()]
        # Una descomposición vacía o excesiva no es de fiar: se ignora.
        if not subs or len(subs) > MAX_SUBPREGUNTAS:
            logger.warning("[RAG+] Descomposición descartada (%d líneas)", len(subs))
            return [query]
        return subs

    def _recuperar_cada_una(
        self, subpreguntas: List[str], namespace: str, top_k: int = None
    ) -> Tuple[List[List[Any]], int]:
        """Busca por cada subpregunta y devuelve **los resultados separados**.

        Se mantienen separados, y no fusionados de entrada, porque saber de qué
        subpregunta viene cada fragmento es lo único que permite repartir con
        equilibrio cuando hay que recortar. `RAGServiceCompleto` lo aprovecha.
        """
        listas: List[List[Any]] = []
        tokens_total = 0
        for sub in subpreguntas:
            docs, tokens = super()._recuperar(sub, namespace, top_k=top_k)
            tokens_total += tokens
            listas.append(docs)
        return listas, tokens_total

    @staticmethod
    def _fusionar(listas: List[List[Any]]) -> List[Any]:
        """Une los resultados descartando repetidos, por puntuación.

        Un mismo fragmento puede aparecer en varias búsquedas; se conserva una
        sola vez y con la **mejor** puntuación obtenida, porque es la que
        refleja su relevancia máxima para el conjunto de la consulta.
        """
        mejores: dict = {}
        for docs in listas:
            for d in docs:
                previo = mejores.get(d.id)
                if previo is None or getattr(d, "score", 0) > getattr(previo, "score", 0):
                    mejores[d.id] = d
        return sorted(mejores.values(), key=lambda d: getattr(d, "score", 0), reverse=True)

    def _recuperar(self, query: str, namespace: str, top_k: int = None) -> Tuple[List[Any], int]:
        """Recupera descomponiendo la consulta si contiene varias preguntas.

        `top_k` se propaga a cada subpregunta: son `top_k` fragmentos **por
        cada una**, no en total.
        """
        with observabilidad.paso("descomposicion", entrada=query) as traza:
            subpreguntas = self._descomponer(query)
            traza["subpreguntas"] = subpreguntas
            traza["n"] = len(subpreguntas)

        # Una sola subpregunta: el camino de la clase base, sin coste añadido.
        if len(subpreguntas) == 1:
            logger.info("[RAG+] Consulta simple, recuperación estándar")
            return super()._recuperar(subpreguntas[0], namespace, top_k=top_k)

        logger.info("[RAG+] Consulta descompuesta en %d: %s",
                    len(subpreguntas), subpreguntas)

        por_subpregunta, tokens_total = self._recuperar_cada_una(
            subpreguntas, namespace, top_k
        )
        fusionados = self._fusionar(por_subpregunta)

        logger.info(
            "[RAG+] %d subpreguntas -> %d fragmentos únicos (de %d recuperados)",
            len(subpreguntas), len(fusionados), len(subpreguntas) * TOP_K,
        )
        return fusionados, tokens_total
