import os
from dataclasses import replace
from datetime import timedelta
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from uuid import uuid4
import unittest
from ferremax.demo import crear_contexto
from ferremax.domain.model import SKU,Vigencia,AutorizacionPago,DisponibilidadInsuficiente
from ferremax.application.services import Actor,PedidoService

@unittest.skipUnless(os.environ.get('TEST_DATABASE_URL'),'Integracion PostgreSQL pendiente: falta TEST_DATABASE_URL')
class PostgreSQLTest(unittest.TestCase):
    def test_dos_conexiones_ultima_unidad(self):
        from ferremax.infrastructure.postgres import PostgresUnitOfWork,PostgresReader
        url=os.environ['TEST_DATABASE_URL']
        _,c,ahora=crear_contexto(); c.folio='TEST-'+uuid4().hex[:10]
        sku='TEST-'+uuid4().hex[:12]
        c.partidas=[replace(c.partidas[0],sku=SKU(sku))]
        c.vigencia=Vigencia(ahora,ahora+timedelta(days=7))
        pedidos=[c.convertir(ahora,True),c.convertir(ahora,True)]
        with PostgresUnitOfWork(url) as uow:
            uow.cotizaciones.guardar_nueva_version(c)
            for p in pedidos: uow.pedidos.guardar(p)
            uow.conn.execute("INSERT INTO ferremax_u3.inventario(sku,ubicacion_id,existencia_fisica) VALUES(%s,'S1',1)",(sku,))
            uow.commit()
        servicio=PedidoService(lambda:PostgresUnitOfWork(url),lambda:ahora)
        def intentar(p):
            try: servicio.confirmar(Actor('caja-test','Caja'),p.id,AutorizacionPago('TEST-PAGO',True),'S1'); return 'Confirmado'
            except DisponibilidadInsuficiente: return 'Rechazado'
        with ThreadPoolExecutor(max_workers=2) as pool: resultados=list(pool.map(intentar,pedidos))
        self.assertCountEqual(resultados,['Confirmado','Rechazado'])
        lector=PostgresReader(url)
        self.assertEqual(Decimal(lector.consultar_disponibilidad(sku)[0]['disponible']),0)
        self.assertCountEqual([lector.consultar_pedido(p.id)['estado'] for p in pedidos],['Confirmado','Pendiente'])
        # Registros sinteticos con SKU unico conservados como evidencia; solo proyecto academico.
