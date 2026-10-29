"""Vector store (Pinecone): almacenamiento y búsqueda semántica de embeddings.
El aislamiento multi-tenant vive aquí, en los namespaces — ver `construir_namespace`
y `docs/trabajo/PINECONE_VECTORES.md`."""
from typing import Any, Dict, List, Optional

from pinecone import Pinecone, ServerlessSpec
from pinecone.exceptions import NotFoundException

from app.core.config import settings
from app.core.exceptions import VectorStoreError


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

        Los metadatos con valor `None` se omiten: Pinecone solo admite texto,
        números, booleanos o listas de texto, y rechaza el upsert completo si
        encuentra un nulo. Le pasaba a las respuestas escritas a mano en
        "Preguntas sin respuesta", que no vienen de ningún documento y llevaban
        `document_id: None`: guardarlas fallaba siempre con un 502. Omitir la
        clave equivale a "no tiene", y quien lee los resultados ya usa
        `metadata.get(...)`.
        """
        indice = self.pc.Index(self.nombre_indice)
        vectores = [
            {**v, "metadata": {k: val for k, val in v["metadata"].items() if val is not None}}
            if v.get("metadata") else v
            for v in vectores
        ]
        kwargs: Dict[str, Any] = {"vectors": vectores}
        if namespace:
            kwargs["namespace"] = namespace
        try:
            indice.upsert(**kwargs)
        except Exception as e:
            raise VectorStoreError(f"Error insertando vectores en Pinecone: {str(e)}") from e

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
            raise VectorStoreError(f"Error buscando vectores en Pinecone: {str(e)}") from e

    def eliminar_vectores(self, ids: List[str], namespace: Optional[str] = None) -> None:
        """Elimina vectores por sus IDs."""
        indice = self.pc.Index(self.nombre_indice)
        kwargs: Dict[str, Any] = {"ids": ids}
        if namespace:
            kwargs["namespace"] = namespace
        try:
            indice.delete(**kwargs)
        except Exception as e:
            raise VectorStoreError(f"Error eliminando vectores de Pinecone: {str(e)}") from e

    def eliminar_por_documento(self, document_id: int, namespace: Optional[str] = None) -> None:
        """
        Elimina todos los chunks de un documento usando filtro de metadata.
        Se llama cuando el usuario borra un documento, y antes de cada
        reindexado para que sea idempotente (ver el comentario en
        `documents.py` junto a su llamada).

        Si el namespace todavía no existe —el primer documento que se indexa
        para un asistente nuevo, por ejemplo— Pinecone responde 404 en vez de
        no borrar nada. No hay nada que borrar, así que se trata como éxito:
        sin esto, subir el primer documento de cualquier asistente fallaba
        siempre con "Namespace not found", sin que el documento tuviera
        ningún problema real.
        """
        indice = self.pc.Index(self.nombre_indice)
        kwargs: Dict[str, Any] = {"filter": {"document_id": document_id}}
        if namespace:
            kwargs["namespace"] = namespace
        try:
            indice.delete(**kwargs)
        except NotFoundException:
            pass
        except Exception as e:
            raise VectorStoreError(f"Error eliminando documento de Pinecone: {str(e)}") from e

    def _listar_ids(self, namespace: Optional[str] = None, prefijo: Optional[str] = None) -> List[str]:
        """Identificadores de los vectores de un espacio, opcionalmente por prefijo.

        `list` pagina, y **la forma de cada página depende de la versión del
        cliente de Pinecone.** La 9.1 devuelve objetos `ListResponse` con un
        atributo `vectors`; versiones anteriores devuelven directamente listas
        de cadenas. Se contemplan ambas porque la diferencia no da error:
        recorrer la forma equivocada simplemente produce una lista vacía, y un
        documento o un espacio sin fragmentos parece mal indexado. La primera
        versión de este método reportó los ocho documentos del corpus como
        desincronizados cuando ninguno lo estaba.
        """
        indice = self.pc.Index(self.nombre_indice)
        kwargs: Dict[str, Any] = {}
        if prefijo:
            kwargs["prefix"] = prefijo
        if namespace:
            kwargs["namespace"] = namespace

        ids: List[str] = []
        for pagina in indice.list(**kwargs):
            vectores = getattr(pagina, "vectors", None)
            if vectores is not None:
                ids.extend(v.id for v in vectores)
            elif isinstance(pagina, str):
                ids.append(pagina)
            else:
                ids.extend(pagina)
        return ids

    def _fetch_fragmentos(self, ids: List[str], namespace: Optional[str] = None) -> List[Dict[str, Any]]:
        """Trae los metadatos de una lista de identificadores, en lotes de 100
        —el límite que admite `fetch` por llamada—."""
        if not ids:
            return []
        indice = self.pc.Index(self.nombre_indice)
        fragmentos: List[Dict[str, Any]] = []
        for i in range(0, len(ids), 100):
            lote = ids[i:i + 100]
            kw: Dict[str, Any] = {"ids": lote}
            if namespace:
                kw["namespace"] = namespace
            respuesta = indice.fetch(**kw)
            for vid, vector in (respuesta.vectors or {}).items():
                meta = vector.metadata or {}
                fragmentos.append({
                    "chunk_id": vid,
                    "document_id": meta.get("document_id"),
                    "document_name": meta.get("document_name", "?"),
                    "chunk_index": int(meta.get("chunk_index", -1)),
                    "text": meta.get("text", ""),
                    "caracteres": len(meta.get("text", "")),
                })
        return fragmentos

    def listar_por_documento(
        self, document_id: int, namespace: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Devuelve los fragmentos indexados de un documento, en orden.

        Permite inspeccionar en qué quedó dividido un documento tras la
        ingesta. Hasta ahora el sistema informaba de *cuántos* fragmentos
        generó —`chunk_count` en la base de datos— pero no de cuáles, de modo
        que un troceado defectuoso solo se detectaba por sus efectos en las
        respuestas.

        **Se recuperan por prefijo de identificador y no por filtro de
        metadatos.** Los identificadores son `doc-{id}-chunk-{i}`, así que el
        prefijo los determina de forma exacta; un filtro por metadatos exigiría
        una consulta con vector ficticio y un `top_k` arbitrario, que podría
        dejar fuera fragmentos sin avisar.

        Devuelve una lista vacía si el documento no tiene nada indexado, que es
        lo que ocurre mientras se procesa o si la ingesta falló.
        """
        try:
            ids = self._listar_ids(namespace=namespace, prefijo=f"doc-{document_id}-chunk-")
            fragmentos = self._fetch_fragmentos(ids, namespace=namespace)
        except Exception as e:
            raise VectorStoreError(f"Error listando los fragmentos del documento: {str(e)}") from e

        # El orden de `list` y `fetch` no está garantizado, y mostrar los
        # fragmentos desordenados impediría precisamente lo que se quiere ver:
        # por dónde se cortó el documento.
        fragmentos.sort(key=lambda f: f["chunk_index"])
        return fragmentos

    def listar_namespace(self, namespace: str) -> List[Dict[str, Any]]:
        """Devuelve todos los fragmentos indexados en un espacio de nombres.

        Es `listar_por_documento` sin el filtro por documento: trae el corpus
        completo que un asistente tiene indexado. Lo usa `RAGServiceHibrido`
        para construir su índice léxico, que necesita ver todos los fragmentos
        y no solo los que la búsqueda densa ya consideró candidatos —si se
        limitara a esos, un documento que la similitud coseno descartó de
        entrada nunca tendría ocasión de ganar por coincidencia literal, que es
        precisamente lo que la parte léxica de un híbrido viene a rescatar.

        Sin orden garantizado: a diferencia de `listar_por_documento`, aquí no
        hay un índice de fragmento único que sirva de criterio, porque mezcla
        varios documentos.
        """
        try:
            ids = self._listar_ids(namespace=namespace)
            return self._fetch_fragmentos(ids, namespace=namespace)
        except Exception as e:
            raise VectorStoreError(f"Error listando el espacio de nombres: {str(e)}") from e

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
