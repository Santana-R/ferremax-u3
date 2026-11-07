"""API REST de FerreMax: inventario, cotizaciones y pedidos."""

from datetime import datetime, timezone
from typing import Callable, Optional

from fastapi import Depends, FastAPI, Path, Request
from fastapi.exceptions import RequestValidationError
from psycopg import Error as ErrorPostgres

from ferremax.application.cqrs import ConsultarDisponibilidad, ConsultarDisponibilidadHandler
from ferremax.application.ports import DisponibilidadReader
from ferremax.application.services import Actor
from ferremax.infrastructure.postgres import PostgresReader
from .schemas import InventarioRespuesta, MensajeError
from .settings import ConfiguracionBaseNoDisponible, conexion_desde_entorno
from .cotizaciones import router as cotizaciones_router, mensaje_solicitud_invalida
from .responses import error_cliente
from .swagger_claro import configurar_swagger
from .pedidos import router as pedidos_router, mensaje_cancelacion_invalida, mensaje_confirmacion_invalida


def obtener_lector(request: Request) -> DisponibilidadReader:
    conexion = request.app.state.database_url
    return PostgresReader(conexion if conexion is not None else conexion_desde_entorno())


def create_app(database_url: Optional[str] = None, reloj: Optional[Callable[[], datetime]] = None) -> FastAPI:
    api = FastAPI(
        title="FerreMax - API",
        version="0.6.0",
        description="Inventario, cotizaciones y pedidos: consulta, confirmacion y cancelacion con reservas.",
        redoc_url=None,
        docs_url=None,
    )
    # La configuracion se resuelve al consultar, no al abrir Swagger.
    api.state.database_url = database_url
    api.state.reloj = reloj or (lambda: datetime.now(timezone.utc))
    api.include_router(cotizaciones_router)
    api.include_router(pedidos_router)

    @api.exception_handler(ErrorPostgres)
    @api.exception_handler(ConfiguracionBaseNoDisponible)
    async def base_no_disponible(request, exc):
        if request.url.path.startswith("/pedidos/"):
            if request.method == "GET":
                return error_cliente("Por el momento no podemos consultar el pedido. Inténtalo de nuevo más tarde.", 503)
            if request.url.path.endswith("/cancelar"):
                return error_cliente("Por el momento no podemos cancelar el pedido. Inténtalo de nuevo más tarde.", 503)
            return error_cliente("Por el momento no podemos confirmar el pedido. Inténtalo de nuevo más tarde.", 503)
        if request.url.path.startswith("/cotizaciones/") and request.url.path.endswith("/convertir"):
            return error_cliente("Por el momento no podemos crear el pedido. Inténtalo de nuevo más tarde.", 503)
        if request.url.path.startswith("/cotizaciones/"):
            return error_cliente("Por el momento no podemos revalidar la cotización. Inténtalo de nuevo más tarde.", 503)
        return error_cliente(
            "Por el momento no podemos consultar el inventario. Inténtalo de nuevo más tarde.", 503,
        )

    @api.exception_handler(RequestValidationError)
    async def solicitud_invalida(request, exc):
        if request.url.path.startswith("/pedidos/"):
            if request.method == "GET":
                return error_cliente("Indica un identificador válido de pedido.", 422)
            if request.url.path.endswith("/cancelar"):
                return error_cliente(mensaje_cancelacion_invalida(exc.errors()), 422)
            return error_cliente(mensaje_confirmacion_invalida(exc.errors()), 422)
        if request.url.path.startswith("/cotizaciones/"):
            return error_cliente(mensaje_solicitud_invalida(
                exc.errors(), conversion=request.url.path.endswith("/convertir"),
            ), 422)
        return error_cliente("Revisa el código del producto e inténtalo de nuevo.", 422)

    @api.get(
        "/inventario/{sku}",
        response_model=InventarioRespuesta,
        summary="Consultar disponibilidad",
        tags=["Inventario"],
        responses={
            400: {"model": MensajeError, "description": "Codigo de producto vacio"},
            404: {"model": MensajeError, "description": "Producto no encontrado en el inventario"},
            422: {"model": MensajeError, "description": "Revisar el codigo del producto"},
            503: {"model": MensajeError, "description": "Consulta temporalmente no disponible"},
        },
    )
    def consultar_inventario(
        sku: str = Path(..., description="Codigo del producto", examples=["FER-API-DEMO"]),
        lector: DisponibilidadReader = Depends(obtener_lector),
    ):
        codigo = sku.strip()
        if not codigo:
            return error_cliente("Escribe el código del producto.", 400)
        # Actor fijo del prototipo local; no representa autenticacion de usuarios.
        resultado = ConsultarDisponibilidadHandler(lector).handle(
            ConsultarDisponibilidad(codigo), Actor("consulta-api-demo", "Vendedor"),
        )
        if not resultado["encontrado"]:
            return error_cliente("Producto no encontrado en el inventario.", 404, codigo)
        return InventarioRespuesta(**resultado)

    configurar_swagger(api)
    return api


app = create_app()
