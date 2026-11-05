"""Confirmacion HTTP, reserva, rollback y concurrencia con PostgreSQL real."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
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
from tests.test_api_confirmacion import solicitud
from tests.test_api_conversion import AHORA


@pytest.fixture
def conexion():
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Confirmacion HTTP con PostgreSQL pendiente: falta TEST_DATABASE_URL")
    return url


def preparar(conexion, cantidad=2, stock=10, segundo_sin_stock=False):
    sku = "API-CONFIRMAR-" + uuid4().hex
    c = Cotizacion(str(uuid4()), "COT-"+uuid4().hex, 1, "CLIENTE-FICTICIO",
                   Vigencia(AHORA-timedelta(days=8), AHORA-timedelta(days=1)),
                   [Partida(1, SKU(sku), cantidad, Dinero("100.00"))], "Condiciones originales")
    if segundo_sin_stock:
        c.partidas.append(Partida(2, SKU("ZZ-"+uuid4().hex), 1, Dinero("30.00")))
    factory = lambda: PostgresUnitOfWork(conexion)
    with factory() as uow:
        uow.cotizaciones.guardar_nueva_version(c)
        for index, partida in enumerate(c.partidas):
            uow.conn.execute("INSERT INTO ferremax_u3.inventario(sku,ubicacion_id,existencia_fisica,en_transito) VALUES(%s,'S1',%s,5)",
                             (partida.sku.valor, stock if index == 0 else 0))
        uow.commit()
    nuevas = [replace(c.partidas[0], precio=Dinero("120.00")), *c.partidas[1:]]
    servicio = CotizacionService(factory, lambda: AHORA)
    actor = Actor("VENDEDOR-TEST", "Vendedor")
    servicio.revalidar(actor, c.id, 1, 7, nuevas, "Condiciones revalidadas", "Revalidacion de prueba")
    creado = servicio.convertir(actor, c.id, 2, True)
    return c, creado["pedido_id"]


def filas(conexion, sentencia, parametros):
    with psycopg.connect(conexion) as conn:
        return conn.execute(sentencia, parametros).fetchall()


def inventarios(conexion, c):
    return filas(conexion,
                 "SELECT sku,existencia_fisica,comprometida,en_transito FROM ferremax_u3.inventario WHERE sku=ANY(%s) ORDER BY sku",
                 ([p.sku.valor for p in c.partidas],))


def comprobar_sin_confirmacion(conexion, pid):
    with PostgresUnitOfWork(conexion) as uow:
        p = uow.pedidos.obtener(pid)
        assert p.estado.value == "Pendiente" and p.referencia_pago is None
    assert filas(conexion, "SELECT pedido_id FROM ferremax_u3.reserva WHERE pedido_id=%s::uuid", (pid,)) == []
    assert filas(conexion, "SELECT id FROM ferremax_u3.outbox WHERE agregado_id=%s AND tipo='PedidoConfirmado'", (pid,)) == []
    assert filas(conexion, "SELECT id FROM ferremax_u3.auditoria WHERE agregado_id=%s AND accion='ConfirmarPedido'", (pid,)) == []


def test_confirmacion_http_persiste_estado_reserva_auditoria_y_evento(conexion, monkeypatch):
    c, pid = preparar(conexion)
    anteriores = filas(conexion, "SELECT version,datos FROM ferremax_u3.cotizacion_version WHERE id=%s::uuid ORDER BY version", (c.id,))
    monkeypatch.setenv("DATABASE_URL", conexion)
    with TestClient(create_app(reloj=lambda: AHORA)) as client:
        response = client.post(f"/pedidos/{pid}/confirmar", json=solicitud())
    assert response.status_code == 200 and response.json()["estado"] == "Confirmado"
    pedido = PostgresReader(conexion).consultar_pedido(pid)
    assert pedido["estado"] == "Confirmado" and pedido["cotizacion_version"] == 2
    assert pedido["total"] == "240.00"
    assert inventarios(conexion, c) == [(c.partidas[0].sku.valor, 10, 2, 5)]
    assert filas(conexion, "SELECT cantidad FROM ferremax_u3.reserva WHERE pedido_id=%s::uuid", (pid,)) == [(2,)]
    with PostgresUnitOfWork(conexion) as uow:
        assert uow.pedidos.obtener(pid).referencia_pago == solicitud()["referencia_pago"]
    auditoria = filas(conexion, "SELECT antes,despues FROM ferremax_u3.auditoria WHERE agregado_id=%s AND accion='ConfirmarPedido'", (pid,))
    assert len(auditoria) == 1
    assert auditoria[0][0]["estado"] == "Pendiente" and auditoria[0][1]["estado"] == "Confirmado"
    assert filas(conexion, "SELECT tipo FROM ferremax_u3.outbox WHERE agregado_id=%s AND tipo='PedidoConfirmado'", (pid,)) == [("PedidoConfirmado",)]
    assert filas(conexion, "SELECT version,datos FROM ferremax_u3.cotizacion_version WHERE id=%s::uuid ORDER BY version", (c.id,)) == anteriores


def test_sin_disponible_suficiente_revierte_estado_y_referencia(conexion):
    c, pid = preparar(conexion, stock=1)
    antes = inventarios(conexion, c)
    with TestClient(create_app(conexion, reloj=lambda: AHORA)) as client:
        response = client.post(f"/pedidos/{pid}/confirmar", json=solicitud())
    assert response.status_code == 409
    comprobar_sin_confirmacion(conexion, pid)
    assert inventarios(conexion, c) == antes


def test_segundo_sku_sin_stock_revierte_primera_reserva(conexion):
    c, pid = preparar(conexion, segundo_sin_stock=True)
    antes = inventarios(conexion, c)
    with TestClient(create_app(conexion, reloj=lambda: AHORA)) as client:
        response = client.post(f"/pedidos/{pid}/confirmar", json=solicitud())
    assert response.status_code == 409
    comprobar_sin_confirmacion(conexion, pid)
    assert inventarios(conexion, c) == antes


def test_confirmar_dos_veces_no_duplica_reserva_ni_evento(conexion):
    c, pid = preparar(conexion)
    with TestClient(create_app(conexion, reloj=lambda: AHORA)) as client:
        assert client.post(f"/pedidos/{pid}/confirmar", json=solicitud()).status_code == 200
        antes = inventarios(conexion, c)
        assert client.post(f"/pedidos/{pid}/confirmar", json={**solicitud(), "referencia_pago": "OTRO-PAGO"}).status_code == 409
    assert inventarios(conexion, c) == antes
    assert filas(conexion, "SELECT cantidad FROM ferremax_u3.reserva WHERE pedido_id=%s::uuid", (pid,)) == [(2,)]
    assert filas(conexion, "SELECT count(*) FROM ferremax_u3.outbox WHERE agregado_id=%s AND tipo='PedidoConfirmado'", (pid,)) == [(1,)]
    with PostgresUnitOfWork(conexion) as uow:
        assert uow.pedidos.obtener(pid).referencia_pago == solicitud()["referencia_pago"]


def test_pago_no_autorizado_no_reserva_ni_confirma(conexion):
    c, pid = preparar(conexion)
    antes = inventarios(conexion, c)
    with TestClient(create_app(conexion, reloj=lambda: AHORA)) as client:
        response = client.post(f"/pedidos/{pid}/confirmar", json={**solicitud(), "pago_autorizado": False})
    assert response.status_code == 409
    comprobar_sin_confirmacion(conexion, pid)
    assert inventarios(conexion, c) == antes


def test_dos_pedidos_compiten_por_ultima_unidad_desde_http(conexion):
    c, primero = preparar(conexion, cantidad=1, stock=1)
    segundo = CotizacionService(lambda: PostgresUnitOfWork(conexion), lambda: AHORA).convertir(
        Actor("VENDEDOR-TEST", "Vendedor"), c.id, 2, True,
    )["pedido_id"]

    def confirmar(pid):
        with TestClient(create_app(conexion, reloj=lambda: AHORA)) as client:
            return client.post(f"/pedidos/{pid}/confirmar", json={**solicitud(), "referencia_pago": "PAGO-"+pid}).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        resultados = list(pool.map(confirmar, [primero, segundo]))
    assert sorted(resultados) == [200, 409]
    estados = [PostgresReader(conexion).consultar_pedido(pid)["estado"] for pid in (primero, segundo)]
    assert sorted(estados) == ["Confirmado", "Pendiente"]
    assert inventarios(conexion, c) == [(c.partidas[0].sku.valor, 1, 1, 5)]
    assert filas(conexion, "SELECT sum(cantidad) FROM ferremax_u3.reserva WHERE sku=%s", (c.partidas[0].sku.valor,)) == [(1,)]
    for pid, estado in zip((primero, segundo), estados):
        if estado == "Pendiente": comprobar_sin_confirmacion(conexion, pid)
