"""Experimento 1 — calidad estructural del chunking.

Compara las dos estrategias que conviven en `PDFService` sobre los mismos
documentos: división por caracteres fijos (la original) y agrupación por
oraciones (la nueva). Mide qué hace cada una con el texto, sin llamar a ningún
modelo: todo ocurre en local y no cuesta nada ejecutarlo.

**Mide el código de produccion, no una copia.** Importa `PDFService` y usa sus
metodos tal cual. Si el experimento reimplementara el chunking, estaria midiendo
otro sistema distinto del que se entrega.

Uso:

    cd api
    python experimentos/medir_chunking.py ../docs/Test-Documentos

Los resultados se guardan en `experimentos/resultados/` con la fecha, para que
las cifras de la memoria tengan un respaldo con el que contrastarlas.
"""
from __future__ import annotations

import io
import json
import statistics
import sys
from datetime import date
from pathlib import Path
from typing import Any, Dict, List

# El paquete `app` cuelga de `api/`, que es el directorio padre de este archivo.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.pdf_service import PDFService  # noqa: E402

# Los mismos valores que usa la ingesta en produccion (ver `PDFService.procesar`).
TARGET_SIZE = 1000
OVERLAP = 200

# Un chunk termina "limpio" si acaba en un signo de cierre de frase. Cualquier
# otra cosa —una letra, una coma— significa que se corto a mitad de idea.
CIERRES_DE_FRASE = ".!?:;"


# ── Métricas ────────────────────────────────────────────────────────────────


def _corta_palabra(chunk: str, es_ultimo: bool) -> bool:
    """¿El chunk termina a mitad de una palabra?

    Se excluye el ultimo chunk del documento: ahi el texto se acabo de verdad,
    no hay corte. Sin esa exclusion, todo documento sumaria un falso positivo.
    """
    if es_ultimo:
        return False
    limpio = chunk.rstrip()
    return bool(limpio) and limpio[-1].isalnum()


def _corta_frase(chunk: str, es_ultimo: bool) -> bool:
    """¿El chunk termina sin cerrar la frase?

    Criterio deliberadamente simple y verificable: se mira el ultimo caracter
    no vacio. Un analisis sintactico real daria una cifra mas fina, pero seria
    otro sistema el que se estaria midiendo, no este.
    """
    if es_ultimo:
        return False
    limpio = chunk.rstrip()
    return bool(limpio) and limpio[-1] not in CIERRES_DE_FRASE


def medir(chunks: List[str], texto_original: str) -> Dict[str, Any]:
    """Calcula las métricas estructurales de una lista de chunks."""
    if not chunks:
        return {"chunks": 0}

    tamanios = [len(c) for c in chunks]
    ultimo = len(chunks) - 1

    cortan_palabra = sum(_corta_palabra(c, i == ultimo) for i, c in enumerate(chunks))
    cortan_frase = sum(_corta_frase(c, i == ultimo) for i, c in enumerate(chunks))
    exceden = sum(1 for t in tamanios if t > TARGET_SIZE)

    # Cuanto texto se indexa frente al original. Por encima del 100% hay
    # duplicacion (el solapamiento se paga dos veces en embeddings); por debajo,
    # se esta perdiendo contenido.
    total_indexado = sum(tamanios)
    cobertura = total_indexado / len(texto_original) if texto_original else 0

    return {
        "chunks": len(chunks),
        "tamanio_medio": round(statistics.mean(tamanios), 1),
        "tamanio_mediana": round(statistics.median(tamanios), 1),
        "tamanio_desviacion": round(statistics.pstdev(tamanios), 1) if len(tamanios) > 1 else 0.0,
        "tamanio_min": min(tamanios),
        "tamanio_max": max(tamanios),
        "cortan_palabra": cortan_palabra,
        "cortan_palabra_pct": round(100 * cortan_palabra / len(chunks), 1),
        "cortan_frase": cortan_frase,
        "cortan_frase_pct": round(100 * cortan_frase / len(chunks), 1),
        "exceden_objetivo": exceden,
        "exceden_objetivo_pct": round(100 * exceden / len(chunks), 1),
        "caracteres_indexados": total_indexado,
        "cobertura_pct": round(100 * cobertura, 1),
    }


def densidad_de_puntos(texto: str) -> float:
    """Puntos por cada 1.000 caracteres.

    Sirve para distinguir prosa de material esquematico sin clasificar los
    documentos a mano: unas diapositivas, hechas de titulos y listas, tienen
    muchos menos puntos que un texto corrido. Importa porque la division
    semantica usa el punto como unico separador de oraciones.
    """
    return round(1000 * texto.count(".") / len(texto), 1) if texto else 0.0


# ── Ejecución ───────────────────────────────────────────────────────────────


def analizar_documento(ruta: Path) -> Dict[str, Any]:
    """Extrae el texto de un documento y mide las dos estrategias sobre él."""
    buffer = io.BytesIO(ruta.read_bytes())
    texto, paginas = PDFService._extraer_pdf(buffer)

    por_caracteres = PDFService.dividir_en_chunks_caracteres(texto, TARGET_SIZE, OVERLAP)
    por_oraciones = PDFService.dividir_en_chunks_semantico(texto, TARGET_SIZE)

    return {
        "documento": ruta.name,
        "kb": round(ruta.stat().st_size / 1024, 1),
        "paginas": paginas,
        "caracteres": len(texto),
        "densidad_puntos_por_mil": densidad_de_puntos(texto),
        "caracteres": medir(por_caracteres, texto),
        "oraciones": medir(por_oraciones, texto),
    }


def _fila(etiqueta: str, m: Dict[str, Any]) -> str:
    return (
        f"  {etiqueta:<14} {m['chunks']:>7} {m['tamanio_medio']:>9.0f} "
        f"{m['tamanio_desviacion']:>9.0f} {m['tamanio_min']:>7} {m['tamanio_max']:>7} "
        f"{m['cortan_palabra_pct']:>9.1f} {m['cortan_frase_pct']:>9.1f} "
        f"{m['exceden_objetivo_pct']:>9.1f} {m['cobertura_pct']:>9.1f}"
    )


def main(carpeta: Path) -> int:
    documentos = sorted(p for p in carpeta.rglob("*.pdf") if p.is_file())
    if not documentos:
        print(f"No hay PDFs en {carpeta}")
        return 1

    print("=" * 110)
    print(f"CALIDAD ESTRUCTURAL DEL CHUNKING · {len(documentos)} documentos")
    print(f"target_size={TARGET_SIZE}  overlap={OVERLAP} (solo lo usa la division por caracteres)")
    print("=" * 110)

    resultados = []
    for ruta in documentos:
        try:
            datos = analizar_documento(ruta)
        except Exception as error:
            print(f"\n{ruta.name}: no se pudo procesar ({type(error).__name__}: {error})")
            continue

        resultados.append(datos)

        print(f"\n{datos['documento']}")
        print(
            f"  {datos['paginas']} paginas · {datos['caracteres']['caracteres_indexados']:,} "
            f"caracteres indexados · densidad de puntos: "
            f"{datos['densidad_puntos_por_mil']} por mil"
        )
        print(
            f"  {'estrategia':<14} {'chunks':>7} {'medio':>9} {'desv':>9} "
            f"{'min':>7} {'max':>7} {'%palabra':>9} {'%frase':>9} {'%excede':>9} {'%cobert':>9}"
        )
        print(_fila("caracteres", datos["caracteres"]))
        print(_fila("oraciones", datos["oraciones"]))

    if not resultados:
        return 1

    # ── Totales ──────────────────────────────────────────────────────────────
    print("\n" + "=" * 110)
    print("AGREGADO")
    print("=" * 110)
    for clave, nombre in (("caracteres", "por caracteres"), ("oraciones", "por oraciones")):
        total_chunks = sum(r[clave]["chunks"] for r in resultados)
        cortan_palabra = sum(r[clave]["cortan_palabra"] for r in resultados)
        cortan_frase = sum(r[clave]["cortan_frase"] for r in resultados)
        print(
            f"  {nombre:<16} {total_chunks:>5} chunks · "
            f"{100 * cortan_palabra / total_chunks:>5.1f}% cortan palabra · "
            f"{100 * cortan_frase / total_chunks:>5.1f}% cortan frase"
        )

    ahorro = sum(r["caracteres"]["chunks"] for r in resultados) - sum(
        r["oraciones"]["chunks"] for r in resultados
    )
    total_caracteres = sum(r["caracteres"]["chunks"] for r in resultados)
    print(
        f"\n  Diferencia de chunks: {ahorro:+} "
        f"({100 * ahorro / total_caracteres:+.1f}%) — cada chunk es un embedding que se paga."
    )

    # ── Respaldo ─────────────────────────────────────────────────────────────
    destino = Path(__file__).parent / "resultados"
    destino.mkdir(exist_ok=True)
    archivo = destino / f"chunking_{date.today().isoformat()}.json"
    archivo.write_text(
        json.dumps(
            {
                "fecha": date.today().isoformat(),
                "target_size": TARGET_SIZE,
                "overlap": OVERLAP,
                "documentos": resultados,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(f"\nResultados guardados en {archivo.relative_to(Path(__file__).parent.parent)}")
    return 0


if __name__ == "__main__":
    carpeta = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("../docs/Test-Documentos")
    sys.exit(main(carpeta.resolve()))
