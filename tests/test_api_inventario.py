"""Contrato HTTP con lector Memory inyectado; la integracion SQL se prueba aparte."""

from copy import deepcopy
from decimal import Decimal

import pytest
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
import psycopg

from ferremax.api.main import create_app, obtener_lector
from ferremax.domain.model import InventarioUbicacion, SKU
from ferremax.infrastructure.memory import MemoryReader, MemoryStore


@pytest.fixture
def consulta():
    store = MemoryStore()
    store.datos["inventarios"][("API-TEST", "S1")] = InventarioUbicacion(
        SKU("API-TEST"), "S1", Decimal(10), Decimal(5), {"OTRO-PEDIDO": Decimal(7)},
    )
    store.datos["inventarios"][("API-CERO", "S1")] = InventarioUbicacion(
        SKU("API-CERO"), "S1", Decimal(0), Decimal(8),
    )
    api = create_app()
    api.dependency_overrides[obtener_lector] = lambda: MemoryReader(store)
    with TestClient(api) as client:
        yield client, store, api


def test_producto_existente_devuelve_disponibilidad_sin_modificar_datos(consulta):
    client, store, _ = consulta
    antes = deepcopy(store.datos)
    response = client.get("/inventario/API-TEST")
    assert response.status_code == 200
    assert response.json() == {
        "mensaje": "Disponibilidad del producto consultada.",
        "sku": "API-TEST", "encontrado": True,
        "ubicaciones": [{"ubicacion_id": "S1", "existencia_fisica": "10",
                          "comprometida": "7", "en_transito": "5", "disponible": "3"}],
    }
    assert store.datos == antes


def test_producto_inexistente_devuelve_mensaje_entendible(consulta):
    client, store, _ = consulta
    antes = deepcopy(store.datos)
    response = client.get("/inventario/NO-EXISTE")
    assert response.status_code == 404
    assert response.json() == {
        "mensaje": "Producto no encontrado en el inventario.", "sku": "NO-EXISTE",
    }
    assert store.datos == antes


def test_producto_sin_disponible_existe_y_transito_no_se_suma(consulta):
    client, _, _ = consulta
    response = client.get("/inventario/API-CERO")
    assert response.status_code == 200
    assert response.json()["encontrado"] is True
    assert response.json()["ubicaciones"][0]["disponible"] == "0"
    assert response.json()["ubicaciones"][0]["en_transito"] == "8"


def test_codigo_en_blanco_devuelve_indicacion_clara(consulta):
    client, _, _ = consulta
    response = client.get("/inventario/%20%20")
    assert response.status_code == 400
    assert response.json() == {"mensaje": "Escribe el código del producto."}


def test_fallo_postgres_no_expone_detalles_internos(consulta):
    client, _, api = consulta

    class LectorNoDisponible:
        def consultar_disponibilidad(self, sku):
            raise psycopg.OperationalError("credencial privada y detalle de SQL")

    api.dependency_overrides[obtener_lector] = lambda: LectorNoDisponible()
    response = client.get("/inventario/API-TEST")
    assert response.status_code == 503
    assert response.json() == {
        "mensaje": "Por el momento no podemos consultar el inventario. Inténtalo de nuevo más tarde.",
    }
    assert "privada" not in response.text


def test_configuracion_ausente_devuelve_503_sin_impedir_swagger(monkeypatch):
    for name in ("DATABASE_URL", "POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD"):
        monkeypatch.delenv(name, raising=False)
    with TestClient(create_app()) as client:
        assert client.get("/docs").status_code == 200
        assert client.get("/inventario/API-TEST").status_code == 503


def test_errores_de_validacion_se_traducen_a_mensaje_cliente(consulta):
    client, _, api = consulta

    def solicitud_invalida():
        raise RequestValidationError([{"type": "missing", "loc": ("path", "sku")}])

    api.dependency_overrides[obtener_lector] = solicitud_invalida
    response = client.get("/inventario/API-TEST")
    assert response.status_code == 422
    assert response.json() == {"mensaje": "Revisa el código del producto e inténtalo de nuevo."}


def test_swagger_y_openapi_publican_la_consulta_y_sus_respuestas(consulta):
    client, _, _ = consulta
    assert "swagger-ui" in client.get("/docs").text
    response = client.get("/openapi.json")
    assert response.status_code == 200
    operation = response.json()["paths"]["/inventario/{sku}"]["get"]
    assert {"200", "400", "404", "422", "503"} <= set(operation["responses"])
    assert operation["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].endswith("InventarioRespuesta")
