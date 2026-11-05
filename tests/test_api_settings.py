import pytest
from psycopg.conninfo import conninfo_to_dict

from ferremax.api.settings import ConfiguracionBaseNoDisponible, conexion_desde_entorno


@pytest.fixture
def entorno(monkeypatch):
    for name in ("DATABASE_URL", "POSTGRES_HOST", "POSTGRES_PORT"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("POSTGRES_DB", "ferremax_test")
    monkeypatch.setenv("POSTGRES_USER", "usuario_test")
    monkeypatch.setenv("POSTGRES_PASSWORD", "clave ficticia con ' comilla")
    return monkeypatch


def test_conexion_local_escapa_credenciales_y_usa_puerto_del_host(entorno):
    valores = conninfo_to_dict(conexion_desde_entorno())
    assert valores == {
        "host": "127.0.0.1", "port": "5433", "dbname": "ferremax_test",
        "user": "usuario_test", "password": "clave ficticia con ' comilla",
    }


def test_host_y_puerto_se_pueden_configurar(entorno):
    entorno.setenv("POSTGRES_HOST", "db")
    entorno.setenv("POSTGRES_PORT", "5432")
    valores = conninfo_to_dict(conexion_desde_entorno())
    assert (valores["host"], valores["port"]) == ("db", "5432")


def test_database_url_tiene_prioridad(entorno):
    entorno.setenv("DATABASE_URL", "postgresql://usuario@db/base_test")
    assert conexion_desde_entorno() == "postgresql://usuario@db/base_test"


@pytest.mark.parametrize("variable", ["POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD"])
def test_configuracion_incompleta_rechaza_conexion(entorno, variable):
    entorno.delenv(variable)
    with pytest.raises(ConfiguracionBaseNoDisponible):
        conexion_desde_entorno()
