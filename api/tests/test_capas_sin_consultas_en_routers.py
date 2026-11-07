"""Los enrutadores no consultan la base de datos: eso es de los repositorios.

La memoria lo afirma (apartados 3.2 y 4.1) y el 2026-11-07 se encontró que ya
no era del todo cierto: `feedback.py` leía el asistente de un mensaje y
`knowledge_gaps.py` los nombres de asistente y documento directamente. Se
movieron a sus repositorios.

Lo que sí hace un enrutador es cerrar la operación (`db.commit`, `db.refresh`),
y la única excepción a lo anterior es `setup.py`: el arranque inicial crea las
tablas, la primera organización y su superadministrador antes de que exista
nada que un repositorio pueda gestionar.
"""
import re
from pathlib import Path

ROUTERS = Path(__file__).resolve().parents[1] / "app" / "routers" / "v1"
LECTURA_DIRECTA = re.compile(r"\bdb\.(query|get|execute|add|add_all|delete|scalar|scalars)\s*\(")
EXCEPCIONES = {"setup.py"}


def test_ningun_enrutador_lee_ni_escribe_la_base_de_datos_directamente():
    culpables = [
        f"{f.name}:{n}"
        for f in sorted(ROUTERS.glob("*.py"))
        if f.name not in EXCEPCIONES
        for n, linea in enumerate(f.read_text(encoding="utf-8").splitlines(), 1)
        if LECTURA_DIRECTA.search(linea) and not linea.lstrip().startswith("#")
    ]
    assert culpables == []
