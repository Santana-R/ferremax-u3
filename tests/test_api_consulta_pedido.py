"""Consulta HTTP del pedido: estados, version de origen y ausencia de escrituras."""

from copy import deepcopy
from dataclasses import replace
from uuid import uuid4

import psycopg
import pytest

from ferremax.api.pedidos import obtener_lector_pedidos
from ferremax.api.settings import ConfiguracionBaseNoDisponible
from ferremax.domain.model import Dinero, ErrorNegocio
from ferremax.infrastructure.memory import MemoryReader
from tests.test_api_confirmacion import escenario, solicitud
from tests.test_api_conversion import contexto as contexto_conversion


@pytest.fixture
def consulta(escenario):
    client, store, crear, _, api = escenario
    api.dependency_overrides[obtener_lector_pedidos] = lambda: MemoryReader(store)
    return client, store, crear, api


@pytest.mark.parametrize("estado", ["Pendiente", "Confirmado", "Cancelado"])
def test_consulta_cada_estado_con_version_y_total_sin_cambiar_datos(consulta, estado):
    client, store, crear, _ = consulta
    pid, confirmar = crear()
    if estado != "Pendiente":
        assert client.post(confirmar, json=solicitud()).status_code == 200
    if estado == "Cancelado":
        assert client.post(f"/pedidos/{pid}/cancelar", json={"motivo": "Cliente cancela"}).status_code == 200
    antes = deepcopy(store.datos)
    for _ in range(2):
        response = client.get(f"/pedidos/{pid}")
        assert response.status_code == 200
        assert response.json() == {
            "mensaje": "Pedido consultado.", "pedido_id": pid, "estado": estado,
            "cotizacion_folio": "COT-CONVERTIR", "cotizacion_version": 2,
            "total": "240.00", "moneda": "MXN",
        }
        assert store.datos == antes


def test_pedido_ausente_devuelve_404_sin_crearlo(consulta):
    client, store, _, _ = consulta
    pid = str(uuid4())
    antes = deepcopy(store.datos)
    response = client.get(f"/pedidos/{pid}")
    assert response.status_code == 404
    assert response.json() == {"mensaje": "Pedido no encontrado.", "pedido_id": pid}
    assert store.datos == antes


@pytest.mark.parametrize("identificador", ["invalido", "confirmar", "cancelar", "%27%20OR%201%3D1--"])
def test_identificador_invalido_devuelve_mensaje_de_consulta(consulta, identificador):
    client, store, _, _ = consulta
    antes = deepcopy(store.datos)
    response = client.get(f"/pedidos/{identificador}")
    assert response.status_code == 422
    assert response.json() == {"mensaje": "Indica un identificador válido de pedido."}
    assert store.datos == antes


def test_total_se_toma_del_pedido_guardado_y_no_de_la_cotizacion_actual(consulta):
    client, store, crear, _ = consulta
    pid, _ = crear()
    pedido = store.datos["pedidos"][pid]
    cotizacion = store.datos["cotizaciones"][(pedido.cotizacion_id, 2)]
    cotizacion.partidas[0] = replace(cotizacion.partidas[0], precio=Dinero("999.00"))
    antes = deepcopy(store.datos)
    response = client.get(f"/pedidos/{pid}")
    assert response.status_code == 200
    assert response.json()["total"] == "240.00"
    assert response.json()["cotizacion_version"] == 2
    assert store.datos == antes


@pytest.mark.parametrize("error", [psycopg.OperationalError, ConfiguracionBaseNoDisponible])
def test_base_no_disponible_da_mensaje_de_consulta_sin_detalles(consulta, error):
    client, store, crear, api = consulta
    pid, _ = crear()
    antes = deepcopy(store.datos)

    def no_disponible():
        raise error("detalle privado de conexion")

    api.dependency_overrides[obtener_lector_pedidos] = no_disponible
    response = client.get(f"/pedidos/{pid}")
    assert response.status_code == 503
    assert response.json() == {"mensaje": "Por el momento no podemos consultar el pedido. Inténtalo de nuevo más tarde."}
    assert store.datos == antes


def test_error_no_reconocido_del_lector_no_expone_informacion_interna(consulta):
    client, store, crear, api = consulta
    pid, _ = crear()
    antes = deepcopy(store.datos)

    class LectorConError:
        def consultar_pedido(self, pedido_id):
            raise ErrorNegocio("detalle privado del pedido")

    api.dependency_overrides[obtener_lector_pedidos] = LectorConError
    response = client.get(f"/pedidos/{pid}")
    assert response.status_code == 422
    assert response.json() == {"mensaje": "No se pudo consultar el pedido. Revisa su identificador.", "pedido_id": pid}
    assert store.datos == antes


def test_openapi_documenta_consulta_y_respuestas(consulta):
    client, _, _, _ = consulta
    spec = client.get("/openapi.json").json()
    operation = spec["paths"]["/pedidos/{pedido_id}"]["get"]
    assert {"200", "404", "422", "503"} <= set(operation["responses"])
    assert "requestBody" not in operation
    schema = spec["components"]["schemas"]["PedidoConsultaRespuesta"]
    assert schema["properties"]["estado"]["enum"] == ["Pendiente", "Confirmado", "Cancelado"]
