"""Preguntas de ALCANCE GLOBAL sobre el corpus — "¿qué documentos tienes?",
"¿qué temas puedo consultar?", "¿de qué trata la documentación?".

## El problema

La recuperación semántica (`top_k` fragmentos por similitud contra Pinecone)
no puede responder bien a estas preguntas, y no es un defecto puntual: es
estructural. Un buscador por similitud devuelve los K fragmentos MÁS
PARECIDOS a la pregunta, nunca "todo lo que hay" — y una pregunta de alcance
no busca el fragmento más parecido a sí misma, busca un resumen de la
totalidad del corpus, que el buscador nunca tuvo completo delante.

**Verificado el 2026-10-25** contra un corpus real de 8 documentos
(asistente 1, empresa 8):

    "¿Qué documentos tienes?"
        → "Tengo acceso al documento titulado 'Resumen Tema 4 Clase 5.pdf'."
        Falso: hay 8, no 1. No es una respuesta incompleta, es una
        afirmación concreta y equivocada sobre la composición del corpus.

    "¿Qué temas puedo consultar?"
        → listó 5 temas sacados de solo 3 de los 8 documentos recuperados,
        presentados como si fueran el catálogo completo, sin ningún aviso
        de que podía faltar algo (faltaban VAEs, GANs y difusión por completo).

Es el mismo fallo que documenta Microsoft Research para GraphRAG (2024):
estas son preguntas de RESUMEN del corpus, no de recuperación — pedirle a un
buscador por similitud que resuma algo que nunca vio completo es pedirle lo
que no puede dar por diseño, no un bug que se arregle afinando el umbral o
subiendo `top_k`.

## La solución: enrutar antes de recuperar, no después

Es un patrón con nombre en la literatura de RAG: **"query routing"** —
clasificar la pregunta ANTES de decidir qué camino sigue, en vez de
mandarla siempre a la búsqueda vectorial. LlamaIndex lo formaliza con su
`RouterQueryEngine`: un índice vectorial para preguntas de contenido
específico, y un "índice de resumen" aparte para preguntas de alcance —
este último consulta TODOS los nodos, no los top-k más parecidos, porque
es una tarea distinta de principio a fin.

Para un corpus de un dígito de documentos por asistente, construir un
índice de resúmenes aparte (o algo más elaborado, como el grafo de
entidades de GraphRAG o el árbol jerárquico de RAPTOR —ambos pensados para
corpus de cientos de miles de palabras—) sería usar una grúa para levantar
una silla. La simplificación que corresponde a esta escala: cuando se
detecta la pregunta, responder directamente con los METADATOS reales de la
base de datos (los nombres de archivo tal como se subieron), sin pasar por
Pinecone ni por el LLM. Una respuesta armada de datos reales no puede
inventar nada, porque no hay generación de por medio.

## Por qué sin LLM, y por qué conservador

Clasificar la intención con un modelo (en vez de con patrones de texto) es
lo habitual en routers más sofisticados, pero para esto no hace falta:
librerías como Semantic Router ya documentan la misma jerarquía de coste
que se sigue aquí — reglas/regex son lo más barato pero frágiles ante
parafraseo; embeddings generalizan mejor pero cuestan más; LLM solo para lo
realmente ambiguo. Dado que ya se decidió no añadir más llamadas al modelo
de las imprescindibles (ver el filtro de descomposición en
`rag_service_avanzado.py`), esta es la capa más barata de esa jerarquía.

El filtro es deliberadamente estricto — cada patrón exige una frase casi
exacta, no un tema de fondo parecido. "¿Qué documentos tienes?" activa esto;
"¿qué documentos necesito para entender X?" NO, porque es una pregunta de
contenido con un documento como posible respuesta, no una pregunta sobre el
catálogo. Ante cualquier duda, no se activa y la pregunta sigue el camino
normal del RAG — el mismo criterio que ya aplica
`rag_service_avanzado._puede_tener_varias_preguntas`: un falso negativo aquí
dejó la pregunta exactamente como estaba antes de que existiera este
archivo (tan malo como hoy, no peor); un falso positivo convertiría una
pregunta de contenido real en una lista de nombres de archivo, que sí sería
una regresión nueva. Por eso el coste de equivocarse es asimétrico y el
filtro se diseñó para fallar siempre hacia el lado barato.
"""
import re
from typing import List, Optional

from sqlalchemy.orm import Session

from app.repositories.document_repository import DocumentRepository

# Cada patrón exige (casi) toda la frase, no una palabra suelta en medio de
# otra pregunta — ver el razonamiento completo en el docstring del módulo.
_PATRONES = [
    re.compile(r"^\s*(?:qu[eé]|cu[aá]les)\s+documentos?\s+(?:tienes|tengo|hay|existen)\s*\??\s*$", re.IGNORECASE),
    re.compile(r"^\s*cu[aá]ntos\s+documentos?\s+(?:tienes|hay)\s*\??\s*$", re.IGNORECASE),
    re.compile(r"^\s*(?:qu[eé]|cu[aá]les)\s+temas\s+(?:puedo|puedes)\s+consultar\s*\??\s*$", re.IGNORECASE),
    re.compile(r"^\s*(?:qu[eé]|cu[aá]les)\s+temas\s+(?:cubre[sn]?|hay|tienes)\s*\??\s*$", re.IGNORECASE),
    re.compile(
        r"^\s*de\s+qu[eé]\s+trata[n]?\s+"
        r"(?:la\s+documentaci[oó]n|los\s+documentos|el\s+corpus|todo\s+esto)"
        r"(?:\s+disponibles?)?\s*\??\s*$",
        re.IGNORECASE,
    ),
    re.compile(r"^\s*qu[eé]\s+informaci[oó]n\s+tienes\s*\??\s*$", re.IGNORECASE),
    re.compile(
        r"^\s*res[uú]me(?:me)?\s+(?:todo\s+lo\s+que\s+sabes|la\s+documentaci[oó]n|todo)\s*\.?\s*$",
        re.IGNORECASE,
    ),
]


def es_pregunta_de_alcance_global(query: str) -> bool:
    """True solo si la pregunta ENTERA coincide con una de las frases de
    alcance global — no si las menciona de paso. Ver el docstring del
    módulo para el porqué de ser tan estricto.

    Se quitan los signos de interrogación de apertura y cierre antes de
    comparar: los patrones ya son estrictos por su cuenta, no hace falta que
    además dependan de si alguien escribió el "¿" inicial, que en español es
    habitual pero no obligatorio.
    """
    texto = query.strip().strip("¿?").strip()
    return any(patron.match(texto) for patron in _PATRONES)


def _nombres_de_documentos_completados(documentos: List) -> List[str]:
    return sorted({d.original_filename for d in documentos if d.status == "completed"})


def responder_alcance_global(db: Session, company_id: int, assistant_id: Optional[int]) -> str:
    """Arma la respuesta desde los metadatos reales de `documents` — nunca
    desde fragmentos recuperados ni desde el LLM — así no hay nada que esta
    función pueda inventar.

    Solo cuentan los documentos con `status == "completed"`: uno que sigue
    procesándose o que falló no es, todavía, un documento "disponible para
    consultar", y listarlo confundiría más de lo que ayuda.
    """
    repo = DocumentRepository(db)
    documentos = repo.get_by_assistant(assistant_id) if assistant_id else repo.get_by_company(company_id)
    nombres = _nombres_de_documentos_completados(documentos)

    if not nombres:
        return "Todavía no hay documentos disponibles para consultar."

    lista = "\n".join(f"- {nombre}" for nombre in nombres)
    plural = "documento" if len(nombres) == 1 else "documentos"
    return f"Tienes acceso a {len(nombres)} {plural}:\n{lista}"
