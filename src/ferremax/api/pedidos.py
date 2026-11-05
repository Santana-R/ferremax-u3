"""Adaptador HTTP para confirmar pedidos y reservar inventario atomicamente."""

from uuid import UUID

from fastapi import APIRouter, Depends, Path, Request

from ferremax.application.cqrs import ConfirmarPedido, ConfirmarPedidoHandler
from ferremax.application.services import Actor, PedidoService
from ferremax.domain.model import DisponibilidadInsuficiente, ErrorNegocio
from ferremax.infrastructure.postgres import PostgresUnitOfWork
from .responses import error_cliente
from .schemas import ConfirmacionSolicitud, MensajeError, PedidoConfirmadoRespuesta
from .settings import conexion_desde_entorno


router = APIRouter(prefix="/pedidos", tags=["Pedidos"])


def obtener_servicio_pedidos(request: Request) -> PedidoService:
    conexion = request.app.state.database_url
    if conexion is None:
        conexion = conexion_desde_entorno()
    return PedidoService(lambda: PostgresUnitOfWork(conexion), request.app.state.reloj)


def mensaje_confirmacion_invalida(errores):
    if errores and errores[0].get("type") == "extra_forbidden":
        return "La solicitud incluye campos no reconocidos. Usa los campos del ejemplo."
    ubicacion = errores[0].get("loc", ()) if errores else ()
    campos = {
        "pedido_id": "Indica un identificador válido de pedido.",
        "referencia_pago": "Indica una referencia de pago válida.",
        "pago_autorizado": "Indica si el pago fue autorizado.",
        "ubicacion_id": "Indica la ubicación desde la que se reservará inventario.",
    }
    for campo in reversed(ubicacion):
        if campo in campos:
            return campos[campo]
    return "Revisa los datos de la confirmación del pedido."


@router.post(
    "/{pedido_id}/confirmar",
    response_model=PedidoConfirmadoRespuesta,
    summary="Confirmar un pedido pendiente y reservar inventario",
    responses={
        404: {"model": MensajeError, "description": "Pedido no encontrado"},
        409: {"model": MensajeError, "description": "Estado, pago o disponibilidad impiden confirmar"},
        422: {"model": MensajeError, "description": "Revisar los datos o la ubicacion de inventario"},
        503: {"model": MensajeError, "description": "Confirmacion temporalmente no disponible"},
    },
)
def confirmar_pedido(
    entrada: ConfirmacionSolicitud,
    pedido_id: UUID = Path(..., examples=["22222222-2222-4222-8222-222222222222"]),
    servicio: PedidoService = Depends(obtener_servicio_pedidos),
):
    try:
        resultado = ConfirmarPedidoHandler(servicio).handle(
            ConfirmarPedido(str(pedido_id), entrada.referencia_pago,
                            entrada.pago_autorizado, entrada.ubicacion_id),
            Actor("caja-api-demo", "Caja"),
        )
    except DisponibilidadInsuficiente:
        return error_cliente(
            "No hay unidades disponibles suficientes para confirmar el pedido. El pedido permanece pendiente.",
            409, pedido_id=pedido_id,
        )
    except ErrorNegocio as exc:
        rechazos = {
            "Pedido inexistente": (404, "Pedido no encontrado."),
            "Pedido no pendiente": (409, "El pedido ya no está pendiente y no puede confirmarse de nuevo."),
            "Pago no autorizado": (409, "El pago no está autorizado para confirmar el pedido."),
            "SKU o ubicacion inexistente": (422, "Uno de los productos del pedido no tiene inventario registrado en la ubicación seleccionada."),
        }
        estado, mensaje = rechazos.get(str(exc), (422, "No se pudo confirmar el pedido. Revisa sus datos y la ubicación."))
        return error_cliente(mensaje, estado, pedido_id=pedido_id)
    return PedidoConfirmadoRespuesta(**resultado)
