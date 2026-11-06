from decimal import Decimal
from typing import Annotated, List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints


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
    cotizacion_id: Optional[UUID] = None
    pedido_id: Optional[UUID] = None


TextoNoVacio = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class PartidaRevalidacion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    numero: int = Field(gt=0, strict=True, description="Numero de renglon de la cotizacion")
    sku: TextoNoVacio
    cantidad: Decimal = Field(gt=0, allow_inf_nan=False)
    precio_unitario: Decimal = Field(ge=0, allow_inf_nan=False)
    moneda: TextoNoVacio = "MXN"


class RevalidacionSolicitud(BaseModel):
    dias_vigencia: int = Field(gt=0, strict=True, description="Dias de vigencia de la nueva version")
    partidas: List[PartidaRevalidacion] = Field(min_length=1)
    condiciones: TextoNoVacio
    motivo: TextoNoVacio
    model_config = ConfigDict(extra="forbid", json_schema_extra={"examples": [{
        "dias_vigencia": 7,
        "partidas": [{"numero": 1, "sku": "FER-API-DEMO", "cantidad": "2",
                      "precio_unitario": "120.00", "moneda": "MXN"}],
        "condiciones": "Precios y condiciones revalidados con el cliente",
        "motivo": "Cliente solicita revalidar la cotizacion vencida",
    }]})


class CotizacionRevalidadaRespuesta(BaseModel):
    mensaje: str = "Se creó una nueva versión de la cotización y se conservó la anterior."
    cotizacion_id: UUID
    version_anterior: int
    folio: str
    version: int
    estado: str


class ConversionSolicitud(BaseModel):
    aceptada: bool = Field(strict=True, description="El cliente acepto esta version de la cotizacion")
    model_config = ConfigDict(extra="forbid", json_schema_extra={"examples": [{"aceptada": True}]})


class DisponibilidadConsultadaRespuesta(BaseModel):
    sku: str
    solicitada: Decimal = Field(gt=0)
    disponible: Decimal = Field(ge=0)


class PedidoCreadoRespuesta(BaseModel):
    mensaje: str = "Pedido creado y pendiente de confirmación."
    pedido_id: UUID
    estado: Literal["Pendiente"]
    cotizacion_id: UUID
    cotizacion_folio: str
    cotizacion_version: int
    total: Decimal = Field(ge=0)
    moneda: str
    disponibilidad_consultada: List[DisponibilidadConsultadaRespuesta] = Field(
        description="Disponibilidad consultada en S1; no representa una reserva",
    )


class ConfirmacionSolicitud(BaseModel):
    referencia_pago: TextoNoVacio
    pago_autorizado: bool = Field(strict=True, description="Autorizacion de pago simulada del prototipo")
    ubicacion_id: TextoNoVacio
    model_config = ConfigDict(extra="forbid", json_schema_extra={"examples": [{
        "referencia_pago": "PAGO-DEMO-001", "pago_autorizado": True, "ubicacion_id": "S1",
    }]})


class PedidoConfirmadoRespuesta(BaseModel):
    mensaje: str = "Pedido confirmado e inventario reservado."
    pedido_id: UUID
    estado: Literal["Confirmado"]
    referencia_pago: str
    ubicacion_id: str


class CancelacionSolicitud(BaseModel):
    motivo: TextoNoVacio
    model_config = ConfigDict(extra="forbid", json_schema_extra={"examples": [{
        "motivo": "El cliente solicita cancelar el pedido antes del surtido",
    }]})


class PedidoCanceladoRespuesta(BaseModel):
    mensaje: str = "Pedido cancelado y su inventario reservado liberado."
    pedido_id: UUID
    estado: Literal["Cancelado"]


class PedidoConsultaRespuesta(BaseModel):
    mensaje: str = "Pedido consultado."
    pedido_id: UUID
    estado: Literal["Pendiente", "Confirmado", "Cancelado"]
    cotizacion_folio: str = Field(description="Folio de la cotizacion utilizada para crear el pedido")
    cotizacion_version: int = Field(gt=0, description="Version utilizada; se conserva aunque se revalide la cotizacion")
    total: Decimal = Field(ge=0, allow_inf_nan=False, description="Total calculado con las partidas guardadas del pedido")
    moneda: str
