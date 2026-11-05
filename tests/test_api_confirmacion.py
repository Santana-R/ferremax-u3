"""Confirmacion HTTP: pago simulado, estados y reserva atomica con Memory."""

from copy import deepcopy
from dataclasses import replace
from decimal import Decimal
from uuid import uuid4

import psycopg
import pytest

from ferremax.api.pedidos import obtener_servicio_pedidos
from ferremax.application.services import Actor, PedidoService
from ferremax.domain.model import Dinero, InventarioUbicacion, Partida, SKU
from ferremax.infrastructure.memory import MemoryUnitOfWork
from tests.test_api_conversion import AHORA, contexto as contexto_conversion


def solicitud():
    return {"referencia_pago": "PAGO-TEST-001", "pago_autorizado": True, "ubicacion_id": "S1"}


@pytest.fixture
def escenario(contexto_conversion):
    client, store, cid, conversion, api = contexto_conversion
    servicio = PedidoService(lambda: MemoryUnitOfWork(store), lambda: AHORA)
    api.dependency_overrides[obtener_servicio_pedidos] = lambda: servicio

    def crear(cantidad=2, segundo_sin_stock=False):
        c = store.datos["cotizaciones"][(cid, 2)]
        c.partidas[0] = replace(c.partidas[0], cantidad=Decimal(cantidad))
        if segundo_sin_stock:
            c.partidas.append(Partida(2, SKU("ZZ-SIN-STOCK"), 1, Dinero(30)))
            store.datos["inventarios"][("ZZ-SIN-STOCK", "S1")] = InventarioUbicacion(SKU("ZZ-SIN-STOCK"), "S1", 0)
        response = client.post(conversion, json={"aceptada": True})
        assert response.status_code == 201
        pid = response.json()["pedido_id"]
        return pid, f"/pedidos/{pid}/confirmar"

    return client, store, crear, servicio, api


def rechazar(client, store, ruta, entrada, estado):
    antes = deepcopy(store.datos)
    response = client.post(ruta, json=entrada)
    assert response.status_code == estado
    assert store.datos == antes
    return response


def test_confirmar_reserva_dos_conserva_siete_ajenas_y_registra_transicion(escenario):
    client, store, crear, _, _ = escenario
    pid, ruta = crear()
    antes = deepcopy(store.datos)
    response = client.post(ruta, json=solicitud())
    assert response.status_code == 200
    assert response.json() == {
        "mensaje": "Pedido confirmado e inventario reservado.", "pedido_id": pid,
        "estado": "Confirmado", "referencia_pago": "PAGO-TEST-001", "ubicacion_id": "S1",
    }
    p = store.datos["pedidos"][pid]
    assert p.estado.value == "Confirmado" and p.referencia_pago == "PAGO-TEST-001"
    assert p.total.importe == 240 and p.cotizacion_version == 2
    inv = store.datos["inventarios"][("FER-API-DEMO", "S1")]
    assert inv.reservas == {"OTRO-PEDIDO": Decimal(7), pid: Decimal(2)}
    assert inv.comprometida == 9 and inv.disponible == 1
    assert inv.existencia_fisica == 10 and inv.en_transito == 5
    assert store.datos["cotizaciones"] == antes["cotizaciones"]
    assert len(store.datos["auditoria"]) == len(antes["auditoria"]) + 1
    audit = store.datos["auditoria"][-1]
    assert audit["antes"]["estado"] == "Pendiente" and audit["despues"]["estado"] == "Confirmado"
    assert len(store.datos["outbox"]) == len(antes["outbox"]) + 1
    assert store.datos["outbox"][-1].tipo == "PedidoConfirmado"


@pytest.mark.parametrize("cantidad,estado", [(3, 200), (4, 409)], ids=["limite_disponible", "insuficiente"])
def test_confirmacion_respeta_disponible_y_limite(escenario, cantidad, estado):
    client, store, crear, _, _ = escenario
    pid, ruta = crear(cantidad)
    if estado == 409:
        response = rechazar(client, store, ruta, solicitud(), estado)
        assert "permanece pendiente" in response.json()["mensaje"]
        assert store.datos["pedidos"][pid].referencia_pago is None
    else:
        assert client.post(ruta, json=solicitud()).status_code == 200
        assert store.datos["inventarios"][("FER-API-DEMO", "S1")].disponible == 0


def test_pago_rechazado_conserva_pedido_pendiente_y_reservas(escenario):
    client, store, crear, _, _ = escenario
    _, ruta = crear()
    response = rechazar(client, store, ruta, {**solicitud(), "pago_autorizado": False}, 409)
    assert response.json()["mensaje"] == "El pago no está autorizado para confirmar el pedido."


def test_confirmacion_repetida_no_duplica_reserva_ni_reemplaza_referencia(escenario):
    client, store, crear, _, _ = escenario
    _, ruta = crear()
    assert client.post(ruta, json=solicitud()).status_code == 200
    response = rechazar(client, store, ruta, {**solicitud(), "referencia_pago": "OTRA-REFERENCIA"}, 409)
    assert "ya no está pendiente" in response.json()["mensaje"]


def test_pedido_cancelado_no_se_puede_confirmar(escenario):
    client, store, crear, servicio, _ = escenario
    pid, ruta = crear()
    assert client.post(ruta, json=solicitud()).status_code == 200
    servicio.cancelar(Actor("VENDEDOR-TEST", "VendedorAutorizadoCancelacion"), pid, "Cliente cancela")
    rechazar(client, store, ruta, solicitud(), 409)


def test_pedido_inexistente_devuelve_404(escenario):
    client, store, _, _, _ = escenario
    pid = str(uuid4())
    response = rechazar(client, store, f"/pedidos/{pid}/confirmar", solicitud(), 404)
    assert response.json() == {"mensaje": "Pedido no encontrado.", "pedido_id": pid}


def test_identificador_invalido_devuelve_mensaje_claro(escenario):
    client, store, _, _, _ = escenario
    response = rechazar(client, store, "/pedidos/invalido/confirmar", solicitud(), 422)
    assert response.json() == {"mensaje": "Indica un identificador válido de pedido."}


@pytest.mark.parametrize("cambio", ["sin_referencia", "referencia_blanca", "pago_texto", "pago_numero",
                                  "pago_nulo", "ubicacion_blanca", "campo_extra", "sin_autorizacion"])
def test_datos_invalidos_se_rechazan_sin_cambios(escenario, cambio):
    client, store, crear, _, _ = escenario
    _, ruta = crear()
    entrada = solicitud()
    if cambio == "sin_referencia": entrada.pop("referencia_pago")
    elif cambio == "referencia_blanca": entrada["referencia_pago"] = "   "
    elif cambio == "pago_texto": entrada["pago_autorizado"] = "true"
    elif cambio == "pago_numero": entrada["pago_autorizado"] = 1
    elif cambio == "pago_nulo": entrada["pago_autorizado"] = None
    elif cambio == "ubicacion_blanca": entrada["ubicacion_id"] = " "
    elif cambio == "campo_extra": entrada["cantidad"] = 99
    else: entrada.pop("pago_autorizado")
    response = rechazar(client, store, ruta, entrada, 422)
    assert set(response.json()) == {"mensaje"}


def test_ubicacion_sin_registro_de_producto_rechaza(escenario):
    client, store, crear, _, _ = escenario
    _, ruta = crear()
    rechazar(client, store, ruta, {**solicitud(), "ubicacion_id": "AUSENTE"}, 422)


def test_ubicacion_con_cero_disponibles_rechaza_sin_reservar(escenario):
    client, store, crear, _, _ = escenario
    _, ruta = crear()
    store.datos["inventarios"][("FER-API-DEMO", "S2")] = InventarioUbicacion(SKU("FER-API-DEMO"), "S2", 0)
    rechazar(client, store, ruta, {**solicitud(), "ubicacion_id": "S2"}, 409)


def test_fallo_segundo_sku_revierte_estado_referencia_y_primera_reserva(escenario):
    client, store, crear, _, _ = escenario
    pid, ruta = crear(segundo_sin_stock=True)
    rechazar(client, store, ruta, solicitud(), 409)
    assert store.datos["pedidos"][pid].estado.value == "Pendiente"
    assert store.datos["pedidos"][pid].referencia_pago is None


def test_json_mal_formado_se_traduce_a_mensaje_cliente(escenario):
    client, store, crear, _, _ = escenario
    _, ruta = crear()
    antes = deepcopy(store.datos)
    response = client.post(ruta, content="{", headers={"Content-Type": "application/json"})
    assert response.status_code == 422
    assert response.json() == {"mensaje": "Revisa los datos de la confirmación del pedido."}
    assert store.datos == antes


def test_base_no_disponible_no_expone_detalles(escenario):
    client, _, crear, _, api = escenario
    _, ruta = crear()

    def no_disponible():
        raise psycopg.OperationalError("detalle privado de conexion")

    api.dependency_overrides[obtener_servicio_pedidos] = no_disponible
    response = client.post(ruta, json=solicitud())
    assert response.status_code == 503
    assert response.json() == {"mensaje": "Por el momento no podemos confirmar el pedido. Inténtalo de nuevo más tarde."}


def test_openapi_documenta_confirmacion_y_respuestas(escenario):
    client, _, _, _, _ = escenario
    spec = client.get("/openapi.json").json()
    operation = spec["paths"]["/pedidos/{pedido_id}/confirmar"]["post"]
    assert "200" in operation["responses"]
    assert {"404", "409", "422", "503"} <= set(operation["responses"])
