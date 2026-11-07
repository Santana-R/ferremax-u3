"""Primera vista de atención, sobre la API de negocio existente."""

from pathlib import Path
from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.encoders import jsonable_encoder
from ferremax.infrastructure.cotizaciones_reader import PostgresCotizacionesReader
from ferremax.infrastructure.atencion_reader import PostgresAtencionReader
from .settings import conexion_desde_entorno

router = APIRouter(include_in_schema=False)


def obtener_cotizaciones_reader(request: Request):
    conexion = request.app.state.database_url
    return PostgresCotizacionesReader(conexion if conexion is not None else conexion_desde_entorno())


@router.get("/cliente", response_class=FileResponse)
def pantalla_cliente():
    return FileResponse(Path(__file__).with_name("cliente.html"), media_type="text/html",
                        headers={"Cache-Control": "no-store"})


@router.get("/cliente/acciones.js", response_class=FileResponse)
def acciones_cliente():
    return FileResponse(Path(__file__).with_name("cliente.js"), media_type="text/javascript",
                        headers={"Cache-Control": "no-store"})


@router.get("/cliente/atencion.js", response_class=FileResponse)
def acciones_atencion():
    return FileResponse(Path(__file__).with_name("atencion.js"), media_type="text/javascript",
                        headers={"Cache-Control": "no-store"})


def obtener_atencion_reader(request: Request):
    conexion = request.app.state.database_url
    return PostgresAtencionReader(conexion if conexion is not None else conexion_desde_entorno())


@router.get("/cliente/catalogo")
def catalogo_atencion(lector=Depends(obtener_atencion_reader)):
    return JSONResponse(jsonable_encoder(lector.catalogo()), headers={"Cache-Control": "no-store"})


@router.get("/cliente/pedidos")
def pedidos_atencion(lector=Depends(obtener_atencion_reader)):
    return JSONResponse(jsonable_encoder({'pedidos': lector.pedidos()}), headers={"Cache-Control": "no-store"})


@router.get("/cliente/cotizaciones")
def listar_cotizaciones(request: Request, lector=Depends(obtener_cotizaciones_reader)):
    return JSONResponse(jsonable_encoder({"cotizaciones": lector.listar_actuales(request.app.state.reloj())}),
                        headers={"Cache-Control": "no-store"})
