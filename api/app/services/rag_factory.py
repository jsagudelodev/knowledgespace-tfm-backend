"""Elige qué configuración del pipeline RAG atiende cada consulta.

Las cuatro clases existen a la vez y se mantienen vivas a propósito: la línea
base es el término de comparación de todos los experimentos del capítulo 5, y
sin ella no habría con qué comparar las mejoras. Lo que este módulo decide es
cuál de las cuatro atiende al usuario.

    RAGService            Naive RAG con filtro por umbral. La línea base.
    RAGServiceAvanzado    + descomposición de consultas  (pre-recuperación)
    RAGServiceReranking   + reordenado de fragmentos     (post-recuperación)
    RAGServiceCompleto    + descomposición con tope de contexto y reparto
                            equilibrado entre subpreguntas

**Por qué el valor por defecto es `descomposicion_acotada`.** Es la variante de
descomposición que demostró efecto sobre el problema que venía a resolver —la
cobertura conjunta de las preguntas compuestas pasó del 48 % al 88 % sobre las
seis parejas medidas, con mejora en las seis— y además acota el contexto que
crece con el número de subpreguntas, repartiéndolo de forma equilibrada en
lugar de dejarlo crecer sin tope. Su coste es proporcional al uso —solo se
encarece la consulta que efectivamente se descompone— y añade alrededor de
1,2 s a la latencia mediana, muy por debajo del límite de quince segundos que
fija el requisito RNF-1.

**Por qué el reordenado no está activo.** Mejora la recuperación de forma
consistente —hit@3 de 0,500 a 0,667 y MRR de 0,394 a 0,447— pero las cuatro
métricas de generación se mueven dentro del margen de ruido del modelo
evaluador, de modo que no se ha demostrado que las respuestas sean mejores. Y
cuesta: la llamada del reordenador consume unos 4.600 tokens de entrada, lo que
multiplica por 3,7 el coste de cada consulta. Queda disponible, medido y
documentado, pero activarlo hoy sería pagar sin cobrar. Ver el apartado 5.3.

Cambiar de configuración no exige tocar código: basta la variable de entorno
`RAG_CONFIGURACION`.
"""
import logging
from typing import Dict, Tuple, Type

from app.core.config import settings
from app.services.rag_service import RAGService
from app.services.rag_service_avanzado import RAGServiceAvanzado
from app.services.rag_service_completo import RAGServiceCompleto
from app.services.rag_service_reranking import RAGServiceReranking

logger = logging.getLogger("uvicorn.error")

# nombre -> (clase, etiqueta con la que se registra en los experimentos)
#
# La etiqueta viaja al JSON de resultados y de ahí al nombre del fichero de
# RAGAS. Una cifra de recuperación no significa nada sin saber con qué
# configuración se obtuvo, de modo que ambas cosas se definen en un solo sitio
# y no pueden divergir.
CONFIGURACIONES: Dict[str, Tuple[Type[RAGService], str]] = {
    "base": (RAGService, "naive_rag_umbral_0.30"),
    "descomposicion": (RAGServiceAvanzado, "avanzado_descomposicion"),
    "reranking": (RAGServiceReranking, "avanzado_reranking"),
    "descomposicion_acotada": (RAGServiceCompleto, "avanzado_descomposicion_acotada"),
}

POR_DEFECTO = "base"


def clase_de(nombre: str) -> Tuple[Type[RAGService], str]:
    """Devuelve la clase y la etiqueta de una configuración.

    Ante un nombre desconocido recurre a la línea base en lugar de fallar: una
    variable de entorno mal escrita no debe dejar el chat sin servicio, y la
    base es la opción segura porque es la que está medida de extremo a extremo.
    """
    if nombre not in CONFIGURACIONES:
        logger.warning(
            "[RAG] Configuración desconocida %r; se usa %r. Valores válidos: %s",
            nombre, POR_DEFECTO, ", ".join(sorted(CONFIGURACIONES)),
        )
        nombre = POR_DEFECTO
    return CONFIGURACIONES[nombre]


def crear_rag_service() -> RAGService:
    """Instancia la configuración que indica el entorno.

    Se instancia por consulta, no una vez al arrancar: el servicio acumula en
    `llamadas_auxiliares` el consumo de la petición en curso, y compartir la
    instancia mezclaría el coste de unas consultas con el de otras.
    """
    clase, etiqueta = clase_de(settings.RAG_CONFIGURACION)
    logger.info("[RAG] Configuración activa: %s (%s)", settings.RAG_CONFIGURACION, etiqueta)
    return clase()
