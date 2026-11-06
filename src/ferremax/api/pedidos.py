"""Consultas y comandos HTTP de pedidos con sus reservas."""

from uuid import UUID

from fastapi import APIRouter, Depends, Path, Request

from ferremax.application.cqrs import (
    CancelarPedido, CancelarPedidoHandler, ConfirmarPedido, ConfirmarPedidoHandler,
    ConsultarPedido, ConsultarPedidoHandler,
)
from ferremax.application.ports import PedidoReader
from ferremax.application.services import Actor, PedidoService
from ferremax.domain.model import DisponibilidadInsuficiente, ErrorNegocio
from ferremax.infrastructure.postgres import PostgresReader, PostgresUnitOfWork
from .responses import error_cliente
from .schemas import (
    CancelacionSolicitud, ConfirmacionSolicitud, MensajeError,
    PedidoCanceladoRespuesta, PedidoConfirmadoRespuesta, PedidoConsultaRespuesta,
)
from .settings import conexion_desde_entorno


router = APIRouter(prefix="/pedidos", tags=["Pedidos"])


def obtener_lector_pedidos(request: Request) -> PedidoReader:
    conexion = request.app.state.database_url
    return PostgresReader(conexion if conexion is not None else conexion_desde_entorno())


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


def mensaje_cancelacion_invalida(errores):
    if errores and errores[0].get("type") == "extra_forbidden":
        return "La solicitud incluye campos no reconocidos. Usa solo el motivo de cancelación."
    ubicacion = errores[0].get("loc", ()) if errores else ()
    if "pedido_id" in ubicacion:
        return "Indica un identificador válido de pedido."
    if "motivo" in ubicacion:
        return "Indica el motivo de la cancelación."
    return "Revisa los datos de la cancelación del pedido."


@router.get(
    "/{pedido_id}",
    response_model=PedidoConsultaRespuesta,
    summary="Consultar estado, cotizacion de origen y total de un pedido",
    responses={
        404: {"model": MensajeError, "description": "Pedido no encontrado"},
        422: {"model": MensajeError, "description": "Revisar identificador del pedido"},
        503: {"model": MensajeError, "description": "Consulta de pedido temporalmente no disponible"},
    },
)
def consultar_pedido(
    pedido_id: UUID = Path(..., examples=["22222222-2222-4222-8222-222222222222"]),
    lector: PedidoReader = Depends(obtener_lector_pedidos),
):
    try:
        resultado = ConsultarPedidoHandler(lector).handle(
            ConsultarPedido(str(pedido_id)), Actor("consulta-pedido-api-demo", "Vendedor"),
        )
    except ErrorNegocio as exc:
        if str(exc) == "Pedido inexistente":
            return error_cliente("Pedido no encontrado.", 404, pedido_id=pedido_id)
        return error_cliente("No se pudo consultar el pedido. Revisa su identificador.", 422, pedido_id=pedido_id)
    return PedidoConsultaRespuesta(**resultado)


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


@router.post(
    "/{pedido_id}/cancelar",
    response_model=PedidoCanceladoRespuesta,
    summary="Cancelar un pedido confirmado antes del surtido y liberar su reserva",
    responses={
        404: {"model": MensajeError, "description": "Pedido no encontrado"},
        409: {"model": MensajeError, "description": "Estado, surtido o reserva impiden cancelar"},
        422: {"model": MensajeError, "description": "Revisar identificador y motivo"},
        503: {"model": MensajeError, "description": "Cancelacion temporalmente no disponible"},
    },
)
def cancelar_pedido(
    entrada: CancelacionSolicitud,
    pedido_id: UUID = Path(..., examples=["22222222-2222-4222-8222-222222222222"]),
    servicio: PedidoService = Depends(obtener_servicio_pedidos),
):
    try:
        resultado = CancelarPedidoHandler(servicio).handle(
            CancelarPedido(str(pedido_id), entrada.motivo),
            Actor("cancelacion-api-demo", "VendedorAutorizadoCancelacion"),
        )
    except ErrorNegocio as exc:
        rechazos = {
            "Pedido inexistente": (404, "Pedido no encontrado."),
            "Solo puede cancelarse un pedido confirmado aun no surtido": (
                409, "Solo puedes cancelar un pedido confirmado que aún no se haya surtido. Si ya fue cancelado, no puede cancelarse de nuevo.",
            ),
            "Indique motivo de cancelacion": (422, "Indica el motivo de la cancelación."),
            "Reserva inexistente": (409, "No se pudo liberar la reserva del pedido. Solicita una revisión antes de volver a intentarlo."),
            "El prototipo requiere una ubicacion por pedido": (
                409, "No se pudo identificar una reserva única para el pedido. Solicita una revisión antes de volver a intentarlo.",
            ),
            "SKU o ubicacion inexistente": (409, "No se encontró el inventario asociado a la reserva. Solicita una revisión antes de volver a intentarlo."),
        }
        estado, mensaje = rechazos.get(str(exc), (422, "No se pudo cancelar el pedido. Revisa sus datos."))
        return error_cliente(mensaje, estado, pedido_id=pedido_id)
    return PedidoCanceladoRespuesta(**resultado)
