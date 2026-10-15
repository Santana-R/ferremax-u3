from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from dataclasses import replace
from decimal import Decimal
import unittest
from ferremax.demo import crear_contexto
from ferremax.application.services import Actor,CotizacionService,PedidoService
from ferremax.application.cqrs import ConsultarDisponibilidad,ConsultarDisponibilidadHandler,ConsultarPedido,ConsultarPedidoHandler
from ferremax.domain.model import AutorizacionPago,CotizacionVencida,DisponibilidadInsuficiente,ErrorNegocio,EstadoPedido,InventarioUbicacion,Partida,SKU,Dinero,CuentaCredito,PoliticaCredito
from ferremax.infrastructure.memory import MemoryUnitOfWork,MemoryReader

class ArquitecturaTest(unittest.TestCase):
    def setUp(self):
        self.store,self.c,self.ahora=crear_contexto()
        self.factory=lambda:MemoryUnitOfWork(self.store)
        self.cs=CotizacionService(self.factory,lambda:self.ahora)
        self.ps=PedidoService(self.factory,lambda:self.ahora)
        self.v=Actor('V1','Vendedor'); self.caja=Actor('C1','Caja')
    def pedido(self):
        if (self.c.id,2) not in self.store.datos['cotizaciones']:
            self.cs.revalidar(self.v,self.c.id,1,7,self.c.partidas,self.c.condiciones,'Revalidacion')
        return self.cs.convertir(self.v,self.c.id,2,True)['pedido_id']
    def confirmar(self,id): return self.ps.confirmar(self.caja,id,AutorizacionPago('PAGO',True),'S1')
    def test_vencida_no_crea_pedido(self):
        with self.assertRaises(CotizacionVencida): self.cs.convertir(self.v,self.c.id,1,True)
        self.assertEqual(self.store.datos['pedidos'],{})
    def test_revalidacion_conserva_version_y_no_reserva(self):
        self.pedido()
        self.assertEqual(set(self.store.datos['cotizaciones']),{(self.c.id,1),(self.c.id,2)})
        self.assertEqual(self.store.datos['inventarios'][('SKU-DEMO','S1')].comprometida,0)
    def test_conversion_requiere_aceptacion(self):
        self.pedido(); n=len(self.store.datos['pedidos'])
        with self.assertRaises(ErrorNegocio): self.cs.convertir(self.v,self.c.id,2,False)
        self.assertEqual(len(self.store.datos['pedidos']),n)
    def test_confirmacion_reserva_auditoria_evento(self):
        id=self.pedido(); self.confirmar(id)
        self.assertEqual(self.store.datos['pedidos'][id].estado,EstadoPedido.CONFIRMADO)
        self.assertEqual(self.store.datos['inventarios'][('SKU-DEMO','S1')].disponible,0)
        a=self.store.datos['auditoria'][-1]
        self.assertEqual(a['accion'],'ConfirmarPedido')
        self.assertEqual(a['antes']['inventarios'][0]['comprometida'],'0')
        self.assertEqual(a['despues']['inventarios'][0]['comprometida'],'1')
        self.assertEqual(self.store.datos['outbox'][-1].tipo,'PedidoConfirmado')
    def test_pago_rechazado_revierte_estado(self):
        id=self.pedido(); previo=deepcopy(self.store.datos)
        with self.assertRaises(ErrorNegocio): self.ps.confirmar(self.caja,id,AutorizacionPago('PAGO',False),'S1')
        self.assertEqual(self.store.datos,previo)
    def test_fallo_despues_primera_reserva_revierte_todo(self):
        id=self.pedido()
        self.store.datos['pedidos'][id].partidas.append(Partida(2,SKU('ZZ-SIN-STOCK'),Decimal(1),Dinero(Decimal(20))))
        self.store.datos['inventarios'][('ZZ-SIN-STOCK','S1')]=InventarioUbicacion(SKU('ZZ-SIN-STOCK'),'S1',Decimal(0))
        previo=deepcopy(self.store.datos)
        guardados=[]
        class Observado(MemoryUnitOfWork):
            def __enter__(inner):
                super(Observado,inner).__enter__()
                guardar=inner.inventarios.guardar
                def spy(inv): guardados.append(inv.sku.valor); guardar(inv)
                inner.inventarios.guardar=spy
                return inner
        servicio=PedidoService(lambda:Observado(self.store),lambda:self.ahora)
        with self.assertRaises(DisponibilidadInsuficiente): servicio.confirmar(self.caja,id,AutorizacionPago('PAGO',True),'S1')
        self.assertEqual(guardados,['SKU-DEMO'])
        self.assertEqual(self.store.datos,previo)
    def test_partidas_mismo_sku_se_acumulan(self):
        id=self.pedido(); self.store.datos['pedidos'][id].partidas.append(Partida(2,SKU('SKU-DEMO'),Decimal(1),Dinero(Decimal(100))))
        with self.assertRaises(DisponibilidadInsuficiente): self.confirmar(id)
        self.assertEqual(self.store.datos['inventarios'][('SKU-DEMO','S1')].comprometida,0)
    def test_dos_pedidos_ultima_unidad(self):
        ids=[self.pedido(),self.pedido()]
        def intentar(id):
            try: self.confirmar(id); return 'Confirmado'
            except DisponibilidadInsuficiente: return 'Rechazado'
        with ThreadPoolExecutor(max_workers=2) as pool: resultados=list(pool.map(intentar,ids))
        self.assertCountEqual(resultados,['Confirmado','Rechazado'])
    def test_cancelar_libera_reserva(self):
        id=self.pedido(); self.confirmar(id)
        self.ps.cancelar(Actor('V2','VendedorAutorizadoCancelacion'),id,'Cliente cancela')
        self.assertEqual(self.store.datos['inventarios'][('SKU-DEMO','S1')].disponible,1)
    def test_no_cancelar_surtido(self):
        id=self.pedido(); self.confirmar(id); self.store.datos['pedidos'][id].surtido=True
        with self.assertRaises(ErrorNegocio): self.ps.cancelar(Actor('V2','VendedorAutorizadoCancelacion'),id,'Motivo')
    def test_query_no_modifica_y_sku_inexistente(self):
        previo=deepcopy(self.store.datos); h=ConsultarDisponibilidadHandler(MemoryReader(self.store))
        self.assertFalse(h.handle(ConsultarDisponibilidad('NO-EXISTE'),self.v)['encontrado'])
        self.assertEqual(len(h.handle(ConsultarDisponibilidad('SKU-DEMO'),self.v)['ubicaciones']),4)
        self.assertEqual(self.store.datos,previo)
    def test_rol_incorrecto_no_confirma(self):
        id=self.pedido()
        with self.assertRaises(ErrorNegocio): self.ps.confirmar(self.v,id,AutorizacionPago('PAGO',True),'S1')
    def test_credito_bloqueado_insuficiente_inactivo(self):
        for activo,bloqueado,saldo in [(True,True,'0'),(False,False,'0'),(True,False,'95')]:
            cuenta=CuentaCredito('C',activo,bloqueado,Dinero(Decimal(100)),Dinero(Decimal(saldo)))
            self.assertEqual(PoliticaCredito().evaluar_normal(cuenta,Dinero(Decimal(10))),'EnRevision')
    def test_transito_no_es_disponible(self):
        i=InventarioUbicacion(SKU('X'),'AC',Decimal(3),Decimal(8),{'P':Decimal(2)})
        self.assertEqual(i.disponible,1)
    def test_valores_invalidos(self):
        for valor in ['NaN','-1','Infinity']:
            with self.assertRaises(ErrorNegocio): Dinero(Decimal(valor))
    def test_vigencia_limite_excluido(self):
        c=self.c.revalidar(self.ahora,7,self.c.partidas,self.c.condiciones)
        self.assertEqual(c.estado_en(c.vigencia.vencimiento),'Vencida')
        self.assertEqual(c.estado_en(self.ahora),'Vigente')
    def test_no_reservar_pedido_pendiente(self):
        id=self.pedido(); inv=self.store.datos['inventarios'][('SKU-DEMO','S1')]
        with self.assertRaises(ErrorNegocio): inv.reservar(self.store.datos['pedidos'][id],Decimal(1))
    def test_no_confirmar_dos_veces(self):
        id=self.pedido(); self.confirmar(id); previo=deepcopy(self.store.datos)
        with self.assertRaises(ErrorNegocio): self.confirmar(id)
        self.assertEqual(self.store.datos,previo)
    def test_resumen_pedido_dto(self):
        id=self.pedido(); r=ConsultarPedidoHandler(MemoryReader(self.store)).handle(ConsultarPedido(id),self.v)
        self.assertEqual(r['estado'],'Pendiente'); self.assertEqual(r['total'],'100.00')
    def test_revalidacion_audita_precio_y_condiciones(self):
        nueva=replace(self.c.partidas[0],precio=Dinero(Decimal(120)))
        self.cs.revalidar(self.v,self.c.id,1,7,[nueva],'Condicion revisada','Motivo')
        a=self.store.datos['auditoria'][-1]
        self.assertEqual(a['antes']['partidas'][0]['precio'],'100.00')
        self.assertEqual(a['despues']['partidas'][0]['precio'],'120')
        self.assertEqual(a['despues']['condiciones'],'Condicion revisada')
if __name__=='__main__': unittest.main()
