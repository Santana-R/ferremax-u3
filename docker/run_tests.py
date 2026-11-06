"""Ejecuta la suite en una base nueva y retira solo esa base al terminar."""

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
from uuid import uuid4
import xml.etree.ElementTree as ET

import psycopg
from psycopg import sql
from psycopg.conninfo import make_conninfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ferremax.api.settings import ConfiguracionBaseNoDisponible, conexion_desde_entorno


def ejecutar(admin_dsn, report_root):
    # El nombre no procede del usuario ni de TEST_DATABASE_URL.
    identificador = uuid4().hex
    database = "ferremax_test_" + identificador
    carpeta = report_root / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ_") + identificador[:8])
    carpeta.mkdir(parents=True, exist_ok=False)

    with psycopg.connect(admin_dsn, autocommit=True, connect_timeout=10) as admin:
        admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database)))
        try:
            test_dsn = make_conninfo(admin_dsn, dbname=database)
            with psycopg.connect(test_dsn, connect_timeout=10) as conn:
                conn.execute((ROOT / "tests/sql/ferremax_pruebas.sql").read_text())
            print("PostgreSQL real: suite en una base temporal independiente de la demostracion.", flush=True)
            proceso = subprocess.run([
                sys.executable, "-m", "pytest", "-q", "--cov=ferremax",
                "--cov-fail-under=80", "--cov-report=term-missing",
                "--cov-report=html:" + str(carpeta / "htmlcov"),
                "--cov-report=json:" + str(carpeta / "coverage.json"),
                "--junitxml=" + str(carpeta / "junit.xml"),
            ], cwd=ROOT, env={
                **os.environ, "TEST_DATABASE_URL": test_dsn, "DATABASE_URL": test_dsn,
                "COVERAGE_FILE": str(carpeta / ".coverage"),
            })
            if proceso.returncode:
                print("La suite no aprobo. Revisa los resultados de esta ejecucion.", flush=True)
                return proceso.returncode if proceso.returncode > 0 else 1

            suites = ET.parse(carpeta / "junit.xml").getroot()
            totales = {campo: sum(int(s.get(campo, 0)) for s in suites.iter("testsuite"))
                       for campo in ("tests", "failures", "errors", "skipped")}
            cobertura = json.loads((carpeta / "coverage.json").read_text())["totals"]["percent_covered"]
            if totales["tests"] == 0 or any(totales[c] for c in ("failures", "errors", "skipped")) or cobertura < 80:
                print("Verificacion incompleta: se requieren pruebas aprobadas, sin omisiones y cobertura >=80%.", flush=True)
                return 1
            print(f"PIA: {totales['tests']} pruebas aprobadas, 0 omitidas; cobertura {cobertura:.2f}%.", flush=True)
            return 0
        finally:
            # Nunca se elimina POSTGRES_DB: solo el nombre aleatorio creado arriba.
            admin.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(database)))
            print("Base temporal eliminada. La base de demostracion se conserva.", flush=True)
            print("Reportes de esta ejecucion:", carpeta, flush=True)


def main():
    try:
        return ejecutar(conexion_desde_entorno(), Path(os.environ.get("TEST_REPORT_DIR", "/reports")).resolve())
    except (psycopg.Error, ConfiguracionBaseNoDisponible):
        print("No se pudo completar la preparacion o limpieza de PostgreSQL. Revisa el servicio db y la configuracion.", file=sys.stderr)
    except (OSError, ET.ParseError, KeyError, ValueError):
        print("No se pudo ejecutar la suite o verificar sus reportes. Revisa la salida de las pruebas.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
