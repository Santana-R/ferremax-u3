"""Contrato de revalidacion con el servicio real y Unit of Work Memory."""

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient
import psycopg
import pytest

from ferremax.api.cotizaciones import obtener_servicio_cotizaciones
from ferremax.api.main import create_app
from ferremax.application.services import CotizacionService
from ferremax.domain.model import Cotizacion, Dinero, InventarioUbicacion, Partida, SKU, Vigencia
from ferremax.infrastructure.memory import MemoryStore, MemoryUnitOfWork


AHORA = datetime(2026, 11, 5, 12, tzinfo=timezone.utc)


def solicitud():
    return {
        "dias_vigencia": 7,
        "partidas": [{"numero": 1, "sku": "FER-API-DEMO", "cantidad": "2",
                      "precio_unitario": "120.00", "moneda": "MXN"}],
        "condiciones": "Condiciones de la nueva version", "motivo": "Cliente solicita revalidar",
    }


@pytest.fixture
def contexto():
    store = MemoryStore()
    c = Cotizacion(str(uuid4()), "COT-HTTP-TEST", 1, "CLIENTE-FICTICIO",
                   Vigencia(AHORA-timedelta(days=8), AHORA-timedelta(days=1)),
                   [Partida(1, SKU("FER-API-DEMO"), Decimal(2), Dinero(Decimal(100)))],
                   "Condiciones originales")
    store.datos["cotizaciones"][(c.id, 1)] = c
    store.datos["inventarios"][("FER-API-DEMO", "S1")] = InventarioUbicacion(SKU("FER-API-DEMO"), "S1", Decimal(10))
    api = create_app(reloj=lambda: AHORA)
    servicio = CotizacionService(lambda: MemoryUnitOfWork(store), lambda: AHORA)
    api.dependency_overrides[obtener_servicio_cotizaciones] = lambda: servicio
    with TestClient(api) as client:
        yield client, store, c, f"/cotizaciones/{c.id}/versiones/1/revalidar", api


def test_revalidar_crea_version_2_conserva_original_y_no_crea_pedido_ni_reservas(contexto):
    client, store, c, ruta, _ = contexto
    original = deepcopy(c)
    inventario = deepcopy(store.datos["inventarios"])
    response = client.post(ruta, json=solicitud())
    assert response.status_code == 201
    assert response.json() == {
        "mensaje": "Se creó una nueva versión de la cotización y se conservó la anterior.",
        "cotizacion_id": c.id, "version_anterior": 1, "folio": c.folio, "version": 2, "estado": "Vigente",
    }
    versiones = store.datos["cotizaciones"]
    assert set(versiones) == {(c.id, 1), (c.id, 2)}
    assert versiones[(c.id, 1)] == original
    nueva = versiones[(c.id, 2)]
    assert nueva.folio == original.folio and nueva.cliente_id == original.cliente_id
    assert nueva.vigencia == Vigencia(AHORA, AHORA+timedelta(days=7))
    assert nueva.partidas[0].precio.importe == Decimal("120.00")
    assert nueva.condiciones == solicitud()["condiciones"]
    assert store.datos["inventarios"] == inventario and store.datos["pedidos"] == {}
    assert [evento.tipo for evento in store.datos["outbox"]] == ["CotizacionRevalidada"]
    auditoria = store.datos["auditoria"]
    assert len(auditoria) == 1
    assert auditoria[0]["antes"]["version"] == 1 and auditoria[0]["despues"]["version"] == 2
    assert auditoria[0]["motivo"] == solicitud()["motivo"]


def test_instante_del_vencimiento_ya_permite_revalidar(contexto):
    client, store, c, ruta, _ = contexto
    c.vigencia = Vigencia(AHORA-timedelta(days=7), AHORA)
    original = deepcopy(c)
    assert client.post(ruta, json=solicitud()).status_code == 201
    assert store.datos["cotizaciones"][(c.id, 1)] == original


@pytest.mark.parametrize("emision,vencimiento", [
    (AHORA-timedelta(days=1), AHORA+timedelta(days=1)),
    (AHORA+timedelta(days=1), AHORA+timedelta(days=2)),
], ids=["aun_vigente", "aun_no_emitida"])
def test_version_no_revalidable_conserva_todos_los_datos(contexto, emision, vencimiento):
    client, store, c, ruta, _ = contexto
    c.vigencia = Vigencia(emision, vencimiento)
    antes = deepcopy(store.datos)
    response = client.post(ruta, json=solicitud())
    assert response.status_code == 409
    assert response.json()["cotizacion_id"] == c.id
    assert store.datos == antes


@pytest.mark.parametrize("cambiar", ["identificador", "version"])
def test_cotizacion_o_version_inexistente_devuelve_404(contexto, cambiar):
    client, store, c, ruta, _ = contexto
    ruta = ruta.replace(c.id, str(uuid4())) if cambiar == "identificador" else ruta.replace("/1/", "/2/")
    antes = deepcopy(store.datos)
    response = client.post(ruta, json=solicitud())
    assert response.status_code == 404
    assert response.json()["mensaje"] == "Cotización o versión no encontrada."
    assert store.datos == antes


def test_repetir_original_o_revalidar_nueva_vigente_no_duplica_version_ni_evento(contexto):
    client, store, _, ruta, _ = contexto
    assert client.post(ruta, json=solicitud()).status_code == 201
    antes = deepcopy(store.datos)
    for intento in (ruta, ruta.replace("/1/", "/2/")):
        assert client.post(intento, json=solicitud()).status_code == 409
        assert store.datos == antes


@pytest.mark.parametrize("campo,valor", [
    ("dias_vigencia", 0), ("dias_vigencia", 7.5), ("dias_vigencia", True),
    ("partidas", []), ("condiciones", "   "), ("motivo", ""),
    ("numero", 0), ("sku", "   "), ("cantidad", "0"), ("cantidad", "-1"),
    ("precio_unitario", "-1"), ("precio_unitario", "NaN"), ("precio_unitario", "Infinity"),
    ("moneda", ""),
])
def test_datos_invalidos_devuelven_422_sin_modificar_estado(contexto, campo, valor):
    client, store, _, ruta, _ = contexto
    entrada = solicitud()
    objetivo = entrada if campo in ("dias_vigencia", "partidas", "condiciones", "motivo") else entrada["partidas"][0]
    objetivo[campo] = valor
    antes = deepcopy(store.datos)
    response = client.post(ruta, json=entrada)
    assert response.status_code == 422
    assert set(response.json()) == {"mensaje"}
    assert store.datos == antes


@pytest.mark.parametrize("cambiar", ["identificador", "version"])
def test_parametros_de_ruta_invalidos_tienen_mensaje_claro(contexto, cambiar):
    client, store, c, ruta, _ = contexto
    ruta = ruta.replace(c.id, "no-es-identificador") if cambiar == "identificador" else ruta.replace("/1/", "/0/")
    antes = deepcopy(store.datos)
    response = client.post(ruta, json=solicitud())
    assert response.status_code == 422 and set(response.json()) == {"mensaje"}
    assert store.datos == antes


@pytest.mark.parametrize("caso", ["renglones_repetidos", "monedas_distintas", "producto_ausente", "vigencia_fuera_de_rango"])
def test_reglas_del_dominio_rechazan_sin_cambios(contexto, caso):
    client, store, _, ruta, _ = contexto
    entrada = solicitud()
    if caso in ("renglones_repetidos", "monedas_distintas"):
        entrada["partidas"].append(deepcopy(entrada["partidas"][0]))
        if caso == "monedas_distintas":
            entrada["partidas"][1].update(numero=2, moneda="USD")
    elif caso == "producto_ausente":
        entrada["partidas"][0]["sku"] = "PRODUCTO-AUSENTE"
    else:
        entrada["dias_vigencia"] = 1000000000
    antes = deepcopy(store.datos)
    response = client.post(ruta, json=entrada)
    assert response.status_code == 422
    assert store.datos == antes


def test_json_mal_formado_devuelve_indicacion_sin_detalles_tecnicos(contexto):
    client, store, _, ruta, _ = contexto
    antes = deepcopy(store.datos)
    response = client.post(ruta, content="{", headers={"Content-Type": "application/json"})
    assert response.status_code == 422
    assert response.json() == {"mensaje": "Revisa los datos de la revalidación."}
    assert store.datos == antes


def test_error_de_base_devuelve_503_sin_exponer_detalles(contexto):
    client, _, _, ruta, api = contexto

    def no_disponible():
        raise psycopg.OperationalError("detalle privado de conexion")

    api.dependency_overrides[obtener_servicio_cotizaciones] = no_disponible
    response = client.post(ruta, json=solicitud())
    assert response.status_code == 503
    assert response.json() == {
        "mensaje": "Por el momento no podemos revalidar la cotización. Inténtalo de nuevo más tarde.",
    }


def test_openapi_documenta_cuerpo_y_respuestas_de_revalidacion(contexto):
    client, _, _, _, _ = contexto
    spec = client.get("/openapi.json").json()
    operation = spec["paths"]["/cotizaciones/{cotizacion_id}/versiones/{version}/revalidar"]["post"]
    assert "requestBody" in operation
    assert {"201", "404", "409", "422", "503"} <= set(operation["responses"])


@pytest.mark.parametrize("nivel", ["solicitud", "partida"])
def test_campos_desconocidos_se_rechazan_para_evitar_errores_silenciosos(contexto, nivel):
    client, store, _, ruta, _ = contexto
    entrada = solicitud()
    objetivo = entrada if nivel == "solicitud" else entrada["partidas"][0]
    objetivo["campo_no_reconocido"] = "valor"
    antes = deepcopy(store.datos)
    response = client.post(ruta, json=entrada)
    assert response.status_code == 422
    assert response.json() == {"mensaje": "La solicitud incluye campos no reconocidos. Usa los campos del ejemplo."}
    assert store.datos == antes
