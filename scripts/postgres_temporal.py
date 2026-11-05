"""Servidor PostgreSQL de pruebas, aislado y sin servicio permanente del sistema.

Utiliza los binarios del paquete pgserver fijado en requirements-e9.txt.
Solo inicializa y detiene el directorio temporal creado por este proceso.
"""

from contextlib import contextmanager
import os
from pathlib import Path
import secrets
import socket
import subprocess
from tempfile import TemporaryDirectory


@contextmanager
def postgres_temporal(esquema):
    import psycopg
    from psycopg.conninfo import make_conninfo
    from pgserver._commands import POSTGRES_BIN_PATH

    with TemporaryDirectory(prefix="fm-e9-") as carpeta:
        root = Path(carpeta).resolve()
        data, log = root / "data", root / "postgres.log"
        binarios = Path(POSTGRES_BIN_PATH)

        def ejecutar(nombre, *args):
            exe = binarios / (nombre + (".exe" if os.name == "nt" else ""))
            r = subprocess.run([str(exe), *map(str, args)], text=True,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               timeout=45)
            if r.returncode:
                detalle = log.read_text(errors="replace") if log.exists() else ""
                raise RuntimeError(f"No arranco PostgreSQL temporal ({nombre}):\n{r.stdout}\n{detalle}")

        usuario = "ferremax_e9"
        if os.name == "nt":
            password = secrets.token_urlsafe(24)
            pwfile = root / "password.txt"
            pwfile.write_text(password + "\n", encoding="utf-8")
            ejecutar("initdb", "-D", data, "-U", usuario, "--encoding=UTF8",
                     "--no-locale", "--auth=scram-sha-256", "--pwfile", pwfile)
            pwfile.unlink()
            with socket.socket() as s:
                s.bind(("127.0.0.1", 0))
                puerto = s.getsockname()[1]
            opciones = f"\nlisten_addresses='127.0.0.1'\nport={puerto}\n"
            uri = make_conninfo(dbname="postgres", user=usuario, password=password,
                                host="127.0.0.1", port=puerto, connect_timeout=5)
            transporte = "TCP loopback con credencial temporal"
        else:
            sock = root / "socket"
            sock.mkdir(mode=0o700)
            ejecutar("initdb", "-D", data, "-U", usuario, "--encoding=UTF8",
                     "--no-locale", "--auth-local=trust", "--auth-host=reject")
            opciones = "\nlisten_addresses=''\nunix_socket_directories='" + str(sock).replace("'", "''") + "'\n"
            uri = make_conninfo(dbname="postgres", user=usuario, host=str(sock), connect_timeout=5)
            transporte = "Socket Unix privado; TCP desactivado"
        opciones += "shared_buffers='16MB'\nmax_connections=20\n"
        with (data / "postgresql.conf").open("a", encoding="utf-8") as f:
            f.write(opciones)
        try:
            ejecutar("pg_ctl", "-D", data, "-l", log, "-w", "-t", "20", "start")
            with psycopg.connect(uri) as conn:
                conn.execute(Path(esquema).read_text(encoding="utf-8"))
                version = conn.execute("SELECT version()").fetchone()[0]
            # La URI queda solo en memoria; no se incluye en los reportes.
            yield uri, {"motor": "PostgreSQL", "version": version,
                        "temporal": True, "transporte": transporte}
        finally:
            if (data / "postmaster.pid").exists():
                ejecutar("pg_ctl", "-D", data, "-m", "fast", "-w", "-t", "20", "stop")
