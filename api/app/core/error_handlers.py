"""Respuesta uniforme para los errores que ningún endpoint captura.

Hasta el 2026-11-04 la aplicación no registraba ningún manejador: un fallo no
previsto —la base de datos caída, S3 sin responder al descargar— llegaba al
cliente como un 500 en texto plano ("Internal Server Error"), y un
`StorageError` o un `VectorStoreError` fuera del chat acababan igual, aunque
fueran una caída transitoria de un proveedor y no un fallo del código.

Ahora:

- **Fallo de un servicio externo** (`EmbeddingError`, `VectorStoreError`,
  `StorageError`): **503**, porque no es culpa de la petición y reintentar
  puede funcionar.
- **Cualquier otra excepción no capturada**: **500**.

En los dos casos la respuesta es JSON con la misma forma que `HTTPException`
(`{"detail": ...}`), que es la que ya lee el frontend, y **nunca incluye el
detalle técnico**: el mensaje de la excepción puede llevar rutas, claves de S3
o fragmentos de SQL. Ese detalle va al log, con la traza completa, el método y
la ruta, para poder reconstruir el fallo.

`HTTPException` y los errores de validación (422) no pasan por aquí: FastAPI
tiene sus propios manejadores y ya responden bien.
"""
import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.exceptions import EmbeddingError, StorageError, VectorStoreError

logger = logging.getLogger("uvicorn.error")

SERVICIOS_EXTERNOS = (EmbeddingError, VectorStoreError, StorageError)

MENSAJE_503 = "Un servicio externo no está disponible en este momento. Intenta de nuevo en unos segundos."
MENSAJE_500 = "Error interno del servidor."


async def servicio_externo_no_disponible(request: Request, exc: Exception) -> JSONResponse:
    logger.error(
        "[Error] %s en %s %s: %s",
        type(exc).__name__, request.method, request.url.path, exc,
        exc_info=exc,
    )
    return JSONResponse(status_code=503, content={"detail": MENSAJE_503})


async def error_no_controlado(request: Request, exc: Exception) -> JSONResponse:
    logger.error(
        "[Error] No controlado %s en %s %s",
        type(exc).__name__, request.method, request.url.path,
        exc_info=exc,
    )
    return JSONResponse(status_code=500, content={"detail": MENSAJE_500})


def registrar_manejadores(app: FastAPI) -> None:
    for tipo in SERVICIOS_EXTERNOS:
        app.add_exception_handler(tipo, servicio_externo_no_disponible)
    app.add_exception_handler(Exception, error_no_controlado)
