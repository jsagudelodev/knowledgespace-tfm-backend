"""Generación de embeddings con OpenAI — el puente entre texto y vectores.
Usado tanto al indexar documentos como al consultar. Ver `docs/RAG_PIPELINE.md`."""
from typing import List, Tuple

from openai import OpenAI

from app.core.config import settings


class EmbeddingService:
    """
    Genera embeddings de texto usando la API de OpenAI.

    Un embedding es un vector numérico que representa el significado semántico
    de un texto. Textos con significado similar tendrán vectores cercanos —
    eso es lo que permite buscar por similitud en Pinecone.
    """

    def __init__(self):
        self.cliente = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.modelo = settings.OPENAI_EMBEDDING_MODEL   # text-embedding-3-small → 1536 dimensiones

    def generar_embedding(self, texto: str) -> List[float]:
        """Genera el embedding de un solo texto. Ver `generar_embedding_con_uso`
        si además se necesita el conteo de tokens (p. ej. para cost tracking)."""
        embedding, _ = self.generar_embedding_con_uso(texto)
        return embedding

    def generar_embedding_con_uso(self, texto: str) -> Tuple[List[float], int]:
        """
        Genera el embedding de un solo texto, junto con los tokens consumidos.

        Embeber la pregunta del usuario es una llamada de pago a OpenAI, igual
        que la del modelo generativo. Sin este conteo quedaba fuera del registro
        de costos, que es una de las contribuciones declaradas del trabajo.
        """
        try:
            respuesta = self.cliente.embeddings.create(
                model=self.modelo,
                input=texto,
            )
            return respuesta.data[0].embedding, respuesta.usage.total_tokens
        except Exception as e:
            raise Exception(f"Error generando embedding: {str(e)}")
        





    def generar_embeddings_batch(self, textos: List[str], batch_size: int = 100) -> List[List[float]]:
        """Genera embeddings para múltiples textos en batches. Ver `generar_embeddings_batch_con_uso`
        si además se necesita el conteo de tokens (p. ej. para cost tracking)."""
        embeddings, _ = self.generar_embeddings_batch_con_uso(textos, batch_size)
        return embeddings

    def generar_embeddings_batch_con_uso(
        self, textos: List[str], batch_size: int = 100
    ) -> Tuple[List[List[float]], int]:
        """
        Genera embeddings para múltiples textos en batches, junto con el total
        de tokens consumidos (para registrar el costo de la llamada).

        En vez de hacer una llamada a OpenAI por cada chunk (costoso y lento),
        enviamos hasta 100 textos por llamada. Para un documento de 50 chunks
        eso es 1 llamada en vez de 50.

        OpenAI acepta hasta 2048 inputs por llamada — 100 es un valor seguro.
        """
        if not textos:
            return [], 0

        todos_los_embeddings: List[List[float]] = []
        total_tokens = 0

        for i in range(0, len(textos), batch_size):
            batch = textos[i: i + batch_size]
            try:
                respuesta = self.cliente.embeddings.create(
                    model=self.modelo,
                    input=batch,
                )
                # La API no garantiza el orden — ordenamos por índice
                embeddings_batch = [
                    item.embedding
                    for item in sorted(respuesta.data, key=lambda x: x.index)
                ]
                todos_los_embeddings.extend(embeddings_batch)
                total_tokens += respuesta.usage.total_tokens
            except Exception as e:
                raise Exception(f"Error generando embeddings en batch: {str(e)}")

        return todos_los_embeddings, total_tokens
