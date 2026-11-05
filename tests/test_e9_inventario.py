"""E9: BR04/BR05 y US09, confirmacion y reserva en una ubicacion.

Cada caso parte de 10 unidades fisicas, 7 reservadas y 5 en transito.
Se prueba el servicio con el adaptador Memory: no es integracion PostgreSQL.
"""

from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal
import unittest

from ferremax.application.services import Actor, PedidoService
from ferremax.domain.model import (
    AutorizacionPago,
    Dinero,
    DisponibilidadInsuficiente,
    EstadoPedido,
    InventarioUbicacion,
    Partida,
    Pedido,
    SKU,
)
from ferremax.infrastructure.memory import MemoryStore, MemoryUnitOfWork


class InventarioE9Test(unittest.TestCase):
    """Exito, error y limite con datos nuevos para cada prueba."""

    def setUp(self):
        self.sku = SKU("FER-P001")
        self.ubicacion = "S1"
        self.pedido_id = "E9-PEDIDO-NUEVO"
        self.pedido_anterior_id = "E9-PEDIDO-ANTERIOR"
        self.pago = AutorizacionPago("E9-PAGO-SIMULADO", True)
        self.caja = Actor("E9-CAJA", "Caja")
        self.ahora = datetime(2026, 11, 4, 18, 0, tzinfo=timezone.utc)
        self.store = MemoryStore()

        # Las siete unidades comprometidas pertenecen a otro pedido confirmado.
        anterior = self._crear_pedido(self.pedido_anterior_id, "7")
        anterior.confirmar(AutorizacionPago("E9-PAGO-ANTERIOR", True))
        self.store.datos["pedidos"][anterior.id] = anterior
        self.store.datos["inventarios"][(self.sku.valor, self.ubicacion)] = (
            InventarioUbicacion(
                sku=self.sku,
                ubicacion_id=self.ubicacion,
                existencia_fisica=Decimal("10"),
                en_transito=Decimal("5"),
                reservas={anterior.id: Decimal("7")},
            )
        )
        self.servicio = PedidoService(
            lambda: MemoryUnitOfWork(self.store), lambda: self.ahora
        )

    def _crear_pedido(self, pedido_id, cantidad):
        return Pedido(
            id=pedido_id,
            cliente_id="E9-CLIENTE",
            cotizacion_id="E9-COTIZACION",
            cotizacion_folio="E9-COT-001",
            cotizacion_version=1,
            partidas=[
                Partida(1, self.sku, Decimal(cantidad), Dinero(Decimal("100.00")))
            ],
        )

    def _preparar_pedido(self, cantidad):
        pedido = self._crear_pedido(self.pedido_id, cantidad)
        self.store.datos["pedidos"][pedido.id] = pedido

    def _confirmar(self):
        return self.servicio.confirmar(
            self.caja, self.pedido_id, self.pago, self.ubicacion
        )

    def _inventario_guardado(self):
        # El UoW guarda copias: consultar el estado persistido en MemoryStore.
        return self.store.datos["inventarios"][(self.sku.valor, self.ubicacion)]

    def _comprobar_confirmacion(self, resultado, cantidad, comprometida, disponible):
        pedido = self.store.datos["pedidos"][self.pedido_id]
        inventario = self._inventario_guardado()
        self.assertEqual(resultado["estado"], "Confirmado")
        self.assertEqual(pedido.estado, EstadoPedido.CONFIRMADO)
        self.assertEqual(pedido.referencia_pago, self.pago.referencia)
        self.assertEqual(inventario.existencia_fisica, Decimal("10"))
        self.assertEqual(inventario.en_transito, Decimal("5"))
        self.assertEqual(inventario.comprometida, Decimal(comprometida))
        self.assertEqual(inventario.disponible, Decimal(disponible))
        self.assertEqual(
            inventario.reservas,
            {self.pedido_anterior_id: Decimal("7"), self.pedido_id: Decimal(cantidad)},
        )
        self.assertEqual(len(self.store.datos["auditoria"]), 1)
        self.assertEqual(self.store.datos["auditoria"][0]["accion"], "ConfirmarPedido")
        eventos = self.store.datos["outbox"]
        self.assertEqual(len(eventos), 1)
        self.assertEqual(eventos[0].tipo, "PedidoConfirmado")
        self.assertEqual(eventos[0].agregado_id, self.pedido_id)

    def test_e9_inv_01_exito_reservar_dos_deja_una_disponible(self):
        # Arrange: existe un pedido pendiente que solicita dos unidades.
        self._preparar_pedido("2")

        # Act: Caja confirma con una autorizacion de pago simulada.
        resultado = self._confirmar()

        # Assert: se reservan dos, se conservan las siete previas y queda una.
        self._comprobar_confirmacion(resultado, cantidad="2", comprometida="9", disponible="1")

    def test_e9_inv_02_error_pedir_cuatro_conserva_pedido_e_inventario(self):
        self._preparar_pedido("4")
        antes = deepcopy(self.store.datos)

        with self.assertRaisesRegex(
            DisponibilidadInsuficiente, "Disponibilidad insuficiente"
        ):
            self._confirmar()

        pedido = self.store.datos["pedidos"][self.pedido_id]
        inventario = self._inventario_guardado()
        self.assertEqual(pedido.estado, EstadoPedido.PENDIENTE)
        self.assertIsNone(pedido.referencia_pago)
        self.assertEqual(inventario.comprometida, Decimal("7"))
        self.assertEqual(inventario.disponible, Decimal("3"))
        self.assertNotIn(self.pedido_id, inventario.reservas)
        self.assertEqual(self.store.datos["outbox"], [])
        self.assertEqual(self.store.datos["auditoria"], [])
        # Tambien protege el pedido anterior, existencia fisica y transito.
        self.assertEqual(self.store.datos, antes)

    def test_e9_inv_03_limite_reservar_tres_agota_el_disponible(self):
        self._preparar_pedido("3")

        resultado = self._confirmar()

        self._comprobar_confirmacion(resultado, cantidad="3", comprometida="10", disponible="0")


if __name__ == "__main__":
    unittest.main()
