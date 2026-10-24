"""Tests de `PineconeService.eliminar_por_documento`.

Se llama antes de cada reindexado para que sea idempotente, y al borrar un
documento. El caso real que motivo este archivo: el primer documento que se
sube a un asistente nuevo fallaba siempre con "Namespace not found", porque
Pinecone responde 404 al borrar en un namespace que todavia no existe -algo
completamente normal cuando no se ha indexado nada ahi antes-, y el metodo lo
trataba como un error real. Son tests de logica pura: el indice se sustituye
por un doble.
"""
import pytest
from pinecone.exceptions import NotFoundException

from app.core.exceptions import VectorStoreError
from app.services.pinecone_service import PineconeService


def _servicio(excepcion_al_borrar=None):
    svc = PineconeService.__new__(PineconeService)
    svc.nombre_indice = "test"

    class _Indice:
        def __init__(self):
            self.kwargs_recibidos = None

        def delete(self, **kwargs):
            self.kwargs_recibidos = kwargs
            if excepcion_al_borrar:
                raise excepcion_al_borrar

    indice = _Indice()
    svc.pc = type("_Cliente", (), {"Index": lambda self, nombre: indice})()
    svc._indice_doble = indice
    return svc


def test_borra_con_el_filtro_y_el_namespace_pedidos():
    svc = _servicio()
    svc.eliminar_por_documento(7, namespace="company-1-assistant-2")
    assert svc._indice_doble.kwargs_recibidos == {
        "filter": {"document_id": 7},
        "namespace": "company-1-assistant-2",
    }


def test_namespace_inexistente_no_se_trata_como_error():
    """Es el caso del primer documento de un asistente nuevo: no hay nada que
    borrar, asi que un 404 de Pinecone equivale a exito, no a fallo."""
    svc = _servicio(excepcion_al_borrar=NotFoundException("Namespace not found", status_code=404))
    svc.eliminar_por_documento(7, namespace="company-1-assistant-2")  # no debe lanzar


def test_otros_errores_de_pinecone_si_se_propagan():
    """Que un 404 se ignore no debe ocultar fallos reales (credenciales,
    indice caido, etc.)."""
    svc = _servicio(excepcion_al_borrar=RuntimeError("fallo de red"))
    with pytest.raises(VectorStoreError):
        svc.eliminar_por_documento(7, namespace="company-1-assistant-2")
