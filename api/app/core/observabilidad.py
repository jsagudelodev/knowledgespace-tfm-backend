"""Trazas del pipeline RAG con Langfuse, activables por configuración.

Langfuse registra cada consulta como una traza: qué se preguntó, qué fragmentos
se recuperaron con qué puntuación, qué contexto se construyó y qué respondió el
modelo. Es lo que permite auditar una respuesta después de que ocurra, que es
precisamente lo que el proyecto no podía hacer: durante cuatro meses hubo
documentos indexados en un namespace equivocado y el sistema respondía con
normalidad, sin dejar rastro de que no los estaba viendo.

**Por qué este módulo existe en lugar de usar Langfuse directamente.**

La dependencia es opcional y el sistema debe funcionar sin ella: quien clone el
repositorio no tiene por qué darse de alta en un servicio de terceros para
levantar la aplicación. Aquí se concentra toda la condicionalidad, de modo que
`rag_service` no se llena de `if settings.LANGFUSE_ENABLED` y el pipeline se lee
igual esté o no activado.

Es una abstracción con dos implementaciones reales —instrumentada y nula—, no
una envoltura especulativa.

**Qué pasa si Langfuse falla.** Nada. El SDK envía en segundo plano y por lotes,
y aquí además se capturan los errores: perder una traza nunca puede romper la
respuesta al usuario. Es el mismo criterio que en el registro de costes.
"""
import logging
from contextlib import contextmanager
from typing import Any, Callable, Dict, Iterator, List, Optional

from app.core.config import settings

logger = logging.getLogger("uvicorn.error")

# El estado se resuelve una vez, al importar, y no en cada consulta.
_activo = False
_cliente = None

if settings.LANGFUSE_ENABLED:
    if not (settings.LANGFUSE_PUBLIC_KEY and settings.LANGFUSE_SECRET_KEY):
        logger.warning(
            "[Observabilidad] LANGFUSE_ENABLED=True pero faltan las claves. "
            "Las trazas quedan desactivadas; el registro por logger sigue activo."
        )
    else:
        try:
            from langfuse import Langfuse, observe  # noqa: F401

            _cliente = Langfuse(
                public_key=settings.LANGFUSE_PUBLIC_KEY,
                secret_key=settings.LANGFUSE_SECRET_KEY,
                host=settings.LANGFUSE_HOST,
            )
            _activo = True
            logger.info("[Observabilidad] Langfuse activo en %s", settings.LANGFUSE_HOST)
        except Exception as e:  # noqa: BLE001
            logger.warning("[Observabilidad] No se pudo inicializar Langfuse: %s", e)


def activo() -> bool:
    """¿Hay trazas? Útil para no construir metadatos que nadie va a leer."""
    return _activo


def cliente() -> Any:
    """Devuelve el cliente de Langfuse para operaciones que `paso` y
    `anotar_traza` no cubren —datasets, *scores*, consultas al propio
    proyecto—.

    El resto del módulo evita exponer `_cliente` directamente para que todo el
    estado de la instrumentación viva en un único sitio; esta función es la
    puerta deliberada para lo que sí necesita el objeto completo. Falla con un
    mensaje claro en vez de devolver `None`, porque un experimento que
    necesita Langfuse y lo usa sin comprobar antes `activo()` debe enterarse
    de inmediato, no fallar más adelante con un `AttributeError` opaco.
    """
    if not _activo:
        raise RuntimeError(
            "Langfuse no está activo. Comprueba LANGFUSE_ENABLED y las claves "
            "antes de llamar a observabilidad.cliente()."
        )
    return _cliente


def cliente_openai():
    """Devuelve la clase `OpenAI` que debe usar el pipeline.

    Con Langfuse activo se devuelve su envoltorio, que traza cada generación
    con su modelo, sus tokens y su coste sin tocar el código que la llama. Sin
    él, la clase original. La firma es idéntica en ambos casos.
    """
    if _activo:
        try:
            from langfuse.openai import OpenAI as OpenAITrazado

            return OpenAITrazado
        except Exception as e:  # noqa: BLE001
            logger.warning("[Observabilidad] Sin envoltorio de OpenAI: %s", e)

    from openai import OpenAI

    return OpenAI


def observar(nombre: str) -> Callable:
    """Decorador que convierte la función en una traza con ese nombre.

    Sin Langfuse devuelve la función intacta, sin coste ni envoltorio.
    """
    if not _activo:
        return lambda f: f

    from langfuse import observe

    return observe(name=nombre)


@contextmanager
def paso(nombre: str, entrada: Optional[Any] = None) -> Iterator[Dict[str, Any]]:
    """Registra una etapa dentro de la traza en curso.

    Se usa como gestor de contexto y entrega un diccionario donde ir dejando lo
    que haya que registrar; al salir, se vuelca como salida del paso. Si no hay
    trazas, el diccionario se descarta y el bloque se ejecuta igual.

        with paso("recuperacion", entrada=consulta) as datos:
            datos["puntuaciones"] = [...]
    """
    datos: Dict[str, Any] = {}
    if not _activo:
        yield datos
        return

    try:
        # En Langfuse 4 el metodo es `start_as_current_observation` con
        # `as_type`; la v3 lo llamaba `start_as_current_span`.
        with _cliente.start_as_current_observation(
            name=nombre, as_type="span", input=entrada
        ) as span:
            try:
                yield datos
            finally:
                try:
                    span.update(output=datos)
                except Exception:  # noqa: BLE001
                    pass
    except Exception as e:  # noqa: BLE001
        logger.warning("[Observabilidad] Falló el paso '%s': %s", nombre, e)
        yield datos


def anotar_traza(
    sesion: Optional[str] = None,
    etiquetas: Optional[List[str]] = None,
    metadatos: Optional[Dict[str, Any]] = None,
) -> None:
    """Añade identificadores a la traza en curso.

    Permite filtrar en Langfuse por empresa, asistente o conversación, que es
    lo que hace útiles las trazas cuando hay miles: sin esto, todas se parecen.

    Langfuse 4 retiró `update_current_trace`. Los metadatos van por la API
    documentada, `update_current_span`, y los atributos de traza —sesión y
    etiquetas— se escriben sobre el span de OpenTelemetry, que es el soporte
    real sobre el que la v4 está construida. Esa segunda parte lleva su propio
    `try`: si cambia la representación interna se pierden las etiquetas, pero
    no los metadatos, que es lo que importa.
    """
    if not _activo:
        return

    if metadatos:
        try:
            _cliente.update_current_span(metadata=metadatos)
        except Exception as e:  # noqa: BLE001
            logger.warning("[Observabilidad] No se pudieron anotar los metadatos: %s", e)

    if sesion or etiquetas:
        try:
            from langfuse import LangfuseOtelSpanAttributes as Attr
            from opentelemetry import trace as otel

            span = otel.get_current_span()
            if sesion:
                span.set_attribute(Attr.TRACE_SESSION_ID, sesion)
            if etiquetas:
                span.set_attribute(Attr.TRACE_TAGS, list(etiquetas))
        except Exception as e:  # noqa: BLE001
            logger.warning("[Observabilidad] No se pudieron anotar sesión/etiquetas: %s", e)


def volcar() -> None:
    """Fuerza el envío de lo pendiente. Necesario en scripts de un solo uso:
    el SDK envía por lotes y un proceso que termina rápido se va sin enviar."""
    if _activo:
        try:
            _cliente.flush()
        except Exception as e:  # noqa: BLE001
            logger.warning("[Observabilidad] Falló el volcado: %s", e)
