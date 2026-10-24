"""Experimento 5a - ejecuta el dataset de evaluacion contra el RAG.

Primera mitad de la evaluacion. Lanza las preguntas de
`dataset_evaluacion.csv` (18 en el dataset original, 27 desde que se amplio)
contra el pipeline de produccion y guarda, por cada
una, lo que el sistema respondio y que fragmentos recupero. El resultado
alimenta tres cosas distintas:

  1. **RAGAS**, que se ejecuta aparte, en `.venv-eval`, porque sus mas de
     sesenta dependencias no deben imponerse al servicio (ver
     `evaluar_ragas.py`).
  2. **Las metricas de recuperacion por frase ancla** —hit@1, hit@3 y MRR—,
     que se calculan aqui mismo: son deterministas, no necesitan modelo juez y
     no cuestan nada.
  3. **La latencia p50 y p95**, que sale gratis de cronometrar cada consulta.

**Mide el pipeline de produccion.** Importa `RAGService` y llama a
`generate_response` tal cual, con los mismos parametros que usa el chat.

**El emparejamiento del ancla** se hace sobre texto normalizado —espacios
colapsados y minusculas— porque la extraccion del PDF introduce saltos de
linea dentro de las frases. No se quitan las tildes: el corpus escribe
"Euclidia" y "Euclidea" en documentos distintos y son terminos diferentes.

Coste: una consulta completa al RAG por pregunta. Las 18 originales costaron
unos 0,008 USD segun las mediciones de `cost_tracking`. Se registran ademas en
esa tabla, como cualquier consulta.

Uso:

    cd api
    .venv\\Scripts\\python.exe experimentos\\ejecutar_dataset.py --empresa 8 --asistente 1
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import re
import statistics
import sys
import time
from datetime import date
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core import observabilidad  # noqa: E402

# Las tres configuraciones comparables se definen en el propio servicio, no
# aqui: la etiqueta viaja al JSON de resultados y de ahi al nombre del fichero
# de RAGAS, de modo que lo que se mide y lo que atiende al usuario no pueden
# describirse de dos maneras distintas.
from app.services.rag_factory import CONFIGURACIONES  # noqa: E402

AQUI = Path(__file__).parent
DATASET = AQUI / "dataset_evaluacion.csv"
ABSTENCION = "No encontré información sobre este tema en los documentos de la empresa."


def normalizar(texto: str) -> str:
    """Colapsa espacios y pasa a minusculas. No toca las tildes."""
    return re.sub(r"\s+", " ", texto or "").strip().lower()


def posicion_del_ancla(ancla: str, contextos: List[str]) -> int:
    """Posicion (1-based) del primer fragmento que contiene el ancla, o 0."""
    objetivo = normalizar(ancla)
    if not objetivo:
        return 0
    for i, c in enumerate(contextos, start=1):
        if objetivo in normalizar(c):
            return i
    return 0


def evaluar_anclas(fila: Dict[str, str], contextos: List[str]) -> Dict[str, Any]:
    """Metricas de recuperacion por frase ancla.

    En las preguntas `multi` el acierto exige LAS DOS anclas entre los
    fragmentos recuperados: si bastara una, se estaria midiendo lo mismo que
    una `literal` y la categoria no aportaria nada.
    """
    anclas = [a for a in (fila["ancla"], fila["ancla_2"]) if a.strip()]
    if not anclas:
        return {"aplica": False}

    posiciones = [posicion_del_ancla(a, contextos) for a in anclas]
    encontradas = [p for p in posiciones if p > 0]
    todas = len(encontradas) == len(anclas)

    # MRR sobre la ultima ancla necesaria: en una `multi`, la respuesta no esta
    # completa hasta que aparece la segunda.
    peor = max(posiciones) if todas else 0

    # `hit_5` compara contra la posicion 5, no contra "aparecio en alguna
    # parte".
    #
    # **Era `todas` a secas y eso lo hacia tramposo.** Con cinco fragmentos
    # ambas cosas coinciden, pero una configuracion que devuelva nueve tiene
    # nueve sitios donde encontrar el ancla y puntuaria mejor sin recuperar
    # mejor: la metrica premiaba el exceso de contexto, que es justo lo que se
    # queria evitar. Ninguna cifra publicada se vio afectada --todas las
    # comparaciones del capitulo 5 se midieron con cinco fragmentos-- pero el
    # defecto estaba latente.
    #
    # Se conserva `hallada` para distinguir "no se recupero" de "se recupero
    # pero mas abajo del quinto puesto", que son fallos distintos.
    return {
        "aplica": True,
        "anclas": len(anclas),
        "posiciones": posiciones,
        "encontradas": len(encontradas),
        "hit_1": todas and peor == 1,
        "hit_3": todas and peor <= 3,
        "hit_5": todas and peor <= 5,
        "hallada": todas,
        "fragmentos_vistos": len(contextos),
        "rr": round(1 / peor, 3) if peor else 0.0,
    }


def ejecutar(empresa: int, asistente: int, configuracion: str = "base",
             temperatura: float = None) -> Dict[str, Any]:
    with io.open(DATASET, encoding="utf-8", newline="") as f:
        filas = list(csv.DictReader(f))

    clase, config = CONFIGURACIONES[configuracion]
    rag = clase()
    # La temperatura forma parte de la configuracion medida: una fidelidad no
    # significa lo mismo a 0 que a 0,7. Si no se indica, se usa la del servicio.
    if temperatura is not None:
        config += f"_temp{temperatura}"
    resultados = []

    print(f"Ejecutando {len(filas)} preguntas contra el RAG [{config}]...\n")
    for fila in filas:
        t0 = time.perf_counter()
        r = rag.generate_response(
            query=fila["pregunta"], company_id=empresa, assistant_id=asistente,
            temperature_override=temperatura,
        )
        latencia = round(time.perf_counter() - t0, 3)

        contextos = r.get("contexts", [])
        anclas = evaluar_anclas(fila, contextos)
        respuesta = r["content"]
        se_abstuvo = normalizar(ABSTENCION) in normalizar(respuesta)

        resultados.append({
            "id": int(fila["id"]),
            "pregunta": fila["pregunta"],
            "tipo": fila["tipo"],
            "documento": fila["documento"],
            "respuesta": respuesta,
            "referencia": fila["respuesta_referencia"],
            "contextos": contextos,
            "fuentes": [s["document_name"] for s in r["sources"]],
            "scores": [s["score"] for s in r["sources"]],
            "anclas": anclas,
            "se_abstuvo": se_abstuvo,
            "latencia_s": latencia,
            "tokens_entrada": r["input_tokens"],
            "tokens_salida": r["output_tokens"],
            "notas": fila["notas"],
        })

        marca = "ABSTIENE" if se_abstuvo else f"{len(contextos)} frag."
        extra = ""
        if anclas["aplica"]:
            extra = f"  anclas {anclas['encontradas']}/{anclas['anclas']} pos={anclas['posiciones']}"
        print(f"  {int(fila['id']):>2}. {fila['tipo']:<14} {marca:<10} {latencia:>5.2f}s{extra}")

    observabilidad.volcar()
    return {"fecha": date.today().isoformat(), "configuracion": config, "resultados": resultados}


def resumir(datos: Dict[str, Any]) -> None:
    res = datos["resultados"]
    con_ancla = [r for r in res if r["anclas"]["aplica"]]
    sin_resp = [r for r in res if r["tipo"] == "sin_respuesta"]
    lat = sorted(r["latencia_s"] for r in res)

    print()
    print("=" * 74)
    print("RECUPERACION (por frase ancla, determinista)")
    print("=" * 74)
    # Un grupo por tipo, en el orden del dataset: un tipo nuevo aparece en el
    # informe sin tener que añadirlo a mano.
    grupos = [("todas", con_ancla)] + [
        (t, [r for r in con_ancla if r["tipo"] == t])
        for t in dict.fromkeys(r["tipo"] for r in con_ancla)
    ]
    for etiqueta, grupo in grupos:
        if not grupo:
            continue
        n = len(grupo)
        print(f"  {etiqueta:<14} n={n:<3} "
              f"hit@1={sum(r['anclas']['hit_1'] for r in grupo)/n:.2f}  "
              f"hit@3={sum(r['anclas']['hit_3'] for r in grupo)/n:.2f}  "
              f"hit@5={sum(r['anclas']['hit_5'] for r in grupo)/n:.2f}  "
              f"MRR={sum(r['anclas']['rr'] for r in grupo)/n:.3f}")

    print()
    print("=" * 74)
    print("ABSTENCION (control de alucinaciones)")
    print("=" * 74)
    aciertos = sum(r["se_abstuvo"] for r in sin_resp)
    print(f"  Preguntas sin respuesta en el corpus : {len(sin_resp)}")
    print(f"  El sistema se abstuvo en             : {aciertos}")
    print(f"  Tasa de abstencion correcta          : {aciertos/len(sin_resp):.0%}")
    fallos = [r for r in sin_resp if not r["se_abstuvo"]]
    for r in fallos:
        print(f"    NO se abstuvo -> {r['id']}. {r['pregunta'][:58]}")
        print(f"       scores={r['scores']}")
    falsas = [r for r in res if r["tipo"] != "sin_respuesta" and r["se_abstuvo"]]
    for r in falsas:
        print(f"    se abstuvo teniendo respuesta -> {r['id']}. {r['pregunta'][:48]}")

    print()
    print("=" * 74)
    print("LATENCIA")
    print("=" * 74)
    print(f"  p50 = {statistics.median(lat):.2f}s    "
          f"p95 = {lat[int(len(lat) * 0.95) - 1]:.2f}s    "
          f"max = {lat[-1]:.2f}s")

    print()
    tok = sum(r["tokens_entrada"] + r["tokens_salida"] for r in res)
    print(f"  Tokens totales: {tok:,}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--empresa", type=int, required=True)
    ap.add_argument("--asistente", type=int, default=None)
    ap.add_argument("--configuracion", choices=sorted(CONFIGURACIONES), default="base",
                    help="qué clase de recuperación se mide")
    ap.add_argument("--temperatura", type=float, default=None,
                    help="fuerza la temperatura del modelo generativo "
                         "(por defecto, la del servicio)")
    args = ap.parse_args()

    datos = ejecutar(args.empresa, args.asistente, args.configuracion, args.temperatura)
    resumir(datos)

    sufijo = "" if args.configuracion == "base" else f"_{args.configuracion}"
    if args.temperatura is not None:
        sufijo += f"_temp{args.temperatura}"
    salida = AQUI / "resultados" / f"dataset_ejecutado_{date.today().isoformat()}{sufijo}.json"
    salida.parent.mkdir(exist_ok=True)
    salida.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nResultados en {salida.relative_to(AQUI.parent)}")
    print("Siguiente paso: evaluar_ragas.py, desde .venv-eval")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
