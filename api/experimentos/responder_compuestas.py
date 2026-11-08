"""EXP-13, parte B - respuestas a las preguntas compuestas.

EXP-05 y EXP-08 midieron qué fragmentos llegan al modelo cuando el mensaje
trae dos preguntas, pero nunca generaron la respuesta. Este script la genera
con cada configuración y le pregunta a un juez qué hizo con cada parte (ver
`juez_compuestas.py`). Es la medición que decide entre la descomposición sin
tope y la acotada: en el conjunto de referencia las dos son indistinguibles
(EXP-13, parte A), porque casi no tiene preguntas compuestas.

**Las mismas seis parejas que EXP-03**, unidas con "y" exactamente igual, para
que las cifras de recuperación de aquel experimento y estas respuestas
describan las mismas consultas.

**Repeticiones.** La misma configuración cambia de fragmentos y de respuesta de
un día para otro (EXP-13, parte A), así que una sola pasada no distingue una
diferencia real de la variación normal. Cada configuración se ejecuta varias
veces, y dentro de cada repetición se alternan las configuraciones para que
cualquier deriva en el tiempo les afecte por igual.

**Mide el pipeline de producción.** Usa `generate_response` como el chat, con
temperatura 0. El juez es otro modelo (gpt-4.1 por defecto), con cliente
propio para que sus llamadas no se mezclen con las trazas del RAG.

Escribe dos archivos en `5-descomposicion/EXP-13_descomposicion-con-o-sin-tope/resultados/`:
el JSON con todo y un Markdown con las respuestas, para leerlas una por una.

Coste aproximado con los valores por defecto: unos 0,30 USD, casi todo del
juez, que lee el contexto completo de cada respuesta.

Uso:

    cd api
    .venv\\Scripts\\python.exe experimentos\\responder_compuestas.py --empresa 8 --asistente 1
"""
from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import sys
import time
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any, Dict, List

AQUI = Path(__file__).parent
sys.path.insert(0, str(AQUI.parent))
sys.path.insert(0, str(AQUI))

from juez_compuestas import construir_prompt, interpretar, responde_ambas  # noqa: E402
from medir_preguntas_compuestas import PAREJAS  # noqa: E402
from openai import OpenAI  # noqa: E402

from app.core import observabilidad  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.services.pinecone_service import PineconeService  # noqa: E402
from app.services.rag_factory import CONFIGURACIONES  # noqa: E402

CARPETA = AQUI / "5-descomposicion" / "EXP-13_descomposicion-con-o-sin-tope" / "resultados"


def version_del_codigo() -> str:
    """Commit actual, marcado si hay cambios sin confirmar: un resultado sin
    la versión del código que lo produjo no se puede reproducir."""
    raiz = AQUI.parent.parent
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=raiz,
                            capture_output=True, text=True).stdout.strip()
    sucio = subprocess.run(["git", "status", "--porcelain"], cwd=raiz,
                           capture_output=True, text=True).stdout.strip()
    return f"{commit}+cambios-locales" if sucio else commit


def juzgar(juez: OpenAI, modelo: str, par: Dict[str, str], r: Dict[str, Any]) -> Dict[str, Any]:
    texto = juez.chat.completions.create(
        model=modelo, temperature=0,
        messages=[{"role": "user", "content": construir_prompt(
            par["a"], par["b"], r["contexts"], r["content"])}],
    ).choices[0].message.content
    return {**interpretar(texto), "texto_juez": texto}


def ejecutar(empresa: int, asistente: int, configuraciones: List[str], repeticiones: int,
             temperatura: float, modelo_juez: str) -> List[Dict[str, Any]]:
    juez = OpenAI(api_key=settings.OPENAI_API_KEY)
    filas = []
    for rep in range(1, repeticiones + 1):
        print(f"\nRepetición {rep}/{repeticiones}")
        for n, par in enumerate(PAREJAS, start=1):
            compuesta = f"{par['a']} y {par['b']}"
            for nombre in configuraciones:
                clase, _ = CONFIGURACIONES[nombre]
                t0 = time.perf_counter()
                r = clase().generate_response(
                    query=compuesta, company_id=empresa, assistant_id=asistente,
                    temperature_override=temperatura,
                )
                latencia = round(time.perf_counter() - t0, 3)
                veredicto = juzgar(juez, modelo_juez, par, r)
                auxiliares = sum(c["tokens_entrada"] + c["tokens_salida"]
                                 for c in r["llamadas_auxiliares"])
                filas.append({
                    "repeticion": rep,
                    "pareja": n,
                    "configuracion": nombre,
                    "a": par["a"],
                    "b": par["b"],
                    "pregunta": compuesta,
                    "respuesta": r["content"],
                    "contextos": r["contexts"],
                    "fragmentos": len(r["contexts"]),
                    "tokens_entrada": r["input_tokens"],
                    "tokens_salida": r["output_tokens"],
                    "tokens_auxiliares": auxiliares,
                    "latencia_s": latencia,
                    "veredicto": veredicto,
                })
                print(f"  P{n} {nombre:<24} {len(r['contexts']):>2} frag.  "
                      f"A={veredicto['a']}  B={veredicto['b']}  inventa={veredicto['inventa']}")
    observabilidad.volcar()
    return filas


def resumir(filas: List[Dict[str, Any]], configuraciones: List[str]) -> Dict[str, Any]:
    resumen = {}
    for nombre in configuraciones:
        grupo = [f for f in filas if f["configuracion"] == nombre]
        partes = Counter(f["veredicto"][p] for f in grupo for p in ("a", "b"))
        resumen[nombre] = {
            "respuestas": len(grupo),
            "responde_ambas": sum(responde_ambas(f["veredicto"]) for f in grupo),
            "partes": {t: partes.get(t, 0) for t in ("responde", "abstiene", "omite")},
            "partes_ilegibles": partes.get(None, 0),
            "inventa": sum(f["veredicto"]["inventa"] is True for f in grupo),
            "fragmentos_medio": round(statistics.mean(f["fragmentos"] for f in grupo), 2),
            "tokens_medio": round(statistics.mean(
                f["tokens_entrada"] + f["tokens_salida"] + f["tokens_auxiliares"] for f in grupo)),
            "latencia_p50_s": round(statistics.median(f["latencia_s"] for f in grupo), 2),
            # Por pareja: cuántas de las repeticiones respondieron las dos
            # partes. Distingue un fallo sistemático de uno ocasional.
            "ambas_por_pareja": {
                n: sum(responde_ambas(f["veredicto"]) for f in grupo if f["pareja"] == n)
                for n in sorted({f["pareja"] for f in grupo})
            },
        }
    return resumen


def imprimir(resumen: Dict[str, Any], repeticiones: int) -> None:
    print("\n" + "=" * 74)
    print("RESPUESTAS A PREGUNTAS COMPUESTAS")
    print("=" * 74)
    for nombre, r in resumen.items():
        print(f"\n  {nombre}")
        print(f"    responde las dos partes : {r['responde_ambas']}/{r['respuestas']}")
        print(f"    partes                  : {r['partes']}  ilegibles={r['partes_ilegibles']}")
        print(f"    inventa                 : {r['inventa']}/{r['respuestas']}")
        print(f"    fragmentos / tokens     : {r['fragmentos_medio']} / {r['tokens_medio']}")
        print(f"    latencia p50            : {r['latencia_p50_s']} s")
        print(f"    ambas por pareja (de {repeticiones}) : {r['ambas_por_pareja']}")


def escribir_markdown(filas: List[Dict[str, Any]], configuraciones: List[str], ruta: Path) -> None:
    """Las respuestas agrupadas por pareja y configuración, para leerlas.

    Las repeticiones con la misma respuesta se muestran una sola vez con su
    recuento: lo que interesa leer es qué respuestas distintas da el sistema.
    """
    lineas = [f"# EXP-13, parte B — respuestas ({date.today().isoformat()})", ""]
    for n in sorted({f["pareja"] for f in filas}):
        primera = next(f for f in filas if f["pareja"] == n)
        lineas += [f"## P{n}. «{primera['pregunta']}»", ""]
        for nombre in configuraciones:
            grupo = [f for f in filas if f["pareja"] == n and f["configuracion"] == nombre]
            lineas += [f"### {nombre}", ""]
            distintas: Dict[str, List[Dict[str, Any]]] = {}
            for f in grupo:
                distintas.setdefault(f["respuesta"], []).append(f)
            for respuesta, iguales in distintas.items():
                v = iguales[0]["veredicto"]
                reps = ", ".join(str(f["repeticion"]) for f in iguales)
                lineas += [
                    f"**Repeticiones {reps}** · {iguales[0]['fragmentos']} fragmentos · "
                    f"A: {v['a']} · B: {v['b']} · inventa: {v['inventa']}",
                    "",
                    f"> {respuesta.strip()}".replace("\n", "\n> "),
                    "",
                    f"*Juez:* {v['motivo']}",
                    "",
                ]
    ruta.write_text("\n".join(lineas), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--empresa", type=int, required=True)
    ap.add_argument("--asistente", type=int, default=None)
    ap.add_argument("--configuraciones", default="descomposicion,descomposicion_acotada",
                    help="separadas por coma")
    ap.add_argument("--repeticiones", type=int, default=3)
    ap.add_argument("--temperatura", type=float, default=0.0)
    ap.add_argument("--juez", default="gpt-4.1", help="modelo juez")
    args = ap.parse_args()

    configuraciones = args.configuraciones.split(",")
    for c in configuraciones:
        if c not in CONFIGURACIONES:
            ap.error(f"configuración desconocida: {c}")

    version = version_del_codigo()
    filas = ejecutar(args.empresa, args.asistente, configuraciones, args.repeticiones,
                     args.temperatura, args.juez)
    resumen = resumir(filas, configuraciones)
    imprimir(resumen, args.repeticiones)

    CARPETA.mkdir(parents=True, exist_ok=True)
    base = CARPETA / f"{date.today().isoformat()}_parte-b"
    base.with_suffix(".json").write_text(json.dumps({
        "experimento": "EXP-13",
        "parte": "B — respuestas a preguntas compuestas",
        "fecha": date.today().isoformat(),
        "commit": version,
        "parametros": {
            "configuraciones": configuraciones,
            "repeticiones": args.repeticiones,
            "temperatura": args.temperatura,
            "modelo_generador": settings.OPENAI_CHAT_MODEL,
            "modelo_embedding": settings.OPENAI_EMBEDDING_MODEL,
            "top_k": settings.RAG_TOP_K,
            "modelo_juez": args.juez,
        },
        "corpus": {"namespace": PineconeService.construir_namespace(args.empresa, args.asistente)},
        "parejas": PAREJAS,
        "resumen": resumen,
        "resultados": filas,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    escribir_markdown(filas, configuraciones, base.with_suffix(".md"))
    print(f"\nResultados en {base.with_suffix('.json').relative_to(AQUI.parent)}")
    print(f"Respuestas para leer en {base.with_suffix('.md').relative_to(AQUI.parent)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
