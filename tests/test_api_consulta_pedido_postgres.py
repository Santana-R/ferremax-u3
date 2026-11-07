"""Consulta HTTP con PostgreSQL real y comprobacion de solo lectura."""

import os
from uuid import uuid4

from fastapi.testclient import TestClient
import psycopg
from psycopg import sql
import pytest

from ferremax.api.main import create_app
from ferremax.domain.model import Dinero, Partida
from ferremax.infrastructure.postgres import PostgresUnitOfWork
from tests.test_api_confirmacion import solicitud
from tests.test_api_confirmacion_postgres import preparar
from tests.test_api_conversion import AHORA


@pytest.fixture
def conexion():
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Consulta de pedido con PostgreSQL pendiente: falta TEST_DATABASE_URL")
    return url


def snapshot(conexion):
    with psycopg.connect(conexion) as conn:
        return {
            nombre: conn.execute(sql.SQL("SELECT to_jsonb(t) FROM {} t ORDER BY to_jsonb(t)::text").format(
                sql.Identifier("ferremax_u3", nombre),
            )).fetchall()
            for nombre in ("pedido", "cotizacion_version", "inventario", "reserva", "auditoria", "outbox")
        }


@pytest.mark.parametrize("estado", ["Pendiente", "Confirmado", "Cancelado"])
def test_http_consulta_estado_persistido_sin_escrituras(conexion, monkeypatch, estado):
    c, pid = preparar(conexion)
    monkeypatch.setenv("DATABASE_URL", conexion)
    with TestClient(create_app(reloj=lambda: AHORA)) as client:
        if estado != "Pendiente":
            assert client.post(f"/pedidos/{pid}/confirmar", json=solicitud()).status_code == 200
        if estado == "Cancelado":
            assert client.post(f"/pedidos/{pid}/cancelar", json={"motivo": "Cliente cancela"}).status_code == 200
        antes = snapshot(conexion)
        for _ in range(2):
            response = client.get(f"/pedidos/{pid}")
            assert response.status_code == 200
            assert response.json() == {
                "mensaje": "Pedido consultado.", "pedido_id": pid, "estado": estado,
                "cotizacion_folio": c.folio, "cotizacion_version": 2,
                "total": "240.00", "moneda": "MXN",
            }
            assert snapshot(conexion) == antes


def test_pedido_inexistente_en_postgres_no_genera_registros(conexion):
    pid = str(uuid4())
    antes = snapshot(conexion)
    with TestClient(create_app(conexion)) as client:
        response = client.get(f"/pedidos/{pid}")
    assert response.status_code == 404
    assert response.json() == {"mensaje": "Pedido no encontrado.", "pedido_id": pid}
    assert snapshot(conexion) == antes


def test_nueva_version_de_cotizacion_no_cambia_origen_ni_total_del_pedido(conexion):
    c, pid = preparar(conexion)
    with PostgresUnitOfWork(conexion) as uow:
        anterior = uow.cotizaciones.obtener(c.id, 2)
        # Nueva version de prueba: no se modifica la version de origen del pedido.
        from dataclasses import replace
        nueva = replace(anterior, version=3,
                        partidas=[Partida(1, c.partidas[0].sku, 2, Dinero("999.00"))])
        uow.cotizaciones.guardar_nueva_version(nueva)
        uow.commit()
    antes = snapshot(conexion)
    with TestClient(create_app(conexion)) as client:
        response = client.get(f"/pedidos/{pid}")
    assert response.status_code == 200
    assert response.json()["total"] == "240.00" and response.json()["cotizacion_version"] == 2
    assert snapshot(conexion) == antes
