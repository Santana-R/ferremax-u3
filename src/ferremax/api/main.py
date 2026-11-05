"""Primera operacion REST: consulta de inventario sobre PostgreSQL."""

from typing import Optional

from fastapi import Depends, FastAPI, Path, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from psycopg import Error as ErrorPostgres

from ferremax.application.cqrs import ConsultarDisponibilidad, ConsultarDisponibilidadHandler
from ferremax.application.ports import DisponibilidadReader
from ferremax.application.services import Actor
from ferremax.infrastructure.postgres import PostgresReader
from .schemas import InventarioRespuesta, MensajeError
from .settings import ConfiguracionBaseNoDisponible, conexion_desde_entorno


def obtener_lector(request: Request) -> DisponibilidadReader:
    conexion = request.app.state.database_url
    return PostgresReader(conexion if conexion is not None else conexion_desde_entorno())


def error_cliente(mensaje, estado, sku=None):
    contenido = {"mensaje": mensaje}
    if sku is not None:
        contenido["sku"] = sku
    return JSONResponse(status_code=estado, content=contenido)


def create_app(database_url: Optional[str] = None) -> FastAPI:
    api = FastAPI(
        title="FerreMax - API",
        version="0.1.0",
        description="Consulta de disponibilidad de productos por sucursal o almacen.",
        redoc_url=None,
    )
    # La configuracion se resuelve al consultar, no al abrir Swagger.
    api.state.database_url = database_url

    @api.exception_handler(ErrorPostgres)
    @api.exception_handler(ConfiguracionBaseNoDisponible)
    async def base_no_disponible(request, exc):
        return error_cliente(
            "Por el momento no podemos consultar el inventario. Inténtalo de nuevo más tarde.", 503,
        )

    @api.exception_handler(RequestValidationError)
    async def solicitud_invalida(request, exc):
        return error_cliente("Revisa el código del producto e inténtalo de nuevo.", 422)

    @api.get(
        "/inventario/{sku}",
        response_model=InventarioRespuesta,
        summary="Consultar disponibilidad de un producto",
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

    return api


app = create_app()
