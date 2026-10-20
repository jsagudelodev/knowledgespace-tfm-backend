"""Búsqueda léxica BM25, en memoria y sin dependencias.

Es la mitad que le falta a la búsqueda densa para que el sistema sea un RAG
híbrido. La similitud coseno compara significado: dos frases sobre lo mismo
quedan cerca aunque no compartan ni una palabra. Eso es su fuerza y también su
punto ciego —un acrónimo, un identificador, un término técnico poco frecuente
puede no tener una representación vectorial distintiva, y la búsqueda densa lo
trata como ruido—. BM25 compara **presencia literal de términos**, ponderada
por lo raros que son en el corpus: es torpe con el significado y preciso con
la letra, justo donde la densa es al revés.

**Por qué a mano y no con `rank-bm25`.** Es una fórmula de una página, sin
estado que mantener entre consultas más allá de las frecuencias del corpus, y
evita sumar una dependencia para un cálculo que cabe en un módulo propio. Se
reconstruye el índice en cada consulta porque el corpus de este trabajo es
pequeño —87 fragmentos—; sobre un corpus de miles, reconstruirlo en cada
consulta sí sería un problema a resolver con una librería madura o con caché.

**Limitación declarada: sin normalización morfológica.** La tokenización
colapsa a minúsculas pero no aplica *stemming* ni quita variantes de género o
número: «modelo» y «modelos» cuentan como términos distintos. En español, con
su flexión rica, eso le resta alcance a la parte léxica frente a una
implementación con lematización. Se documenta como limitación y no se corrige
aquí porque añadir un lematizador es otra dependencia más, y el efecto real
sobre este corpus concreto es lo que mide el experimento, no una suposición.
"""
import math
import re
from collections import Counter
from typing import Dict, List, Tuple

# Los valores estándar de la fórmula Okapi BM25 (Robertson y Zaragoza, 2009).
# K1 controla cuánto satura la frecuencia de un término dentro de un mismo
# fragmento —que aparezca diez veces no debe valer diez veces más que una vez
# sola—; B controla cuánto penaliza a los fragmentos largos frente a los
# cortos. No se midieron a propósito para este corpus: son los valores de
# referencia de la literatura, y ajustarlos exigiría un conjunto de preguntas
# mucho mayor que el disponible para no sobreajustar a dieciocho casos.
K1 = 1.5
B = 0.75


def _tokenizar(texto: str) -> List[str]:
    """Minúsculas y secuencias alfanuméricas. Sin *stemming*, sin *stopwords*:
    ver la limitación declarada en el docstring del módulo."""
    return re.findall(r"\w+", (texto or "").lower())


class IndiceLexico:
    """Índice BM25 sobre una colección fija de fragmentos.

    Se construye una vez por consulta híbrida, sobre el corpus completo del
    espacio de nombres —no solo los candidatos que la búsqueda densa ya trajo—
    porque el objetivo es precisamente poder rescatar un fragmento que la
    similitud coseno descartó de entrada.
    """

    def __init__(self, documentos: List[Tuple[str, str]]):
        """`documentos` es una lista de `(identificador, texto)`."""
        self._ids = [d[0] for d in documentos]
        self._tokens = [_tokenizar(d[1]) for d in documentos]
        self._longitudes = [len(t) for t in self._tokens]
        self._longitud_media = (
            sum(self._longitudes) / len(self._longitudes) if self._longitudes else 0.0
        )
        self._frecuencias: List[Counter] = [Counter(t) for t in self._tokens]

        # Documentos en que aparece cada término, para el IDF.
        self._en_cuantos_documentos: Dict[str, int] = Counter()
        for frecuencia in self._frecuencias:
            for termino in frecuencia:
                self._en_cuantos_documentos[termino] += 1

    def _idf(self, termino: str) -> float:
        n = len(self._ids)
        n_t = self._en_cuantos_documentos.get(termino, 0)
        # La forma con +1 dentro del logaritmo evita un IDF negativo cuando un
        # término aparece en más de la mitad del corpus —algo plausible en un
        # corpus de 87 fragmentos sobre un único dominio—, a costa de que ya
        # no pueda ser exactamente cero.
        return math.log(1 + (n - n_t + 0.5) / (n_t + 0.5))

    def buscar(self, consulta: str, top_k: int) -> List[Tuple[str, float]]:
        """Devuelve hasta `top_k` pares `(identificador, puntuación BM25)`,
        ordenados de mayor a menor. Lista vacía si ningún fragmento comparte
        ningún término con la consulta."""
        terminos = set(_tokenizar(consulta))
        if not terminos or not self._ids:
            return []

        puntuaciones: List[Tuple[str, float]] = []
        for i, doc_id in enumerate(self._ids):
            frecuencia = self._frecuencias[i]
            longitud = self._longitudes[i]
            puntuacion = 0.0
            for termino in terminos:
                f = frecuencia.get(termino, 0)
                if f == 0:
                    continue
                idf = self._idf(termino)
                numerador = f * (K1 + 1)
                denominador = f + K1 * (
                    1 - B + B * (longitud / self._longitud_media if self._longitud_media else 1)
                )
                puntuacion += idf * (numerador / denominador)
            if puntuacion > 0:
                puntuaciones.append((doc_id, puntuacion))

        puntuaciones.sort(key=lambda par: par[1], reverse=True)
        return puntuaciones[:top_k]
