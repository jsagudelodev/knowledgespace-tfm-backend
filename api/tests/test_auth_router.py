"""Tests de `routers/v1/auth.py` — ausencia de registro público, perfil propio
y cambio de contraseña (verificación de la contraseña actual).

Son tests de lógica pura: `UserRepository`/`CompanyRepository` se sustituyen
por dobles y las funciones async del router se llaman directamente con
`asyncio.run` -no hace falta FastAPI ni una base de datos real para esto-.
"""
import asyncio
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.routers.v1 import auth as auth_module
from app.schemas.user import ChangePassword, ProfileUpdate


def _usuario(**kwargs) -> SimpleNamespace:
    base = dict(id=1, company_id=8, email="ana@empresa.com", full_name="Ana",
                role="user", is_active=True, hashed_password=None)
    base.update(kwargs)
    return SimpleNamespace(**base)


class _UserRepoFalso:
    def __init__(self):
        self.actualizados = []

    def update(self, user):
        self.actualizados.append(user)
        return user


def _patch_repos(monkeypatch, user_repo):
    monkeypatch.setattr(auth_module, "UserRepository", lambda db: user_repo)


# ── Sin registro público ─────────────────────────────────────────────────

def test_no_existe_registro_publico():
    """El registro público tomaba `company_id` del body: cualquiera podía
    darse de alta en una empresa ajena y consultar su documentación. Se
    eliminó; los usuarios solo los crea un admin con la empresa de su token."""
    rutas = {ruta.path for ruta in auth_module.router.routes}

    assert "/register" not in rutas
    assert "/login" in rutas


# ── Perfil propio ────────────────────────────────────────────────────────

def test_actualizar_perfil_solo_toca_el_nombre(monkeypatch):
    usuario = _usuario(full_name="Nombre Viejo", role="user")
    user_repo = _UserRepoFalso()
    _patch_repos(monkeypatch, user_repo)

    actualizado = asyncio.run(
        auth_module.update_profile(ProfileUpdate(full_name="Nombre Nuevo"), current_user=usuario, db=None)
    )

    assert actualizado.full_name == "Nombre Nuevo"
    assert actualizado.role == "user"  # ProfileUpdate ni siquiera tiene campo `role`


# ── Cambio de contraseña ─────────────────────────────────────────────────

def test_cambiar_contrasena_rechaza_si_la_actual_no_coincide(monkeypatch):
    from app.core.security import get_password_hash
    usuario = _usuario(hashed_password=get_password_hash("ClaveReal123"))
    _patch_repos(monkeypatch, _UserRepoFalso())
    data = ChangePassword(current_password="ClaveEquivocada", new_password="NuevaClave456")

    with pytest.raises(HTTPException) as exc:
        asyncio.run(auth_module.change_password(data, current_user=usuario, db=None))
    assert exc.value.status_code == 400


def test_cambiar_contrasena_rechaza_si_la_nueva_es_igual_a_la_actual(monkeypatch):
    from app.core.security import get_password_hash
    usuario = _usuario(hashed_password=get_password_hash("ClaveReal123"))
    _patch_repos(monkeypatch, _UserRepoFalso())
    data = ChangePassword(current_password="ClaveReal123", new_password="ClaveReal123")

    with pytest.raises(HTTPException) as exc:
        asyncio.run(auth_module.change_password(data, current_user=usuario, db=None))
    assert exc.value.status_code == 400


def test_cambiar_contrasena_actualiza_el_hash_cuando_todo_es_valido(monkeypatch):
    from app.core.security import get_password_hash, verify_password
    usuario = _usuario(hashed_password=get_password_hash("ClaveReal123"))
    user_repo = _UserRepoFalso()
    _patch_repos(monkeypatch, user_repo)
    data = ChangePassword(current_password="ClaveReal123", new_password="ClaveNueva456")

    asyncio.run(auth_module.change_password(data, current_user=usuario, db=None))

    assert verify_password("ClaveNueva456", usuario.hashed_password)
    assert len(user_repo.actualizados) == 1
