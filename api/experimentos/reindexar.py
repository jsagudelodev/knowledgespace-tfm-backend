"""Reindexa documentos ejecutando el pipeline de ingesta de produccion.

Reconstruye los vectores de uno o varios documentos con la configuracion
ACTUAL del codigo: fragmentacion por oraciones y el namespace que construye
`PineconeService.construir_namespace`. Sirve para resincronizar el indice
cuando cambia la estrategia de fragmentacion o el esquema de nombres, que es
justo lo que ocurrio en este proyecto (ver `docs/NUCLEO_RAG.md` seccion 0).

**Usa el pipeline de produccion, no una copia.** Importa
`_procesar_documento_background` de `routers/v1/documents.py`, la misma funcion
que corre al subir un documento o al pulsar "Reintentar procesamiento".

Uso:

    cd api
    .venv\\Scripts\\python.exe experimentos\\reindexar.py --listar
    .venv\\Scripts\\python.exe experimentos\\reindexar.py --docs 28,30,31,32
    .venv\\Scripts\\python.exe experimentos\\reindexar.py --asistente 1

Cada documento reindexado cuesta sus embeddings. Para el corpus completo de
este proyecto son decimas de centimo.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text  # noqa: E402

from app.core.database import SessionLocal  # noqa: E402
from app.routers.v1.documents import _procesar_documento_background  # noqa: E402
from app.services.pinecone_service import PineconeService  # noqa: E402

CONSULTA = """
    SELECT id, original_filename, filename, file_path, company_id,
           assistant_id, uploaded_by, chunk_count
    FROM documents
    WHERE {filtro}
    ORDER BY id
"""


def documentos(filtro: str, params: dict):
    db = SessionLocal()
    try:
        return list(db.execute(text(CONSULTA.format(filtro=filtro)), params))
    finally:
        db.close()


def vectores_por_namespace() -> dict:
    p = PineconeService()
    stats = p.pc.Index(p.nombre_indice).describe_index_stats()
    return {ns: info["vector_count"] for ns, info in stats.get("namespaces", {}).items()}


def listar(asistente: int) -> None:
    print(f"Documentos del asistente {asistente}:\n")
    total = 0
    for d in documentos("assistant_id = :a", {"a": asistente}):
        total += d.chunk_count or 0
        ns = PineconeService.construir_namespace(d.company_id, d.assistant_id)
        print(f"  id={d.id:<4} {str(d.original_filename)[:44]:<46} "
              f"chunks={d.chunk_count or 0:<4} namespace={ns}")
    print(f"\n  Suma de chunk_count en la base: {total}")
    print("\nVectores por namespace en Pinecone:")
    for ns, n in sorted(vectores_por_namespace().items()):
        print(f"  {ns:<34} {n}")


def reindexar(ids: list[int]) -> None:
    filas = documentos("id = ANY(:ids)", {"ids": ids})
    encontrados = {d.id for d in filas}
    for faltante in sorted(set(ids) - encontrados):
        print(f"  AVISO: el documento {faltante} no existe en la base")

    print(f"\nReindexando {len(filas)} documento(s)...\n")
    for d in filas:
        antes = d.chunk_count or 0
        extension = d.filename.split(".")[-1].lower()
        print(f"  id={d.id:<4} {str(d.original_filename)[:40]:<42} ", end="", flush=True)
        try:
            _procesar_documento_background(
                document_id=d.id,
                s3_key=d.file_path,
                file_type=extension,
                company_id=d.company_id,
                assistant_id=d.assistant_id,
                original_filename=d.original_filename,
                uploaded_by=d.uploaded_by,
            )
        except Exception as e:  # noqa: BLE001
            print(f"ERROR: {e}")
            continue

        db = SessionLocal()
        try:
            ahora = db.execute(
                text("SELECT chunk_count FROM documents WHERE id = :i"), {"i": d.id}
            ).scalar()
        finally:
            db.close()
        flecha = "=" if ahora == antes else "->"
        print(f"chunks {antes} {flecha} {ahora}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--docs", help="ids separados por coma, p. ej. 28,30,31")
    ap.add_argument("--asistente", type=int, help="reindexa todos los de un asistente")
    ap.add_argument("--listar", action="store_true", help="solo muestra el estado")
    args = ap.parse_args()

    if args.listar:
        listar(args.asistente or 1)
        return 0

    if args.docs:
        ids = [int(x) for x in args.docs.split(",") if x.strip()]
    elif args.asistente:
        ids = [d.id for d in documentos("assistant_id = :a", {"a": args.asistente})]
    else:
        ap.error("indica --docs, --asistente o --listar")
        return 1

    antes = vectores_por_namespace()
    reindexar(ids)
    despues = vectores_por_namespace()

    print("\nVectores por namespace (antes -> despues):")
    for ns in sorted(set(antes) | set(despues)):
        a, b = antes.get(ns, 0), despues.get(ns, 0)
        marca = "" if a == b else "   <-- cambio"
        print(f"  {ns:<34} {a:>5} -> {b:>5}{marca}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
