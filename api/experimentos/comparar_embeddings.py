"""EXP-14 - ¿recupera mejor otro modelo de embedding?

Compara la recuperación con el modelo de producción (`text-embedding-3-small`,
la variante `control`) y con otro modelo, sobre **los mismos fragmentos**.

**Por qué hace falta reindexar.** Cada modelo de embedding construye su propio
espacio vectorial: un vector de `3-small` y uno de `3-large` no son
comparables, aunque tengan el mismo número de dimensiones. Para consultar con
otro modelo, los documentos tienen que estar convertidos con ese mismo modelo.

**Los mismos fragmentos, no un troceado nuevo.** El texto se copia de los
fragmentos ya indexados en el espacio de producción, con sus mismos
identificadores y metadatos. Volver a procesar los PDF podría producir otros
fragmentos, y entonces la diferencia no se podría atribuir al modelo.

**Sin tocar producción.** Los vectores nuevos van a un espacio propio, que
tiene que empezar por `exp-`: el script se niega a escribir en cualquier otro.
Ningún usuario puede llegar a ese espacio, porque el chat solo busca en
`company-{empresa}-assistant-{asistente}`. El espacio de producción solo se
lee, y se cuentan sus vectores antes y después para dejar constancia de que
no cambió.

**Sin umbral.** El 0,30 se calibró para `3-small` y otro modelo puntúa en otra
escala: aplicarlo descartaría fragmentos válidos del modelo candidato. La
comparación usa los cinco primeros resultados sin filtrar (hit@1, hit@3,
hit@5 y MRR por frase ancla, deterministas y sin juez). Aparte, se repite la
medición de banda de EXP-02 con sus mismas nueve consultas, para saber qué
umbral necesitaría el modelo candidato.

**Dimensiones.** El índice es de 1.536. `text-embedding-3-large` produce 3.072
por defecto, pero la API admite pedirle menos (`--dimensiones`): se mide el
modelo reducido a 1.536, y así se declara.

Coste: convertir el corpus y las consultas, menos de un céntimo de dólar. No
genera respuestas.

Uso:

    cd api
    .venv\\Scripts\\python.exe experimentos\\comparar_embeddings.py --empresa 8 --asistente 1
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import subprocess
import sys
import time
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional

AQUI = Path(__file__).parent
sys.path.insert(0, str(AQUI.parent))
sys.path.insert(0, str(AQUI))

from ejecutar_dataset import DATASET, evaluar_anclas  # noqa: E402
from medir_umbral import CONSULTAS, analizar  # noqa: E402
from openai import OpenAI  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.services.pinecone_service import PineconeService  # noqa: E402

CARPETA = AQUI / "EXP-14_modelo-embedding" / "resultados"
PREFIJO_EXPERIMENTAL = "exp-"


def version_del_codigo() -> str:
    raiz = AQUI.parent.parent
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=raiz,
                            capture_output=True, text=True).stdout.strip()
    sucio = subprocess.run(["git", "status", "--porcelain"], cwd=raiz,
                           capture_output=True, text=True).stdout.strip()
    return f"{commit}+cambios-locales" if sucio else commit


def exigir_espacio_experimental(espacio: str) -> None:
    """La única barrera entre un parámetro mal escrito y el espacio real."""
    if not espacio.startswith(PREFIJO_EXPERIMENTAL):
        raise SystemExit(f"Solo se escribe en espacios que empiecen por "
                         f"'{PREFIJO_EXPERIMENTAL}'; se recibió '{espacio}'.")


class Embedder:
    """Un modelo de embedding con sus dimensiones y su consumo acumulado."""

    def __init__(self, cliente: OpenAI, modelo: str, dimensiones: Optional[int] = None):
        self.cliente, self.modelo, self.dimensiones = cliente, modelo, dimensiones
        self.tokens = 0

    def convertir(self, textos: List[str]) -> List[List[float]]:
        vectores: List[List[float]] = []
        for i in range(0, len(textos), 100):
            kw: Dict[str, Any] = {"model": self.modelo, "input": textos[i:i + 100]}
            if self.dimensiones:
                kw["dimensions"] = self.dimensiones
            r = self.cliente.embeddings.create(**kw)
            vectores.extend(d.embedding for d in sorted(r.data, key=lambda d: d.index))
            self.tokens += r.usage.total_tokens
        return vectores


def vectores_en(pine: PineconeService, espacio: str) -> int:
    stats = pine.pc.Index(pine.nombre_indice).describe_index_stats()
    return stats.get("namespaces", {}).get(espacio, {}).get("vector_count", 0)


def indexar(pine: PineconeService, emb: Embedder, origen: str, destino: str) -> int:
    """Copia los fragmentos de `origen` a `destino`, convertidos con `emb`."""
    exigir_espacio_experimental(destino)
    fragmentos = [f for f in pine.listar_namespace(origen) if f["text"].strip()]
    vectores = emb.convertir([f["text"] for f in fragmentos])
    lote = [{
        "id": f["chunk_id"],
        "values": v,
        "metadata": {"document_id": f["document_id"], "document_name": f["document_name"],
                     "chunk_index": f["chunk_index"], "text": f["text"]},
    } for f, v in zip(fragmentos, vectores, strict=True)]
    for i in range(0, len(lote), 100):
        pine.upsert_vectores(lote[i:i + 100], namespace=destino)

    # Pinecone serverless tarda unos segundos en reflejar lo escrito: medir
    # antes de que esté completo compararía un corpus a medias.
    for _ in range(30):
        if vectores_en(pine, destino) >= len(lote):
            break
        time.sleep(2)
    else:
        raise SystemExit(f"{destino} no llegó a {len(lote)} vectores")
    return len(lote)


def buscar(pine: PineconeService, emb: Embedder, consulta: str, espacio: str, top_k: int):
    docs = pine.buscar_vectores(emb.convertir([consulta])[0], top_k=top_k, namespace=espacio)
    return [((d.metadata or {}).get("text", ""), round(float(d.score), 3), d.id) for d in docs]


def medir_dataset(pine: PineconeService, emb: Embedder, espacio: str, top_k: int) -> List[Dict[str, Any]]:
    with io.open(DATASET, encoding="utf-8", newline="") as f:
        filas = list(csv.DictReader(f))
    salida = []
    for fila in filas:
        res = buscar(pine, emb, fila["pregunta"], espacio, top_k)
        salida.append({
            "id": int(fila["id"]),
            "tipo": fila["tipo"],
            "pregunta": fila["pregunta"],
            "anclas": evaluar_anclas(fila, [t for t, _, _ in res]),
            "scores": [s for _, s, _ in res],
            "ids": [i for _, _, i in res],
        })
    return salida


def medir_banda(pine: PineconeService, emb: Embedder, espacio: str, top_k: int) -> Dict[str, Any]:
    """Las nueve consultas de EXP-02, con el mismo cálculo de banda."""
    res: Dict[str, List[Dict[str, Any]]] = {}
    for familia, preguntas in CONSULTAS.items():
        res[familia] = []
        for q in preguntas:
            scores = [s for _, s, _ in buscar(pine, emb, q, espacio, top_k)]
            res[familia].append({"consulta": q, "scores": scores,
                                 "top_1": scores[0] if scores else 0.0,
                                 "top_k": scores[-1] if scores else 0.0})
    return {"consultas": res, "analisis": analizar(res)}


def resumir(filas: List[Dict[str, Any]]) -> Dict[str, Any]:
    con = [f for f in filas if f["anclas"]["aplica"]]
    grupos = {"todas": con}
    for t in dict.fromkeys(f["tipo"] for f in con):
        grupos[t] = [f for f in con if f["tipo"] == t]
    return {g: {"n": len(fs),
                "hit_1": round(sum(f["anclas"]["hit_1"] for f in fs) / len(fs), 3),
                "hit_3": round(sum(f["anclas"]["hit_3"] for f in fs) / len(fs), 3),
                "hit_5": round(sum(f["anclas"]["hit_5"] for f in fs) / len(fs), 3),
                "mrr": round(sum(f["anclas"]["rr"] for f in fs) / len(fs), 3)}
            for g, fs in grupos.items() if fs}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--empresa", type=int, required=True)
    ap.add_argument("--asistente", type=int, required=True)
    ap.add_argument("--modelo", default="text-embedding-3-large")
    ap.add_argument("--dimensiones", type=int, default=PineconeService.DIMENSION)
    ap.add_argument("--espacio", default="exp-emb-3-large")
    ap.add_argument("--reindexar", action="store_true",
                    help="vuelve a convertir el corpus aunque el espacio ya tenga vectores")
    args = ap.parse_args()
    exigir_espacio_experimental(args.espacio)

    top_k = settings.RAG_TOP_K
    pine = PineconeService()
    cliente = OpenAI(api_key=settings.OPENAI_API_KEY)
    produccion = PineconeService.construir_namespace(args.empresa, args.asistente)
    control = Embedder(cliente, settings.OPENAI_EMBEDDING_MODEL)
    candidato = Embedder(cliente, args.modelo, args.dimensiones)

    vectores_produccion_antes = vectores_en(pine, produccion)
    print(f"Producción  {produccion}: {vectores_produccion_antes} vectores")

    if args.reindexar or vectores_en(pine, args.espacio) == 0:
        n = indexar(pine, candidato, produccion, args.espacio)
        print(f"Indexados   {args.espacio}: {n} fragmentos con {args.modelo} ({args.dimensiones} dim.)")
    tokens_indexado = candidato.tokens
    print(f"Candidato   {args.espacio}: {vectores_en(pine, args.espacio)} vectores\n")

    variantes = {
        "control": (control, produccion),
        args.espacio.removeprefix(PREFIJO_EXPERIMENTAL): (candidato, args.espacio),
    }
    resultados = {}
    for nombre, (emb, espacio) in variantes.items():
        filas = medir_dataset(pine, emb, espacio, top_k)
        resultados[nombre] = {"modelo": emb.modelo, "dimensiones": emb.dimensiones or PineconeService.DIMENSION,
                              "espacio": espacio, "resumen": resumir(filas),
                              "banda": medir_banda(pine, emb, espacio, top_k), "por_pregunta": filas}

    vectores_produccion_despues = vectores_en(pine, produccion)

    print(f"{'':<16}" + "".join(f"{n:>26}" for n in resultados))
    for grupo in resultados["control"]["resumen"]:
        linea = f"  {grupo:<14}"
        for r in resultados.values():
            s = r["resumen"].get(grupo)
            linea += f"  hit@1 {s['hit_1']:.2f} hit@3 {s['hit_3']:.2f} MRR {s['mrr']:.3f}" if s else " " * 26
        print(linea)
    print()
    for nombre, r in resultados.items():
        a = r["banda"]["analisis"]
        print(f"  banda {nombre:<12} ruido máx {a['ruido_maximo']:.3f}  señal mín {a['senal_minima']:.3f}  "
              f"banda {a['banda_vacia']:+.3f}  centro {a['centro_de_la_banda']:.3f}")
    cambio = "" if vectores_produccion_despues == vectores_produccion_antes else "   <-- CAMBIÓ"
    print(f"\n  Producción antes/después: {vectores_produccion_antes} / {vectores_produccion_despues}{cambio}")

    CARPETA.mkdir(parents=True, exist_ok=True)
    salida = CARPETA / f"{date.today().isoformat()}.json"
    salida.write_text(json.dumps({
        "experimento": "EXP-14",
        "pregunta": "¿Recupera mejor otro modelo de embedding, sobre los mismos fragmentos?",
        "fecha": date.today().isoformat(),
        "commit": version_del_codigo(),
        "dataset": {"archivo": DATASET.name,
                    "sha256": hashlib.sha256(DATASET.read_bytes()).hexdigest()},
        "parametros": {"top_k": top_k, "umbral": "ninguno (ver docstring)",
                       "modelo_control": control.modelo, "modelo_candidato": args.modelo,
                       "dimensiones_candidato": args.dimensiones},
        "corpus": {"espacio_produccion": produccion,
                   "vectores_produccion_antes": vectores_produccion_antes,
                   "vectores_produccion_despues": vectores_produccion_despues,
                   "espacio_candidato": args.espacio},
        "tokens": {"indexado_candidato": tokens_indexado,
                   "consultas_control": control.tokens,
                   "consultas_candidato": candidato.tokens - tokens_indexado},
        "variantes": resultados,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nResultados en {salida.relative_to(AQUI.parent)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
