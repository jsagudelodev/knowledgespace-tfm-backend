"""Experimento 8 - sube el conjunto de evaluación a Langfuse y lo ejecuta ahí.

Cierra lo único de la petición del tutor que quedaba a medias: las trazas de
Langfuse funcionan desde el 9 de octubre y cada consulta deja su rastro, pero
eso no es lo mismo que «un dataset apuntado contra el RAG» en el sentido que
Langfuse le da al término. Un *dataset* de Langfuse es una colección con
entrada y salida esperada por fila, y una *run* es el resultado de pasar esa
colección entera por una función, con cada traza vinculada automáticamente a
su fila. Es la diferencia entre tener trazas sueltas y poder comparar dos
ejecuciones completas del conjunto de referencia desde la propia interfaz.

**Qué hace este script.**

1. Crea el dataset en Langfuse si no existe —se identifica por nombre, así que
   ejecutar el script dos veces no lo duplica— y sube como fila cada una de las
   dieciocho preguntas de `dataset_evaluacion.csv`, con su tipo y sus anclas
   como metadatos.
2. Ejecuta el dataset contra la configuración indicada usando
   `dataset.run_experiment`, que es la API de alto nivel del SDK 4: por cada
   fila llama a la función de tarea, crea la traza, la vincula al dataset y
   agrupa el conjunto bajo una *run* con nombre y fecha.

**Qué NO hace.** No sustituye a `ejecutar_dataset.py`. Las métricas de
recuperación por frase ancla —hit@k, MRR— y RAGAS siguen calculándose ahí,
porque son deterministas o corren en un entorno aislado y no dependen de que
Langfuse esté activo. Tampoco deja rastro en `cost_tracking`: ese registro vive
en el enrutador del chat, y este script llama al servicio directamente, igual
que el resto de experimentos — decisión deliberada, documentada en
`docs/OBSERVABILIDAD.md`, para no mezclar ejecuciones de evaluación con el
gasto real de una organización. El coste de esta corrida queda visible en la
propia interfaz de Langfuse, consulta por consulta. Este script es la
demostración de que el dataset vive también dentro de Langfuse, apuntado
contra el RAG, que es la pregunta que el
tutor hizo literalmente.

Uso:

    cd api
    .venv\\Scripts\\python.exe experimentos\\langfuse_dataset.py --empresa 8 --asistente 1
"""
from __future__ import annotations

import argparse
import csv
import io
import sys
from pathlib import Path

# La consola de Windows usa cp1252 por defecto, que no sabe mostrar los
# emojis con que `resultado.format()` del SDK de Langfuse adorna su resumen.
# Se reconfigura la salida a UTF-8 en vez de depender de que el sistema la
# tenga ya así: un experimento no debería fallar por cómo se imprime su
# resultado, después de haber gastado ya las llamadas reales al proveedor.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core import observabilidad  # noqa: E402
from app.services.rag_factory import CONFIGURACIONES  # noqa: E402

AQUI = Path(__file__).parent
DATASET = AQUI / "dataset_evaluacion.csv"
NOMBRE_DATASET = "knowledgespace-conjunto-referencia"


def cargar_filas() -> list[dict]:
    with io.open(DATASET, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def asegurar_dataset(cliente) -> None:
    """Crea el dataset y sus filas si no existen aún.

    **Se comprueba con `get_dataset` antes de crear**, en lugar de llamar a
    `create_dataset` y confiar en que el backend lo trate como una operación
    sin efecto si el nombre ya existe: esa idempotencia no está documentada en
    el SDK instalado, y fallar a ciegas sobre un supuesto no verificado habría
    sido la misma clase de error que ya costó caro una vez con la paginación
    de Pinecone. Los ítems sí se comprueban uno a uno por su `id` del CSV en
    los metadatos, para que ejecutar el script más de una vez no acumule
    copias.
    """
    try:
        cliente.get_dataset(NOMBRE_DATASET)
        print(f"Dataset '{NOMBRE_DATASET}' ya existe.")
    except Exception:
        cliente.create_dataset(
            name=NOMBRE_DATASET,
            description=(
                "Las 18 preguntas de experimentos/dataset_evaluacion.csv: 8 de "
                "respuesta literal, 4 de respuesta distribuida y 6 sin respuesta "
                "en el corpus. Construido a mano, con frases ancla verificadas "
                "como únicas en el corpus — ver GUIA_DATASET.md."
            ),
        )
        print(f"Dataset '{NOMBRE_DATASET}' creado.")

    existentes = {
        item.metadata.get("id") for item in cliente.get_dataset(NOMBRE_DATASET).items
        if item.metadata
    }

    filas = cargar_filas()
    nuevas = [f for f in filas if f["id"] not in existentes]
    if not nuevas:
        print(f"Dataset ya tiene sus {len(filas)} filas; no se sube nada nuevo.")
        return

    for fila in nuevas:
        cliente.create_dataset_item(
            dataset_name=NOMBRE_DATASET,
            input=fila["pregunta"],
            # La salida esperada es la frase ancla, no una respuesta completa:
            # es lo único que el propio proyecto verificó como único en el
            # corpus, y es lo que los evaluadores de Langfuse podrían
            # contrastar más adelante sin depender de RAGAS.
            expected_output=fila["ancla"] or None,
            metadata={
                "id": fila["id"],
                "tipo": fila["tipo"],
                "documento": fila["documento"],
                "ancla_2": fila["ancla_2"],
                "notas": fila["notas"],
            },
        )
    print(f"Subidas {len(nuevas)} filas nuevas al dataset '{NOMBRE_DATASET}'.")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--empresa", type=int, required=True)
    ap.add_argument("--asistente", type=int, default=None)
    ap.add_argument("--configuracion", choices=sorted(CONFIGURACIONES), default="base")
    args = ap.parse_args()

    if not observabilidad.activo():
        print("LANGFUSE_ENABLED no está activo. Define las claves en .env y vuelve a intentarlo.")
        return 1

    cliente = observabilidad.cliente()
    asegurar_dataset(cliente)

    clase, etiqueta = CONFIGURACIONES[args.configuracion]
    rag = clase()

    def responder(*, item, **_):
        resultado = rag.generate_response(
            query=item.input, company_id=args.empresa, assistant_id=args.asistente
        )
        return {
            "respuesta": resultado["content"],
            "fuentes": [s["document_name"] for s in resultado["sources"]],
            "tokens_entrada": resultado["input_tokens"],
            "tokens_salida": resultado["output_tokens"],
        }

    dataset = cliente.get_dataset(NOMBRE_DATASET)
    resultado = dataset.run_experiment(
        name=f"knowledgespace-{etiqueta}",
        description=f"Conjunto de referencia contra la configuración '{args.configuracion}'.",
        task=responder,
        metadata={"configuracion": args.configuracion, "empresa": args.empresa},
    )

    observabilidad.volcar()
    print(resultado.format())
    print(f"\nVer en Langfuse: {resultado.dataset_run_url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
