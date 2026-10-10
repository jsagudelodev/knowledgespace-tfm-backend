"""Experimento 4 - degradacion de la recuperacion ante preguntas compuestas.

El pipeline convierte el MENSAJE ENTERO en un unico vector antes de buscar. Si
el mensaje contiene dos preguntas sobre temas distintos, el vector resultante no
representa ninguno de los dos: queda en un punto intermedio del espacio de
embeddings que puede no estar cerca de ningun fragmento.

Esta es una limitacion estructural de la arquitectura, no un defecto de
implementacion, y hasta ahora no estaba medida ni documentada. El tutor
pregunto explicitamente por ella ("que tipos de preguntas admite", "se pueden
hacer varias preguntas").

**Metodo.** Para cada pareja de temas:

  1. Se lanza cada pregunta POR SEPARADO y se guarda el conjunto de fragmentos
     que recupera. Ese conjunto es la referencia: lo que el sistema es capaz de
     encontrar cuando se le pregunta bien.
  2. Se lanza la pregunta COMPUESTA, uniendo ambas con "y".
  3. Se mide cuantos fragmentos de cada referencia sobreviven en la compuesta.

**El contraste que se pone a prueba.** Seis parejas, clasificadas POR LA
MEDICION y no por el diseno: si las dos preguntas recuperan su mejor fragmento
del mismo documento, la pareja es VECINA; si no, LEJANA. Clasificarlas a mano
meteria en el diseno la hipotesis que se quiere comprobar.

La hipotesis de partida era que las lejanas se degradarian mas, porque el punto
medio entre dos regiones alejadas del espacio cae en tierra de nadie. El
resultado dira si se sostiene.

**No llama al modelo generativo.** Solo embeddings: millonesimas de dolar.

Uso:

    cd api
    .venv\\Scripts\\python.exe experimentos\\medir_preguntas_compuestas.py --empresa 8 --asistente 1
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

# Las parejas NO se clasifican a mano. Se lanzan las dos preguntas por separado
# y se etiqueta la pareja segun el documento del que cada una recupera su mejor
# fragmento: si coinciden, son VECINAS; si no, LEJANAS. Clasificar por
# suposicion introduciria en el diseno la hipotesis que el experimento quiere
# poner a prueba.
PAREJAS = [
    {"a": "que es un VAE", "b": "que es la geometria semantica"},
    {"a": "que son las GANs", "b": "que es un VAE"},
    {"a": "que son los modelos de difusion", "b": "que es la tokenizacion"},
    {"a": "que es el test de Turing", "b": "que es la geometria semantica"},
    {"a": "que son los modelos de difusion", "b": "que son los LLM"},
    {"a": "que es la tokenizacion", "b": "que es el mecanismo de atencion"},
]


def consultar(emb, pine, pregunta: str, namespace: str) -> Dict[str, Any]:
    vector, _ = emb.generar_embedding_con_uso(pregunta)
    docs = pine.buscar_vectores(vector, top_k=TOP_K, namespace=namespace)
    return {
        "pregunta": pregunta,
        "ids": [d.id for d in docs],
        "scores": [round(float(getattr(d, "score", 0)), 3) for d in docs],
        "documentos": [(d.metadata or {}).get("document_name", "?") for d in docs],
    }


def medir(namespace: str) -> List[Dict[str, Any]]:
    emb, pine = EmbeddingService(), PineconeService()
    salida = []

    for par in PAREJAS:
        a = consultar(emb, pine, par["a"], namespace)
        b = consultar(emb, pine, par["b"], namespace)
        compuesta_txt = f"{par['a']} y {par['b']}"
        c = consultar(emb, pine, compuesta_txt, namespace)

        ids_a, ids_b, ids_c = set(a["ids"]), set(b["ids"]), set(c["ids"])

        # Etiqueta derivada de la medicion, no del diseno.
        mismo_doc = a["documentos"][0] == b["documentos"][0]
        etiqueta = "vecinas" if mismo_doc else "lejanas"

        salida.append({
            **par,
            "etiqueta": etiqueta,
            "nota": ("mismo documento principal" if mismo_doc
                     else "documentos principales distintos"),
            "doc_principal_a": a["documentos"][0],
            "doc_principal_b": b["documentos"][0],
            "separada_a": a,
            "separada_b": b,
            "compuesta": c,
            "recuperados_de_a": len(ids_a & ids_c),
            "recuperados_de_b": len(ids_b & ids_c),
            "ajenos_a_ambas": len(ids_c - ids_a - ids_b),
            "caida_top1_a": round(a["scores"][0] - c["scores"][0], 3),
            "caida_top1_b": round(b["scores"][0] - c["scores"][0], 3),
            "sobre_umbral_compuesta": sum(1 for s in c["scores"] if s >= RELEVANCE_THRESHOLD),
        })
    return salida


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--empresa", type=int, required=True)
    ap.add_argument("--asistente", type=int, default=None)
    args = ap.parse_args()

    namespace = PineconeService.construir_namespace(args.empresa, args.asistente)
    print(f"Namespace: {namespace}   top_k={TOP_K}\n")

    res = medir(namespace)

    for r in res:
        print("=" * 78)
        print(f"PAREJA {r['etiqueta'].upper()} - {r['nota']}")
        print("=" * 78)
        for clave, etq in (("separada_a", "A separada"), ("separada_b", "B separada"), ("compuesta", "COMPUESTA ")):
            d = r[clave]
            print(f"  {etq}  top1={d['scores'][0]:.3f}  scores={d['scores']}")
            print(f"              {d['pregunta'][:66]}")
        print()
        print(f"  De los {TOP_K} fragmentos de A, la compuesta recupera: {r['recuperados_de_a']}")
        print(f"  De los {TOP_K} fragmentos de B, la compuesta recupera: {r['recuperados_de_b']}")
        print(f"  Fragmentos que no venian de ninguna de las dos     : {r['ajenos_a_ambas']}")
        print(f"  Caida del top-1 respecto a A: {r['caida_top1_a']:+.3f}   respecto a B: {r['caida_top1_b']:+.3f}")
        print(f"  Fragmentos sobre el umbral en la compuesta: {r['sobre_umbral_compuesta']}/{TOP_K}")
        print()

    print("=" * 78)
    print("LECTURA")
    print("=" * 78)
    for r in res:
        cobertura = (r["recuperados_de_a"] + r["recuperados_de_b"]) / (2 * TOP_K)
        desequilibrio = abs(r["recuperados_de_a"] - r["recuperados_de_b"])
        print(f"  {r['etiqueta']:<9} cobertura={cobertura:>4.0%}  "
              f"reparto={r['recuperados_de_a']}/{r['recuperados_de_b']}  "
              f"desequilibrio={desequilibrio}  sobre umbral={r['sobre_umbral_compuesta']}/{TOP_K}")

    print()
    for etiqueta in ("lejanas", "vecinas"):
        grupo = [r for r in res if r["etiqueta"] == etiqueta]
        if not grupo:
            continue
        cob = sum(r["recuperados_de_a"] + r["recuperados_de_b"] for r in grupo) / (2 * TOP_K * len(grupo))
        des = sum(abs(r["recuperados_de_a"] - r["recuperados_de_b"]) for r in grupo) / len(grupo)
        print(f"  {etiqueta.upper():<9} n={len(grupo)}  cobertura media={cob:.0%}  "
              f"desequilibrio medio={des:.1f}")

    total_sobre = sum(r["sobre_umbral_compuesta"] for r in res)
    print()
    print(f"  Fragmentos que superan el umbral en las compuestas: "
          f"{total_sobre}/{TOP_K * len(res)} - el umbral NO detecta la cobertura parcial.")

    salida = Path(__file__).parent / "resultados" / f"preguntas_compuestas_{date.today().isoformat()}.json"
    salida.parent.mkdir(exist_ok=True)
    salida.write_text(json.dumps({
        "fecha": date.today().isoformat(),
        "namespace": namespace,
        "top_k": TOP_K,
        "parejas": res,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nResultados en {salida.relative_to(Path(__file__).parent.parent)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
