from __future__ import annotations
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional
from uuid import uuid4

class ErrorNegocio(ValueError): pass
class CotizacionVencida(ErrorNegocio): pass
class DisponibilidadInsuficiente(ErrorNegocio): pass
class AccesoDenegado(ErrorNegocio): pass

@dataclass(frozen=True)
class SKU:
    valor: str
    def __post_init__(self):
        if not self.valor.strip(): raise ErrorNegocio('El SKU es obligatorio')

@dataclass(frozen=True)
class Dinero:
    importe: Decimal
    moneda: str = 'MXN'
    def __post_init__(self):
        object.__setattr__(self, 'importe', Decimal(str(self.importe)))
        if not self.importe.is_finite() or self.importe < 0 or not self.moneda:
            raise ErrorNegocio('Importe o moneda invalidos')

@dataclass(frozen=True)
class Vigencia:
    emision: datetime
    vencimiento: datetime
    def __post_init__(self):
        if self.emision.tzinfo is None or self.vencimiento.tzinfo is None:
            raise ErrorNegocio('Las fechas requieren zona horaria')
        if self.vencimiento <= self.emision: raise ErrorNegocio('Vigencia invalida')
    def esta_vigente(self, ahora): return self.emision <= ahora < self.vencimiento

@dataclass(frozen=True)
class Partida:
    numero: int
    sku: SKU
    cantidad: Decimal
    precio: Dinero
    def __post_init__(self):
        object.__setattr__(self, 'cantidad', Decimal(str(self.cantidad)))
        if self.numero < 1 or not self.cantidad.is_finite() or self.cantidad <= 0:
            raise ErrorNegocio('Numero y cantidad de partida deben ser positivos')

def validar_partidas(partidas):
    if not partidas or len({p.numero for p in partidas}) != len(partidas):
        raise ErrorNegocio('Se requieren partidas con numeros distintos')
    if len({p.precio.moneda for p in partidas}) != 1:
        raise ErrorNegocio('Las partidas requieren la misma moneda')

@dataclass(frozen=True)
class EventoDominio:
    tipo: str
    agregado_id: str
    datos: dict
    ocurrido: datetime
    id: str = field(default_factory=lambda: str(uuid4()))

@dataclass
class Cotizacion:
    id: str
    folio: str
    version: int
    cliente_id: str
    vigencia: Vigencia
    partidas: List[Partida]
    condiciones: str
    def __post_init__(self):
        validar_partidas(self.partidas)
        if not self.id or not self.folio or self.version < 1 or not self.cliente_id:
            raise ErrorNegocio('Cotizacion incompleta')
    def estado_en(self, ahora):
        return 'Vigente' if self.vigencia.esta_vigente(ahora) else 'Vencida'
    def revalidar(self, ahora, dias, partidas, condiciones):
        if ahora < self.vigencia.emision: raise ErrorNegocio('La cotizacion aun no fue emitida')
        if self.vigencia.esta_vigente(ahora):
            raise ErrorNegocio('Este caso revalida cotizaciones vencidas')
        if dias <= 0 or not condiciones.strip(): raise ErrorNegocio('Indique vigencia y condiciones')
        return replace(self, version=self.version+1,
                       vigencia=Vigencia(ahora, ahora+timedelta(days=dias)),
                       partidas=list(partidas), condiciones=condiciones)
    def convertir(self, ahora, aceptada):
        if not self.vigencia.esta_vigente(ahora):
            raise CotizacionVencida('Revalide precio, disponibilidad y condiciones')
        if not aceptada: raise ErrorNegocio('Se requiere aceptacion del cliente')
        return Pedido(str(uuid4()), self.cliente_id, self.id, self.folio,
                      self.version, list(self.partidas))

class EstadoPedido(str, Enum):
    PENDIENTE='Pendiente'
    CONFIRMADO='Confirmado'
    CANCELADO='Cancelado'

@dataclass(frozen=True)
class AutorizacionPago:
    referencia: str
    autorizada: bool

@dataclass
class Pedido:
    id: str
    cliente_id: str
    cotizacion_id: str
    cotizacion_folio: str
    cotizacion_version: int
    partidas: List[Partida]
    estado: EstadoPedido = EstadoPedido.PENDIENTE
    surtido: bool = False
    referencia_pago: Optional[str] = None
    def __post_init__(self): validar_partidas(self.partidas)
    @property
    def total(self):
        return Dinero(sum((p.cantidad*p.precio.importe for p in self.partidas), Decimal(0)), self.partidas[0].precio.moneda)
    def cantidades_por_sku(self):
        resultado={}
        for p in self.partidas:
            resultado[p.sku.valor]=resultado.get(p.sku.valor, Decimal(0))+p.cantidad
        return resultado
    def confirmar(self, pago):
        if self.estado != EstadoPedido.PENDIENTE: raise ErrorNegocio('Pedido no pendiente')
        if not pago.autorizada or not pago.referencia.strip(): raise ErrorNegocio('Pago no autorizado')
        self.estado, self.referencia_pago=EstadoPedido.CONFIRMADO, pago.referencia
    def cancelar(self, motivo):
        if self.estado != EstadoPedido.CONFIRMADO or self.surtido:
            raise ErrorNegocio('Solo puede cancelarse un pedido confirmado aun no surtido')
        if not motivo.strip(): raise ErrorNegocio('Indique motivo de cancelacion')
        self.estado=EstadoPedido.CANCELADO

@dataclass
class InventarioUbicacion:
    sku: SKU
    ubicacion_id: str
    existencia_fisica: Decimal
    en_transito: Decimal = Decimal(0)
    reservas: Dict[str, Decimal] = field(default_factory=dict)
    def __post_init__(self):
        self.existencia_fisica=Decimal(str(self.existencia_fisica))
        self.en_transito=Decimal(str(self.en_transito))
        self.validar()
    @property
    def comprometida(self): return sum(self.reservas.values(), Decimal(0))
    @property
    def disponible(self): return self.existencia_fisica-self.comprometida
    def validar(self):
        if any(not v.is_finite() or v < 0 for v in [self.existencia_fisica,self.en_transito,*self.reservas.values()]) or self.disponible < 0:
            raise ErrorNegocio('Inventario negativo, no finito o sobrecomprometido')
    def reservar(self, pedido, cantidad):
        if pedido.estado != EstadoPedido.CONFIRMADO: raise ErrorNegocio('Solo un pedido confirmado puede reservar')
        if cantidad <= 0 or pedido.id in self.reservas: raise ErrorNegocio('Reserva invalida o duplicada')
        if self.disponible < cantidad: raise DisponibilidadInsuficiente('Disponibilidad insuficiente para '+self.sku.valor)
        self.reservas[pedido.id]=cantidad
        self.validar()
    def liberar(self, pedido_id):
        if pedido_id not in self.reservas: raise ErrorNegocio('Reserva inexistente')
        del self.reservas[pedido_id]

@dataclass(frozen=True)
class CuentaCredito:
    cliente_id: str
    activo: bool
    bloqueado: bool
    limite: Dinero
    saldo: Dinero
    def evaluar(self, importe):
        if importe.moneda != self.limite.moneda or self.saldo.moneda != self.limite.moneda:
            raise ErrorNegocio('Monedas incompatibles')
        return self.activo and not self.bloqueado and importe.importe <= self.limite.importe-self.saldo.importe

class PoliticaCredito:
    def evaluar_normal(self, cuenta, importe):
        return 'AutorizadoNormal' if cuenta.evaluar(importe) else 'EnRevision'
