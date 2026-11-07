"""E9: BR02/BR03 y US04/US05, vigencia e historial de cotizaciones.

Se usa un reloj fijo en UTC y el adaptador Memory. No acredita persistencia SQL.
"""

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import unittest

from ferremax.application.services import Actor, CotizacionService
from ferremax.domain.model import (
    Cotizacion,
    CotizacionVencida,
    Dinero,
    EstadoPedido,
    InventarioUbicacion,
    Partida,
    SKU,
    Vigencia,
)
from ferremax.infrastructure.memory import MemoryStore, MemoryUnitOfWork


class CotizacionesE9Test(unittest.TestCase):
    def setUp(self):
        self.vencimiento = datetime(2026, 11, 4, 12, 0, tzinfo=timezone.utc)
        self.ahora = self.vencimiento + timedelta(minutes=1)
        self.sku = SKU("FER-P001")
        self.vendedor = Actor("E9-VENDEDOR", "Vendedor")
        self.cotizacion = Cotizacion(
            id="E9-COTIZACION",
            folio="COT-001",
            version=1,
            cliente_id="E9-CLIENTE",
            vigencia=Vigencia(self.vencimiento - timedelta(days=7), self.vencimiento),
            partidas=[Partida(1, self.sku, Decimal("2"), Dinero(Decimal("100.00")))],
            condiciones="Condiciones de la version original",
        )
        self.store = MemoryStore()
        self.store.datos["cotizaciones"][(self.cotizacion.id, 1)] = self.cotizacion
        self.store.datos["inventarios"][(self.sku.valor, "S1")] = (
            InventarioUbicacion(self.sku, "S1", Decimal("10"))
        )
        self.servicio = CotizacionService(
            lambda: MemoryUnitOfWork(self.store), lambda: self.ahora
        )

    def test_e9_cot_01_exito_revalidar_conserva_historial_y_pedido_usa_version_nueva(self):
        # Arrange: version 1 vencida, con precios y condiciones que conservaremos.
        original = deepcopy(self.cotizacion)
        partidas_nuevas = [
            Partida(1, self.sku, Decimal("2"), Dinero(Decimal("120.00")))
        ]

        # Act: revalidar y convertir la version nueva con aceptacion del cliente.
        revalidada = self.servicio.revalidar(
            self.vendedor,
            original.id,
            1,
            7,
            partidas_nuevas,
            "Precios y condiciones revalidados",
            "Cliente solicita revalidacion de la cotizacion vencida",
        )
        resultado = self.servicio.convertir(self.vendedor, original.id, 2, True)

        # Assert: ambas versiones existen y la primera permanece intacta.
        versiones = self.store.datos["cotizaciones"]
        self.assertEqual(set(versiones), {(original.id, 1), (original.id, 2)})
        self.assertEqual(versiones[(original.id, 1)], original)
        nueva = versiones[(original.id, 2)]
        self.assertEqual(revalidada["version"], 2)
        self.assertEqual(revalidada["estado"], "Vigente")
        self.assertEqual(nueva.folio, original.folio)
        self.assertEqual(nueva.vigencia.emision, self.ahora)
        self.assertEqual(nueva.vigencia.vencimiento, self.ahora + timedelta(days=7))
        self.assertEqual(nueva.partidas, partidas_nuevas)
        self.assertEqual(nueva.condiciones, "Precios y condiciones revalidados")

        # El pedido conserva la referencia y los precios de la version aceptada.
        self.assertEqual(len(self.store.datos["pedidos"]), 1)
        pedido = self.store.datos["pedidos"][resultado["pedido_id"]]
        self.assertEqual(pedido.cotizacion_id, original.id)
        self.assertEqual(pedido.cotizacion_folio, original.folio)
        self.assertEqual(pedido.cotizacion_version, 2)
        self.assertEqual(pedido.partidas, partidas_nuevas)
        self.assertEqual(pedido.total.importe, Decimal("240.00"))
        self.assertEqual(pedido.estado, EstadoPedido.PENDIENTE)
        inventario = self.store.datos["inventarios"][(self.sku.valor, "S1")]
        self.assertEqual(inventario.reservas, {})
        self.assertEqual(inventario.disponible, Decimal("10"))
        self.assertEqual(
            [evento.tipo for evento in self.store.datos["outbox"]],
            ["CotizacionRevalidada", "PedidoCreado"],
        )

    def test_e9_cot_02_error_version_vencida_no_crea_pedido_ni_modifica_datos(self):
        # El reloj marca las 12:01, un minuto despues del vencimiento.
        antes = deepcopy(self.store.datos)

        with self.assertRaises(CotizacionVencida) as rechazo:
            self.servicio.convertir(self.vendedor, self.cotizacion.id, 1, True)
        self.rechazo_observado = {
            "tipo": type(rechazo.exception).__name__, "mensaje": str(rechazo.exception)
        }

        self.assertEqual(self.store.datos["pedidos"], {})
        self.assertEqual(self.store.datos["outbox"], [])
        self.assertEqual(self.store.datos["auditoria"], [])
        self.assertEqual(self.store.datos, antes)

    def test_e9_cot_03_limite_instante_del_vencimiento_no_permite_conversion(self):
        # Exactamente 12:00: el extremo final de la vigencia esta excluido.
        self.ahora = self.vencimiento
        antes = deepcopy(self.store.datos)

        with self.assertRaises(CotizacionVencida) as rechazo:
            self.servicio.convertir(self.vendedor, self.cotizacion.id, 1, True)
        self.rechazo_observado = {
            "tipo": type(rechazo.exception).__name__, "mensaje": str(rechazo.exception)
        }

        self.assertEqual(self.store.datos["pedidos"], {})
        self.assertEqual(self.store.datos["outbox"], [])
        self.assertEqual(self.store.datos["auditoria"], [])
        self.assertEqual(self.store.datos, antes)


if __name__ == "__main__":
    unittest.main()
