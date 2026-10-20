"""RAG híbrido: búsqueda densa y léxica, fusionadas por posición.

La búsqueda densa compara significado —dos frases sobre lo mismo quedan cerca
aunque no compartan palabra alguna—. Eso es lo que permite que una pregunta
reformulada con sinónimos siga encontrando su respuesta, y es también su punto
ciego: un acrónimo, un identificador o un término técnico poco frecuente puede
no tener una representación vectorial distintiva, y la similitud coseno lo
trata como si fuera ruido. La búsqueda léxica —aquí, BM25— es la operación
inversa: ciega al significado, precisa con la letra. Un RAG híbrido combina
ambas para que lo que una pasa por alto, la otra pueda rescatarlo.

## El problema de diseño que resuelve esta clase

BM25 y la similitud coseno **no viven en la misma escala**. El umbral de
relevancia, 0,30, está medido exclusivamente sobre puntuaciones coseno —el
apartado 5.3 de la memoria documenta esa medición—; una puntuación BM25 no
tiene techo fijo y comparar una contra la otra directamente no significa nada.
Mezclarlas sin cuidado produce dos modos de fallo opuestos: si se exige que la
puntuación fusionada supere 0,30, el sistema puede dejar de abstenerse nunca
—BM25 encuentra *alguna* coincidencia de palabras funcionales en casi
cualquier corpus— o abstenerse siempre —si la fusión diluye la puntuación
densa por debajo del umbral—. Cualquiera de los dos rompería el requisito
RNF-3.

**La solución, coherente con el resto del pipeline: el umbral protege
primero, la fusión opera después.** Es el mismo patrón que `RAGServiceReranking`
—filtrar antes de reordenar— y que `RAGServiceCompleto` —filtrar antes de
repartir—. Aquí:

    1. búsqueda densa ensanchada (RAG_CANDIDATOS_LEXICOS candidatos)
    2. filtro por umbral, IDÉNTICO al de la línea base
    3. si no sobrevive nada → abstención, igual que la base;
       BM25 no tiene voto sobre si el sistema responde o no
    4. si sobrevive algo → se busca también por BM25 sobre el namespace
       completo, y los dos rankings se fusionan por POSICIÓN
       (Reciprocal Rank Fusion), no por puntuación absoluta
    5. se devuelven los TOP_K mejores de la fusión

**Por qué por posición y no por puntuación.** RRF solo necesita el lugar que
ocupa cada fragmento en cada ranking, nunca el valor numérico de su
puntuación. Es precisamente lo que permite combinar dos métricas en escalas
distintas sin inventar una fórmula de conversión entre ellas.

**Qué puede aportar un fragmento rescatado solo por BM25.** Un fragmento que
no superó el umbral de similitud —incluso uno que la búsqueda densa descartó
por completo, con una puntuación muy baja— puede entrar a la fusión si
comparte términos fuertes con la consulta, siempre que **otro** fragmento de
la misma consulta sí haya superado el umbral —el paso 3 garantiza que nunca es
la única señal—. Es precisamente la operación que un híbrido debe aportar:
rescatar evidencia que la similitud coseno descartó por mala suerte en la
representación vectorial, sin que eso abra una vía alternativa de abstención.

## Coste

Una consulta adicional sin llamada al proveedor —BM25 corre en memoria, sin
coste de tokens— más el tiempo de construir el índice léxico sobre el
namespace completo en cada consulta. Para el corpus de este trabajo, ochenta y
siete fragmentos, es del orden de milisegundos; sobre un corpus de varios
órdenes de magnitud mayor, reconstruirlo en cada consulta dejaría de ser
gratuito y haría falta cachear el índice — ver la limitación declarada en
`indice_lexico.py`.
"""
import logging
from typing import Any, Dict, List, Tuple

from app.core.config import settings
from app.services.indice_lexico import IndiceLexico
from app.services.rag_service import RELEVANCE_THRESHOLD, TOP_K, RAGService

logger = logging.getLogger("uvicorn.error")


class RAGServiceHibrido(RAGService):
    """RAG con búsqueda densa y léxica (BM25), fusionadas por posición."""

    def _fusionar_rrf(
        self,
        densos: List[Any],
        lexicos: List[Tuple[str, float]],
        por_id: Dict[str, Any],
    ) -> List[Any]:
        """Combina dos rankings por *Reciprocal Rank Fusion*.

        `densos` ya superó el umbral. `lexicos` son pares
        `(identificador, puntuación BM25)` del índice léxico, ordenados de
        mayor a menor. `por_id` resuelve el objeto completo —con sus
        metadatos— de cualquier identificador que BM25 haya encontrado y que
        no estuviera entre los candidatos densos.
        """
        k = settings.RAG_RRF_K
        puntuacion_rrf: Dict[str, float] = {}

        for posicion, doc in enumerate(densos, start=1):
            puntuacion_rrf[doc.id] = puntuacion_rrf.get(doc.id, 0.0) + 1.0 / (k + posicion)

        for posicion, (doc_id, _bm25) in enumerate(lexicos, start=1):
            puntuacion_rrf[doc_id] = puntuacion_rrf.get(doc_id, 0.0) + 1.0 / (k + posicion)

        # El orden importa: `por_id` trae un objeto centinela para TODO el
        # corpus, incluidos los fragmentos que ya eran densos. Si se
        # sobrescribiera al revés, un fragmento con puntuación coseno real se
        # quedaría con el valor centinela del umbral, perdiendo la medición
        # que sí se hizo.
        objetos_por_id = dict(por_id)
        objetos_por_id.update({d.id: d for d in densos})

        ordenados = sorted(puntuacion_rrf.items(), key=lambda par: par[1], reverse=True)
        return [objetos_por_id[doc_id] for doc_id, _ in ordenados if doc_id in objetos_por_id]

    def _recuperar(self, query: str, namespace: str, top_k: int = None) -> Tuple[List[Any], int]:
        top_k = TOP_K if top_k is None else top_k
        candidatos_densos, tokens = super()._recuperar(
            query, namespace, top_k=settings.RAG_CANDIDATOS_LEXICOS
        )

        relevantes = [d for d in candidatos_densos
                      if float(getattr(d, "score", 0)) >= RELEVANCE_THRESHOLD]

        if not relevantes:
            logger.info("[RAG~] Ningún candidato denso supera el umbral; se abstiene como la base")
            return [], tokens

        try:
            corpus = self.pinecone_service.listar_namespace(namespace)
        except Exception as e:  # noqa: BLE001
            # BM25 es un complemento; si no se puede traer el corpus completo,
            # se recupera como la línea base en lugar de fallar la consulta.
            logger.warning("[RAG~] No se pudo listar el namespace, solo se usa la búsqueda densa: %s", e)
            return relevantes[:top_k], tokens

        indice = IndiceLexico([(f["chunk_id"], f["text"]) for f in corpus])
        lexicos = indice.buscar(query, top_k=settings.RAG_CANDIDATOS_LEXICOS)

        por_id = {f["chunk_id"]: self._como_documento(f) for f in corpus}
        fusionados = self._fusionar_rrf(relevantes, lexicos, por_id)

        finales = fusionados[:top_k]
        rescatados = sum(1 for d in finales if d.id not in {r.id for r in relevantes})
        logger.info(
            "[RAG~] %d densos sobre umbral, %d candidatos léxicos -> %d al modelo (%d rescatados por BM25)",
            len(relevantes), len(lexicos), len(finales), rescatados,
        )
        return finales, tokens

    @staticmethod
    def _como_documento(fragmento: Dict[str, Any]):
        """Fragmentos que `listar_namespace` trae en forma de diccionario y
        que el resto del pipeline espera como objetos con `.id`, `.score` y
        `.metadata` —la misma forma que devuelve Pinecone—.

        **El `score` es un valor centinela, no una medición.** Un fragmento
        rescatado solo por BM25 nunca participó en la búsqueda por similitud,
        así que no existe una puntuación coseno real que asignarle.
        `generate_response`, heredado, vuelve a filtrar por
        `score >= RELEVANCE_THRESHOLD` sobre lo que `_recuperar` devuelva —es
        el mismo filtro aplicado dos veces, redundante pero inofensivo para el
        resto de configuraciones, porque sus fragmentos ya lo superaron—. Si
        aquí se dejara `None`, esa segunda comparación lanzaría un error en
        tiempo de ejecución. Se usa el propio umbral como marcador: pasa ese
        filtro sin falsificar una similitud que nunca se calculó, y queda
        reconocible en los registros porque ningún fragmento legítimo de la
        búsqueda densa puntúa exactamente ese valor.
        """
        from types import SimpleNamespace
        return SimpleNamespace(
            id=fragmento["chunk_id"],
            score=RELEVANCE_THRESHOLD,
            metadata={
                "document_id": fragmento.get("document_id"),
                "document_name": fragmento.get("document_name", "?"),
                "chunk_index": fragmento.get("chunk_index"),
                "text": fragmento.get("text", ""),
                "rescatado_por_bm25": True,
            },
        )
