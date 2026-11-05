"""Conversion HTTP: version aceptada, importe del dominio y pedido Pendiente."""

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
import psycopg
import pytest

from ferremax.api.cotizaciones import obtener_servicio_cotizaciones
from ferremax.api.main import create_app
from ferremax.application.services import Actor, CotizacionService
from ferremax.domain.model import Cotizacion, Dinero, InventarioUbicacion, Partida, SKU, Vigencia
from ferremax.infrastructure.memory import MemoryStore, MemoryUnitOfWork


AHORA = datetime(2026, 11, 5, 12, tzinfo=timezone.utc)


@pytest.fixture
def contexto():
    store = MemoryStore()
    c = Cotizacion(str(uuid4()), "COT-CONVERTIR", 1, "CLIENTE-FICTICIO",
                   Vigencia(AHORA-timedelta(days=8), AHORA-timedelta(days=1)),
                   [Partida(1, SKU("FER-API-DEMO"), Decimal(2), Dinero(Decimal("100.00")))],
                   "Condiciones originales")
    store.datos["cotizaciones"][(c.id, 1)] = c
    store.datos["inventarios"][("FER-API-DEMO", "S1")] = InventarioUbicacion(
        SKU("FER-API-DEMO"), "S1", Decimal(10), Decimal(5), {"OTRO-PEDIDO": Decimal(7)},
    )
    servicio = CotizacionService(lambda: MemoryUnitOfWork(store), lambda: AHORA)
    servicio.revalidar(Actor("VENDEDOR-TEST", "Vendedor"), c.id, 1, 7,
                       [Partida(1, SKU("FER-API-DEMO"), Decimal(2), Dinero(Decimal("120.00")))],
                       "Condiciones revalidadas", "Cliente solicita revalidar")
    api = create_app(reloj=lambda: AHORA)
    api.dependency_overrides[obtener_servicio_cotizaciones] = lambda: servicio
    with TestClient(api) as client:
        yield client, store, c.id, f"/cotizaciones/{c.id}/versiones/2/convertir", api


def test_version_2_crea_pedido_pendiente_por_240_sin_reservar(contexto):
    client, store, cid, ruta, _ = contexto
    antes = deepcopy(store.datos)
    response = client.post(ruta, json={"aceptada": True})
    assert response.status_code == 201
    body = response.json()
    pid = body.pop("pedido_id")
    UUID(pid)
    assert body == {
        "mensaje": "Pedido creado y pendiente de confirmación.",
        "estado": "Pendiente", "cotizacion_id": cid,
        "cotizacion_folio": "COT-CONVERTIR", "cotizacion_version": 2,
        "total": "240.00", "moneda": "MXN",
        "disponibilidad_consultada": [{"sku": "FER-API-DEMO", "solicitada": "2", "disponible": "3"}],
    }
    pedido = store.datos["pedidos"][pid]
    assert len(store.datos["pedidos"]) == 1 and pedido.estado.value == "Pendiente"
    assert pedido.cotizacion_id == cid and pedido.cotizacion_version == 2
    assert pedido.partidas == antes["cotizaciones"][(cid, 2)].partidas
    assert pedido.total.importe == Decimal("240.00") and pedido.referencia_pago is None
    assert store.datos["cotizaciones"] == antes["cotizaciones"]
    assert store.datos["inventarios"] == antes["inventarios"]
    assert len(store.datos["auditoria"]) == len(antes["auditoria"]) + 1
    assert store.datos["auditoria"][-1]["agregado_id"] == pid
    assert store.datos["auditoria"][-1]["despues"]["total"] == "240.00"
    assert len(store.datos["outbox"]) == len(antes["outbox"]) + 1
    assert store.datos["outbox"][-1].tipo == "PedidoCreado"


@pytest.mark.parametrize("aceptada", [True, False])
def test_version_1_vencida_rechaza_antes_de_crear_pedido(contexto, aceptada):
    client, store, _, ruta, _ = contexto
    antes = deepcopy(store.datos)
    response = client.post(ruta.replace("/2/", "/1/"), json={"aceptada": aceptada})
    assert response.status_code == 409
    assert "no está vigente" in response.json()["mensaje"]
    assert store.datos == antes


@pytest.mark.parametrize("instante", ["antes_emision", "al_vencer", "despues_vencer"])
def test_fuera_de_vigencia_rechaza_sin_cambios(contexto, instante):
    client, store, cid, ruta, _ = contexto
    if instante == "antes_emision":
        vigencia = Vigencia(AHORA+timedelta(seconds=1), AHORA+timedelta(days=1))
    else:
        fin = AHORA if instante == "al_vencer" else AHORA-timedelta(microseconds=1)
        vigencia = Vigencia(AHORA-timedelta(days=7), fin)
    store.datos["cotizaciones"][(cid, 2)].vigencia = vigencia
    antes = deepcopy(store.datos)
    response = client.post(ruta, json={"aceptada": True})
    assert response.status_code == 409 and store.datos == antes


def test_sin_aceptacion_rechaza_una_version_vigente(contexto):
    client, store, _, ruta, _ = contexto
    antes = deepcopy(store.datos)
    response = client.post(ruta, json={"aceptada": False})
    assert response.status_code == 409
    assert "aceptar esta versión" in response.json()["mensaje"]
    assert store.datos == antes


@pytest.mark.parametrize("cambiar", ["identificador", "version"])
def test_cotizacion_o_version_inexistente_no_crea_pedido(contexto, cambiar):
    client, store, cid, ruta, _ = contexto
    ruta = ruta.replace(cid, str(uuid4())) if cambiar == "identificador" else ruta.replace("/2/", "/99/")
    antes = deepcopy(store.datos)
    response = client.post(ruta, json={"aceptada": True})
    assert response.status_code == 404
    assert response.json()["mensaje"] == "Cotización o versión no encontrada."
    assert store.datos == antes


@pytest.mark.parametrize("cambiar", ["identificador", "cero", "texto"])
def test_ruta_invalida_tiene_mensaje_claro(contexto, cambiar):
    client, store, cid, ruta, _ = contexto
    ruta = ruta.replace(cid, "invalido") if cambiar == "identificador" else ruta.replace("/2/", "/0/" if cambiar == "cero" else "/abc/")
    antes = deepcopy(store.datos)
    response = client.post(ruta, json={"aceptada": True})
    assert response.status_code == 422 and set(response.json()) == {"mensaje"}
    assert store.datos == antes


@pytest.mark.parametrize("entrada", [{}, {"aceptada": "true"}, {"aceptada": "false"},
                                    {"aceptada": 1}, {"aceptada": None}, {"aceptada": []}])
def test_aceptacion_debe_ser_booleana_explicita(contexto, entrada):
    client, store, _, ruta, _ = contexto
    antes = deepcopy(store.datos)
    response = client.post(ruta, json=entrada)
    assert response.status_code == 422
    assert response.json() == {"mensaje": "Indica si el cliente aceptó esta versión de la cotización."}
    assert store.datos == antes


@pytest.mark.parametrize("campo,valor", [("total", "0"), ("partidas", [])])
def test_no_se_reciben_precios_ni_partidas_en_la_conversion(contexto, campo, valor):
    client, store, _, ruta, _ = contexto
    antes = deepcopy(store.datos)
    response = client.post(ruta, json={"aceptada": True, campo: valor})
    assert response.status_code == 422 and store.datos == antes


def test_disponible_cero_permite_pedido_pendiente_sin_reserva(contexto):
    client, store, _, ruta, _ = contexto
    inv = store.datos["inventarios"][("FER-API-DEMO", "S1")]
    inv.existencia_fisica = inv.comprometida
    antes = deepcopy(store.datos["inventarios"])
    response = client.post(ruta, json={"aceptada": True})
    assert response.status_code == 201 and response.json()["estado"] == "Pendiente"
    assert response.json()["disponibilidad_consultada"][0]["disponible"] == "0"
    assert store.datos["inventarios"] == antes


def test_producto_sin_registro_en_sucursal_rechaza_sin_crear_pedido(contexto):
    client, store, _, ruta, _ = contexto
    del store.datos["inventarios"][("FER-API-DEMO", "S1")]
    antes = deepcopy(store.datos)
    response = client.post(ruta, json={"aceptada": True})
    assert response.status_code == 422 and store.datos == antes


def test_json_mal_formado_devuelve_mensaje_de_conversion(contexto):
    client, store, _, ruta, _ = contexto
    antes = deepcopy(store.datos)
    response = client.post(ruta, content="{", headers={"Content-Type": "application/json"})
    assert response.status_code == 422
    assert response.json() == {"mensaje": "Revisa los datos de la conversión."}
    assert store.datos == antes


def test_base_no_disponible_no_expone_detalles(contexto):
    client, _, _, ruta, api = contexto

    def no_disponible():
        raise psycopg.OperationalError("detalle privado de conexion")

    api.dependency_overrides[obtener_servicio_cotizaciones] = no_disponible
    response = client.post(ruta, json={"aceptada": True})
    assert response.status_code == 503
    assert response.json() == {"mensaje": "Por el momento no podemos crear el pedido. Inténtalo de nuevo más tarde."}


def test_total_y_cantidades_agrupadas_se_toman_de_la_version_guardada(contexto):
    client, store, cid, ruta, _ = contexto
    store.datos["cotizaciones"][(cid, 2)].partidas.append(
        Partida(2, SKU("FER-API-DEMO"), Decimal(1), Dinero(Decimal("50.00"))),
    )
    response = client.post(ruta, json={"aceptada": True})
    assert response.status_code == 201 and response.json()["total"] == "290.00"
    assert response.json()["disponibilidad_consultada"] == [{"sku": "FER-API-DEMO", "solicitada": "3", "disponible": "3"}]


def test_openapi_documenta_conversion_y_respuestas(contexto):
    client, _, _, _, _ = contexto
    operation = client.get("/openapi.json").json()["paths"]["/cotizaciones/{cotizacion_id}/versiones/{version}/convertir"]["post"]
    assert "requestBody" in operation
    assert {"201", "404", "409", "422", "503"} <= set(operation["responses"])
