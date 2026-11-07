"""Matriz de estados y guardas de pedidos de FerreMax: US09/US10, BR04-06."""

from copy import deepcopy
from dataclasses import dataclass
from decimal import Decimal

import pytest

from ferremax.application.services import Actor, CotizacionService, PedidoService
from ferremax.demo import crear_contexto
from ferremax.domain.model import AutorizacionPago, ErrorNegocio, EstadoPedido
from ferremax.infrastructure.memory import MemoryStore, MemoryUnitOfWork


PAGO = AutorizacionPago("PAGO-STATE-MACHINE", True)
MOTIVO = "Cliente cancela antes del surtido"


@dataclass
class Flujo:
    store: MemoryStore
    servicio: PedidoService
    pedido_id: str


@pytest.fixture
def flujo():
    store, cotizacion, ahora = crear_contexto()
    factory = lambda: MemoryUnitOfWork(store)
    cotizaciones = CotizacionService(factory, lambda: ahora)
    vendedor = Actor("VENDEDOR-SM", "Vendedor")
    cotizaciones.revalidar(
        vendedor, cotizacion.id, 1, 7, cotizacion.partidas,
        cotizacion.condiciones, "Revalidacion para el caso de prueba",
    )
    resultado = cotizaciones.convertir(vendedor, cotizacion.id, 2, True)
    return Flujo(store, PedidoService(factory, lambda: ahora), resultado["pedido_id"])


def ejecutar(flujo, accion, pago=PAGO, motivo=MOTIVO, actor=None):
    if accion == "confirmar":
        return flujo.servicio.confirmar(
            actor or Actor("CAJA-SM", "Caja"), flujo.pedido_id, pago, "S1",
        )
    return flujo.servicio.cancelar(
        actor or Actor("VENDEDOR-SM", "VendedorAutorizadoCancelacion"),
        flujo.pedido_id, motivo,
    )


def llevar_a(flujo, estado):
    # Llegar al estado por operaciones reales; cada caso recibe datos nuevos.
    if estado in (EstadoPedido.CONFIRMADO, EstadoPedido.CANCELADO):
        ejecutar(flujo, "confirmar")
    if estado == EstadoPedido.CANCELADO:
        ejecutar(flujo, "cancelar")
    assert flujo.store.datos["pedidos"][flujo.pedido_id].estado == estado


def comprobar_rechazo(flujo, accion, mensaje, **argumentos):
    antes = deepcopy(flujo.store.datos)
    with pytest.raises(ErrorNegocio, match=mensaje):
        ejecutar(flujo, accion, **argumentos)
    # Incluye pedido, referencia de pago, inventario, auditoria y eventos.
    assert flujo.store.datos == antes


TRANSICIONES_PERMITIDAS = {
    (EstadoPedido.PENDIENTE, "confirmar"): (EstadoPedido.CONFIRMADO, "PedidoConfirmado"),
    (EstadoPedido.CONFIRMADO, "cancelar"): (EstadoPedido.CANCELADO, "PedidoCancelado"),
}


@pytest.mark.parametrize("estado", list(EstadoPedido), ids=lambda e: e.value)
@pytest.mark.parametrize("accion", ["confirmar", "cancelar"])
def test_matriz_completa_de_transiciones(flujo, estado, accion):
    llevar_a(flujo, estado)
    esperada = TRANSICIONES_PERMITIDAS.get((estado, accion))
    if esperada is None:
        mensaje = "Pedido no pendiente" if accion == "confirmar" else "Solo puede cancelarse"
        comprobar_rechazo(flujo, accion, mensaje)
        return

    destino, evento = esperada
    cantidad_auditorias = len(flujo.store.datos["auditoria"])
    cantidad_eventos = len(flujo.store.datos["outbox"])
    resultado = ejecutar(flujo, accion)
    datos = flujo.store.datos
    assert resultado["estado"] == destino.value
    assert datos["pedidos"][flujo.pedido_id].estado == destino
    inventario = datos["inventarios"][("SKU-DEMO", "S1")]
    assert inventario.reservas == ({flujo.pedido_id: Decimal(1)} if accion == "confirmar" else {})
    assert inventario.disponible == (Decimal(0) if accion == "confirmar" else Decimal(1))
    assert len(datos["auditoria"]) == cantidad_auditorias + 1
    assert datos["auditoria"][-1]["antes"]["estado"] == estado.value
    assert datos["auditoria"][-1]["despues"]["estado"] == destino.value
    assert len(datos["outbox"]) == cantidad_eventos + 1
    assert datos["outbox"][-1].tipo == evento


@pytest.mark.parametrize("pago", [
    AutorizacionPago("PAGO-RECHAZADO", False),
    AutorizacionPago("   ", True),
], ids=["rechazado", "sin_referencia"])
def test_confirmar_exige_pago_autorizado_con_referencia(flujo, pago):
    comprobar_rechazo(flujo, "confirmar", "Pago no autorizado", pago=pago)


@pytest.mark.parametrize("motivo", ["", "   "], ids=["vacio", "espacios"])
def test_cancelar_exige_motivo(flujo, motivo):
    llevar_a(flujo, EstadoPedido.CONFIRMADO)
    comprobar_rechazo(flujo, "cancelar", "Indique motivo de cancelacion", motivo=motivo)


def test_cancelar_rechaza_pedido_ya_surtido(flujo):
    llevar_a(flujo, EstadoPedido.CONFIRMADO)
    # El prototipo representa surtido con una bandera; no implementa ese proceso.
    flujo.store.datos["pedidos"][flujo.pedido_id].surtido = True
    comprobar_rechazo(flujo, "cancelar", "Solo puede cancelarse")


@pytest.mark.parametrize("estado,accion", [
    (EstadoPedido.PENDIENTE, "confirmar"),
    (EstadoPedido.CONFIRMADO, "cancelar"),
])
def test_operacion_permitida_exige_rol_autorizado(flujo, estado, accion):
    llevar_a(flujo, estado)
    comprobar_rechazo(
        flujo, accion, "La operacion requiere el rol",
        actor=Actor("ACTOR-SIN-PERMISO", "Consulta"),
    )
