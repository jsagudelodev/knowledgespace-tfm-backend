"""EXP-15 - ¿qué tamaño de fragmento recupera mejor?

EXP-01 comparó la *estrategia* de troceado (por caracteres o por oraciones),
pero el *tamaño* objetivo, 1.000 caracteres, nunca se varió. Este script
trocea los mismos documentos originales a varios tamaños con la función de
producción (`PDFService.dividir_en_chunks_semantico`) y mide la recuperación
de cada uno.

**Desde los originales, no desde los fragmentos guardados.** El texto que se
guarda junto a cada vector se recorta a 1.000 caracteres
(`routers/v1/documents.py`), así que no sirve para reconstruir los
documentos. Se extraen de nuevo de S3 con los extractores de producción. La
variante de 1.000 se rehace igual que las demás, para que el control salga del
mismo procedimiento; se guarda el texto completo de cada fragmento.

**Dos comparaciones, porque el tamaño cambia cuánto texto llega.** Con cinco
fragmentos fijos, los de 1.500 caracteres entregan el triple de texto que los
de 500, y una diferencia podría deberse solo a eso. Se mide con los cinco de
producción y, además, con el mismo volumen de texto (unos 5.000 caracteres:
10, 5 y 3 fragmentos).

**Frases ancla partidas.** Un fragmento pequeño puede cortar una frase ancla
por la mitad, y entonces la métrica cuenta un fallo que no lo es. Se cuenta
cuántas anclas no aparecen enteras en ningún fragmento de cada variante.

Sin umbral, como EXP-14, y con la banda de EXP-02 por variante: el tamaño del
fragmento cambia la escala de las puntuaciones, que es justo lo que motivó
EXP-02.

**Sin tocar producción.** Cada variante va a su espacio `exp-chunk-<tamaño>`,
con la misma protección que EXP-14. Las respuestas escritas a mano que hay en
el espacio de producción, que no vienen de ningún documento, se copian sin
cambios a cada variante para que el corpus sea el mismo.

Coste: los embeddings del corpus tres veces, unos 0,002 USD. No genera
respuestas.

Uso:

    cd api
    .venv\\Scripts\\python.exe experimentos\\comparar_tamano_fragmento.py --empresa 8 --asistente 1
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import statistics
import sys
import time
from datetime import date
from pathlib import Path
from typing import Any, Dict, List

AQUI = Path(__file__).parent
sys.path.insert(0, str(AQUI.parent))
sys.path.insert(0, str(AQUI))

from comparar_embeddings import (  # noqa: E402
    Embedder,
    exigir_espacio_experimental,
    medir_banda,
    medir_dataset,
    resumir,
    vectores_en,
    version_del_codigo,
)
from ejecutar_dataset import DATASET, normalizar  # noqa: E402
from openai import OpenAI  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.database import SessionLocal  # noqa: E402
from app.services.pdf_service import PDFService  # noqa: E402
from app.services.pinecone_service import PineconeService  # noqa: E402

CARPETA = AQUI / "9-embeddings-y-tamano" / "EXP-15_tamano-fragmento" / "resultados"
VOLUMEN = 5000
RECORTE_PRODUCCION = 1000   # `chunk[:1000]` en routers/v1/documents.py
EXTRACTORES = {"pdf": PDFService._extraer_pdf, "docx": PDFService._extraer_docx,
               "txt": PDFService._extraer_txt, "md": PDFService._extraer_txt}


def documentos(asistente: int) -> List[Any]:
    db = SessionLocal()
    try:
        return list(db.execute(text(
            "SELECT id, original_filename, filename, file_path FROM documents "
            "WHERE assistant_id = :a AND status = 'completed' ORDER BY id"), {"a": asistente}))
    finally:
        db.close()


def extraer(docs: List[Any]) -> Dict[int, Dict[str, Any]]:
    textos = {}
    for d in docs:
        extension = d.filename.split(".")[-1].lower()
        texto, _ = EXTRACTORES[extension](PDFService._obtener_buffer(d.file_path))
        textos[d.id] = {"nombre": d.original_filename, "texto": texto,
                        "sha256": hashlib.sha256(texto.encode("utf-8")).hexdigest()}
        print(f"  doc {d.id:<4} {str(d.original_filename)[:44]:<46} {len(texto):>7} caracteres")
    return textos


def trocear(textos: Dict[int, Dict[str, Any]], tamano: int) -> List[Dict[str, Any]]:
    fragmentos = []
    for doc_id, t in textos.items():
        for i, trozo in enumerate(PDFService.dividir_en_chunks_semantico(t["texto"], target_size=tamano)):
            fragmentos.append({"id": f"doc-{doc_id}-chunk-{i}", "document_id": doc_id,
                               "document_name": t["nombre"], "chunk_index": i, "text": trozo})
    return fragmentos


def indexar(pine: PineconeService, emb: Embedder, fragmentos: List[Dict[str, Any]], espacio: str) -> None:
    exigir_espacio_experimental(espacio)
    vectores = emb.convertir([f["text"] for f in fragmentos])
    lote = [{"id": f["id"], "values": v,
             "metadata": {k: f[k] for k in ("document_id", "document_name", "chunk_index", "text")
                          if f.get(k) is not None}}
            for f, v in zip(fragmentos, vectores, strict=True)]
    for i in range(0, len(lote), 100):
        pine.upsert_vectores(lote[i:i + 100], namespace=espacio)
    for _ in range(30):
        if vectores_en(pine, espacio) >= len(lote):
            return
        time.sleep(2)
    raise SystemExit(f"{espacio} no llegó a {len(lote)} vectores")


def anclas_partidas(fragmentos: List[Dict[str, Any]]) -> List[int]:
    """Preguntas con alguna frase ancla que no aparece entera en ningún fragmento."""
    corpus = [normalizar(f["text"]) for f in fragmentos]
    with io.open(DATASET, encoding="utf-8", newline="") as fh:
        filas = list(csv.DictReader(fh))
    return [int(fila["id"]) for fila in filas
            for a in (fila["ancla"], fila["ancla_2"])
            if a.strip() and not any(normalizar(a) in c for c in corpus)]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--empresa", type=int, required=True)
    ap.add_argument("--asistente", type=int, required=True)
    ap.add_argument("--tamanos", default="500,1000,1500", help="caracteres, separados por coma")
    ap.add_argument("--control", type=int, default=1000, help="el tamaño de producción")
    args = ap.parse_args()
    tamanos = [int(t) for t in args.tamanos.split(",")]
    for t in tamanos:
        exigir_espacio_experimental(f"exp-chunk-{t}")

    pine = PineconeService()
    produccion = PineconeService.construir_namespace(args.empresa, args.asistente)
    antes = vectores_en(pine, produccion)
    print(f"Producción {produccion}: {antes} vectores\n\nExtrayendo los originales de S3:")
    textos = extraer(documentos(args.asistente))

    # Lo que hay en producción y no viene de un documento (respuestas escritas
    # a mano): se copia igual en todas las variantes.
    extra = [{"id": f["chunk_id"], "document_id": f["document_id"], "document_name": f["document_name"],
              "chunk_index": f["chunk_index"], "text": f["text"]}
             for f in pine.listar_namespace(produccion) if not f["chunk_id"].startswith("doc-")]

    cliente = OpenAI(api_key=settings.OPENAI_API_KEY)
    variantes: Dict[str, Any] = {}
    for tamano in tamanos:
        espacio = f"exp-chunk-{tamano}"
        emb = Embedder(cliente, settings.OPENAI_EMBEDDING_MODEL)
        fragmentos = trocear(textos, tamano) + extra
        if vectores_en(pine, espacio) == 0:
            indexar(pine, emb, fragmentos, espacio)
        tokens_indexado = emb.tokens
        largos = [len(f["text"]) for f in fragmentos]
        k_volumen = max(1, round(VOLUMEN / tamano))
        variantes[str(tamano)] = {
            "espacio": espacio,
            "fragmentos": len(fragmentos),
            "longitud_media": round(statistics.mean(largos)),
            "longitud_max": max(largos),
            "sobre_recorte_produccion": sum(1 for x in largos if x > RECORTE_PRODUCCION),
            "caracteres_que_perderia_el_recorte": sum(max(0, x - RECORTE_PRODUCCION) for x in largos),
            "anclas_partidas_en_preguntas": anclas_partidas(fragmentos),
            "tokens_indexado": tokens_indexado,
            "top_5": {"resumen": resumir(filas := medir_dataset(pine, emb, espacio, 5)),
                      "por_pregunta": filas},
            "mismo_volumen": {"k": k_volumen,
                              "resumen": resumir(filas_v := medir_dataset(pine, emb, espacio, k_volumen)),
                              "por_pregunta": filas_v},
            "banda": medir_banda(pine, emb, espacio, 5),
        }
        v = variantes[str(tamano)]
        print(f"\n  {espacio}: {v['fragmentos']} fragmentos, media {v['longitud_media']} car., "
              f"máx {v['longitud_max']}, anclas partidas {v['anclas_partidas_en_preguntas']}")

    despues = vectores_en(pine, produccion)
    print("\n" + "=" * 92)
    print(f"{'':<8}{'top 5: hit@1  hit@3   MRR':<34}{'mismo volumen: k  hit@1  hit@3   MRR':<40}banda")
    for t, v in variantes.items():
        a, b, c = v["top_5"]["resumen"]["todas"], v["mismo_volumen"]["resumen"]["todas"], v["banda"]["analisis"]
        print(f"  {t:<6}       {a['hit_1']:.2f}  {a['hit_3']:.2f}  {a['mrr']:.3f}"
              f"                 {v['mismo_volumen']['k']:>2}  {b['hit_1']:.2f}  {b['hit_3']:.2f}  {b['mrr']:.3f}"
              f"     ruido {c['ruido_maximo']:.3f} señal {c['senal_minima']:.3f}")
    control = variantes.get(str(args.control))
    if control:
        print(f"\n  Con {args.control}: {control['sobre_recorte_produccion']} fragmentos superan los "
              f"{RECORTE_PRODUCCION} caracteres que guarda producción; perderían "
              f"{control['caracteres_que_perderia_el_recorte']} caracteres en total.")
    marca = "" if despues == antes else "   <-- CAMBIÓ"
    print(f"  Producción antes/después: {antes} / {despues}{marca}")

    CARPETA.mkdir(parents=True, exist_ok=True)
    salida = CARPETA / f"{date.today().isoformat()}.json"
    salida.write_text(json.dumps({
        "experimento": "EXP-15",
        "pregunta": "¿Qué tamaño de fragmento recupera mejor, sobre los mismos documentos?",
        "fecha": date.today().isoformat(),
        "commit": version_del_codigo(),
        "dataset": {"archivo": DATASET.name, "sha256": hashlib.sha256(DATASET.read_bytes()).hexdigest()},
        "parametros": {"modelo_embedding": settings.OPENAI_EMBEDDING_MODEL, "umbral": "ninguno",
                       "tamanos": tamanos, "control": args.control, "volumen_igualado": VOLUMEN},
        "corpus": {"espacio_produccion": produccion, "vectores_produccion_antes": antes,
                   "vectores_produccion_despues": despues,
                   "documentos": {i: {"nombre": t["nombre"], "caracteres": len(t["texto"]),
                                      "sha256": t["sha256"]} for i, t in textos.items()},
                   "fragmentos_no_documentales": len(extra)},
        "variantes": variantes,
    }, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"\nResultados en {salida.relative_to(AQUI.parent)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
