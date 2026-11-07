"""Revalidacion por HTTP con persistencia real y transacciones PostgreSQL."""

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import timedelta
import os
from uuid import uuid4

from fastapi.testclient import TestClient
import psycopg
import pytest

from ferremax.api.main import create_app
from ferremax.domain.model import Cotizacion, Dinero, Partida, SKU, Vigencia
from ferremax.infrastructure.postgres import PostgresUnitOfWork, datos
from scripts.cargar_cotizacion_demo import COTIZACION_DEMO_ID, cargar_cotizacion
from tests.test_api_revalidacion import AHORA, solicitud


@pytest.fixture
def conexion():
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Revalidacion HTTP con PostgreSQL pendiente: falta TEST_DATABASE_URL")
    return url


def preparar(conexion, vencimiento=None):
    sku = "API-REVALIDAR-" + uuid4().hex
    c = Cotizacion(str(uuid4()), "COT-"+uuid4().hex, 1, "CLIENTE-FICTICIO",
                   Vigencia(AHORA-timedelta(days=8), vencimiento or AHORA-timedelta(days=1)),
                   [Partida(1, SKU(sku), 2, Dinero("100.00"))], "Condiciones originales")
    with PostgresUnitOfWork(conexion) as uow:
        uow.cotizaciones.guardar_nueva_version(c)
        uow.conn.execute("INSERT INTO ferremax_u3.inventario(sku,ubicacion_id,existencia_fisica,en_transito) VALUES(%s,'S1',10,5)", (sku,))
        uow.commit()
    entrada = solicitud()
    entrada["partidas"][0]["sku"] = sku
    return c, entrada, f"/cotizaciones/{c.id}/versiones/1/revalidar"


def filas(conexion, sentencia, parametros):
    with psycopg.connect(conexion) as conn:
        return conn.execute(sentencia, parametros).fetchall()


def versiones(conexion, cotizacion_id):
    return filas(conexion, "SELECT version,datos FROM ferremax_u3.cotizacion_version WHERE id=%s::uuid ORDER BY version", (cotizacion_id,))


def test_http_persiste_dos_versiones_auditoria_y_evento_sin_pedido_ni_reserva(conexion, monkeypatch):
    c, entrada, ruta = preparar(conexion)
    original = deepcopy(datos(c))
    # Verificar tambien la configuracion por entorno, igual que Uvicorn.
    monkeypatch.setenv("DATABASE_URL", conexion)
    with TestClient(create_app(reloj=lambda: AHORA)) as client:
        response = client.post(ruta, json=entrada)
    assert response.status_code == 201
    guardadas = versiones(conexion, c.id)
    assert [v for v, _ in guardadas] == [1, 2]
    assert guardadas[0][1] == original
    assert guardadas[1][1]["partidas"][0]["precio"]["importe"] == "120.00"
    assert guardadas[1][1]["vigencia"]["vencimiento"] == (AHORA+timedelta(days=7)).isoformat()
    assert guardadas[1][1]["condiciones"] == entrada["condiciones"]
    assert filas(conexion, "SELECT estado FROM ferremax_u3.pedido WHERE cotizacion_id=%s::uuid", (c.id,)) == []
    sku = c.partidas[0].sku.valor
    assert filas(conexion, "SELECT existencia_fisica,comprometida,en_transito FROM ferremax_u3.inventario WHERE sku=%s AND ubicacion_id='S1'", (sku,)) == [(10, 0, 5)]
    assert filas(conexion, "SELECT pedido_id FROM ferremax_u3.reserva WHERE sku=%s", (sku,)) == []
    auditoria = filas(conexion, "SELECT antes,despues,motivo FROM ferremax_u3.auditoria WHERE agregado_id=%s", (c.id,))
    assert len(auditoria) == 1
    assert auditoria[0][0]["version"] == 1 and auditoria[0][1]["version"] == 2
    assert auditoria[0][2] == entrada["motivo"]
    assert filas(conexion, "SELECT tipo FROM ferremax_u3.outbox WHERE agregado_id=%s", (c.id,)) == [("CotizacionRevalidada",)]


def test_version_inexistente_en_postgres_no_agrega_versiones(conexion):
    c, entrada, ruta = preparar(conexion)
    antes = versiones(conexion, c.id)
    with TestClient(create_app(conexion, reloj=lambda: AHORA)) as client:
        response = client.post(ruta.replace("/1/", "/8/"), json=entrada)
    assert response.status_code == 404
    assert versiones(conexion, c.id) == antes


def test_producto_ausente_en_segunda_partida_revierte_sin_auditar(conexion):
    c, entrada, ruta = preparar(conexion)
    entrada["partidas"].append({**entrada["partidas"][0], "numero": 2, "sku": "API-AUSENTE-"+uuid4().hex})
    antes = versiones(conexion, c.id)
    with TestClient(create_app(conexion, reloj=lambda: AHORA)) as client:
        response = client.post(ruta, json=entrada)
    assert response.status_code == 422
    assert versiones(conexion, c.id) == antes
    assert filas(conexion, "SELECT id FROM ferremax_u3.auditoria WHERE agregado_id=%s", (c.id,)) == []
    assert filas(conexion, "SELECT id FROM ferremax_u3.outbox WHERE agregado_id=%s", (c.id,)) == []


def test_dos_revalidaciones_concurrentes_crean_una_sola_version(conexion):
    c, entrada, ruta = preparar(conexion)

    def revalidar():
        with TestClient(create_app(conexion, reloj=lambda: AHORA)) as client:
            return client.post(ruta, json=entrada).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        resultados = list(pool.map(lambda _: revalidar(), range(2)))
    assert sorted(resultados) == [201, 409]
    assert [v for v, _ in versiones(conexion, c.id)] == [1, 2]
    assert filas(conexion, "SELECT count(*) FROM ferremax_u3.outbox WHERE agregado_id=%s", (c.id,)) == [(1,)]
    assert filas(conexion, "SELECT count(*) FROM ferremax_u3.auditoria WHERE agregado_id=%s", (c.id,)) == [(1,)]


def test_revalidar_en_instante_del_vencimiento_en_postgres(conexion):
    c, entrada, ruta = preparar(conexion, vencimiento=AHORA)
    with TestClient(create_app(conexion, reloj=lambda: AHORA)) as client:
        assert client.post(ruta, json=entrada).status_code == 201
    assert [v for v, _ in versiones(conexion, c.id)] == [1, 2]


def test_carga_demo_no_reescribe_historial_despues_de_revalidar(conexion):
    cargar_cotizacion(conexion, ahora=AHORA)
    ruta = f"/cotizaciones/{COTIZACION_DEMO_ID}/versiones/1/revalidar"
    with TestClient(create_app(conexion, reloj=lambda: AHORA)) as client:
        assert client.post(ruta, json=solicitud()).status_code == 201
    antes = versiones(conexion, COTIZACION_DEMO_ID)
    cargar_cotizacion(conexion, ahora=AHORA+timedelta(days=3))
    assert versiones(conexion, COTIZACION_DEMO_ID) == antes
