from datetime import datetime,timedelta,timezone
from decimal import Decimal
from uuid import uuid4
import json
from ferremax.domain.model import Cotizacion,Partida,SKU,Dinero,Vigencia,InventarioUbicacion
from ferremax.application.services import Actor,CotizacionService,PedidoService
from ferremax.application.cqrs import ConfirmarPedido,ConfirmarPedidoHandler,CancelarPedido,CancelarPedidoHandler,ConsultarDisponibilidad,ConsultarDisponibilidadHandler
from ferremax.infrastructure.memory import MemoryStore,MemoryUnitOfWork,MemoryReader

def crear_contexto(cantidad=Decimal(1)):
    ahora=datetime.now(timezone.utc)
    c=Cotizacion(str(uuid4()),'DEMO-U3',1,'CLIENTE-SIMULADO',
        Vigencia(ahora-timedelta(days=8),ahora-timedelta(days=1)),
        [Partida(1,SKU('SKU-DEMO'),Decimal(1),Dinero(Decimal('100.00')))],'Condiciones comerciales simuladas')
    store=MemoryStore()
    store.datos['cotizaciones'][(c.id,c.version)]=c
    for ubicacion,fisica in [('S1',cantidad),('S2',Decimal(3)),('S3',Decimal(0)),('AC',Decimal(4))]:
        store.datos['inventarios'][('SKU-DEMO',ubicacion)]=InventarioUbicacion(SKU('SKU-DEMO'),ubicacion,fisica)
    return store,c,ahora
def main():
    store,c,ahora=crear_contexto()
    factory=lambda:MemoryUnitOfWork(store)
    cs=CotizacionService(factory,lambda:ahora)
    ps=PedidoService(factory,lambda:ahora)
    v=Actor('vendedor-demo','Vendedor')
    salida=[ConsultarDisponibilidadHandler(MemoryReader(store)).handle(ConsultarDisponibilidad('SKU-DEMO'),v)]
    salida.append(cs.revalidar(v,c.id,1,7,c.partidas,c.condiciones,'Revalidacion solicitada'))
    creado=cs.convertir(v,c.id,2,True); salida.append(creado)
    salida.append(ConfirmarPedidoHandler(ps).handle(ConfirmarPedido(creado['pedido_id'],'PAGO-DEMO',True,'S1'),Actor('caja-demo','Caja')))
    salida.append(CancelarPedidoHandler(ps).handle(CancelarPedido(creado['pedido_id'],'Cliente cancela antes del surtido'),Actor('vendedor-demo','VendedorAutorizadoCancelacion')))
    print(json.dumps(salida,ensure_ascii=False,indent=2))
if __name__=='__main__': main()
