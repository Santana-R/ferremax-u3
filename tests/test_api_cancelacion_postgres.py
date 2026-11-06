"""Cancelacion HTTP sobre PostgreSQL: persistencia, concurrencia y rollback."""

from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient
import psycopg
import pytest

from ferremax.api.main import create_app
from ferremax.application.services import Actor, CotizacionService
from ferremax.infrastructure.postgres import PgInventarios, PostgresReader, PostgresUnitOfWork
from tests.test_api_cancelacion import MOTIVO
from tests.test_api_confirmacion import solicitud
from tests.test_api_confirmacion_postgres import conexion, filas, inventarios, preparar
from tests.test_api_conversion import AHORA


def confirmar(client, pid):
    assert client.post(f"/pedidos/{pid}/confirmar", json=solicitud()).status_code == 200


def cancelaciones(conexion, pid):
    return filas(conexion, "SELECT antes,despues,motivo,actor_id FROM ferremax_u3.auditoria WHERE agregado_id=%s AND accion='CancelarPedido'", (pid,))


def test_cancela_y_persiste_liberacion_conservando_otro_pedido(conexion):
    c, pid = preparar(conexion)
    otro = CotizacionService(lambda: PostgresUnitOfWork(conexion), lambda: AHORA).convertir(
        Actor("VENDEDOR-TEST", "Vendedor"), c.id, 2, True,
    )["pedido_id"]
    cotizaciones = filas(conexion, "SELECT version,datos FROM ferremax_u3.cotizacion_version WHERE id=%s::uuid ORDER BY version", (c.id,))
    with TestClient(create_app(conexion, reloj=lambda: AHORA)) as client:
        confirmar(client, pid)
        confirmar(client, otro)
        assert inventarios(conexion, c) == [(c.partidas[0].sku.valor, 10, 4, 5)]
        response = client.post(f"/pedidos/{pid}/cancelar", json={"motivo": MOTIVO})
    assert response.status_code == 200 and response.json()["estado"] == "Cancelado"
    assert PostgresReader(conexion).consultar_pedido(pid)["estado"] == "Cancelado"
    assert PostgresReader(conexion).consultar_pedido(otro)["estado"] == "Confirmado"
    assert inventarios(conexion, c) == [(c.partidas[0].sku.valor, 10, 2, 5)]
    assert filas(conexion, "SELECT pedido_id::text,cantidad FROM ferremax_u3.reserva WHERE sku=%s", (c.partidas[0].sku.valor,)) == [(otro, 2)]
    audit = cancelaciones(conexion, pid)
    assert len(audit) == 1 and audit[0][0]["estado"] == "Confirmado" and audit[0][1]["estado"] == "Cancelado"
    assert audit[0][2:] == (MOTIVO, "cancelacion-api-demo")
    assert filas(conexion, "SELECT tipo FROM ferremax_u3.outbox WHERE agregado_id=%s AND tipo='PedidoCancelado'", (pid,)) == [("PedidoCancelado",)]
    assert filas(conexion, "SELECT version,datos FROM ferremax_u3.cotizacion_version WHERE id=%s::uuid ORDER BY version", (c.id,)) == cotizaciones
    with PostgresUnitOfWork(conexion) as uow:
        assert uow.pedidos.obtener(pid).referencia_pago == solicitud()["referencia_pago"]


@pytest.mark.parametrize("situacion", ["pendiente", "surtido", "repetida"])
def test_rechazos_conservan_datos_y_no_agregan_cancelaciones(conexion, situacion):
    c, pid = preparar(conexion)
    with TestClient(create_app(conexion, reloj=lambda: AHORA)) as client:
        if situacion != "pendiente": confirmar(client, pid)
        if situacion == "surtido":
            with PostgresUnitOfWork(conexion) as uow:
                p = uow.pedidos.obtener(pid)
                p.surtido = True
                uow.pedidos.guardar(p)
                uow.commit()
        ruta = f"/pedidos/{pid}/cancelar"
        if situacion == "repetida":
            assert client.post(ruta, json={"motivo": MOTIVO}).status_code == 200
        antes = inventarios(conexion, c)
        pedido = filas(conexion, "SELECT estado,datos FROM ferremax_u3.pedido WHERE id=%s::uuid", (pid,))
        auditoria = cancelaciones(conexion, pid)
        eventos = filas(conexion, "SELECT id FROM ferremax_u3.outbox WHERE agregado_id=%s", (pid,))
        assert client.post(ruta, json={"motivo": "Intento rechazado"}).status_code == 409
    assert inventarios(conexion, c) == antes
    assert filas(conexion, "SELECT estado,datos FROM ferremax_u3.pedido WHERE id=%s::uuid", (pid,)) == pedido
    assert cancelaciones(conexion, pid) == auditoria
    assert filas(conexion, "SELECT id FROM ferremax_u3.outbox WHERE agregado_id=%s", (pid,)) == eventos


def test_fallo_al_liberar_segundo_producto_revierte_toda_la_transaccion(conexion, monkeypatch):
    c, pid = preparar(conexion, segundo_sin_stock=True)
    with psycopg.connect(conexion) as conn:
        conn.execute("UPDATE ferremax_u3.inventario SET existencia_fisica=10 WHERE sku=%s", (c.partidas[1].sku.valor,))
    with TestClient(create_app(conexion, reloj=lambda: AHORA)) as client:
        confirmar(client, pid)
        antes = inventarios(conexion, c)
        reservas = filas(conexion, "SELECT sku,cantidad FROM ferremax_u3.reserva WHERE pedido_id=%s::uuid ORDER BY sku", (pid,))
        guardar = PgInventarios.guardar
        liberaciones = []

        def fallar_segunda(repo, inv):
            if pid not in inv.reservas:
                liberaciones.append(inv.sku.valor)
                if len(liberaciones) == 2:
                    raise psycopg.OperationalError("Fallo simulado durante la segunda liberacion")
            return guardar(repo, inv)

        monkeypatch.setattr(PgInventarios, "guardar", fallar_segunda)
        response = client.post(f"/pedidos/{pid}/cancelar", json={"motivo": MOTIVO})
    assert response.status_code == 503 and len(liberaciones) == 2
    assert PostgresReader(conexion).consultar_pedido(pid)["estado"] == "Confirmado"
    assert inventarios(conexion, c) == antes
    assert filas(conexion, "SELECT sku,cantidad FROM ferremax_u3.reserva WHERE pedido_id=%s::uuid ORDER BY sku", (pid,)) == reservas
    assert cancelaciones(conexion, pid) == []
    assert filas(conexion, "SELECT id FROM ferremax_u3.outbox WHERE agregado_id=%s AND tipo='PedidoCancelado'", (pid,)) == []


def test_dos_cancelaciones_concurrentes_liberan_una_sola_vez(conexion):
    c, pid = preparar(conexion)
    with TestClient(create_app(conexion, reloj=lambda: AHORA)) as client:
        confirmar(client, pid)

    def cancelar(_):
        with TestClient(create_app(conexion, reloj=lambda: AHORA)) as client:
            return client.post(f"/pedidos/{pid}/cancelar", json={"motivo": MOTIVO}).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        resultados = list(pool.map(cancelar, range(2)))
    assert sorted(resultados) == [200, 409]
    assert inventarios(conexion, c) == [(c.partidas[0].sku.valor, 10, 0, 5)]
    assert filas(conexion, "SELECT cantidad FROM ferremax_u3.reserva WHERE pedido_id=%s::uuid", (pid,)) == []
    assert PostgresReader(conexion).consultar_pedido(pid)["estado"] == "Cancelado"
    assert len(cancelaciones(conexion, pid)) == 1
    assert filas(conexion, "SELECT count(*) FROM ferremax_u3.outbox WHERE agregado_id=%s AND tipo='PedidoCancelado'", (pid,)) == [(1,)]
