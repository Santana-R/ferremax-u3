from dataclasses import dataclass
from ferremax.domain.model import AutorizacionPago

@dataclass(frozen=True)
class ConfirmarPedido:
    pedido_id: str
    referencia_pago: str
    pago_autorizado: bool
    ubicacion_id: str
@dataclass(frozen=True)
class CancelarPedido:
    pedido_id: str
    motivo: str
@dataclass(frozen=True)
class ConsultarDisponibilidad:
    sku: str
@dataclass(frozen=True)
class ConsultarPedido:
    pedido_id: str
class ConfirmarPedidoHandler:
    def __init__(self, servicio): self.servicio=servicio
    def handle(self, comando, actor):
        return self.servicio.confirmar(actor,comando.pedido_id,
          AutorizacionPago(comando.referencia_pago,comando.pago_autorizado),comando.ubicacion_id)
class CancelarPedidoHandler:
    def __init__(self, servicio): self.servicio=servicio
    def handle(self, comando, actor): return self.servicio.cancelar(actor,comando.pedido_id,comando.motivo)
class ConsultarDisponibilidadHandler:
    def __init__(self, lector): self.lector=lector
    def handle(self, consulta, actor):
        actor.exigir('Vendedor')
        filas=self.lector.consultar_disponibilidad(consulta.sku)
        return {'sku':consulta.sku,'encontrado':bool(filas),'ubicaciones':filas}
class ConsultarPedidoHandler:
    def __init__(self, lector): self.lector=lector
    def handle(self, consulta, actor):
        actor.exigir('Vendedor')
        return self.lector.consultar_pedido(consulta.pedido_id)
