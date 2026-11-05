"""Ejercicio separado: mocks de pago aprobado, rechazado y timeout."""

from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import Mock
import pytest

from examples.e9_pago_simulado import (
    AdaptadorPagoSimulado, ProveedorPago, confirmar_con_pago_simulado,
)
from ferremax.application.services import Actor, PedidoService
from ferremax.domain.model import Dinero, ErrorNegocio, EstadoPedido, InventarioUbicacion, Partida, Pedido, SKU
from ferremax.infrastructure.memory import MemoryStore, MemoryUnitOfWork


@pytest.fixture
def contexto_pago():
    sku = SKU("FER-P001")
    pedido = Pedido("E9-PAGO", "E9-CLIENTE", "E9-COT", "COT-001", 1,
                    [Partida(1, sku, Decimal("2"), Dinero(Decimal("100.00")))])
    store = MemoryStore()
    store.datos["pedidos"][pedido.id] = pedido
    store.datos["inventarios"][(sku.valor, "S1")] = InventarioUbicacion(sku, "S1", Decimal("10"))
    ahora = datetime(2026, 11, 4, 18, 0, tzinfo=timezone.utc)
    servicio = PedidoService(lambda: MemoryUnitOfWork(store), lambda: ahora)
    proveedor = Mock(spec=ProveedorPago)
    return store, pedido, servicio, proveedor


def ejecutar(contexto):
    store, pedido, servicio, proveedor = contexto
    return confirmar_con_pago_simulado(pedido, servicio, Actor("E9-CAJA", "Caja"),
                                      AdaptadorPagoSimulado(proveedor), "E9-REF", "S1")


def test_e9_mock_01_pago_aprobado_confirma_y_reserva(contexto_pago, request):
    store, pedido, _, proveedor = contexto_pago
    proveedor.cobrar.return_value = True
    resultado = ejecutar(contexto_pago)
    proveedor.cobrar.assert_called_once_with(pedido.id, Dinero(Decimal("200.00")))
    assert resultado["estado"] == "Confirmado"
    assert store.datos["pedidos"][pedido.id].estado == EstadoPedido.CONFIRMADO
    inv = store.datos["inventarios"][("FER-P001", "S1")]
    assert inv.disponible == Decimal("8")
    request.node.user_properties.append(("evidencia", {
        "proveedor": "Mock; sin red ni cobros reales",
        "importe_solicitado": str(proveedor.cobrar.call_args[0][1].importe),
        "llamadas": proveedor.cobrar.call_count, "estado": resultado["estado"],
        "disponible": str(inv.disponible),
    }))


def test_e9_mock_02_pago_rechazado_no_confirma_ni_reserva(contexto_pago, request):
    store, pedido, _, proveedor = contexto_pago
    proveedor.cobrar.return_value = False
    antes = deepcopy(store.datos)
    with pytest.raises(ErrorNegocio, match="rechazo el pago") as exc:
        ejecutar(contexto_pago)
    proveedor.cobrar.assert_called_once_with(pedido.id, Dinero(Decimal("200.00")))
    assert store.datos == antes
    request.node.user_properties.append(("evidencia", {
        "proveedor": "Mock", "importe_solicitado": str(proveedor.cobrar.call_args[0][1].importe),
        "llamadas": proveedor.cobrar.call_count,
        "rechazo": str(exc.value), "estado": store.datos["pedidos"][pedido.id].estado.value,
        "disponible": str(store.datos["inventarios"][("FER-P001", "S1")].disponible),
        "datos_sin_cambios": store.datos == antes,
    }))


def test_e9_mock_03_timeout_no_confirma_ni_reserva(contexto_pago, request):
    store, pedido, _, proveedor = contexto_pago
    proveedor.cobrar.side_effect = TimeoutError("Timeout simulado")
    antes = deepcopy(store.datos)
    with pytest.raises(ErrorNegocio, match="No se obtuvo respuesta") as exc:
        ejecutar(contexto_pago)
    proveedor.cobrar.assert_called_once_with(pedido.id, Dinero(Decimal("200.00")))
    assert store.datos == antes
    request.node.user_properties.append(("evidencia", {
        "proveedor": "Mock", "fallo_simulado": "TimeoutError", "llamadas": proveedor.cobrar.call_count,
        "rechazo": str(exc.value), "estado": store.datos["pedidos"][pedido.id].estado.value,
        "disponible": str(store.datos["inventarios"][("FER-P001", "S1")].disponible),
        "datos_sin_cambios": store.datos == antes,
    }))
