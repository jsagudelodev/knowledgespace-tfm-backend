"""Test de regresion: el cliente de embeddings debe pedirse a `observabilidad`.

`EmbeddingService` creaba su propio cliente con `from openai import OpenAI`
directo. Funcionaba trazado en Langfuse por un efecto secundario: Langfuse 4
no envuelve una instancia, parchea la clase `openai.OpenAI` para todo el
proceso en el momento en que se importa `langfuse.openai`. Como el chat
siempre instancia `RAGService` primero --que llama a
`observabilidad.cliente_openai()` y dispara ese parche-- el cliente de
`EmbeddingService`, creado justo despues en el mismo `__init__`, quedaba
trazado de rebote.

La ingesta de documentos no tiene esa garantia: `documents.py` instancia
`EmbeddingService` directamente, sin que ningun `RAGService` se haya creado
antes en ese proceso. Verificado en un proceso limpio que reproducia
exactamente ese flujo: la llamada quedaba sin trazar.

Lo que se fija aqui es que `EmbeddingService` pide el cliente a
`observabilidad.cliente_openai()`, igual que `RAGService`, de modo que la
trazabilidad dependa del diseño y no del orden en que arranca cada worker.
"""
from unittest.mock import MagicMock

from app.core import observabilidad
from app.services.embedding_service import EmbeddingService


def test_pide_el_cliente_a_observabilidad(monkeypatch):
    """No debe construir `openai.OpenAI` por su cuenta: debe pasar por el
    mismo punto que `RAGService`, para que ambos quedan sujetos a la misma
    decision de si hay o no envoltorio de trazas."""
    clase_falsa = MagicMock(name="ClienteFalso")
    monkeypatch.setattr(observabilidad, "cliente_openai", lambda: clase_falsa)

    EmbeddingService()

    clase_falsa.assert_called_once()


def test_coincide_con_el_cliente_que_usa_rag_service(monkeypatch):
    """Si algun dia alguno de los dos deja de pasar por `observabilidad`,
    quedarian trazados de forma distinta sin que nada lo avisara."""
    llamadas = []
    clase_falsa = MagicMock(name="ClienteFalso")
    monkeypatch.setattr(observabilidad, "cliente_openai",
                        lambda: llamadas.append(1) or clase_falsa)

    EmbeddingService()
    assert len(llamadas) == 1, "EmbeddingService debe pedir el cliente a observabilidad"
