"""Crea una version 1 vencida ficticia, sin sobrescribir versiones anteriores."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from dotenv import load_dotenv
import psycopg
from psycopg.types.json import Jsonb

from ferremax.api.settings import ConfiguracionBaseNoDisponible, conexion_desde_entorno
from ferremax.domain.model import Cotizacion, Dinero, Partida, SKU, Vigencia
from ferremax.infrastructure.postgres import datos
from scripts.cargar_inventario_demo import cargar_demo


COTIZACION_DEMO_ID = "11111111-1111-4111-8111-111111111111"


def cargar_cotizacion(conexion, ahora=None, cotizacion_id=COTIZACION_DEMO_ID, folio="COT-API-DEMO"):
    cargar_demo(conexion)
    ahora = ahora or datetime.now(timezone.utc)
    original = Cotizacion(
        cotizacion_id, folio, 1, "CLIENTE-API-DEMO",
        Vigencia(ahora-timedelta(days=8), ahora-timedelta(days=1)),
        [Partida(1, SKU("FER-API-DEMO"), Decimal(2), Dinero(Decimal("100.00")))],
        "Condiciones de la version original",
    )
    with psycopg.connect(conexion) as conn:
        conn.execute(
            "INSERT INTO ferremax_u3.cotizacion_version(id,version,folio,datos) "
            "VALUES(%s::uuid,%s,%s,%s) ON CONFLICT(id,version) DO NOTHING",
            (original.id, original.version, original.folio, Jsonb(datos(original))),
        )


def main():
    load_dotenv(ROOT / ".env", override=False)
    try:
        cargar_cotizacion(conexion_desde_entorno())
    except (psycopg.Error, ConfiguracionBaseNoDisponible):
        print("No se pudo cargar la cotización de ejemplo. Revisa .env y PostgreSQL.", file=sys.stderr)
        return 1
    print("Cotización ficticia COT-API-DEMO, versión 1; se conservan las versiones existentes.")
    print("Identificador:", COTIZACION_DEMO_ID)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
