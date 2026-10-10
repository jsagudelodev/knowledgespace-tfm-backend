"""Experimento 3 - revalidacion del umbral de relevancia.

El `RELEVANCE_THRESHOLD = 0.30` de `rag_service.py` se midio en junio de 2026
sobre un indice fragmentado POR CARACTERES. Desde el 3 de octubre la ingesta
fragmenta por oraciones, y al cambiar la fragmentacion cambia la distribucion de
similitudes: los fragmentos son mas cortos, mas homogeneos semanticamente y
terminan en limites de frase, de modo que los rangos de la medicion original no
son automaticamente transferibles.

Este guion repite la metodologia original sobre el indice actual.

**Metodo.** Tres familias de consultas contra el indice real:

  - CUBIERTA   : el corpus responde a la pregunta.
  - TANGENCIAL : del dominio, pero no cubierta especificamente.
  - AJENA      : nada que ver con el corpus.

De ahi salen los dos numeros que sostienen el umbral:

  - RUIDO MAXIMO : la puntuacion mas alta que alcanza una consulta ajena. Por
                   encima de ella, el umbral deja pasar basura.
  - SENAL MINIMA : la puntuacion mas baja de un fragmento legitimamente
                   recuperado, definida como el ultimo resultado (el quinto) de
                   la consulta cubierta peor servida. Por debajo de ella, el
                   umbral descarta evidencia valida.

Si existe una banda vacia entre ambos, cualquier valor dentro de ella funciona y
el centro es la eleccion mas robusta. Si no existe banda, el umbral no puede
separar senal de ruido y hay que revisar el diseno, no el valor.

**No llama al modelo generativo.** Solo genera los embeddings de las consultas,
cuyo coste es de millonesimas de dolar.

Uso:

    cd api
    .venv\\Scripts\\python.exe experimentos\\medir_umbral.py --empresa 8 --asistente 1
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.embedding_service import EmbeddingService  # noqa: E402
from app.services.pinecone_service import PineconeService  # noqa: E402
from app.services.rag_service import RELEVANCE_THRESHOLD  # noqa: E402

TOP_K = 5

# Las consultas replican las familias de la medicion original (ver
# docs/RAG_PIPELINE.md seccion 6), adaptadas al corpus que hay indexado hoy:
# modelos autoregresivos, VAEs, GANs, difusion, LLMs y geometria semantica.
CONSULTAS: Dict[str, List[str]] = {
    "cubierta": [
        "que son las GANs",
        "que es un VAE",
        "que son los modelos de difusion",
        "que es la geometria semantica",
    ],
    "tangencial": [
        "que es la arquitectura transformer",
        "como se entrena una red neuronal",
    ],
    "ajena": [
        "cual es la capital de Francia",
        "como preparo una paella",
        "cuanto cuesta un billete de tren a Madrid",
    ],
}


def medir(namespace: str) -> Dict[str, Any]:
    emb = EmbeddingService()
    pine = PineconeService()
    resultados: Dict[str, Any] = {}

    for familia, preguntas in CONSULTAS.items():
        filas = []
        for q in preguntas:
            vector, _ = emb.generar_embedding_con_uso(q)
            docs = pine.buscar_vectores(vector, top_k=TOP_K, namespace=namespace)
            scores = [round(float(getattr(d, "score", 0)), 3) for d in docs]
            filas.append({
                "consulta": q,
                "scores": scores,
                "top_1": scores[0] if scores else 0.0,
                "top_k": scores[-1] if scores else 0.0,
                "documentos": [
                    (d.metadata or {}).get("document_name", "?") for d in docs
                ],
            })
        resultados[familia] = filas
    return resultados


def analizar(res: Dict[str, Any]) -> Dict[str, Any]:
    # Ruido maximo: lo mas alto que consigue una consulta ajena, en cualquier
    # posicion. Es el listo mas peligroso del grupo que NO debe pasar.
    ruido_max = max((s for f in res["ajena"] for s in f["scores"]), default=0.0)

    # Senal minima: el ultimo resultado de la consulta cubierta peor servida.
    # No se toma el top-1: si el umbral solo respetara el primer resultado,
    # descartaria evidencia complementaria que el modelo si deberia ver.
    senal_min = min((f["top_k"] for f in res["cubierta"]), default=0.0)

    banda = senal_min - ruido_max
    return {
        "ruido_maximo": round(ruido_max, 3),
        "senal_minima": round(senal_min, 3),
        "banda_vacia": round(banda, 3),
        "centro_de_la_banda": round((ruido_max + senal_min) / 2, 3),
        "hay_banda": banda > 0,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--empresa", type=int, required=True)
    ap.add_argument("--asistente", type=int, default=None)
    args = ap.parse_args()

    namespace = PineconeService.construir_namespace(args.empresa, args.asistente)
    print(f"Namespace: {namespace}   top_k={TOP_K}   umbral actual={RELEVANCE_THRESHOLD}\n")

    res = medir(namespace)

    for familia in ("cubierta", "tangencial", "ajena"):
        print(f"--- {familia.upper()} ---")
        for f in res[familia]:
            pasan = sum(1 for s in f["scores"] if s >= RELEVANCE_THRESHOLD)
            print(f"  {f['consulta'][:42]:<44} top1={f['top_1']:.3f}  "
                  f"top{TOP_K}={f['top_k']:.3f}  pasan={pasan}/{len(f['scores'])}")
        print()

    a = analizar(res)
    print("=" * 74)
    print(f"  Ruido maximo (consulta ajena)      : {a['ruido_maximo']:.3f}")
    print(f"  Senal minima (cubierta peor servida): {a['senal_minima']:.3f}")
    print(f"  Banda vacia                        : {a['banda_vacia']:.3f}")
    print(f"  Centro de la banda                 : {a['centro_de_la_banda']:.3f}")
    print(f"  Umbral actual                      : {RELEVANCE_THRESHOLD}")
    print("=" * 74)

    if not a["hay_banda"]:
        print("\n  NO HAY BANDA: el ruido alcanza o supera a la senal. El umbral")
        print("  no puede separar ambos grupos con este corpus.")
    else:
        desvio = abs(RELEVANCE_THRESHOLD - a["centro_de_la_banda"])
        dentro = a["ruido_maximo"] < RELEVANCE_THRESHOLD < a["senal_minima"]
        print(f"\n  El umbral {RELEVANCE_THRESHOLD} {'SI' if dentro else 'NO'} cae dentro de la banda.")
        print(f"  Desviacion respecto al centro: {desvio:.3f}")
        print(f"  Margen sobre el ruido: {RELEVANCE_THRESHOLD - a['ruido_maximo']:.3f}")
        print(f"  Margen bajo la senal : {a['senal_minima'] - RELEVANCE_THRESHOLD:.3f}")

    salida = Path(__file__).parent / "resultados" / f"umbral_{date.today().isoformat()}.json"
    salida.parent.mkdir(exist_ok=True)
    salida.write_text(json.dumps({
        "fecha": date.today().isoformat(),
        "namespace": namespace,
        "top_k": TOP_K,
        "umbral_vigente": RELEVANCE_THRESHOLD,
        "analisis": a,
        "consultas": res,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nResultados guardados en {salida.relative_to(Path(__file__).parent.parent)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
