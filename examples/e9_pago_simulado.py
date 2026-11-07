"""Ejercicio U5: puerto de pago y adaptador con proveedor simulado.

FerreMax no integra una pasarela real. Este ejercicio muestra la interaccion
usando el servicio existente y no agrega una regla comercial nueva al PIA.
"""

from typing import Protocol
from ferremax.domain.model import AutorizacionPago, Dinero, ErrorNegocio


class ProveedorPago(Protocol):
    def cobrar(self, pedido_id: str, importe: Dinero) -> bool: ...


class AdaptadorPagoSimulado:
    def __init__(self, proveedor: ProveedorPago):
        self.proveedor = proveedor

    def autorizar(self, pedido_id, importe, referencia):
        try:
            aprobado = self.proveedor.cobrar(pedido_id, importe)
        except TimeoutError as exc:
            raise ErrorNegocio("No se obtuvo respuesta del proveedor de pago") from exc
        return AutorizacionPago(referencia, aprobado)


def confirmar_con_pago_simulado(pedido, servicio, actor, adaptador, referencia, ubicacion):
    """Solo se solicita confirmar cuando el proveedor simulado aprueba."""
    pago = adaptador.autorizar(pedido.id, pedido.total, referencia)
    if not pago.autorizada:
        raise ErrorNegocio("El proveedor simulado rechazo el pago")
    return servicio.confirmar(actor, pedido.id, pago, ubicacion)
