"""Etapa de consulta del pipeline RAG: recuperación en Pinecone + generación
con OpenAI. Es el núcleo del producto — ver `docs/RAG_PIPELINE.md` §4."""
from typing import Any, Dict, List, Optional

from openai import OpenAI

from app.core.config import settings
from app.services.embedding_service import EmbeddingService
from app.services.pinecone_service import PineconeService

RELEVANCE_THRESHOLD = 0.30   # umbral mínimo de similitud coseno para evitar hallucinations
MAX_RESPONSE_TOKENS = 1000   # límite de tokens en la respuesta del LLM

DEFAULT_SYSTEM_PROMPT = """Eres el asistente de IA interno de la empresa.
RESPONDE ÚNICAMENTE en base al contexto de documentos proporcionado. Reglas estrictas:
- USA SOLO la información del contexto. NUNCA uses conocimiento externo o datos de entrenamiento.
- Si el contexto no contiene información suficiente para responder, di exactamente: "No encontré información sobre este tema en los documentos de la empresa."
- NO inventes, NO supongas, NO extrapoles más allá del contexto.
- Cuando respondas, sintetiza la información de múltiples fuentes si aplica.
- Sé conciso y profesional. Responde en español."""


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
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.embedding_service = EmbeddingService()
        self.pinecone_service = PineconeService()

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
        query_embedding = self.embedding_service.generar_embedding(query)

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

        raw_docs: List[Any] = self.pinecone_service.buscar_vectores(
            query_embedding, top_k=5, namespace=namespace
        )

        relevant_docs = [d for d in raw_docs if getattr(d, "score", 0) >= RELEVANCE_THRESHOLD]

        context = self._build_context(relevant_docs)
        messages = self._build_messages(query, context, conversation_history, system_prompt_override)

        effective_model = model_override or settings.OPENAI_CHAT_MODEL
        effective_temperature = temperature_override if temperature_override is not None else 0.7

        response = self.client.chat.completions.create(
            model=effective_model,
            messages=messages,
            temperature=effective_temperature,
            max_tokens=MAX_RESPONSE_TOKENS,
        )

        return {
            "content": response.choices[0].message.content,
            "sources": [
                {
                    "document_id": d.metadata.get("document_id"),
                    "document_name": d.metadata.get("document_name", "Documento desconocido"),
                    "text": (d.metadata.get("text") or "")[:300],
                    "score": round(getattr(d, "score", 0), 3),
                }
                for d in relevant_docs
            ],
            "token_count": response.usage.total_tokens,
            "input_tokens": response.usage.prompt_tokens,
            "output_tokens": response.usage.completion_tokens,
            "model": effective_model,
        }

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

            1. system  → reglas de comportamiento (prompt del asistente o el
                         DEFAULT_SYSTEM_PROMPT, que prohíbe usar conocimiento
                         externo al contexto).
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
        messages = [{"role": "system", "content": system_prompt_override or DEFAULT_SYSTEM_PROMPT}]

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
