"""Excepciones propias de los servicios de infraestructura.

Sustituyen los `raise Exception(...)` genéricos que antes usaban
`embedding_service`, `pinecone_service`, `s3_service` y `pdf_service`. El
problema que resolvían esos `Exception` a secas era de legibilidad del fallo,
no de captura: como todo el código que los invoca atrapa con `except
Exception`, tipar estas clases no cambia qué se captura hoy, pero permite que
el que lo necesite (como `RAGUnavailableError` en `rag_service.py`) capture
solo el fallo esperado de ese servicio concreto, sin enmascarar un error
propio —un `TypeError`, por ejemplo— como si fuera una caída transitoria del
proveedor externo.
"""


class EmbeddingError(Exception):
    """Fallo al generar un embedding con la API de OpenAI."""


class VectorStoreError(Exception):
    """Fallo al operar sobre el índice vectorial (Pinecone): insertar,
    buscar, eliminar o listar vectores."""


class StorageError(Exception):
    """Fallo al operar sobre el almacenamiento de archivos (S3): subir,
    descargar, eliminar o firmar una URL temporal."""


class DocumentExtractionError(Exception):
    """Fallo al extraer texto de un documento subido (PDF, DOCX o TXT)."""
