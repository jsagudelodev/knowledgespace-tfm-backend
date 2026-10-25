"""Etapa de consulta del pipeline RAG: recuperación en Pinecone + generación
con OpenAI. Es el núcleo del producto — ver `docs/RAG_PIPELINE.md` §4."""
import logging
from typing import Any, Dict, List, Optional

from app.core import observabilidad
from app.core.config import settings
from app.core.exceptions import EmbeddingError, VectorStoreError
from app.services.embedding_service import EmbeddingService
from app.services.pinecone_service import PineconeService

logger = logging.getLogger("uvicorn.error")


class RAGUnavailableError(Exception):
    """Un servicio externo del pipeline (OpenAI o Pinecone) no respondió.

    Se distingue de cualquier otro error para que el router pueda traducirla a
    un 503 con un mensaje entendible, en vez de dejar escapar un 500 con la
    traza. Lleva `etapa` para saber dónde se rompió sin leer los logs.

    **Corregido el 20 de octubre.** Los dos primeros puntos de captura
    atendían `except Exception` a secas porque `embedding_service` y
    `pinecone_service` envolvían cualquier fallo en una `Exception` genérica,
    sin un tipo más fino al que atender — con el riesgo de enmascarar un
    defecto propio (un `TypeError`, por ejemplo) como una caída transitoria
    del proveedor externo. Ahora esos servicios lanzan `EmbeddingError` y
    `VectorStoreError` (`app/core/exceptions.py`), y las dos capturas
    correspondientes se estrecharon a ese tipo concreto. El tercer punto —la
    llamada directa a `self.client.chat.completions.create`— sigue con
    `except Exception` a secas porque ahí sí captura lo que lance el propio
    SDK de OpenAI, no un servicio propio que se pueda tipar. Los tres
    registran con `exc_info=True`: el cliente recibe un mensaje suave, pero la
    traza real queda en el log y el bug sigue siendo diagnosticable.
    """

    def __init__(self, etapa: str, causa: Exception):
        self.etapa = etapa
        self.causa = causa
        super().__init__(f"Fallo en la etapa '{etapa}' del pipeline RAG: {causa}")

# Umbral mínimo de similitud coseno para descartar evidencia débil antes de
# construir el contexto. El 0.30 no es convencional: cae dentro de la banda
# vacía que separa el ruido de la señal en el corpus indexado.
#
# Revalidado el 2026-10-09 sobre el índice fragmentado por oraciones (87
# fragmentos): ruido máximo 0.258, señal mínima 0.393, banda de 0.135 con
# centro en 0.326. El umbral queda con +0.042 de margen sobre el ruido y
# +0.093 bajo la señal.
#
# La medición anterior, de junio y sobre fragmentación por caracteres, daba
# 0.229 / 0.389 y centro en 0.309. La banda se estrechó un 16 % al cambiar la
# fragmentación: prueba de que este valor depende de la configuración y no es
# una constante del dominio. Se mantiene en 0.30 y no se sube al centro porque,
# dentro de la banda, descartar evidencia válida es peor que admitir un
# fragmento mediocre — del segundo ya protege el prompt restrictivo.
#
# Reproducir: `python experimentos/medir_umbral.py --empresa N --asistente M`.
# Razonamiento completo y comparativa en docs/RAG_PIPELINE.md §6.
#
# Hay que repetir la medición si cambia el corpus, la fragmentación, el modelo
# de embeddings o el idioma: los rangos de similitud coseno no son
# transferibles, y nada en el sistema avisa de que el umbral dejó de valer.
# Los tres salen de `settings`, de modo que se ajustan por variable de entorno
# sin tocar código. Se conservan como nombres de módulo porque son los que
# citan los tests, los experimentos y el capítulo 5 de la memoria: renombrarlos
# obligaría a reescribir las referencias de todo eso sin ganar nada.
RELEVANCE_THRESHOLD = settings.RAG_UMBRAL_RELEVANCIA
MAX_RESPONSE_TOKENS = settings.RAG_MAX_TOKENS_RESPUESTA
TOP_K = settings.RAG_TOP_K

# Temperatura por defecto del modelo generativo.
#
# **Era 0.7 y se bajó a 0 tras medirlo** (2026-10-14). El 0.7 contradecía el
# requisito central del sistema: responder únicamente con el contexto recibido.
# Es un valor de escritura creativa, no de respuesta factual, y además el
# descompositor de `rag_service_avanzado` ya usaba 0 — la tarea determinista
# tenía el valor correcto y la que no debe inventar, el incorrecto.
#
# Medición con RAGAS sobre las 12 preguntas con respuesta de
# `experimentos/dataset_evaluacion.csv` (las 6 sin respuesta se evalúan aparte,
# por abstención), mismos contextos recuperados en las dos pasadas (la
# temperatura no afecta a la búsqueda):
#
#     fidelidad (RAGAS)        0,888 -> 0,939
#     mínimo por pregunta      0,538 -> 0,750
#     pertinencia              0,822 -> 0,839
#     5 preguntas suben, 1 baja, 6 quedan igual
#
# La mejora se concentra en los dos peores casos (+0,344 y +0,285), que es lo
# que cabe esperar si la temperatura alta causaba deriva respecto del contexto.
#
# Cautela al citar la cifra: en la misma comparación, `context_precision` se
# movió 3,5 puntos **con entradas idénticas**, lo que acota la variabilidad del
# modelo juez. La media sube por encima de ese ruido, pero la evidencia sólida
# son los casos extremos, no el promedio.
DEFAULT_TEMPERATURE = settings.RAG_TEMPERATURA

# El prompt de sistema tiene dos capas. La identidad por defecto se sustituye
# por la personalidad que cada asistente define en su campo `system_prompt`;
# las reglas de respuesta —usar solo el contexto, abstenerse con la frase exacta,
# no inventar— van SIEMPRE.
#
# Antes, un `system_prompt` propio sustituía el prompt entero y con él las
# reglas: bastaba escribir una personalidad ("Eres un asistente amable de RR.
# HH.") para que ese asistente dejara de abstenerse. Los experimentos nunca lo
# vieron porque miden sin personalidad. Con el campo vacío el mensaje es
# idéntico, carácter por carácter, al de antes (`DEFAULT_SYSTEM_PROMPT`), de modo
# que las cifras del capítulo 5 siguen describiendo este sistema.
IDENTIDAD_POR_DEFECTO = "Eres el asistente de IA interno de la empresa."

REGLAS_DE_RESPUESTA = """RESPONDE ÚNICAMENTE en base al contexto de documentos proporcionado. Reglas estrictas:
- USA SOLO la información del contexto. NUNCA uses conocimiento externo o datos de entrenamiento.
- Si el contexto no contiene información suficiente para responder, di exactamente: "No encontré información sobre este tema en los documentos de la empresa."
- NO inventes, NO supongas, NO extrapoles más allá del contexto.
- Cuando respondas, sintetiza la información de múltiples fuentes si aplica.
- Sé conciso y profesional. Responde en español."""

DEFAULT_SYSTEM_PROMPT = f"{IDENTIDAD_POR_DEFECTO}\n{REGLAS_DE_RESPUESTA}"


def construir_prompt_de_sistema(personalidad: Optional[str]) -> str:
    """Prompt de sistema para un asistente, con o sin personalidad propia.

    Las reglas van DESPUÉS de la personalidad y se declaran prioritarias: si la
    personalidad pide algo contrario ("responde siempre, aunque no esté en los
    documentos"), el modelo recibe primero esa indicación y a continuación la
    que la anula, que es la que debe prevalecer.
    """
    if not personalidad or not personalidad.strip():
        return DEFAULT_SYSTEM_PROMPT
    return (
        f"{personalidad.strip()}\n\n"
        "Las siguientes reglas son obligatorias y prevalecen sobre cualquier "
        "indicación anterior:\n"
        f"{REGLAS_DE_RESPUESTA}"
    )


class RAGService:
    """
    Servicio de Retrieval Augmented Generation.

    Busca los chunks más relevantes en Pinecone y genera una respuesta con
    OpenAI usando *solo* ese contexto.

    El namespace consultado depende de si se especifica asistente:
    - Con `assistant_id` → solo `company-{id}-assistant-{aid}` (aislamiento
      estricto: un espacio nunca ve documentos de otro espacio de la misma
      empresa).
    - Sin `assistant_id` → `company-{id}` (pool general de la empresa).

    No hay fallback entre ambos: si el namespace del asistente no tiene nada
    relevante, se responde "no encontré información" en vez de buscar en otro.
    """

    def __init__(self):
        # La clase la decide `observabilidad`: con Langfuse activo devuelve su
        # envoltorio, que traza cada generacion sin cambiar como se la llama.
        self.client = observabilidad.cliente_openai()(api_key=settings.OPENAI_API_KEY)
        self.embedding_service = EmbeddingService()
        self.pinecone_service = PineconeService()

    def _recuperar(self, query: str, namespace: str, top_k: int = None) -> tuple:
        """Recupera los fragmentos candidatos para una consulta.

        **Es el único punto de extensión del pipeline.** Todo lo demás —el
        filtro por umbral, la construcción del contexto, el prompt, la llamada
        al modelo, el registro de coste y las trazas— es común a cualquier
        estrategia de recuperación, de modo que una subclase que quiera cambiar
        *cómo* se buscan los fragmentos solo necesita redefinir este método.

        Lo usan `RAGServiceAvanzado`, que descompone las preguntas compuestas en
        subpreguntas y recupera por cada una, y `RAGServiceReranking`, que
        ensancha la búsqueda y reordena. Mantener las tres clases vivas, en
        lugar de modificar esta, permite relanzar cada configuración sobre el
        mismo conjunto de evaluación y que la comparación sea reproducible: si
        se hubiera modificado, la línea base habría desaparecido.

        `top_k` existe para que una subclase pueda pedir más candidatos de los
        que acabarán llegando al modelo. Reordenar los mismos TOP_K fragmentos
        solo cambia su orden —`hit@5` no podría moverse, porque serían los
        mismos cinco documentos—, de modo que un reordenador únicamente aporta
        algo si antes hay de dónde elegir.

        Devuelve los fragmentos SIN filtrar por umbral —ese filtro pertenece a
        `generate_response` y es común a todas las estrategias— y los tokens
        consumidos al vectorizar.
        """
        top_k = TOP_K if top_k is None else top_k
        # Sin span propio: el cliente de OpenAI ya está envuelto por Langfuse
        # (ver `observabilidad.cliente_openai`), así que esta llamada queda
        # registrada sola como una observación "OpenAI-embedding", con sus
        # tokens y sus dimensiones. Un span manual alrededor solo duplicaba esa
        # misma información en una segunda fila, y Langfuse Cloud factura por
        # observación ingerida: la redundancia se pagaba dos veces por nada.
        try:
            query_embedding, embedding_tokens = self.embedding_service.generar_embedding_con_uso(query)
        except EmbeddingError as e:
            logger.error("[RAG] Falló el embedding de la consulta: %s", e, exc_info=True)
            raise RAGUnavailableError("embedding de la consulta", e) from e

        try:
            with observabilidad.paso("recuperacion", entrada={"namespace": namespace, "top_k": top_k}) as traza:
                raw_docs: List[Any] = self.pinecone_service.buscar_vectores(
                    query_embedding, top_k=top_k, namespace=namespace
                )
                traza["fragmentos"] = [
                    {
                        "documento": (d.metadata or {}).get("document_name", "?"),
                        "score": round(float(getattr(d, "score", 0)), 3),
                        "supera_umbral": float(getattr(d, "score", 0)) >= RELEVANCE_THRESHOLD,
                    }
                    for d in raw_docs
                ]
                traza["umbral"] = RELEVANCE_THRESHOLD
        except VectorStoreError as e:
            logger.error("[RAG] Falló la búsqueda en Pinecone (namespace=%s): %s", namespace, e, exc_info=True)
            raise RAGUnavailableError("búsqueda vectorial", e) from e

        return raw_docs, embedding_tokens

    def _preparar_generacion(
        self,
        query: str,
        company_id: int,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        assistant_id: Optional[int] = None,
        system_prompt_override: Optional[str] = None,
        model_override: Optional[str] = None,
        temperature_override: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Recuperación + construcción del prompt, compartidas por la
        generación normal y la de streaming (`generate_response_stream`).

        Deliberadamente NO incluye la llamada final al modelo generativo: esa
        es la única parte que difiere entre ambas —con o sin `stream=True`— y
        cada una la hace a su manera.
        """
        # Cada asistente es un espacio de conocimiento aislado: si se pide un
        # assistant_id, la búsqueda se queda en su namespace exclusivamente.
        # Sin esto, un asistente sin match filtraba contenido de otros espacios
        # de la misma empresa — el propio DEFAULT_SYSTEM_PROMPT ya cubre el caso
        # "sin contexto suficiente" respondiendo que no encontró información.
        # El fallback a nivel empresa solo aplica cuando no se especifica asistente.
        if assistant_id:
            namespace = PineconeService.construir_namespace(company_id, assistant_id)
        else:
            namespace = PineconeService.construir_namespace(company_id)

        # Las subclases pueden hacer llamadas de pago al modelo dentro de
        # `_recuperar` —descomponer la consulta, reordenar los fragmentos—. Cada
        # una anota aquí su consumo y el enrutador lo registra: un registro de
        # costes incompleto no es un registro de costes. Se vacía en cada
        # consulta porque el servicio se instancia por petición.
        self.llamadas_auxiliares: List[Dict[str, Any]] = []

        raw_docs, embedding_tokens = self._recuperar(query, namespace)

        relevant_docs = [d for d in raw_docs if getattr(d, "score", 0) >= RELEVANCE_THRESHOLD]

        # Traza de la recuperación. Es la única forma de reconstruir después por
        # qué una respuesta salió como salió: con qué puntuaciones se recuperó y
        # cuántos fragmentos sobrevivieron al umbral. Sin esto, un "no encontré
        # información" es indistinguible de un fallo de indexación.
        puntuaciones = [round(getattr(d, "score", 0), 3) for d in raw_docs]
        logger.info(
            "[RAG] namespace=%s | recuperados=%d | sobre umbral %.2f=%d | scores=%s | consulta=%r",
            namespace, len(raw_docs), RELEVANCE_THRESHOLD, len(relevant_docs),
            puntuaciones, query[:80],
        )
        if not relevant_docs:
            logger.info(
                "[RAG] Ningún fragmento supera el umbral (máximo=%s). El modelo "
                "responderá sin contexto y debe abstenerse.",
                max(puntuaciones, default=0),
            )

        # Identificadores para filtrar en Langfuse. La etiqueta `sin_contexto`
        # permite localizar de un vistazo las consultas en las que el sistema
        # deberia haberse abstenido, que son las que hay que revisar.
        etiquetas = ["rag"] + ([] if relevant_docs else ["sin_contexto"])
        observabilidad.anotar_traza(
            sesion=f"company-{company_id}",
            etiquetas=etiquetas,
            metadatos={
                "company_id": company_id,
                "assistant_id": assistant_id,
                "namespace": namespace,
                "recuperados": len(raw_docs),
                "sobre_umbral": len(relevant_docs),
            },
        )

        context = self._build_context(relevant_docs)
        messages = self._build_messages(query, context, conversation_history, system_prompt_override)

        effective_model = model_override or settings.OPENAI_CHAT_MODEL
        # El chat nunca pasa `temperature_override`: la temperatura no es
        # configurable por asistente. Solo lo usan los experimentos, para medir
        # otras temperaturas sin cambiar la configuración.
        effective_temperature = (
            temperature_override if temperature_override is not None else DEFAULT_TEMPERATURE
        )

        return {
            "messages": messages,
            "effective_model": effective_model,
            "effective_temperature": effective_temperature,
            "relevant_docs": relevant_docs,
            "embedding_tokens": embedding_tokens,
        }

    @observabilidad.observar("rag.consulta")
    def generate_response(
        self,
        query: str,
        company_id: int,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        assistant_id: Optional[int] = None,
        system_prompt_override: Optional[str] = None,
        model_override: Optional[str] = None,
        temperature_override: Optional[float] = None,
    ) -> Dict[str, Any]:
        preparado = self._preparar_generacion(
            query, company_id, conversation_history, assistant_id,
            system_prompt_override, model_override, temperature_override,
        )
        messages = preparado["messages"]
        effective_model = preparado["effective_model"]
        effective_temperature = preparado["effective_temperature"]
        relevant_docs = preparado["relevant_docs"]
        embedding_tokens = preparado["embedding_tokens"]

        try:
            response = self.client.chat.completions.create(
                model=effective_model,
                messages=messages,
                temperature=effective_temperature,
                max_tokens=MAX_RESPONSE_TOKENS,
            )
        except Exception as e:
            logger.error("[RAG] Falló la generación con %s: %s", effective_model, e, exc_info=True)
            raise RAGUnavailableError("generación de la respuesta", e) from e

        logger.info(
            "[RAG] modelo=%s | temperatura=%.2f | tokens entrada=%d salida=%d",
            effective_model, effective_temperature,
            response.usage.prompt_tokens, response.usage.completion_tokens,
        )

        return {
            "content": response.choices[0].message.content,
            "sources": self._build_sources(relevant_docs),
            # El texto ÍNTEGRO de cada fragmento relevante, no el extracto de
            # 300 caracteres que `sources` lleva para mostrarlo en pantalla.
            # Lo consume la evaluación: para juzgar si una respuesta se apoya en
            # el contexto hay que disponer del contexto que el modelo recibió,
            # no de un recorte. Ver `experimentos/GUIA_DATASET.md`.
            "contexts": [
                (d.metadata.get("text") or "") for d in relevant_docs
            ],
            "token_count": response.usage.total_tokens,
            "input_tokens": response.usage.prompt_tokens,
            "output_tokens": response.usage.completion_tokens,
            "model": effective_model,
            "embedding_model": self.embedding_service.modelo,
            "embedding_tokens": embedding_tokens,
            # Vacía en la clase base, que no hace más llamadas que las dos ya
            # registradas. Las subclases la rellenan. Ver `llamadas_auxiliares`
            # más arriba.
            "llamadas_auxiliares": self.llamadas_auxiliares,
        }

    def generate_response_stream(
        self,
        query: str,
        company_id: int,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        assistant_id: Optional[int] = None,
        system_prompt_override: Optional[str] = None,
        model_override: Optional[str] = None,
        temperature_override: Optional[float] = None,
    ):
        """Igual que `generate_response`, pero entrega la respuesta token a
        token según llega de OpenAI, en vez de esperar a tenerla completa.

        Generador que produce eventos `{"type": "delta", "content": str}` a
        medida que el modelo escribe, y termina con un único evento
        `{"type": "done", ...}` con la misma forma que devuelve
        `generate_response` (content completo, sources, tokens, costes) —
        quien llama (el router) persiste el mensaje y registra el coste igual
        en los dos casos, cambia solo cómo se entrega al cliente.

        No sustituye a `generate_response`: viven lado a lado porque la
        latencia total medida para la memoria usa la ruta síncrona, y
        cambiarla habría invalidado esas cifras sin necesidad. El streaming
        no reduce esa latencia total, reduce la ESPERA PERCIBIDA hasta que
        aparece el primer token.
        """
        preparado = self._preparar_generacion(
            query, company_id, conversation_history, assistant_id,
            system_prompt_override, model_override, temperature_override,
        )
        messages = preparado["messages"]
        effective_model = preparado["effective_model"]
        effective_temperature = preparado["effective_temperature"]
        relevant_docs = preparado["relevant_docs"]
        embedding_tokens = preparado["embedding_tokens"]

        try:
            stream = self.client.chat.completions.create(
                model=effective_model,
                messages=messages,
                temperature=effective_temperature,
                max_tokens=MAX_RESPONSE_TOKENS,
                stream=True,
                # Sin esto el chunk final no trae `usage`: con streaming, el
                # conteo de tokens no viene gratis en cada trozo como en la
                # respuesta normal, hay que pedirlo explícitamente.
                stream_options={"include_usage": True},
            )

            contenido = []
            input_tokens = output_tokens = 0
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    texto = chunk.choices[0].delta.content
                    contenido.append(texto)
                    yield {"type": "delta", "content": texto}
                # Llega en el ultimo chunk, el que no trae ningun choice con
                # delta -por eso es un `if` aparte y no un `elif`.
                if chunk.usage:
                    input_tokens = chunk.usage.prompt_tokens
                    output_tokens = chunk.usage.completion_tokens
        except Exception as e:
            logger.error("[RAG] Falló la generación en streaming con %s: %s", effective_model, e, exc_info=True)
            raise RAGUnavailableError("generación de la respuesta", e) from e

        texto_completo = "".join(contenido)
        logger.info(
            "[RAG] (stream) modelo=%s | temperatura=%.2f | tokens entrada=%d salida=%d",
            effective_model, effective_temperature, input_tokens, output_tokens,
        )

        yield {
            "type": "done",
            "content": texto_completo,
            "sources": self._build_sources(relevant_docs),
            "token_count": input_tokens + output_tokens,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "model": effective_model,
            "embedding_model": self.embedding_service.modelo,
            "embedding_tokens": embedding_tokens,
            "llamadas_auxiliares": self.llamadas_auxiliares,
        }

    @staticmethod
    def _build_sources(relevant_docs: List[Any]) -> List[Dict[str, Any]]:
        """Fuentes citables para mostrar en pantalla, a partir de los
        fragmentos que superaron el umbral de relevancia.

        Compartido por `generate_response` y `generate_response_stream`: el
        criterio de qué fragmento es citable no depende de cómo se entrega la
        respuesta.
        """
        return [
            {
                "document_id": d.metadata.get("document_id"),
                "document_name": d.metadata.get("document_name", "Documento desconocido"),
                # **El fragmento entero, no un extracto.** Estuvo recortado
                # a 300 caracteres y eso hacía ilegible la comprobación:
                # ante "¿qué son los hiperparámetros?", el fragmento que
                # contenía la definición la tenía a partir del carácter
                # 470, de modo que quien abría la fuente veía un texto
                # sobre capas y accuracy y concluía que el sistema se
                # había inventado la respuesta.
                #
                # Poder verificar la cita es justamente lo que distingue a
                # este sistema de un modelo conversacional: recortar el
                # fragmento anulaba esa garantía. El índice guarda 1.000
                # caracteres por fragmento, así que esto no trae nada que
                # no estuviera ya en memoria.
                "text": d.metadata.get("text") or "",
                "score": round(getattr(d, "score", 0), 3),
                # Qué fragmento concreto del documento es, no solo de qué
                # documento procede. Sin esto, dos respuestas apoyadas en
                # partes distintas del mismo PDF son indistinguibles, y no
                # se puede ir a comprobar la cita en el original.
                "chunk_index": d.metadata.get("chunk_index"),
                "chunk_id": getattr(d, "id", None),
            }
            for d in relevant_docs
        ]

    def _anotar_llamada(
        self, operacion: str, respuesta: Any, duracion_ms: Optional[int] = None
    ) -> None:
        """Registra el consumo —y, si se mide, la duración— de una llamada
        auxiliar al modelo.

        La usan las subclases tras descomponer o reordenar. Si el proveedor no
        devolviera el consumo —no debería, pero la respuesta es de un tercero—
        la llamada no se anota en lugar de anotarse con ceros: una fila de
        coste con cero tokens es peor que ninguna, porque parece una medición.

        `duracion_ms` es opcional porque medirla es responsabilidad de quien
        llama —cronometrar alrededor de `_anotar_llamada` mediría también el
        procesamiento de la respuesta, no solo la llamada al proveedor—. Antes
        de esto, el único dato de latencia por consulta era el total de
        `generate_response`; esta columna permite además saber cuánto de ese
        total se va en descomponer o reordenar, no solo en la generación
        final.
        """
        uso = getattr(respuesta, "usage", None)
        if uso is None:
            logger.warning("[RAG] La llamada '%s' no devolvió consumo; no se registra", operacion)
            return
        # La lista la prepara `generate_response`, pero los experimentos llaman
        # a `_recuperar` directamente para medir solo la recuperación. Se crea
        # aquí si falta, de modo que medir no exija pasar por el pipeline
        # completo ni pagar una generación que no se va a evaluar.
        if not hasattr(self, "llamadas_auxiliares"):
            self.llamadas_auxiliares = []
        self.llamadas_auxiliares.append({
            "operacion": operacion,
            "modelo": settings.OPENAI_CHAT_MODEL,
            "tokens_entrada": uso.prompt_tokens,
            "tokens_salida": uso.completion_tokens,
            "duracion_ms": duracion_ms,
        })

    @staticmethod
    def _build_context(relevant_docs: List[Any]) -> str:
        parts = []
        for i, doc in enumerate(relevant_docs):
            metadata = doc.metadata if hasattr(doc, "metadata") else {}
            name = metadata.get("document_name", "Documento desconocido")
            text = metadata.get("text", "")
            score = round(getattr(doc, "score", 0), 3)
            parts.append(f"[Fuente {i + 1}] {name} (relevancia: {score})\n{text}")
        return "\n\n".join(parts)

    @staticmethod
    def _build_messages(
        query: str,
        context: str,
        conversation_history: Optional[List[Dict[str, str]]],
        system_prompt_override: Optional[str],
    ) -> List[Dict[str, str]]:
        """
        Arma la lista de mensajes que se envía al LLM. El orden es deliberado:

            1. system  → la personalidad del asistente, si tiene, seguida
                         SIEMPRE de las reglas de respuesta, que prohíben usar
                         conocimiento externo al contexto (ver
                         `construir_prompt_de_sistema`).
            2. system  → el contexto recuperado de los documentos.
            3. historial de la conversación (turnos user/assistant previos).
            4. user    → la pregunta actual.

        Por qué el contexto va como un *segundo mensaje de system* y no dentro
        del mensaje del usuario: así el modelo lo trata como hecho dado y no
        como algo que el usuario afirma —  reduce que lo contradiga o lo
        reinterprete— y mantiene la pregunta del usuario limpia, sin miles de
        tokens de documentos pegados que diluyan la intención real.

        Por qué el historial va *después* del contexto y no antes: el mensaje
        más cercano a la pregunta debe ser la conversación reciente, que es lo
        que da sentido a referencias como "y eso cuánto cuesta". El contexto,
        al ir arriba, funciona como marco estable de toda la conversación.

        Cuando no hay contexto relevante se dice explícitamente en vez de
        mandar un bloque vacío: un hueco silencioso invita a que el modelo lo
        rellene con conocimiento propio, que es justo lo que se quiere evitar.
        """
        messages = [{"role": "system", "content": construir_prompt_de_sistema(system_prompt_override)}]

        messages.append({
            "role": "system",
            "content": (
                f"Contexto de documentos de la empresa:\n{context}"
                if context
                else "No se encontró contexto relevante en los documentos de la empresa."
            ),
        })

        if conversation_history:
            messages.extend(conversation_history)

        messages.append({"role": "user", "content": query})
        return messages
