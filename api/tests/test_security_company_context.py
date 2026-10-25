"""Tests de `get_company_context`: el mecanismo que permite a un superadmin
ver y administrar los datos de OTRA empresa, pidiéndolo con el header
`X-Company-Context`.

Es la pieza central del selector de empresa — sin esto no hay forma segura de
que un superadmin "entre" a una empresa ajena. Estuvo escrita pero sin usar y
sin ningún test hasta ahora: nada impedía que un cambio futuro abriera el
aislamiento multi-tenant a cualquier rol, o lo cerrara por error para
usuarios normales. Son tests de lógica pura: la función no hace I/O, así que
se llama directamente con dobles, sin FastAPI ni base de datos.
"""
import asyncio
from types import SimpleNamespace

from app.routers.v1.security import get_company_context


def _usuario(role: str, company_id: int) -> SimpleNamespace:
    return SimpleNamespace(role=role, company_id=company_id)


def _contexto(current_user, x_company_context=None) -> int:
    return asyncio.run(get_company_context(x_company_context, current_user))


# ── El caso normal: nadie pidió cambiar de empresa ──────────────────────────

def test_sin_header_devuelve_la_empresa_propia_del_usuario():
    assert _contexto(_usuario("user", company_id=5)) == 5


def test_un_superadmin_sin_header_ve_su_propia_empresa():
    """Por defecto, ni un superadmin cambia de contexto sin pedirlo."""
    assert _contexto(_usuario("superadmin", company_id=3)) == 3


# ── Solo un superadmin puede cambiar de contexto ────────────────────────────

def test_un_superadmin_con_header_ve_la_empresa_pedida():
    assert _contexto(_usuario("superadmin", company_id=3), x_company_context=8) == 8


def test_un_admin_de_empresa_no_puede_cambiar_de_contexto():
    """El header lo podría mandar cualquiera -lo controla el cliente, no el
    servidor-, así que ignorarlo para quien no es superadmin es la única
    defensa real. Sin esto, cualquier admin podría leer los documentos de
    otra empresa con solo añadir una cabecera a su petición."""
    assert _contexto(_usuario("admin", company_id=3), x_company_context=8) == 3


def test_un_usuario_normal_no_puede_cambiar_de_contexto():
    assert _contexto(_usuario("user", company_id=3), x_company_context=8) == 3
