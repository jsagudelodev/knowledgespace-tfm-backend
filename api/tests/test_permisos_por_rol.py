"""Permisos por rol (2026-11-02). Con la cuenta de demo de rol `user` se podía
borrar cualquier documento, crear o borrar asistentes y categorías, indexar
respuestas escritas a mano y ver el feedback de todos con nombre. La regla:
un usuario puede aportar (chatear, calificar, subir y gestionar lo suyo), pero
lo que cambia lo que el asistente responde a los demás, o expone datos de otros
usuarios, exige admin.

Se comprueba sobre el árbol de dependencias de cada ruta, sin levantar la app:
si alguien vuelve a abrir un endpoint de gestión, este test lo detecta.
"""
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.routers.v1 import assistants, categories, documents, feedback, knowledge_gaps
from app.routers.v1.security import get_current_admin_user


def _dependencias(dependant):
    for dep in dependant.dependencies:
        yield dep.call
        yield from _dependencias(dep)


def _exige_admin(route) -> bool:
    return get_current_admin_user in set(_dependencias(route.dependant))


def _rutas(router, metodo, ruta):
    return [r for r in router.routes if metodo in r.methods and r.path == ruta]


def _una(router, metodo, ruta):
    encontradas = _rutas(router, metodo, ruta)
    assert len(encontradas) == 1, f"{metodo} {ruta} no existe"
    return encontradas[0]


# ── Lo que exige admin ──────────────────────────────────────────────────────

@pytest.mark.parametrize("metodo,ruta", [("POST", "/"), ("PUT", "/{assistant_id}"), ("DELETE", "/{assistant_id}")])
def test_gestionar_asistentes_exige_admin(metodo, ruta):
    assert _exige_admin(_una(assistants.router, metodo, ruta))


@pytest.mark.parametrize("metodo,ruta", [("POST", "/"), ("PUT", "/{category_id}"), ("DELETE", "/{category_id}")])
def test_gestionar_categorias_exige_admin(metodo, ruta):
    assert _exige_admin(_una(categories.router, metodo, ruta))


def test_todo_preguntas_sin_respuesta_exige_admin():
    rutas = list(knowledge_gaps.router.routes)
    assert rutas, "el router no tiene rutas"
    abiertas = [f"{sorted(r.methods)} {r.path}" for r in rutas if not _exige_admin(r)]
    assert abiertas == []


@pytest.mark.parametrize("metodo,ruta", [
    ("GET", "/stats"), ("GET", "/export"), ("GET", "/"), ("GET", "/{feedback_id}"),
    ("PATCH", "/{feedback_id}/status"), ("POST", "/{feedback_id}/convert-gap"),
])
def test_ver_y_gestionar_el_feedback_de_todos_exige_admin(metodo, ruta):
    assert _exige_admin(_una(feedback.router, metodo, ruta))


# ── Lo que sigue abierto a cualquier usuario ────────────────────────────────

@pytest.mark.parametrize("router,metodo,ruta", [
    (feedback.router, "POST", "/"),
    (feedback.router, "GET", "/me"),
    (documents.router, "POST", "/upload"),
    (documents.router, "GET", "/"),
    (assistants.router, "GET", "/"),
    (categories.router, "GET", "/"),
])
def test_aportar_y_leer_sigue_abierto(router, metodo, ruta):
    assert not _exige_admin(_una(router, metodo, ruta))


# ── Documentos: dueño o admin ────────────────────────────────────────────────

def _doc(uploaded_by=7):
    return SimpleNamespace(uploaded_by=uploaded_by)


def _usuario(user_id, role="user"):
    return SimpleNamespace(id=user_id, role=role)


def test_un_usuario_gestiona_lo_que_subio():
    documents._exigir_dueno_o_admin(_doc(uploaded_by=7), _usuario(7))


def test_un_usuario_no_toca_documentos_ajenos():
    with pytest.raises(HTTPException) as exc:
        documents._exigir_dueno_o_admin(_doc(uploaded_by=7), _usuario(9))
    assert exc.value.status_code == 403


@pytest.mark.parametrize("rol", ["admin", "superadmin"])
def test_un_admin_gestiona_cualquier_documento(rol):
    documents._exigir_dueno_o_admin(_doc(uploaded_by=7), _usuario(9, rol))
