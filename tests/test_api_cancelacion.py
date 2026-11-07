"""Cancelacion HTTP: liberacion propia, guardas y rechazos sin cambios."""

from copy import deepcopy
from decimal import Decimal
from uuid import uuid4

import psycopg
import pytest

from ferremax.api.pedidos import obtener_servicio_pedidos
from ferremax.api.settings import ConfiguracionBaseNoDisponible
from ferremax.domain.model import ErrorNegocio
from tests.test_api_confirmacion import escenario, solicitud
from tests.test_api_conversion import contexto as contexto_conversion


MOTIVO = "El cliente solicita cancelar antes del surtido"


def confirmado(escenario, cantidad=2):
    client, _, crear, _, _ = escenario
    pid, ruta = crear(cantidad)
    assert client.post(ruta, json=solicitud()).status_code == 200
    return pid, f"/pedidos/{pid}/cancelar"


def rechazar(client, store, ruta, entrada, estado):
    antes = deepcopy(store.datos)
    response = client.post(ruta, json=entrada)
    assert response.status_code == estado
    assert store.datos == antes
    return response


def test_cancelar_libera_solo_reserva_propia_y_registra_motivo(escenario):
    client, store, _, _, _ = escenario
    pid, ruta = confirmado(escenario)
    antes = deepcopy(store.datos)
    response = client.post(ruta, json={"motivo": "  " + MOTIVO + "  "})
    assert response.status_code == 200
    assert response.json() == {
        "mensaje": "Pedido cancelado y su inventario reservado liberado.",
        "pedido_id": pid, "estado": "Cancelado",
    }
    inv = store.datos["inventarios"][("FER-API-DEMO", "S1")]
    assert inv.reservas == {"OTRO-PEDIDO": Decimal(7)}
    assert inv.comprometida == 7 and inv.disponible == 3
    assert inv.existencia_fisica == 10 and inv.en_transito == 5
    assert store.datos["pedidos"][pid].estado.value == "Cancelado"
    assert store.datos["pedidos"][pid].referencia_pago == "PAGO-TEST-001"
    assert store.datos["cotizaciones"] == antes["cotizaciones"]
    assert len(store.datos["auditoria"]) == len(antes["auditoria"]) + 1
    audit = store.datos["auditoria"][-1]
    assert audit["antes"]["estado"] == "Confirmado" and audit["despues"]["estado"] == "Cancelado"
    assert audit["accion"] == "CancelarPedido" and audit["motivo"] == MOTIVO
    assert audit["actor_id"] == "cancelacion-api-demo"
    assert len(store.datos["outbox"]) == len(antes["outbox"]) + 1
    assert store.datos["outbox"][-1].tipo == "PedidoCancelado"


def test_cancelar_repetido_no_aumenta_disponible_ni_duplica_evento(escenario):
    client, store, _, _, _ = escenario
    _, ruta = confirmado(escenario)
    assert client.post(ruta, json={"motivo": MOTIVO}).status_code == 200
    response = rechazar(client, store, ruta, {"motivo": "Segundo intento"}, 409)
    assert "no puede cancelarse de nuevo" in response.json()["mensaje"]


def test_cancelar_pedido_que_agoto_disponible_restaura_solo_lo_reservado(escenario):
    client, store, _, _, _ = escenario
    _, ruta = confirmado(escenario, cantidad=3)
    assert store.datos["inventarios"][("FER-API-DEMO", "S1")].disponible == 0
    assert client.post(ruta, json={"motivo": MOTIVO}).status_code == 200
    assert store.datos["inventarios"][("FER-API-DEMO", "S1")].disponible == 3


@pytest.mark.parametrize("estado", ["pendiente", "surtido"])
def test_guardas_rechazan_sin_modificar_pedido_ni_inventario(escenario, estado):
    client, store, crear, _, _ = escenario
    if estado == "pendiente":
        pid, _ = crear()
        ruta = f"/pedidos/{pid}/cancelar"
    else:
        pid, ruta = confirmado(escenario)
        # No existe operacion de surtido en el prototipo; se prepara su guarda.
        store.datos["pedidos"][pid].surtido = True
    response = rechazar(client, store, ruta, {"motivo": MOTIVO}, 409)
    assert "confirmado que aún no se haya surtido" in response.json()["mensaje"]


def test_pedido_inexistente_devuelve_404(escenario):
    client, store, _, _, _ = escenario
    pid = str(uuid4())
    response = rechazar(client, store, f"/pedidos/{pid}/cancelar", {"motivo": MOTIVO}, 404)
    assert response.json() == {"mensaje": "Pedido no encontrado.", "pedido_id": pid}


def test_identificador_invalido_devuelve_mensaje_claro(escenario):
    client, store, _, _, _ = escenario
    response = rechazar(client, store, "/pedidos/invalido/cancelar", {"motivo": MOTIVO}, 422)
    assert response.json() == {"mensaje": "Indica un identificador válido de pedido."}


@pytest.mark.parametrize("entrada", [{}, {"motivo": ""}, {"motivo": "  "}, {"motivo": None},
                                    {"motivo": 12}, {"motivo": []}, {"motivo": MOTIVO, "cantidad": 99}])
def test_motivo_obligatorio_y_solicitud_sin_cantidades(escenario, entrada):
    client, store, _, _, _ = escenario
    _, ruta = confirmado(escenario)
    response = rechazar(client, store, ruta, entrada, 422)
    assert set(response.json()) == {"mensaje"}
    texto_esperado = "campos no reconocidos" if "cantidad" in entrada else "motivo"
    assert texto_esperado in response.json()["mensaje"]


def test_json_mal_formado_tiene_mensaje_de_cancelacion(escenario):
    client, store, _, _, _ = escenario
    _, ruta = confirmado(escenario)
    antes = deepcopy(store.datos)
    response = client.post(ruta, content="{", headers={"Content-Type": "application/json"})
    assert response.status_code == 422
    assert response.json() == {"mensaje": "Revisa los datos de la cancelación del pedido."}
    assert store.datos == antes


@pytest.mark.parametrize("error", [psycopg.OperationalError, ConfiguracionBaseNoDisponible])
def test_base_no_disponible_no_expone_detalles(escenario, error):
    client, store, _, _, api = escenario
    _, ruta = confirmado(escenario)
    antes = deepcopy(store.datos)

    def no_disponible():
        raise error("detalle privado de conexion")

    api.dependency_overrides[obtener_servicio_pedidos] = no_disponible
    response = client.post(ruta, json={"motivo": MOTIVO})
    assert response.status_code == 503
    assert response.json() == {"mensaje": "Por el momento no podemos cancelar el pedido. Inténtalo de nuevo más tarde."}
    assert store.datos == antes


@pytest.mark.parametrize("reserva", ["sin_reserva", "falta_segundo_producto"])
def test_inconsistencia_de_reserva_no_cancela_ni_libera_parcialmente(escenario, reserva):
    client, store, _, _, _ = escenario
    pid, ruta = confirmado(escenario)
    inv = store.datos["inventarios"][("FER-API-DEMO", "S1")]
    del inv.reservas[pid]
    if reserva == "falta_segundo_producto":
        # Reserva incompleta: la ubicacion existe pero falta la reserva del SKU pedido.
        from ferremax.domain.model import InventarioUbicacion, SKU
        store.datos["inventarios"][("OTRO-SKU", "S1")] = InventarioUbicacion(SKU("OTRO-SKU"), "S1", 1, reservas={pid: Decimal(1)})
    response = rechazar(client, store, ruta, {"motivo": MOTIVO}, 409)
    assert "Solicita una revisión" in response.json()["mensaje"]


def test_error_negocio_no_reconocido_no_expone_detalles(escenario, monkeypatch):
    client, store, _, servicio, _ = escenario
    _, ruta = confirmado(escenario)

    def fallar(*args):
        raise ErrorNegocio("detalle interno de la regla")

    monkeypatch.setattr(servicio, "cancelar", fallar)
    response = rechazar(client, store, ruta, {"motivo": MOTIVO}, 422)
    assert response.json()["mensaje"] == "No se pudo cancelar el pedido. Revisa sus datos."


def test_openapi_documenta_cancelacion_y_motivo(escenario):
    client, _, _, _, _ = escenario
    spec = client.get("/openapi.json").json()
    operation = spec["paths"]["/pedidos/{pedido_id}/cancelar"]["post"]
    assert {"200", "404", "409", "422", "503"} <= set(operation["responses"])
    schema = spec["components"]["schemas"]["CancelacionSolicitud"]
    assert schema["required"] == ["motivo"] and schema["additionalProperties"] is False
