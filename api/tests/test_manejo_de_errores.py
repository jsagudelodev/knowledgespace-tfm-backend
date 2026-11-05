"""Manejo global de errores: siempre JSON, 503 si falla un proveedor, y nunca
el detalle técnico en la respuesta.

Se monta una app mínima con los mismos manejadores que `main.py` en vez de la
app real, porque el arranque de esta conecta con Pinecone.
"""
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

import main
from app.core.error_handlers import MENSAJE_500, MENSAJE_503, registrar_manejadores
from app.core.exceptions import EmbeddingError, StorageError, VectorStoreError

SECRETO = "s3://bucket-interno/empresa-8/clave.pdf NoSuchKey"


@pytest.fixture
def cliente():
    app = FastAPI()
    registrar_manejadores(app)

    @app.get("/storage")
    def storage():
        raise StorageError(SECRETO)

    @app.get("/vectores")
    def vectores():
        raise VectorStoreError(SECRETO)

    @app.get("/embedding")
    def embedding():
        raise EmbeddingError(SECRETO)

    @app.get("/bug")
    def bug():
        raise KeyError(SECRETO)

    @app.get("/no-existe")
    def no_existe():
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    # raise_server_exceptions=False: así el cliente recibe la respuesta del
    # manejador de 500 en vez de relanzar la excepción en el test.
    return TestClient(app, raise_server_exceptions=False)


@pytest.mark.parametrize("ruta", ["/storage", "/vectores", "/embedding"])
def test_un_proveedor_caido_da_503_en_json(cliente, ruta):
    r = cliente.get(ruta)
    assert r.status_code == 503
    assert r.json() == {"detail": MENSAJE_503}


def test_un_error_no_previsto_da_500_en_json_no_texto_plano(cliente):
    r = cliente.get("/bug")
    assert r.status_code == 500
    assert r.headers["content-type"].startswith("application/json")
    assert r.json() == {"detail": MENSAJE_500}


@pytest.mark.parametrize("ruta", ["/storage", "/bug"])
def test_la_respuesta_no_filtra_el_detalle_tecnico(cliente, ruta):
    assert "bucket-interno" not in cliente.get(ruta).text


def test_el_error_queda_en_el_log_con_la_ruta(cliente, caplog):
    with caplog.at_level("ERROR", logger="uvicorn.error"):
        cliente.get("/storage")
    assert any("StorageError" in m and "/storage" in m for m in caplog.messages)


def test_las_httpexception_siguen_respondiendo_como_siempre(cliente):
    r = cliente.get("/no-existe")
    assert r.status_code == 404
    assert r.json() == {"detail": "Documento no encontrado"}


def test_ningun_router_devuelve_el_error_crudo_al_cliente():
    """Hasta el 2026-11-04, cuatro respuestas de `documents.py` llevaban
    `str(e)` en el `detail`, con la clave de S3 o el error del SDK. El detalle
    técnico va al log, nunca a la respuesta."""
    import re
    from pathlib import Path

    routers = Path(__file__).resolve().parents[1] / "app" / "routers" / "v1"
    crudo = re.compile(r"detail\s*=\s*(str\(\s*e(xc)?\s*\)|f[\"'][^\"']*\{\s*(str\()?\s*e(xc)?\b)")
    culpables = [
        f"{f.name}:{n}"
        for f in routers.glob("*.py")
        for n, linea in enumerate(f.read_text(encoding="utf-8").splitlines(), 1)
        if crudo.search(linea)
    ]
    assert culpables == []


def test_la_app_real_registra_los_manejadores():
    manejadores = main.app.exception_handlers
    for tipo in (Exception, EmbeddingError, VectorStoreError, StorageError):
        assert tipo in manejadores
