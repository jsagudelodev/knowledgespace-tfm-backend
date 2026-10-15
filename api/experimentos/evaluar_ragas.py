"""Experimento 5b - evaluacion con RAGAS.

Segunda mitad de la evaluacion. Lee el JSON que produce `ejecutar_dataset.py` y
calcula las cuatro metricas de RAGAS sobre las 12 preguntas con respuesta en el
corpus.

**Se ejecuta en `.venv-eval`, no en el entorno de la aplicacion.** RAGAS arrastra
mas de sesenta dependencias —LangChain, LangGraph, pandas, numpy, scipy,
pyarrow, datasets, huggingface-hub— y ademas cambiaria la version de tres
paquetes que la API ya usa, entre ellos `pydantic-settings`, del que depende la
carga de configuracion. Imponer todo eso a un servicio de veinte dependencias no
esta justificado: la evaluacion no es parte del producto.

De ahi que el flujo sea en dos pasos y que la comunicacion entre ambos sea un
fichero:

    .venv        ejecutar_dataset.py   ->  dataset_ejecutado_AAAA-MM-DD.json
    .venv-eval   evaluar_ragas.py      ->  ragas_AAAA-MM-DD.json

**Las metricas.** Dos miden cada mitad del pipeline:

    RECUPERACION    context_precision   de lo recuperado, cuanto servia
                    context_recall      de lo necesario, cuanto se recupero

    GENERACION      faithfulness        la respuesta se apoya en el contexto
                    answer_relevancy    la respuesta contesta la pregunta

`faithfulness` es la que el tutor pidio como control minimo de alucinaciones:
descompone la respuesta en afirmaciones y verifica cada una contra el contexto
recuperado.

**Las preguntas `sin_respuesta` se excluyen.** Su respuesta correcta es la
abstencion, y medir la fidelidad de "no encontre informacion" respecto de un
contexto vacio no significa nada. Esas se evaluan con la tasa de abstencion
correcta, que calcula `ejecutar_dataset.py` y que dio el 100 %.

**Limitacion que hay que declarar:** RAGAS emplea un LLM como juez, es decir, un
modelo evaluando a otro modelo. Es la practica estandar del campo y es lo que
se pidio, pero introduce su propio sesgo y figura como limitacion en el
capitulo 5.

Uso:

    cd api
    .venv-eval\\Scripts\\python.exe experimentos\\evaluar_ragas.py
    .venv-eval\\Scripts\\python.exe experimentos\\evaluar_ragas.py --entrada resultados\\dataset_ejecutado_2026-10-11.json
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
from datetime import date
from pathlib import Path
from typing import Any, Dict, List

AQUI = Path(__file__).parent
RESULTADOS = AQUI / "resultados"


def cargar_clave() -> str:
    """Lee OPENAI_API_KEY del .env de la aplicacion.

    Este entorno no tiene pydantic-settings ni el paquete `app`, asi que se
    hace a mano: solo se necesita una variable.
    """
    env = AQUI.parent / ".env"
    if "OPENAI_API_KEY" in os.environ:
        return os.environ["OPENAI_API_KEY"]
    if env.exists():
        for linea in env.read_text(encoding="utf-8").splitlines():
            if linea.strip().startswith("OPENAI_API_KEY="):
                valor = linea.split("=", 1)[1].strip().strip('"').strip("'")
                os.environ["OPENAI_API_KEY"] = valor
                return valor
    raise SystemExit("No se encontró OPENAI_API_KEY ni en el entorno ni en api/.env")


def ultimo_json() -> Path:
    candidatos = sorted(RESULTADOS.glob("dataset_ejecutado_*.json"))
    if not candidatos:
        raise SystemExit("No hay ningún dataset_ejecutado_*.json. Ejecuta antes ejecutar_dataset.py")
    return candidatos[-1]


def construir_muestras(datos: Dict[str, Any]) -> List[Any]:
    from ragas.dataset_schema import SingleTurnSample

    muestras = []
    for r in datos["resultados"]:
        if r["tipo"] == "sin_respuesta":
            continue
        muestras.append(SingleTurnSample(
            user_input=r["pregunta"],
            response=r["respuesta"],
            retrieved_contexts=r["contextos"],
            reference=r["referencia"],
        ))
    return muestras


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--entrada", help="JSON de ejecutar_dataset.py (por defecto, el más reciente)")
    ap.add_argument("--modelo", default="gpt-4o-mini", help="modelo juez")
    args = ap.parse_args()

    cargar_clave()

    entrada = Path(args.entrada) if args.entrada else ultimo_json()
    if not entrada.is_absolute():
        entrada = AQUI / entrada
    datos = json.loads(entrada.read_text(encoding="utf-8"))
    print(f"Entrada: {entrada.name}  ({datos['fecha']})")

    from langchain_openai import ChatOpenAI, OpenAIEmbeddings
    from ragas import EvaluationDataset, evaluate
    from ragas.llms import LangchainLLMWrapper
    from ragas.embeddings import LangchainEmbeddingsWrapper
    from ragas.metrics import (
        Faithfulness,
        ResponseRelevancy,
        LLMContextPrecisionWithReference,
        LLMContextRecall,
    )

    juez = LangchainLLMWrapper(ChatOpenAI(model=args.modelo, temperature=0))
    emb = LangchainEmbeddingsWrapper(OpenAIEmbeddings(model="text-embedding-3-small"))

    muestras = construir_muestras(datos)
    print(f"Evaluando {len(muestras)} preguntas con respuesta "
          f"(se excluyen las sin_respuesta)\n")

    metricas = [
        LLMContextPrecisionWithReference(llm=juez),
        LLMContextRecall(llm=juez),
        Faithfulness(llm=juez),
        ResponseRelevancy(llm=juez, embeddings=emb),
    ]

    resultado = evaluate(dataset=EvaluationDataset(samples=muestras), metrics=metricas)
    df = resultado.to_pandas()

    # ── Resumen ─────────────────────────────────────────────────────────────
    # RAGAS nombra las columnas segun la clase de metrica, no segun su nombre
    # corto: `LLMContextPrecisionWithReference` produce
    # `llm_context_precision_with_reference`. Filtrar por nombres exactos deja
    # fuera metricas calculadas sin avisar, asi que se seleccionan por patron.
    IGNORAR = {"user_input", "response", "reference", "retrieved_contexts"}
    cols = [c for c in df.columns
            if c not in IGNORAR and df[c].dtype.kind in "fi"]

    print()
    print("=" * 74)
    print("LINEA BASE — Naive RAG con filtro por umbral")
    print("=" * 74)
    for c in cols:
        serie = df[c].dropna()
        print(f"  {c:<22} {serie.mean():.3f}   (n={len(serie)})")

    # Por tipo de pregunta
    tipos = [r["tipo"] for r in datos["resultados"] if r["tipo"] != "sin_respuesta"]
    df = df.assign(tipo=tipos)
    print()
    print("  Por tipo de pregunta:")
    for t in ("literal", "multi"):
        sub = df[df["tipo"] == t]
        if sub.empty:
            continue
        linea = "  ".join(f"{c}={sub[c].dropna().mean():.3f}" for c in cols)
        print(f"    {t:<9} n={len(sub)}  {linea}")

    # ── Peores casos ────────────────────────────────────────────────────────
    if "faithfulness" in cols:
        print()
        print("  Menor fidelidad:")
        ids = [r["id"] for r in datos["resultados"] if r["tipo"] != "sin_respuesta"]
        df = df.assign(id=ids)
        for _, fila in df.nsmallest(3, "faithfulness").iterrows():
            print(f"    P{fila['id']}  faithfulness={fila['faithfulness']:.3f}  "
                  f"{str(fila['user_input'])[:46]}")

    # El nombre arrastra la configuracion que se evaluo. Antes era solo la
    # fecha, y evaluar dos configuraciones el mismo dia sobrescribia la
    # primera: se perdio asi una linea base que hubo que recuperar de git.
    # La configuracion sale del propio JSON de entrada, no de aqui, para que
    # no puedan divergir.
    config = datos.get("configuracion", "desconocida")
    salida = RESULTADOS / f"ragas_{date.today().isoformat()}_{config}.json"
    salida.write_text(json.dumps({
        "fecha": date.today().isoformat(),
        "entrada": entrada.name,
        "modelo_juez": args.modelo,
        "configuracion": config,
        "n_preguntas": len(muestras),
        "promedios": {c: float(df[c].dropna().mean()) for c in cols},
        "por_pregunta": df.to_dict(orient="records"),
    }, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"\nResultados en {salida.relative_to(AQUI.parent)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
