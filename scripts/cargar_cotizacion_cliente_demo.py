"""Agrega un folio ficticio para probar la vista, sin reiniciar cotizaciones."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from dotenv import load_dotenv
import psycopg
from ferremax.api.settings import ConfiguracionBaseNoDisponible, conexion_desde_entorno
from scripts.cargar_cotizacion_demo import cargar_cotizacion

CLIENTE_DEMO_ID = "22222222-2222-4222-8222-222222222222"


def cargar_cliente_demo(conexion, ahora=None):
    cargar_cotizacion(conexion, ahora=ahora, cotizacion_id=CLIENTE_DEMO_ID, folio="COT-RENOVAR-DEMO")


def main():
    load_dotenv(ROOT / ".env", override=False)
    try:
        cargar_cliente_demo(conexion_desde_entorno())
    except (psycopg.Error, ConfiguracionBaseNoDisponible):
        print("No pudimos preparar la cotización de demostración. Revisa la conexión a la base de datos.", file=sys.stderr)
        return 1
    print("Cotización COT-RENOVAR-DEMO disponible en /cliente. Se conservan todos los datos existentes.")
    print("Si ya la renovaste, seguirá vigente: este comando no borra ni reinicia el historial.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
