"""Un documento fallido muestra qué pasó y qué hacer, no el error técnico.

Hasta el 2026-11-04 el listado de Documentos enseñaba el `error_message`
crudo, p. ej. "Error descargando archivo de S3: An error occurred (NoSuchKey)".
El original se conserva en la base de datos y en el log.
"""
from datetime import datetime
from types import SimpleNamespace

import pytest

from app.schemas import mensajes_documento as m
from app.schemas.document import DocumentResponse

S3_CRUDO = (
    "Error descargando archivo de S3: An error occurred (NoSuchKey) when calling "
    "the GetObject operation: The specified key does not exist."
)


@pytest.mark.parametrize("original, legible", [
    ("No se pudo extraer texto del PDF con ningún parser disponible", m.TEXTO_ILEGIBLE),
    ("No se pudo extraer texto del documento", m.TEXTO_ILEGIBLE),
    ("Tipo de archivo 'xlsx' no soportado", m.TIPO_NO_ADMITIDO),
    (S3_CRUDO, m.ARCHIVO_NO_DISPONIBLE),
    ("Error generando embeddings en batch: Rate limit reached", m.IA_NO_DISPONIBLE),
    ("Error insertando vectores en Pinecone: Namespace not found", m.INDICE_NO_DISPONIBLE),
    ("KeyError: 'page_content'", m.GENERICO),
])
def test_cada_fallo_tiene_su_mensaje(original, legible):
    assert m.mensaje_legible(original) == legible


def test_sin_error_no_inventa_mensaje():
    assert m.mensaje_legible(None) is None
    assert m.mensaje_legible("") == ""


def test_la_respuesta_de_la_api_no_lleva_el_error_tecnico():
    documento = SimpleNamespace(
        id=1, chunk_count=0, status="failed", error_message=S3_CRUDO, created_at=datetime(2026, 11, 4),
    )
    respuesta = DocumentResponse.model_validate(documento)

    assert respuesta.error_message == m.ARCHIVO_NO_DISPONIBLE
    assert "NoSuchKey" not in respuesta.model_dump_json()
    # El original no se toca: sigue en el objeto de base de datos.
    assert documento.error_message == S3_CRUDO
