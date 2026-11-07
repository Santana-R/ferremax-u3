"""API con PostgreSQL real; usar una base de pruebas separada."""

import os
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from ferremax.api.main import create_app
from scripts.cargar_inventario_demo import cargar_demo


@pytest.fixture
def conexion():
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Integracion API pendiente: falta TEST_DATABASE_URL")
    return url


def test_consulta_http_lee_postgres_sin_modificar_inventario(conexion):
    import psycopg
    sku = "API-TEST-" + uuid4().hex
    with psycopg.connect(conexion) as conn:
        conn.execute(
            "INSERT INTO ferremax_u3.inventario(sku,ubicacion_id,existencia_fisica,en_transito) "
            "VALUES (%s,'S1',10,5),(%s,'S2',0,8)", (sku, sku),
        )
    with TestClient(create_app(conexion)) as client:
        response = client.get("/inventario/" + sku)
    assert response.status_code == 200
    assert response.json()["ubicaciones"] == [
        {"ubicacion_id": "S1", "existencia_fisica": "10", "comprometida": "0", "en_transito": "5", "disponible": "10"},
        {"ubicacion_id": "S2", "existencia_fisica": "0", "comprometida": "0", "en_transito": "8", "disponible": "0"},
    ]
    with psycopg.connect(conexion) as conn:
        filas = conn.execute(
            "SELECT ubicacion_id,existencia_fisica,comprometida,en_transito FROM ferremax_u3.inventario WHERE sku=%s ORDER BY ubicacion_id", (sku,),
        ).fetchall()
    assert filas == [("S1", 10, 0, 5), ("S2", 0, 0, 8)]


def test_consulta_http_producto_no_existente_en_postgres(conexion):
    with TestClient(create_app(conexion)) as client:
        response = client.get("/inventario/API-AUSENTE-" + uuid4().hex)
    assert response.status_code == 404
    assert response.json()["mensaje"] == "Producto no encontrado en el inventario."


def test_consulta_sku_se_trata_como_dato_y_no_como_sql(conexion):
    with TestClient(create_app(conexion)) as client:
        response = client.get("/inventario/%27%20OR%201%3D1--")
    assert response.status_code == 404


def test_carga_demo_repetida_no_duplica_ni_sobrescribe(conexion):
    import psycopg
    cargar_demo(conexion)
    with psycopg.connect(conexion) as conn:
        conn.execute("UPDATE ferremax_u3.inventario SET existencia_fisica=9 WHERE sku='FER-API-DEMO' AND ubicacion_id='S1'")
    cargar_demo(conexion)
    with psycopg.connect(conexion) as conn:
        filas = conn.execute("SELECT ubicacion_id,existencia_fisica FROM ferremax_u3.inventario WHERE sku='FER-API-DEMO' ORDER BY ubicacion_id").fetchall()
    assert filas == [("S1", 9), ("S2", 0)]
