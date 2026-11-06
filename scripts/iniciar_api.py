"""Arranque para Docker/Render; bootstrap explicito y sin reiniciar el historial."""

import os
from pathlib import Path
import sys

import psycopg

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from ferremax.api.settings import ConfiguracionBaseNoDisponible, conexion_desde_entorno
from scripts.cargar_cotizacion_demo import cargar_cotizacion


def booleano(nombre):
    valor = os.environ.get(nombre, "false").strip().lower()
    if valor not in ("true", "false"):
        raise ValueError(f"{nombre} debe ser true o false")
    return valor == "true"


def preparar_base(conexion, inicializar=False, demo=False):
    if inicializar:
        esquema = (ROOT / "tests/sql/ferremax_pruebas.sql").read_text()
        with psycopg.connect(conexion, connect_timeout=10) as conn:
            # Serializa el DDL si dos instancias arrancan a la vez.
            conn.execute("SET LOCAL lock_timeout = '10s'")
            conn.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", ("ferremax-schema-v1",))
            conn.execute(esquema)
        print("Esquema de FerreMax preparado; se conservan las tablas y datos existentes.", flush=True)
    if demo:
        cargar_cotizacion(conexion)
        print("Datos ficticios preparados sin sobrescribir registros existentes.", flush=True)


def main():
    try:
        puerto = int(os.environ.get("PORT", "8000"))
        if not 1 <= puerto <= 65535:
            raise ValueError("PORT fuera de rango")
        inicializar = booleano("FERREMAX_INIT_DB")
        demo = booleano("FERREMAX_SEED_DEMO")
        if inicializar or demo:
            preparar_base(conexion_desde_entorno(), inicializar, demo)
    except (ValueError, ConfiguracionBaseNoDisponible):
        print("No se pudo iniciar la API. Revisa PORT, las opciones de inicializacion y la configuracion de PostgreSQL.", file=sys.stderr)
        return 1
    except (psycopg.Error, OSError):
        print("No se pudo preparar PostgreSQL. Revisa la conexion y el esquema antes de iniciar la API.", file=sys.stderr)
        return 1
    # Uvicorn reemplaza este proceso y recibe las senales de parada del contenedor.
    os.execv(sys.executable, [sys.executable, "-m", "uvicorn", "ferremax.api.main:app",
                            "--app-dir", str(ROOT / "src"), "--host", "0.0.0.0", "--port", str(puerto)])


if __name__ == "__main__":
    raise SystemExit(main())
