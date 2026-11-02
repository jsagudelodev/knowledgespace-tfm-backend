"""Los dos textos que terminan indexados en Pinecone (la respuesta escrita a
mano y la pregunta enviada desde Feedback) no pueden llegar vacíos ni solo con
espacios. Antes solo lo impedía el frontend; una llamada directa a la API
habría indexado un vector sin contenido."""
import pytest
from pydantic import ValidationError

from app.schemas.feedback import FeedbackConvertGap
from app.schemas.knowledge_gap import KnowledgeGapAnswerRequest


@pytest.mark.parametrize("valor", ["", "   ", "\n\t "])
def test_respuesta_vacia_o_solo_espacios_se_rechaza(valor):
    with pytest.raises(ValidationError):
        KnowledgeGapAnswerRequest(answer_text=valor)


@pytest.mark.parametrize("valor", ["", "   ", "\n\t "])
def test_pregunta_vacia_o_solo_espacios_se_rechaza(valor):
    with pytest.raises(ValidationError):
        FeedbackConvertGap(question=valor)


def test_el_texto_valido_llega_recortado():
    assert KnowledgeGapAnswerRequest(answer_text="  Sí, los viernes.  ").answer_text == "Sí, los viernes."
    assert FeedbackConvertGap(question="  que es RAG \n").question == "que es RAG"
