"""Configuracion de conexion; no abre conexiones ni carga archivos al importar."""

import os

from psycopg.conninfo import make_conninfo


class ConfiguracionBaseNoDisponible(RuntimeError):
    pass


def conexion_desde_entorno() -> str:
    url = os.environ.get("DATABASE_URL", "").strip()
    if url:
        return url
    requeridas = ("POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD")
    if not all(os.environ.get(nombre) for nombre in requeridas):
        raise ConfiguracionBaseNoDisponible("Falta configurar la conexion a PostgreSQL")
    # libpq escapa espacios y comillas de credenciales; no concatenar una URI.
    return make_conninfo(
        host=os.environ.get("POSTGRES_HOST", "127.0.0.1"),
        port=os.environ.get("POSTGRES_PORT", "5433"),
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
    )
