"""Conversion HTTP y persistencia real en una base PostgreSQL de pruebas."""

from datetime import timedelta
import os
from uuid import uuid4

from fastapi.testclient import TestClient
import psycopg
import pytest

from ferremax.api.main import create_app
from ferremax.application.services import Actor, CotizacionService
from ferremax.domain.model import Cotizacion, Dinero, Partida, SKU, Vigencia
from ferremax.infrastructure.postgres import PostgresReader, PostgresUnitOfWork
from tests.test_api_conversion import AHORA


@pytest.fixture
def conexion():
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Conversion HTTP con PostgreSQL pendiente: falta TEST_DATABASE_URL")
    return url


def preparar(conexion):
    sku = "API-CONVERTIR-" + uuid4().hex
    c = Cotizacion(str(uuid4()), "COT-"+uuid4().hex, 1, "CLIENTE-FICTICIO",
                   Vigencia(AHORA-timedelta(days=8), AHORA-timedelta(days=1)),
                   [Partida(1, SKU(sku), 2, Dinero("100.00"))], "Condiciones originales")
    factory = lambda: PostgresUnitOfWork(conexion)
    with factory() as uow:
        uow.cotizaciones.guardar_nueva_version(c)
        uow.conn.execute("INSERT INTO ferremax_u3.inventario(sku,ubicacion_id,existencia_fisica,en_transito) VALUES(%s,'S1',10,5)", (sku,))
        uow.commit()
    CotizacionService(factory, lambda: AHORA).revalidar(
        Actor("VENDEDOR-TEST", "Vendedor"), c.id, 1, 7,
        [Partida(1, SKU(sku), 2, Dinero("120.00"))], "Condiciones nuevas", "Revalidacion de prueba",
    )
    return c, f"/cotizaciones/{c.id}/versiones/2/convertir"


def filas(conexion, sentencia, parametros):
    with psycopg.connect(conexion) as conn:
        return conn.execute(sentencia, parametros).fetchall()


def versiones(conexion, cid):
    return filas(conexion, "SELECT version,datos FROM ferremax_u3.cotizacion_version WHERE id=%s::uuid ORDER BY version", (cid,))


def test_pedido_http_persiste_version_2_total_240_y_evento_sin_reserva(conexion, monkeypatch):
    c, ruta = preparar(conexion)
    originales = versiones(conexion, c.id)
    sku = c.partidas[0].sku.valor
    monkeypatch.setenv("DATABASE_URL", conexion)
    with TestClient(create_app(reloj=lambda: AHORA)) as client:
        response = client.post(ruta, json={"aceptada": True})
    assert response.status_code == 201
    body = response.json()
    assert body["estado"] == "Pendiente" and body["total"] == "240.00" and body["moneda"] == "MXN"
    pid = body["pedido_id"]
    p = PostgresReader(conexion).consultar_pedido(pid)
    assert p["estado"] == "Pendiente" and p["cotizacion_version"] == 2
    assert p["cotizacion_folio"] == c.folio and p["total"] == "240.00"
    with PostgresUnitOfWork(conexion) as uow:
        pedido = uow.pedidos.obtener(pid)
        assert pedido.referencia_pago is None and pedido.partidas[0].precio.importe == 120
        assert pedido.cotizacion_id == c.id
    assert versiones(conexion, c.id) == originales
    assert filas(conexion, "SELECT existencia_fisica,comprometida,en_transito FROM ferremax_u3.inventario WHERE sku=%s", (sku,)) == [(10, 0, 5)]
    assert filas(conexion, "SELECT pedido_id FROM ferremax_u3.reserva WHERE sku=%s", (sku,)) == []
    eventos = filas(conexion, "SELECT tipo,datos FROM ferremax_u3.outbox WHERE agregado_id=%s", (pid,))
    assert len(eventos) == 1 and eventos[0][0] == "PedidoCreado"
    assert eventos[0][1]["total"] == "240.00" and eventos[0][1]["cotizacion_version"] == 2
    auditoria = filas(conexion, "SELECT accion,despues FROM ferremax_u3.auditoria WHERE agregado_id=%s", (pid,))
    assert len(auditoria) == 1 and auditoria[0][0] == "CrearPedidoDesdeCotizacion"
    assert auditoria[0][1]["estado"] == "Pendiente"


@pytest.mark.parametrize("version,aceptada", [(1, True), (2, False)], ids=["vencida", "sin_aceptacion"])
def test_rechazos_http_no_persisten_pedidos_ni_eventos_de_creacion(conexion, version, aceptada):
    c, ruta = preparar(conexion)
    antes = versiones(conexion, c.id)
    with TestClient(create_app(conexion, reloj=lambda: AHORA)) as client:
        response = client.post(ruta.replace("/2/", f"/{version}/"), json={"aceptada": aceptada})
    assert response.status_code == 409
    assert versiones(conexion, c.id) == antes
    assert filas(conexion, "SELECT id FROM ferremax_u3.pedido WHERE cotizacion_id=%s::uuid", (c.id,)) == []
    assert filas(conexion, "SELECT id FROM ferremax_u3.outbox WHERE tipo='PedidoCreado' AND datos->>'cotizacion_folio'=%s", (c.folio,)) == []


def test_version_inexistente_en_postgres_devuelve_404(conexion):
    c, ruta = preparar(conexion)
    antes = versiones(conexion, c.id)
    with TestClient(create_app(conexion, reloj=lambda: AHORA)) as client:
        response = client.post(ruta.replace("/2/", "/99/"), json={"aceptada": True})
    assert response.status_code == 404 and versiones(conexion, c.id) == antes
    assert filas(conexion, "SELECT id FROM ferremax_u3.pedido WHERE cotizacion_id=%s::uuid", (c.id,)) == []


def test_sin_stock_se_crea_pendiente_pero_no_reserva(conexion):
    c, ruta = preparar(conexion)
    sku = c.partidas[0].sku.valor
    with psycopg.connect(conexion) as conn:
        conn.execute("UPDATE ferremax_u3.inventario SET existencia_fisica=0 WHERE sku=%s", (sku,))
    with TestClient(create_app(conexion, reloj=lambda: AHORA)) as client:
        response = client.post(ruta, json={"aceptada": True})
    assert response.status_code == 201 and response.json()["estado"] == "Pendiente"
    assert response.json()["disponibilidad_consultada"][0]["disponible"] == "0"
    assert filas(conexion, "SELECT pedido_id FROM ferremax_u3.reserva WHERE sku=%s", (sku,)) == []
    assert PostgresReader(conexion).consultar_pedido(response.json()["pedido_id"])["estado"] == "Pendiente"


def test_producto_sin_inventario_rechaza_sin_pedido_parcial(conexion):
    c, ruta = preparar(conexion)
    with psycopg.connect(conexion) as conn:
        conn.execute("DELETE FROM ferremax_u3.inventario WHERE sku=%s", (c.partidas[0].sku.valor,))
    with TestClient(create_app(conexion, reloj=lambda: AHORA)) as client:
        response = client.post(ruta, json={"aceptada": True})
    assert response.status_code == 422
    assert filas(conexion, "SELECT id FROM ferremax_u3.pedido WHERE cotizacion_id=%s::uuid", (c.id,)) == []
    assert filas(conexion, "SELECT id FROM ferremax_u3.outbox WHERE tipo='PedidoCreado' AND datos->>'cotizacion_folio'=%s", (c.folio,)) == []
