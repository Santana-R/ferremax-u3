from dataclasses import dataclass
from decimal import Decimal
from ferremax.domain.model import AccesoDenegado, ErrorNegocio, EventoDominio

@dataclass(frozen=True)
class Actor:
    id: str
    rol: str
    def exigir(self, rol):
        if not self.id or self.rol != rol: raise AccesoDenegado('La operacion requiere el rol '+rol)

def foto_cotizacion(c, ahora):
    return {'folio':c.folio,'version':c.version,'estado':c.estado_en(ahora),
            'vigencia':c.vigencia.vencimiento.isoformat(),'condiciones':c.condiciones,
            'partidas':[{'numero':p.numero,'sku':p.sku.valor,'cantidad':str(p.cantidad),
                         'precio':str(p.precio.importe),'moneda':p.precio.moneda} for p in c.partidas]}
def foto_inventario(inv):
    return {'sku':inv.sku.valor,'ubicacion_id':inv.ubicacion_id,
            'fisica':str(inv.existencia_fisica),'comprometida':str(inv.comprometida),
            'disponible':str(inv.disponible),'reservas':{pid:str(q) for pid,q in inv.reservas.items()}}

class CotizacionService:
    def __init__(self, uow_factory, reloj): self.uow_factory,self.reloj=uow_factory,reloj
    def revalidar(self, actor, cotizacion_id, version, dias, partidas, condiciones, motivo):
        actor.exigir('Vendedor')
        if not motivo.strip(): raise ErrorNegocio('Indique motivo de revalidacion')
        with self.uow_factory() as uow:
            original=uow.cotizaciones.obtener(cotizacion_id,version)
            antes=foto_cotizacion(original,self.reloj())
            for p in sorted(partidas,key=lambda p:p.sku.valor):
                uow.inventarios.obtener_para_actualizar(p.sku.valor,'S1')
            nueva=original.revalidar(self.reloj(),dias,partidas,condiciones)
            uow.cotizaciones.guardar_nueva_version(nueva)
            despues=foto_cotizacion(nueva,self.reloj())
            uow.registrar(actor.id,'RevalidarCotizacion',nueva.id,antes,despues,motivo,
                          EventoDominio('CotizacionRevalidada',nueva.id,despues,self.reloj()))
            uow.commit()
            return {'folio':nueva.folio,'version':nueva.version,'estado':nueva.estado_en(self.reloj())}
    def convertir(self, actor, cotizacion_id, version, aceptada):
        actor.exigir('Vendedor')
        with self.uow_factory() as uow:
            c=uow.cotizaciones.obtener(cotizacion_id,version)
            p=c.convertir(self.reloj(),aceptada)
            disponibilidad=[]
            for sku,cantidad in sorted(p.cantidades_por_sku().items()):
                inv=uow.inventarios.obtener_para_actualizar(sku,'S1')
                disponibilidad.append({'sku':sku,'solicitada':str(cantidad),'disponible':str(inv.disponible)})
            uow.pedidos.guardar(p)
            resultado={'pedido_id':p.id,'estado':p.estado.value,'cotizacion_folio':c.folio,
                       'cotizacion_version':c.version,'disponibilidad_consultada':disponibilidad}
            uow.registrar(actor.id,'CrearPedidoDesdeCotizacion',p.id,{},resultado,'Cotizacion aceptada por cliente',
                          EventoDominio('PedidoCreado',p.id,resultado,self.reloj()))
            uow.commit()
            return resultado

class PedidoService:
    def __init__(self, uow_factory, reloj): self.uow_factory,self.reloj=uow_factory,reloj
    def confirmar(self, actor, pedido_id, pago, ubicacion_id):
        actor.exigir('Caja')
        with self.uow_factory() as uow:
            p=uow.pedidos.obtener(pedido_id)
            inventarios=[(uow.inventarios.obtener_para_actualizar(sku,ubicacion_id),q)
                         for sku,q in sorted(p.cantidades_por_sku().items())]
            antes={'estado':p.estado.value,'inventarios':[foto_inventario(i) for i,_ in inventarios]}
            p.confirmar(pago)
            for inv,cantidad in inventarios:
                inv.reservar(p,cantidad)
                uow.inventarios.guardar(inv)
            uow.pedidos.guardar(p)
            resultado={'pedido_id':p.id,'estado':p.estado.value,'referencia_pago':pago.referencia,'ubicacion_id':ubicacion_id}
            despues={**resultado,'inventarios':[foto_inventario(i) for i,_ in inventarios]}
            uow.registrar(actor.id,'ConfirmarPedido',p.id,antes,despues,'Pago autorizado registrado por Caja',
                          EventoDominio('PedidoConfirmado',p.id,resultado,self.reloj()))
            uow.commit()
            return resultado
    def cancelar(self, actor, pedido_id, motivo):
        actor.exigir('VendedorAutorizadoCancelacion')
        with self.uow_factory() as uow:
            p=uow.pedidos.obtener(pedido_id)
            ubicacion=uow.inventarios.ubicacion_reserva(pedido_id)
            inventarios=[uow.inventarios.obtener_para_actualizar(sku,ubicacion) for sku in sorted(p.cantidades_por_sku())]
            antes={'estado':p.estado.value,'inventarios':[foto_inventario(i) for i in inventarios]}
            p.cancelar(motivo)
            for inv in inventarios:
                inv.liberar(p.id)
                uow.inventarios.guardar(inv)
            uow.pedidos.guardar(p)
            resultado={'pedido_id':p.id,'estado':p.estado.value}
            despues={**resultado,'inventarios':[foto_inventario(i) for i in inventarios]}
            uow.registrar(actor.id,'CancelarPedido',p.id,antes,despues,motivo,
                          EventoDominio('PedidoCancelado',p.id,resultado,self.reloj()))
            uow.commit()
            return resultado
