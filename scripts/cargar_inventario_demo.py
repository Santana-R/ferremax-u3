"""Carga manual e idempotente de un SKU ficticio para probar la consulta en Swagger."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dotenv import load_dotenv
import psycopg

from ferremax.api.settings import ConfiguracionBaseNoDisponible, conexion_desde_entorno


def cargar_demo(conexion):
    with psycopg.connect(conexion) as conn:
        with conn.cursor() as cursor:
            cursor.executemany(
                "INSERT INTO ferremax_u3.inventario "
                "(sku,ubicacion_id,existencia_fisica,en_transito) "
                "VALUES (%s,%s,%s,%s) ON CONFLICT (sku,ubicacion_id) DO NOTHING",
                [("FER-API-DEMO", "S1", 10, 5), ("FER-API-DEMO", "S2", 0, 0)],
            )


def main():
    load_dotenv(ROOT / ".env", override=False)
    try:
        cargar_demo(conexion_desde_entorno())
    except (psycopg.Error, ConfiguracionBaseNoDisponible):
        print("No se pudo cargar el ejemplo. Revisa .env y que PostgreSQL esté disponible.", file=sys.stderr)
        return 1
    print("Producto ficticio FER-API-DEMO disponible en S1 y S2; no se sobrescriben filas existentes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
