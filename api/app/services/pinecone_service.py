"""Vector store (Pinecone): almacenamiento y búsqueda semántica de embeddings.
El aislamiento multi-tenant vive aquí, en los namespaces — ver `construir_namespace`
y `docs/PINECONE_VECTORES.md`."""
from typing import Any, Dict, List, Optional

from pinecone import Pinecone, ServerlessSpec

from app.core.config import settings


class PineconeService:
    """
    Gestiona el almacenamiento y búsqueda de vectores en Pinecone.

    Pinecone es una base de datos vectorial — en vez de buscar por texto exacto,
    busca por similitud semántica usando los embeddings generados por OpenAI.

    Namespaces (aislamiento multi-tenant):
    - Cada empresa tiene su propio namespace: "company-5"
    - Cada asistente tiene el suyo:           "company-5-assistant-3"
    - Esto garantiza que empresa A nunca vea datos de empresa B.
    """

    DIMENSION = 1536   # dimensiones de text-embedding-3-small

    def __init__(self):
        self.pc = Pinecone(api_key=settings.PINECONE_API_KEY)
        self.nombre_indice = settings.PINECONE_INDEX_NAME

    def asegurar_indice(self) -> None:
        """
        Crea el índice si no existe.
        Llamar una vez al arrancar la app, no en cada request.
        """
        indices = [idx.name for idx in self.pc.list_indexes().indexes]
        if self.nombre_indice not in indices:
            self.pc.create_index(
                name=self.nombre_indice,
                dimension=self.DIMENSION,
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region="us-east-1"),
            )

    def upsert_vectores(self, vectores: List[Dict[str, Any]], namespace: Optional[str] = None) -> None:
        """
        Inserta o actualiza vectores en el índice.

        Cada vector es un dict con:
        - id: identificador único del chunk
        - values: lista de 1536 floats (el embedding)
        - metadata: datos adicionales para filtrar o mostrar en resultados
        """
        indice = self.pc.Index(self.nombre_indice)
        kwargs: Dict[str, Any] = {"vectors": vectores}
        if namespace:
            kwargs["namespace"] = namespace
        try:
            indice.upsert(**kwargs)
        except Exception as e:
            raise Exception(f"Error insertando vectores en Pinecone: {str(e)}")

    def buscar_vectores(
        self,
        vector_consulta: List[float],
        top_k: int = 5,
        filtro: Optional[Dict] = None,
        namespace: Optional[str] = None,
    ) -> List[Dict]:
        """
        Busca los vectores más similares a la consulta.

        - top_k: cuántos resultados retornar
        - filtro: condiciones adicionales sobre metadata (ej: document_id)
        - namespace: limita la búsqueda al namespace de la empresa/asistente
        """
        indice = self.pc.Index(self.nombre_indice)
        kwargs: Dict[str, Any] = {
            "vector": vector_consulta,
            "top_k": top_k,
            "include_metadata": True,
        }
        if filtro:
            kwargs["filter"] = filtro
        if namespace:
            kwargs["namespace"] = namespace
        try:
            resultados = indice.query(**kwargs)
            return resultados.matches
        except Exception as e:
            raise Exception(f"Error buscando vectores en Pinecone: {str(e)}")

    def eliminar_vectores(self, ids: List[str], namespace: Optional[str] = None) -> None:
        """Elimina vectores por sus IDs."""
        indice = self.pc.Index(self.nombre_indice)
        kwargs: Dict[str, Any] = {"ids": ids}
        if namespace:
            kwargs["namespace"] = namespace
        try:
            indice.delete(**kwargs)
        except Exception as e:
            raise Exception(f"Error eliminando vectores de Pinecone: {str(e)}")

    def eliminar_por_documento(self, document_id: int, namespace: Optional[str] = None) -> None:
        """
        Elimina todos los chunks de un documento usando filtro de metadata.
        Se llama cuando el usuario borra un documento — limpia Pinecone también.
        """
        indice = self.pc.Index(self.nombre_indice)
        kwargs: Dict[str, Any] = {"filter": {"document_id": document_id}}
        if namespace:
            kwargs["namespace"] = namespace
        try:
            indice.delete(**kwargs)
        except Exception as e:
            raise Exception(f"Error eliminando documento de Pinecone: {str(e)}")

    @staticmethod
    def construir_namespace(company_id: int, assistant_id: Optional[int] = None) -> str:
        """
        Construye el namespace de Pinecone para aislar datos multi-tenant.

        Sin asistente: "company-5"
        Con asistente: "company-5-assistant-3"
        """
        if assistant_id:
            return f"company-{company_id}-assistant-{assistant_id}"
        return f"company-{company_id}"
