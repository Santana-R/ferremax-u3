"""Arranque configurable, inicializacion atomica y datos conservados al reiniciar."""

from concurrent.futures import ThreadPoolExecutor
import os
from uuid import uuid4

from fastapi.testclient import TestClient
import psycopg
from psycopg import sql
from psycopg.conninfo import make_conninfo
import pytest

from ferremax.api.main import create_app
from scripts import iniciar_api
from scripts.cargar_cotizacion_demo import COTIZACION_DEMO_ID
from scripts.cargar_cotizacion_cliente_demo import CLIENTE_DEMO_ID
from tests.test_api_consulta_pedido_postgres import snapshot


@pytest.mark.parametrize("variable,valor", [("PORT", "0"), ("PORT", "no-es-puerto"),
                                           ("FERREMAX_INIT_DB", "talvez")])
def test_configuracion_invalida_falla_antes_de_conectar_y_no_expone_credenciales(monkeypatch, capsys, variable, valor):
    monkeypatch.setenv("PORT", "8000")
    monkeypatch.setenv("FERREMAX_INIT_DB", "false")
    monkeypatch.setenv("FERREMAX_SEED_DEMO", "false")
    monkeypatch.setenv("DATABASE_URL", "postgresql://usuario:CLAVE-PRIVADA@host/base")
    monkeypatch.setenv(variable, valor)
    assert iniciar_api.main() == 1
    salida = capsys.readouterr()
    assert "Revisa PORT" in salida.err
    assert "CLAVE-PRIVADA" not in salida.err + salida.out


@pytest.fixture
def base_vacia():
    origen = os.environ.get("TEST_DATABASE_URL")
    if not origen:
        pytest.skip("Inicializacion de Render pendiente: falta TEST_DATABASE_URL")
    nombre = "ferremax_boot_" + uuid4().hex
    with psycopg.connect(origen, autocommit=True) as admin:
        admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(nombre)))
        try:
            yield make_conninfo(origen, dbname=nombre)
        finally:
            admin.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(nombre)))


def test_base_nueva_recibe_seis_tablas_y_datos_ficticios(base_vacia):
    iniciar_api.preparar_base(base_vacia, inicializar=True, demo=True)
    with psycopg.connect(base_vacia) as conn:
        tablas = conn.execute("SELECT tablename FROM pg_tables WHERE schemaname='ferremax_u3' ORDER BY tablename").fetchall()
        assert tablas == [(n,) for n in ("auditoria", "cotizacion_version", "inventario", "outbox", "pedido", "reserva")]
        assert conn.execute("SELECT ubicacion_id,existencia_fisica,comprometida FROM ferremax_u3.inventario WHERE sku='FER-API-DEMO' ORDER BY ubicacion_id").fetchall() == [("S1", 10, 0), ("S2", 0, 0)]
        assert conn.execute("SELECT version FROM ferremax_u3.cotizacion_version WHERE id=%s::uuid", (COTIZACION_DEMO_ID,)).fetchall() == [(1,)]
        assert conn.execute("SELECT version FROM ferremax_u3.cotizacion_version WHERE id=%s::uuid", (CLIENTE_DEMO_ID,)).fetchall() == [(1,)]


def test_reiniciar_conserva_cotizaciones_pedido_confirmado_reserva_y_auditoria(base_vacia):
    iniciar_api.preparar_base(base_vacia, inicializar=True, demo=True)
    with TestClient(create_app(base_vacia)) as client:
        ruta = f"/cotizaciones/{COTIZACION_DEMO_ID}/versiones"
        entrada = {"dias_vigencia": 7, "partidas": [{"numero": 1, "sku": "FER-API-DEMO", "cantidad": "2", "precio_unitario": "120.00", "moneda": "MXN"}], "condiciones": "Condiciones nuevas", "motivo": "Revalidacion de prueba"}
        assert client.post(ruta + "/1/revalidar", json=entrada).status_code == 201
        creado = client.post(ruta + "/2/convertir", json={"aceptada": True})
        assert creado.status_code == 201
        pid = creado.json()["pedido_id"]
        assert client.post(f"/pedidos/{pid}/confirmar", json={"pago_autorizado": True, "referencia_pago": "PAGO-FICTICIO", "ubicacion_id": "S1"}).status_code == 200
        antes = snapshot(base_vacia)
        iniciar_api.preparar_base(base_vacia, inicializar=True, demo=True)
        assert snapshot(base_vacia) == antes
        pedido = client.get(f"/pedidos/{pid}").json()
        assert pedido["estado"] == "Confirmado" and pedido["total"] == "240.00"
        assert client.get("/inventario/FER-API-DEMO").json()["ubicaciones"][0]["comprometida"] == "2"


def test_dos_arranques_simultaneos_crean_un_solo_esquema_y_demo(base_vacia):
    with ThreadPoolExecutor(max_workers=2) as pool:
        futuros = [pool.submit(iniciar_api.preparar_base, base_vacia, True, True) for _ in range(2)]
        for futuro in futuros:
            futuro.result()
    with psycopg.connect(base_vacia) as conn:
        assert conn.execute("SELECT count(*) FROM ferremax_u3.cotizacion_version").fetchone() == (2,)
        assert conn.execute("SELECT count(*) FROM ferremax_u3.inventario").fetchone() == (2,)


def test_error_del_ddl_revierte_la_inicializacion_completa(base_vacia, monkeypatch, tmp_path):
    carpeta = tmp_path / "tests/sql"
    carpeta.mkdir(parents=True)
    (carpeta / "ferremax_pruebas.sql").write_text("CREATE SCHEMA ferremax_u3; CREATE TABLE ferremax_u3.parcial(id integer); SENTENCIA_INVALIDA;")
    monkeypatch.setattr(iniciar_api, "ROOT", tmp_path)
    with pytest.raises(psycopg.Error):
        iniciar_api.preparar_base(base_vacia, inicializar=True)
    with psycopg.connect(base_vacia) as conn:
        assert conn.execute("SELECT schema_name FROM information_schema.schemata WHERE schema_name='ferremax_u3'").fetchall() == []
