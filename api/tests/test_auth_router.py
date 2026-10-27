"""Tests de `routers/v1/auth.py` — registro propio, perfil propio y cambio de
contraseña. Nunca tuvo ningún test hasta ahora, a pesar de tener reglas de
negocio reales (cupo de usuarios de la empresa, verificación de la
contraseña actual, el rol que se auto-asigna un usuario nuevo).

Son tests de lógica pura: `UserRepository`/`CompanyRepository` se sustituyen
por dobles y las funciones async del router se llaman directamente con
`asyncio.run` -no hace falta FastAPI ni una base de datos real para esto-.
"""
import asyncio
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.routers.v1 import auth as auth_module
from app.schemas.user import ChangePassword, ProfileUpdate, UserCreate


def _usuario(**kwargs) -> SimpleNamespace:
    base = dict(id=1, company_id=8, email="ana@empresa.com", full_name="Ana",
                role="user", is_active=True, hashed_password=None)
    base.update(kwargs)
    return SimpleNamespace(**base)


def _empresa(max_users: int) -> SimpleNamespace:
    return SimpleNamespace(id=8, max_users=max_users)


class _UserRepoFalso:
    def __init__(self, por_email=None, conteo_por_empresa=0):
        self._por_email = por_email or {}
        self.conteo_por_empresa = conteo_por_empresa
        self.creados = []
        self.actualizados = []

    def get_by_email(self, email):
        return self._por_email.get(email)

    def count_by_company(self, company_id):
        return self.conteo_por_empresa

    def create(self, user):
        self.creados.append(user)
        return user

    def update(self, user):
        self.actualizados.append(user)
        return user


class _CompanyRepoFalso:
    def __init__(self, empresa=None):
        self._empresa = empresa

    def get(self, company_id):
        return self._empresa


def _patch_repos(monkeypatch, user_repo, company_repo=None):
    monkeypatch.setattr(auth_module, "UserRepository", lambda db: user_repo)
    if company_repo is not None:
        monkeypatch.setattr(auth_module, "CompanyRepository", lambda db: company_repo)


# ── Registro propio ──────────────────────────────────────────────────────

def test_el_registro_asigna_rol_user_sin_importar_lo_que_pida_el_payload(monkeypatch):
    """UserCreate acepta un campo `role` en el payload -lo usa la creación
    desde el panel de admin-, pero el registro público nunca debe dejar que
    alguien se autoasigne admin o superadmin con solo mandarlo en el body."""
    user_repo = _UserRepoFalso(conteo_por_empresa=3)
    _patch_repos(monkeypatch, user_repo, _CompanyRepoFalso(_empresa(max_users=10)))

    data = UserCreate(email="nuevo@empresa.com", full_name="Nuevo", password="password123",
                       company_id=8, role="superadmin")

    creado = asyncio.run(auth_module.register(data, db=None))

    assert creado.role == "user"
    assert user_repo.creados[0].role == "user"


def test_el_registro_falla_si_el_email_ya_existe(monkeypatch):
    user_repo = _UserRepoFalso(por_email={"ya@empresa.com": _usuario(email="ya@empresa.com")})
    _patch_repos(monkeypatch, user_repo, _CompanyRepoFalso(_empresa(max_users=10)))
    data = UserCreate(email="ya@empresa.com", full_name="X", password="password123", company_id=8)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(auth_module.register(data, db=None))
    assert exc.value.status_code == 409


def test_el_registro_falla_si_la_empresa_no_existe(monkeypatch):
    user_repo = _UserRepoFalso()
    _patch_repos(monkeypatch, user_repo, _CompanyRepoFalso(empresa=None))
    data = UserCreate(email="x@empresa.com", full_name="X", password="password123", company_id=999)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(auth_module.register(data, db=None))
    assert exc.value.status_code == 404


def test_el_registro_respeta_el_cupo_maximo_de_usuarios_de_la_empresa(monkeypatch):
    user_repo = _UserRepoFalso(conteo_por_empresa=5)
    _patch_repos(monkeypatch, user_repo, _CompanyRepoFalso(_empresa(max_users=5)))
    data = UserCreate(email="x@empresa.com", full_name="X", password="password123", company_id=8)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(auth_module.register(data, db=None))
    assert exc.value.status_code == 409


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
