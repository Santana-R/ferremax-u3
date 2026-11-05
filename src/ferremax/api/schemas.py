from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field


class InventarioUbicacionRespuesta(BaseModel):
    ubicacion_id: str = Field(description="Codigo de la sucursal o almacen")
    existencia_fisica: Decimal = Field(ge=0, description="Unidades fisicas")
    comprometida: Decimal = Field(ge=0, description="Unidades reservadas")
    en_transito: Decimal = Field(ge=0, description="Unidades en traslado; no son disponibles")
    disponible: Decimal = Field(ge=0, description="Existencia fisica menos comprometida")


class InventarioRespuesta(BaseModel):
    mensaje: str = "Disponibilidad del producto consultada."
    sku: str
    encontrado: bool
    ubicaciones: List[InventarioUbicacionRespuesta]


class MensajeError(BaseModel):
    mensaje: str
    sku: Optional[str] = None
