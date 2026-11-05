"""Adaptador HTTP de revalidacion y conversion de cotizaciones de FerreMax."""

from uuid import UUID

from fastapi import APIRouter, Depends, Path, Request

from ferremax.application.services import Actor, CotizacionService
from ferremax.domain.model import CotizacionVencida, Dinero, ErrorNegocio, Partida, SKU
from ferremax.infrastructure.postgres import PostgresUnitOfWork
from .responses import error_cliente
from .schemas import (
    ConversionSolicitud, CotizacionRevalidadaRespuesta, MensajeError,
    PedidoCreadoRespuesta, RevalidacionSolicitud,
)
from .settings import conexion_desde_entorno


router = APIRouter(prefix="/cotizaciones", tags=["Cotizaciones"])


def obtener_servicio_cotizaciones(request: Request) -> CotizacionService:
    conexion = request.app.state.database_url
    if conexion is None:
        conexion = conexion_desde_entorno()
    return CotizacionService(lambda: PostgresUnitOfWork(conexion), request.app.state.reloj)


def mensaje_solicitud_invalida(errores, conversion=False):
    if errores and errores[0].get("type") == "extra_forbidden":
        return "La solicitud incluye campos no reconocidos. Usa los campos del ejemplo."
    ubicacion = errores[0].get("loc", ()) if errores else ()
    if "cotizacion_id" in ubicacion:
        return "Indica un identificador válido de cotización."
    if "version" in ubicacion:
        return "Indica una versión entera mayor que cero."
    campos = {
        "dias_vigencia": "Indica los días de vigencia como un entero mayor que cero.",
        "partidas": "Incluye al menos una partida válida en la cotización.",
        "numero": "Cada partida debe tener un número entero mayor que cero.",
        "sku": "Indica el código del producto de cada partida.",
        "cantidad": "La cantidad de cada partida debe ser un número mayor que cero.",
        "precio_unitario": "El precio unitario debe ser un número igual o mayor que cero.",
        "moneda": "Indica la moneda de cada partida.",
        "condiciones": "Indica las condiciones de la nueva cotización.",
        "motivo": "Indica el motivo de la revalidación.",
        "aceptada": "Indica si el cliente aceptó esta versión de la cotización.",
    }
    for campo in reversed(ubicacion):
        if campo in campos:
            return campos[campo]
    return "Revisa los datos de la conversión." if conversion else "Revisa los datos de la revalidación."


RECHAZOS = {
    "Cotizacion o version inexistente": (404, "Cotización o versión no encontrada."),
    "Version duplicada; vuelva a consultar": (409, "Ya existe la siguiente versión de esta cotización. Usa la versión más reciente."),
    "Este caso revalida cotizaciones vencidas": (409, "La cotización todavía está vigente; esta operación revalida cotizaciones vencidas."),
    "La cotizacion aun no fue emitida": (409, "La cotización todavía no ha sido emitida."),
    "SKU o ubicacion inexistente": (422, "Uno de los productos no está registrado en la sucursal de revalidación."),
    "Se requieren partidas con numeros distintos": (422, "Usa un número diferente para cada partida de la cotización."),
    "Las partidas requieren la misma moneda": (422, "Todas las partidas deben usar la misma moneda."),
    "Indique motivo de revalidacion": (422, "Indica el motivo de la revalidación."),
    "Indique vigencia y condiciones": (422, "Indica la vigencia y las condiciones de la nueva cotización."),
}


@router.post(
    "/{cotizacion_id}/versiones/{version}/revalidar",
    status_code=201,
    response_model=CotizacionRevalidadaRespuesta,
    summary="Revalidar una cotizacion vencida conservando su historial",
    responses={
        404: {"model": MensajeError, "description": "Cotizacion o version no encontrada"},
        409: {"model": MensajeError, "description": "La version no admite esta revalidacion"},
        422: {"model": MensajeError, "description": "Revisar los datos de la revalidacion"},
        503: {"model": MensajeError, "description": "Revalidacion temporalmente no disponible"},
    },
)
def revalidar_cotizacion(
    entrada: RevalidacionSolicitud,
    cotizacion_id: UUID = Path(..., examples=["11111111-1111-4111-8111-111111111111"]),
    version: int = Path(..., gt=0, examples=[1]),
    servicio: CotizacionService = Depends(obtener_servicio_cotizaciones),
):
    try:
        partidas = [Partida(p.numero, SKU(p.sku), p.cantidad, Dinero(p.precio_unitario, p.moneda))
                    for p in entrada.partidas]
        resultado = servicio.revalidar(
            Actor("vendedor-api-demo", "Vendedor"), str(cotizacion_id), version,
            entrada.dias_vigencia, partidas, entrada.condiciones, entrada.motivo,
        )
    except ErrorNegocio as exc:
        estado, mensaje = RECHAZOS.get(str(exc), (422, "No se pudo revalidar la cotización con los datos proporcionados."))
        return error_cliente(mensaje, estado, cotizacion_id=cotizacion_id)
    except OverflowError:
        return error_cliente("La vigencia solicitada excede el rango de fechas permitido.", 422, cotizacion_id=cotizacion_id)
    return CotizacionRevalidadaRespuesta(
        cotizacion_id=cotizacion_id, version_anterior=version, **resultado,
    )


@router.post(
    "/{cotizacion_id}/versiones/{version}/convertir",
    status_code=201,
    response_model=PedidoCreadoRespuesta,
    summary="Crear un pedido desde una version vigente y aceptada",
    responses={
        404: {"model": MensajeError, "description": "Cotizacion o version no encontrada"},
        409: {"model": MensajeError, "description": "Cotizacion no vigente o sin aceptacion"},
        422: {"model": MensajeError, "description": "Revisar la solicitud o los productos de la cotizacion"},
        503: {"model": MensajeError, "description": "Creacion del pedido temporalmente no disponible"},
    },
)
def convertir_cotizacion(
    entrada: ConversionSolicitud,
    cotizacion_id: UUID = Path(..., examples=["11111111-1111-4111-8111-111111111111"]),
    version: int = Path(..., gt=0, examples=[2]),
    servicio: CotizacionService = Depends(obtener_servicio_cotizaciones),
):
    try:
        resultado = servicio.convertir(
            Actor("vendedor-api-demo", "Vendedor"), str(cotizacion_id), version, entrada.aceptada,
        )
    except CotizacionVencida:
        return error_cliente(
            "Esta versión de la cotización no está vigente. Usa una versión vigente para crear el pedido.",
            409, cotizacion_id=cotizacion_id,
        )
    except ErrorNegocio as exc:
        rechazos = {
            "Cotizacion o version inexistente": (404, "Cotización o versión no encontrada."),
            "Se requiere aceptacion del cliente": (409, "El cliente debe aceptar esta versión de la cotización antes de crear el pedido."),
            "SKU o ubicacion inexistente": (422, "Uno de los productos de la cotización no está registrado en la sucursal de consulta."),
        }
        estado, mensaje = rechazos.get(str(exc), (422, "No se pudo crear el pedido con los datos proporcionados."))
        return error_cliente(mensaje, estado, cotizacion_id=cotizacion_id)
    return PedidoCreadoRespuesta(cotizacion_id=cotizacion_id, **resultado)
