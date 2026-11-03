"""Elige qué configuración del pipeline RAG atiende cada consulta.

Las seis clases existen a la vez y se mantienen vivas a propósito: la línea
base es el término de comparación de todos los experimentos del capítulo 5, y
sin ella no habría con qué comparar las mejoras. Lo que este módulo decide es
cuál de las seis atiende al usuario.

    RAGService            Naive RAG con filtro por umbral. La línea base.
    RAGServiceAvanzado    + descomposición de consultas  (pre-recuperación)
    RAGServiceReranking   + reordenado de fragmentos     (post-recuperación)
    RAGServiceCompleto    + descomposición con tope de contexto y reparto
                            equilibrado entre subpreguntas
    RAGServiceHibrido     + búsqueda léxica BM25 fusionada con la densa
                            (Reciprocal Rank Fusion, post-recuperación)
    RAGServiceDescomposicionHibrida   descomposición con reparto Y BM25 por
                            subpregunta — resuelven problemas distintos y se
                            combinan sin pisarse

**Por qué el valor por defecto es `descomposicion_acotada`.** La descomposición
sin tope (`RAGServiceAvanzado`) sube la cobertura conjunta del 48 % al 88 %,
pero enviando hasta el doble de fragmentos al modelo. Con el presupuesto fijo
en `TOP_K` el techo de cobertura es matemáticamente ~50 %, así que
`RAGServiceCompleto` no persigue ese 88 %: persigue el reparto. Y ahí sí hay
mejora medida —desequilibrio de 1,83 en la base a 0,83 con reparto en turnos,
sobre las seis parejas—, es decir, ninguna subpregunta se queda sin
representación, al mismo coste de contexto que la línea base. Ver
`rag_service_completo.py` para la cifra completa y por qué se descartó
recortar por reordenado antes de llegar a esta solución.

Su coste es proporcional al uso —solo se encarece la consulta que
efectivamente se descompone— y añade alrededor de 1,2 s a la latencia mediana,
muy por debajo del límite de quince segundos que fija el requisito RNF-1.

**Por qué el reordenado no está activo.** Mejora la recuperación de forma
consistente —hit@3 de 0,500 a 0,667 y MRR de 0,394 a 0,447— pero las cuatro
métricas de generación se mueven dentro del margen de ruido del modelo
evaluador, de modo que no se ha demostrado que las respuestas sean mejores. Y
cuesta: la llamada del reordenador consume unos 4.600 tokens de entrada, lo que
multiplica por 3,7 el coste de cada consulta. Queda disponible, medido y
documentado, pero activarlo hoy sería pagar sin cobrar. Ver el apartado 5.3.

**Por qué el híbrido tampoco está activo.** Medido el 2026-10-19 contra el
conjunto de referencia: es el que mejor encuentra el fragmento correcto —hit@1
de 0,25 a 0,42— y sube la fidelidad de 0,939 a 0,965, pero busca con la
pregunta completa y baja la cobertura de las preguntas de dos temas del 48 % al
30 %, peor que la línea base. Combinado con el reparto equilibrado
(`descomposicion_hibrida`) recupera parte de esa cobertura, hasta el 37 %, sin
llegar a la base, y es la configuración más lenta de las seis. Ninguna de las
dos se activa porque retroceden justo en las preguntas compuestas. Ver el
apartado 5.3.

**`POR_DEFECTO` no es la configuración activa.** La activa la fija
`settings.RAG_CONFIGURACION`, cuyo valor por defecto es
`descomposicion_acotada`. `POR_DEFECTO` es solo la red de seguridad ante un
nombre mal escrito.

Cambiar de configuración no exige tocar código: basta la variable de entorno
`RAG_CONFIGURACION`.
"""
import logging
from typing import Dict, Tuple, Type

from app.core.config import settings
from app.services.rag_service import RAGService
from app.services.rag_service_avanzado import RAGServiceAvanzado
from app.services.rag_service_completo import RAGServiceCompleto
from app.services.rag_service_descomposicion_hibrida import RAGServiceDescomposicionHibrida
from app.services.rag_service_hibrido import RAGServiceHibrido
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
    "hibrido": (RAGServiceHibrido, "avanzado_hibrido_bm25"),
    "descomposicion_hibrida": (RAGServiceDescomposicionHibrida, "avanzado_descomposicion_hibrida"),
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
