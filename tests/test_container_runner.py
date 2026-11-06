"""El ejecutor retira su base incluso si pytest falla o deja pruebas omitidas."""

import json
import os
from pathlib import Path
from types import SimpleNamespace

import psycopg
from psycopg.conninfo import conninfo_to_dict
import pytest

from docker.run_tests import ejecutar
from tests.test_api_consulta_pedido_postgres import snapshot


@pytest.mark.parametrize("resultado", ["fallo_pytest", "pruebas_omitidas"])
def test_base_propia_se_retira_y_base_origen_se_conserva(monkeypatch, tmp_path, resultado):
    conexion = os.environ.get("TEST_DATABASE_URL")
    if not conexion:
        pytest.skip("Ejecutor de contenedor pendiente: falta TEST_DATABASE_URL")
    antes = snapshot(conexion)
    nombres = []

    def pytest_simulado(comando, *, cwd, env):
        dsn = env["TEST_DATABASE_URL"]
        nombre = conninfo_to_dict(dsn)["dbname"]
        assert nombre != conninfo_to_dict(conexion)["dbname"]
        assert env["DATABASE_URL"] == dsn
        nombres.append(nombre)
        # La preparacion y la escritura son reales, en la base creada por el ejecutor.
        with psycopg.connect(dsn) as conn:
            conn.execute("INSERT INTO ferremax_u3.inventario(sku,ubicacion_id,existencia_fisica) VALUES('TEST-RUNNER','S1',1)")
        if resultado == "fallo_pytest":
            return SimpleNamespace(returncode=2)
        reportes = Path(env["COVERAGE_FILE"]).parent
        (reportes / "junit.xml").write_text('<testsuites><testsuite tests="1" failures="0" errors="0" skipped="1"/></testsuites>')
        (reportes / "coverage.json").write_text(json.dumps({"totals": {"percent_covered": 90}}))
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr("docker.run_tests.subprocess.run", pytest_simulado)
    codigo = ejecutar(conexion, tmp_path)
    assert codigo == (2 if resultado == "fallo_pytest" else 1)
    assert len(nombres) == 1
    with psycopg.connect(conexion) as conn:
        assert conn.execute("SELECT datname FROM pg_database WHERE datname=%s", (nombres[0],)).fetchall() == []
    assert snapshot(conexion) == antes
