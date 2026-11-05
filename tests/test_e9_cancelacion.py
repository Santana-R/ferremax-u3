"""E9: BR06 y US10, cancelacion y liberacion de la reserva propia.

Cada caso parte de un pedido confirmado con dos unidades reservadas,
siete reservadas para otro pedido y una unidad disponible. Adaptador Memory.
"""

from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal
import unittest

from ferremax.application.services import Actor, PedidoService
from ferremax.domain.model import (
    AutorizacionPago,
    Dinero,
    ErrorNegocio,
    EstadoPedido,
    InventarioUbicacion,
    Partida,
    Pedido,
    SKU,
)
from ferremax.infrastructure.memory import MemoryStore, MemoryUnitOfWork


class CancelacionE9Test(unittest.TestCase):
    def setUp(self):
        self.sku = SKU("FER-P001")
        self.pedido_id = "E9-PEDIDO-CANCELAR"
        self.otro_id = "E9-OTRO-PEDIDO"
        self.motivo = "Cliente cancela antes del surtido"
        self.autorizado = Actor("E9-VENDEDOR", "VendedorAutorizadoCancelacion")
        self.ahora = datetime(2026, 11, 4, 18, 0, tzinfo=timezone.utc)
        self.store = MemoryStore()

        otro = self._crear_pedido(self.otro_id, "7")
        otro.confirmar(AutorizacionPago("E9-PAGO-ANTERIOR", True))
        self.otro_original = deepcopy(otro)
        self.store.datos["pedidos"][otro.id] = otro
        self.store.datos["pedidos"][self.pedido_id] = self._crear_pedido(
            self.pedido_id, "2"
        )
        self.store.datos["inventarios"][(self.sku.valor, "S1")] = (
            InventarioUbicacion(
                self.sku,
                "S1",
                Decimal("10"),
                Decimal("5"),
                {self.otro_id: Decimal("7")},
            )
        )
        self.servicio = PedidoService(
            lambda: MemoryUnitOfWork(self.store), lambda: self.ahora
        )
        # Confirmar por el servicio real crea la reserva y su evento inicial.
        self.servicio.confirmar(
            Actor("E9-CAJA", "Caja"),
            self.pedido_id,
            AutorizacionPago("E9-PAGO-SIMULADO", True),
            "S1",
        )

    def _crear_pedido(self, pedido_id, cantidad):
        return Pedido(
            id=pedido_id,
            cliente_id="E9-CLIENTE",
            cotizacion_id="E9-COTIZACION",
            cotizacion_folio="COT-001",
            cotizacion_version=1,
            partidas=[
                Partida(1, self.sku, Decimal(cantidad), Dinero(Decimal("100.00")))
            ],
        )

    def _cancelar(self):
        return self.servicio.cancelar(self.autorizado, self.pedido_id, self.motivo)

    def _inventario(self):
        return self.store.datos["inventarios"][(self.sku.valor, "S1")]

    def test_e9_can_01_exito_libera_dos_y_conserva_las_siete_de_otro_pedido(self):
        # Arrange: 10 fisicas - 7 ajenas - 2 propias = 1 disponible.
        self.assertEqual(self._inventario().disponible, Decimal("1"))

        resultado = self._cancelar()

        pedido = self.store.datos["pedidos"][self.pedido_id]
        inventario = self._inventario()
        self.assertEqual(resultado["estado"], "Cancelado")
        self.assertEqual(pedido.estado, EstadoPedido.CANCELADO)
        self.assertEqual(inventario.reservas, {self.otro_id: Decimal("7")})
        self.assertEqual(inventario.comprometida, Decimal("7"))
        self.assertEqual(inventario.disponible, Decimal("3"))
        self.assertEqual(inventario.existencia_fisica, Decimal("10"))
        self.assertEqual(inventario.en_transito, Decimal("5"))
        self.assertEqual(self.store.datos["pedidos"][self.otro_id], self.otro_original)
        self.assertEqual(len(self.store.datos["auditoria"]), 2)
        auditoria = self.store.datos["auditoria"][-1]
        self.assertEqual(auditoria["accion"], "CancelarPedido")
        self.assertEqual(auditoria["actor_id"], self.autorizado.id)
        self.assertEqual(auditoria["motivo"], self.motivo)
        self.assertEqual(auditoria["antes"]["estado"], "Confirmado")
        self.assertEqual(auditoria["despues"]["estado"], "Cancelado")
        self.assertEqual(
            [evento.tipo for evento in self.store.datos["outbox"]],
            ["PedidoConfirmado", "PedidoCancelado"],
        )

    def test_e9_can_02_error_pedido_surtido_conserva_estado_reservas_y_eventos(self):
        self.store.datos["pedidos"][self.pedido_id].surtido = True
        antes = deepcopy(self.store.datos)

        with self.assertRaisesRegex(ErrorNegocio, "Solo puede cancelarse") as rechazo:
            self._cancelar()
        self.rechazo_observado = {
            "tipo": type(rechazo.exception).__name__, "mensaje": str(rechazo.exception)
        }

        self.assertEqual(self.store.datos["pedidos"][self.pedido_id].estado,
                         EstadoPedido.CONFIRMADO)
        self.assertEqual(self._inventario().disponible, Decimal("1"))
        self.assertEqual(self._inventario().reservas[self.pedido_id], Decimal("2"))
        self.assertEqual(self.store.datos, antes)

    def test_e9_can_03_limite_segunda_cancelacion_no_libera_ni_registra_otro_evento(self):
        self._cancelar()
        despues_de_cancelar = deepcopy(self.store.datos)

        # Debe rechazar por la regla del pedido, no por una reserva inexistente.
        with self.assertRaisesRegex(ErrorNegocio, "Solo puede cancelarse") as rechazo:
            self._cancelar()
        self.rechazo_observado = {
            "tipo": type(rechazo.exception).__name__, "mensaje": str(rechazo.exception)
        }

        self.assertEqual(self._inventario().disponible, Decimal("3"))
        self.assertEqual(self._inventario().reservas, {self.otro_id: Decimal("7")})
        cancelaciones = [
            evento for evento in self.store.datos["outbox"]
            if evento.tipo == "PedidoCancelado" and evento.agregado_id == self.pedido_id
        ]
        self.assertEqual(len(cancelaciones), 1)
        self.assertEqual(self.store.datos, despues_de_cancelar)


if __name__ == "__main__":
    unittest.main()
