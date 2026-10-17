"""Tests de la seleccion de configuracion del pipeline.

Las tres clases conviven y una variable de entorno decide cual atiende al
usuario. Lo que se fija aqui:

    1. cada nombre devuelve su clase, y la etiqueta que viaja a los resultados
       de los experimentos sale del mismo sitio, de modo que lo que se mide y
       lo que atiende al usuario no pueden describirse de dos maneras,
    2. un nombre desconocido NO deja el chat sin servicio: recurre a la linea
       base, que es la configuracion medida de extremo a extremo,
    3. el valor por defecto es la descomposicion, que es la decision
       justificada en `rag_factory` y en el apartado 5.3.
"""
from app.core.config import settings
from app.services.rag_factory import (
    CONFIGURACIONES,
    POR_DEFECTO,
    clase_de,
    crear_rag_service,
)
from app.services.rag_service import RAGService
from app.services.rag_service_avanzado import RAGServiceAvanzado
from app.services.rag_service_completo import RAGServiceCompleto
from app.services.rag_service_reranking import RAGServiceReranking


def test_cada_nombre_devuelve_su_clase():
    assert clase_de("base")[0] is RAGService
    assert clase_de("descomposicion")[0] is RAGServiceAvanzado
    assert clase_de("reranking")[0] is RAGServiceReranking


def test_las_tres_heredan_de_la_linea_base():
    """Es lo que permite que compartan el umbral, el prompt, la abstencion y
    el registro de coste, y que solo cambie como se recuperan los fragmentos."""
    for clase, _ in CONFIGURACIONES.values():
        assert issubclass(clase, RAGService)


def test_cada_configuracion_tiene_una_etiqueta_distinta():
    """La etiqueta nombra el fichero de resultados. Dos iguales harian que una
    medicion sobrescribiera a otra, que ya paso una vez con RAGAS."""
    etiquetas = [e for _, e in CONFIGURACIONES.values()]
    assert len(set(etiquetas)) == len(etiquetas)


def test_un_nombre_desconocido_no_rompe_y_cae_en_la_base():
    """Una variable de entorno mal escrita no puede dejar el chat sin
    servicio. La base es la opcion segura porque es la unica medida de extremo
    a extremo en las siete ejecuciones del capitulo 5."""
    clase, _ = clase_de("rerankng")       # errata deliberada
    assert clase is RAGService
    assert POR_DEFECTO == "base"


def test_la_configuracion_por_defecto_es_la_completa():
    """Descomposicion CON tope de contexto.

    Fue "descomposicion" hasta el 16 de octubre de 2026: resolvia la cobertura
    pero ensanchaba sin recortar, enviando nueve fragmentos donde la base
    enviaba cinco. "completo" conserva el reparto entre subpreguntas con la
    mitad del contexto y el coste de la linea base.

    Este test existe para que cambiarla sea deliberado y no un descuido: es un
    cambio de comportamiento del sistema en produccion, no un ajuste.
    """
    assert settings.RAG_CONFIGURACION == "descomposicion_acotada"
    assert isinstance(crear_rag_service(), RAGServiceCompleto)
    # Sigue siendo una descomposicion: hereda de ella y la especializa.
    assert isinstance(crear_rag_service(), RAGServiceAvanzado)
