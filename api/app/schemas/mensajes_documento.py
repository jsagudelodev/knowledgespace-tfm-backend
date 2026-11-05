"""Mensaje legible para un documento cuyo procesamiento falló.

`documents.error_message` guarda el error original de la ingesta (p. ej.
"Error descargando archivo de S3: An error occurred (NoSuchKey)..."), que sirve
para diagnosticar y además queda en el log con la traza. Hasta el 2026-11-04
la API lo devolvía tal cual y el listado de Documentos lo mostraba a quien
subió el archivo.

Ahora la respuesta lo traduce a un mensaje que dice qué pasó y qué hacer. Se
traduce al responder, no al guardar, para que valga también con los documentos
que ya fallaron antes de este cambio y para no perder el original.

Los mensajes de origen los generan nuestros propios servicios con prefijos
estables (`pdf_service`, `s3_service`, `embedding_service`,
`pinecone_service`); lo que no encaja en ninguno recibe el mensaje genérico.
"""
from typing import Optional

TEXTO_ILEGIBLE = (
    "No se pudo leer el texto del archivo. Si es un PDF escaneado, no tiene texto "
    "seleccionable: prueba con una versión que sí lo tenga."
)
TIPO_NO_ADMITIDO = "Este tipo de archivo no se admite. Formatos válidos: PDF, DOCX, TXT y MD."
ARCHIVO_NO_DISPONIBLE = "No se encontró el archivo almacenado. Vuelve a subir el documento."
IA_NO_DISPONIBLE = "El servicio de IA no respondió al procesar el documento. Reinténtalo en unos minutos."
INDICE_NO_DISPONIBLE = "No se pudo guardar el documento en el índice de búsqueda. Reinténtalo en unos minutos."
GENERICO = (
    "No se pudo procesar el documento. Reinténtalo; si vuelve a fallar, comprueba "
    "que el archivo se abre bien."
)

# (fragmento del mensaje original, mensaje legible), en orden de comprobación.
_REGLAS = (
    ("No se pudo extraer texto", TEXTO_ILEGIBLE),
    ("no soportado", TIPO_NO_ADMITIDO),
    ("S3", ARCHIVO_NO_DISPONIBLE),
    ("embedding", IA_NO_DISPONIBLE),
    ("Pinecone", INDICE_NO_DISPONIBLE),
)


def mensaje_legible(original: Optional[str]) -> Optional[str]:
    if not original:
        return original
    for fragmento, legible in _REGLAS:
        if fragmento.lower() in original.lower():
            return legible
    return GENERICO
