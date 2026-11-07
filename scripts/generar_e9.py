"""Ejecuta E9 y exporta observaciones, matriz CSV y cobertura real.

Uso desde la raiz: .venv/bin/python scripts/generar_e9.py
Los resultados se observan en las instancias ejecutadas; no se copian de los
resultados esperados. Los rechazos se capturan dentro de cada prueba.
"""

import argparse
from contextlib import redirect_stderr, redirect_stdout
import csv
from datetime import datetime, timezone
import hashlib
from io import StringIO
import json
import os
from pathlib import Path
import subprocess
import sys
from xml.etree import ElementTree
from zipfile import ZipFile, ZIP_DEFLATED

import coverage
import pytest


ROOT = Path(__file__).resolve().parents[1]
PRUEBAS_BASE = [f"tests/test_e9_{tema}.py" for tema in (
    "inventario", "cotizaciones", "cancelacion"
)]
PRUEBAS = PRUEBAS_BASE + ["tests/test_e9_persistencia.py",
                         "tests/test_e9_adaptador_simulado.py", "tests/test_postgres.py"]
# Alcance funcional de E9: archivos completos invocados por sus nueve casos.
# Todo src se instrumenta y tambien se publica sin filtrar como contraste.
ALCANCE = [
    "src/ferremax/domain/model.py",
    "src/ferremax/application/services.py",
    "src/ferremax/infrastructure/memory.py",
    "src/ferremax/infrastructure/postgres.py",
]

# ID, nombre pytest, regla, historias, tipo, entrada, oraculo independiente.
CASOS = [
    ("E9-INV-01", "test_e9_inv_01_exito_reservar_dos_deja_una_disponible",
     "BR04/BR05", "US09", "Exito",
     "Fisica=10; comprometida=7; transito=5; cantidad=2; pago autorizado simulado",
     "Pedido Confirmado; comprometida=9; disponible=1; conserva reserva ajena=7; un PedidoConfirmado"),
    ("E9-INV-02", "test_e9_inv_02_error_pedir_cuatro_conserva_pedido_e_inventario",
     "BR04/BR05", "US09", "Error",
     "Fisica=10; comprometida=7; transito=5; cantidad=4; pago autorizado simulado",
     "DisponibilidadInsuficiente; pedido Pendiente; comprometida=7; disponible=3; datos intactos"),
    ("E9-INV-03", "test_e9_inv_03_limite_reservar_tres_agota_el_disponible",
     "BR04/BR05", "US09", "Limite",
     "Fisica=10; comprometida=7; transito=5; cantidad=3; pago autorizado simulado",
     "Pedido Confirmado; comprometida=10; disponible=0; conserva reserva ajena=7"),
    ("E9-COT-01", "test_e9_cot_01_exito_revalidar_conserva_historial_y_pedido_usa_version_nueva",
     "BR02/BR03", "US04/US05", "Exito",
     "Version 1 vencida; revalidar 7 dias; precio 100.00 a 120.00 MXN; cantidad=2; cliente acepta version 2",
     "Version 1 intacta; version 2 vigente, mismo folio y condiciones nuevas; pedido version=2, total=240.00; sin reserva"),
    ("E9-COT-02", "test_e9_cot_02_error_version_vencida_no_crea_pedido_ni_modifica_datos",
     "BR03", "US04/US05", "Error",
     "Version 1 vence 2026-11-04 12:00 UTC; convertir a las 12:01 UTC; cliente acepta",
     "CotizacionVencida; ningun pedido, evento ni auditoria nuevos; datos intactos"),
    ("E9-COT-03", "test_e9_cot_03_limite_instante_del_vencimiento_no_permite_conversion",
     "BR03", "US04/US05", "Limite",
     "Version 1 vence 2026-11-04 12:00 UTC; convertir exactamente a las 12:00 UTC; cliente acepta",
     "CotizacionVencida; ningun pedido, evento ni auditoria nuevos; datos intactos"),
    ("E9-CAN-01", "test_e9_can_01_exito_libera_dos_y_conserva_las_siete_de_otro_pedido",
     "BR06", "US10", "Exito",
     "Fisica=10; reservas ajenas=7 y propia=2; pedido Confirmado, no surtido; actor autorizado y motivo",
     "Pedido Cancelado; comprometida=7; disponible=3; conserva otro pedido; auditoria Confirmado a Cancelado; un PedidoCancelado"),
    ("E9-CAN-02", "test_e9_can_02_error_pedido_surtido_conserva_estado_reservas_y_eventos",
     "BR06", "US10", "Error",
     "Fisica=10; reservas ajenas=7 y propia=2; pedido Confirmado y surtido; actor autorizado y motivo",
     "ErrorNegocio de cancelacion; estado Confirmado, comprometida=9 y disponible=1; datos intactos"),
    ("E9-CAN-03", "test_e9_can_03_limite_segunda_cancelacion_no_libera_ni_registra_otro_evento",
     "BR06", "US10", "Limite",
     "Pedido cancelado previamente; reserva propia ya liberada; intentar otra cancelacion autorizada",
     "ErrorNegocio de cancelacion; estado Cancelado, comprometida=7 y disponible=3; conserva un solo PedidoCancelado; datos intactos"),
]


def observar(instancia):
    """Lee los objetos al terminar la prueba, incluidos los cambios persistidos."""
    store = getattr(instancia, "store", None)
    if store is None:
        return {}
    datos = store.datos
    return {
        "rechazo": getattr(instancia, "rechazo_observado", None),
        "reloj_utc": instancia.ahora.isoformat(),
        "pedido_objetivo": getattr(instancia, "pedido_id", None),
        "inventarios": [
            {"sku": inv.sku.valor, "ubicacion": inv.ubicacion_id,
             "fisica": str(inv.existencia_fisica), "comprometida": str(inv.comprometida),
             "disponible": str(inv.disponible), "transito": str(inv.en_transito),
             "reservas": {pid: str(q) for pid, q in inv.reservas.items()}}
            for inv in datos["inventarios"].values()
        ],
        "pedidos": [
            {"id": p.id, "estado": p.estado.value, "surtido": p.surtido,
             "cotizacion_id": p.cotizacion_id, "folio": p.cotizacion_folio,
             "version": p.cotizacion_version, "total": str(p.total.importe),
             "partidas": [{"sku": partida.sku.valor, "cantidad": str(partida.cantidad),
                           "precio": str(partida.precio.importe)} for partida in p.partidas]}
            for p in datos["pedidos"].values()
        ],
        "cotizaciones": [
            {"id": c.id, "folio": c.folio, "version": c.version,
             "emision": c.vigencia.emision.isoformat(),
             "vencimiento": c.vigencia.vencimiento.isoformat(),
             "condiciones": c.condiciones,
             "precios": [str(p.precio.importe) for p in c.partidas],
             "cantidades": [str(p.cantidad) for p in c.partidas]}
            for c in datos["cotizaciones"].values()
        ],
        "eventos": [e.tipo for e in datos["outbox"]],
        "auditoria": [
            {"accion": a["accion"], "actor": a["actor_id"], "motivo": a["motivo"],
             "estado_anterior": a["antes"].get("estado"),
             "estado_nuevo": a["despues"].get("estado")}
            for a in datos["auditoria"]
        ],
    }


def resumir(obs):
    partes = []
    if obs.get("reloj_utc"):
        partes.append("Reloj=" + obs["reloj_utc"])
    if obs.get("rechazo"):
        partes.append("Rechazo: " + obs["rechazo"]["tipo"] + ": " + obs["rechazo"]["mensaje"])
    objetivo = obs.get("pedido_objetivo")
    for p in obs.get("pedidos", []):
        if objetivo is None or p["id"] == objetivo:
            partes.append(f"Pedido={p['estado']}; version={p['version']}; total={p['total']}")
    if not obs.get("pedidos"):
        partes.append("Pedidos=0")
    for i in obs.get("inventarios", []):
        partes.append(f"Comprometida={i['comprometida']}; disponible={i['disponible']}; reservas="
                      + json.dumps(i["reservas"], ensure_ascii=False, sort_keys=True))
    for c in obs.get("cotizaciones", []):
        partes.append(f"Cotizacion={c['folio']}/v{c['version']}; precios={','.join(c['precios'])}; condiciones={c['condiciones']}")
    partes.append("Eventos=" + (", ".join(obs.get("eventos", [])) or "ninguno"))
    return " | ".join(partes)


class RegistroE9:
    def __init__(self):
        self.resultados = {}
        self.complementarias = {}
        self.nombres = {c[1] for c in CASOS}

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_makereport(self, item, call):
        outcome = yield
        report = outcome.get_result()
        if report.when != "call" and not (report.when == "setup" and not report.passed):
            return
        if item.name not in self.nombres:
            instancia = getattr(item, "instance", None)
            observado = getattr(instancia, "evidencia", None)
            if observado is None:
                observado = dict(item.user_properties).get("evidencia", {})
            self.complementarias[item.nodeid] = {
                "estado": report.outcome.upper(), "observado": observado,
                "detalle": report.longreprtext if not report.passed else "",
            }
            return
        self.resultados[item.name] = {
            "estado": report.outcome.upper(), "prueba": item.nodeid,
            "observado": observar(getattr(item, "instance", None)),
            "detalle_fallo": report.longreprtext if report.failed else "",
        }


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def exportar_matriz(registro, salida, commit, fecha):
    filas, detalle = [], []
    for caso_id, nombre, regla, historias, tipo, entrada, esperado in CASOS:
        resultado = registro.resultados.get(nombre, {
            "estado": "NO_EJECUTADO", "prueba": nombre, "observado": {}, "detalle_fallo": ""
        })
        filas.append({
            "id": caso_id, "regla": regla, "historias": historias, "tipo": tipo,
            "entrada": entrada, "resultado_esperado": esperado,
            "resultado_real": resumir(resultado["observado"]),
            "estado": resultado["estado"], "prueba": resultado["prueba"],
            "commit_codigo": commit, "fecha_utc": fecha,
            "detalle": "observaciones_e9.json#" + caso_id,
        })
        detalle.append({"id": caso_id, **resultado})
    with (salida / "matriz_e9.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(filas[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(filas)
    (salida / "observaciones_e9.json").write_text(
        json.dumps(detalle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return filas


def generar(args, postgres_info=None):
    os.chdir(ROOT)
    salida = Path(args.salida).resolve()
    salida.mkdir(parents=True, exist_ok=True)
    fecha = datetime.now(timezone.utc).isoformat()
    commit = git("rev-parse", "HEAD")
    fuentes = sorted([
        *ROOT.glob("src/**/*.py"), *ROOT.glob("tests/**/*.py"),
        ROOT / "scripts/generar_e9.py", ROOT / "pytest.ini", ROOT / "requirements-dev.txt",
        ROOT / ".coveragerc", ROOT / "requirements-e9.txt",
        *ROOT.glob("examples/**/*.py"), *ROOT.glob("tests/sql/*.sql"),
        ROOT / "scripts/postgres_temporal.py",
    ])
    hashes = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in fuentes}

    registro = RegistroE9()
    consola = StringIO()
    anterior = os.environ.get("COVERAGE_FILE")
    os.environ["COVERAGE_FILE"] = str(salida / ".coverage_e9")
    try:
        with redirect_stdout(consola), redirect_stderr(consola):
            codigo_e9 = int(pytest.main([
                *PRUEBAS, "-v", "--color=no", "--cov=src", "--cov-report=term-missing",
                "--cov-report=json:" + str(salida / "cobertura_e9_todo_src.json"),
            ], plugins=[registro]))
    finally:
        if anterior is None:
            os.environ.pop("COVERAGE_FILE", None)
        else:
            os.environ["COVERAGE_FILE"] = anterior
    (salida / "ejecucion_e9.txt").write_text(consola.getvalue(), encoding="utf-8")
    filas = exportar_matriz(registro, salida, commit, fecha)
    (salida / "complementarias_e9.json").write_text(
        json.dumps(registro.complementarias, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    cov = coverage.Coverage(data_file=str(salida / ".coverage_e9"))
    cov.load()
    cov.json_report(outfile=str(salida / "cobertura_e9.json"), include=ALCANCE)
    cov.html_report(directory=str(salida / "htmlcov"), include=ALCANCE, precision=2,
                    title="FerreMax E9: dominio, servicios, Memory y PostgreSQL")
    reporte_e9 = json.loads((salida / "cobertura_e9.json").read_text())
    if set(reporte_e9["files"]) != set(ALCANCE):
        raise RuntimeError("El reporte no contiene exactamente los cuatro archivos declarados")

    entorno = {**os.environ, "COVERAGE_FILE": str(salida / ".coverage_global")}
    regresion = subprocess.run([
        sys.executable, "-m", "pytest", "-v", "--color=no", "--cov=src",
        "--cov-report=term-missing",
        "--cov-report=json:" + str(salida / "cobertura_global.json"),
        "--cov-report=html:" + str(salida / "htmlcov_global"),
        "--junitxml=" + str(salida / "regresion.xml"),
    ], cwd=ROOT, env=entorno, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (salida / "ejecucion_regresion.txt").write_text(regresion.stdout, encoding="utf-8")
    suites = ElementTree.parse(salida / "regresion.xml").getroot().findall("testsuite")
    cantidades = {k: sum(int(s.attrib.get(k, 0)) for s in suites)
                  for k in ("tests", "failures", "errors", "skipped")}
    cantidades["passed"] = cantidades["tests"] - sum(cantidades[k] for k in (
        "failures", "errors", "skipped"
    ))
    global_json = json.loads((salida / "cobertura_global.json").read_text())
    nueve_src = json.loads((salida / "cobertura_e9_todo_src.json").read_text())
    porcentaje = reporte_e9["totals"]["percent_covered"]
    pg = {k: v for k, v in registro.complementarias.items()
          if "test_e9_persistencia.py" in k or "test_postgres.py" in k}
    mocks = {k: v for k, v in registro.complementarias.items()
             if "test_e9_adaptador_simulado.py" in k}
    pg_ok = len(pg) == 6 and all(r["estado"] == "PASSED" for r in pg.values())
    mock_ok = len(mocks) == 3 and all(r["estado"] == "PASSED" for r in mocks.values())
    pendientes = []
    if not pg_ok:
        pendientes.append("Ejecutar las seis pruebas reales PostgreSQL: cinco de persistencia y una de concurrencia")
    if not mock_ok:
        pendientes.append("Ejecutar los tres casos del ejercicio separado con adaptador simulado")
    if porcentaje < 80:
        pendientes.append("Alcanzar 80% de cobertura en los cuatro componentes de E9")
    if codigo_e9 or regresion.returncode or any(f["estado"] != "PASSED" for f in filas):
        pendientes.append("Resolver pruebas fallidas u omitidas del bloque requerido")
    completa = not pendientes
    resumen = {
        "fecha_utc": fecha, "commit_codigo": commit,
        "url_codigo": "https://github.com/Santana-R/ferremax-u3/tree/" + commit,
        "sha256_archivos_medidos": hashes,
        "e9": {"casos": len(filas), "aprobados": sum(f["estado"] == "PASSED" for f in filas),
               "archivos_alcance": ALCANCE, "cobertura": reporte_e9["totals"],
               "umbral_lineas": 80, "cumple_umbral": porcentaje >= 80,
               "todo_src_bloque_e9": nueve_src["totals"]},
        "regresion": {**cantidades, "cobertura_todo_src": global_json["totals"]},
        "persistencia": {"aprobadas": sum(v["estado"] == "PASSED" for v in pg.values()),
                          "esperadas": 6, "completa": pg_ok, "servidor": postgres_info},
        "ejercicio_simulado": {"aprobadas": sum(v["estado"] == "PASSED" for v in mocks.values()),
                               "esperadas": 3, "completo": mock_ok,
                               "alcance": "Ejercicio separado con Mock; no existe integracion externa operativa"},
        "e9_completa": completa, "pendientes": pendientes,
    }
    (salida / "resumen_e9.json").write_text(
        json.dumps(resumen, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    global_pct = global_json["totals"]["percent_covered"]
    nota = f"""# Resultado de E9 de FerreMax

Generado: {fecha}. Codigo ejecutado: [{commit}]({resumen['url_codigo']}).

## Medicion

| Ejecucion y alcance | Lineas cubiertas | Lineas medibles | Cobertura |
| --- | ---: | ---: | ---: |
| Bloque E9: nueve casos, persistencia y ejercicio simulado; cuatro componentes | {reporte_e9['totals']['covered_lines']} | {reporte_e9['totals']['num_statements']} | {porcentaje:.2f}% |
| Mismo bloque E9; todo src como contraste | {nueve_src['totals']['covered_lines']} | {nueve_src['totals']['num_statements']} | {nueve_src['totals']['percent_covered']:.2f}% |
| Suite de regresion; todo src | {global_json['totals']['covered_lines']} | {global_json['totals']['num_statements']} | {global_pct:.2f}% |

E9: {resumen['e9']['aprobados']}/9 casos de negocio aprobados.
PostgreSQL real: {resumen['persistencia']['aprobadas']}/6 aprobadas.
Ejercicio separado con mocks: {resumen['ejercicio_simulado']['aprobadas']}/3 aprobadas.
Estado: {'E9 completa tecnicamente; pendiente incorporacion en U5 por Roberto' if completa else 'AVANCE; persistencia o verificaciones pendientes'}.
Regresion: {cantidades['passed']} aprobadas, {cantidades['skipped']} omitida(s),
{cantidades['failures']} fallidas y {cantidades['errors']} errores.

El alcance E9 se declara en scripts/generar_e9.py: incluye sin recortar lineas
model.py, services.py, memory.py y postgres.py completos. Se ejecutan los nueve
casos de negocio y las nueve pruebas complementarias (persistencia y mocks).
Las omisiones, si existen, aparecen en las salidas. No se recortan esos archivos.
Es cobertura de lineas, no de ramas.
Los JSON completos y htmlcov_global permiten revisar tambien todo src. El
porcentaje E9 no acredita el 80% global que exigira el PIA.

Abrir htmlcov/index.html para E9 y htmlcov_global/index.html para el total.
Una prueba omitida no acredita persistencia. Las pruebas PostgreSQL usan el
adaptador real y conexiones distintas. Las pruebas con Mock son un ejercicio
separado porque no existe una pasarela externa operativa en FerreMax. No se
realizan cobros ni llamadas de red a proveedores.

Pendientes de esta ejecucion: {json.dumps(pendientes, ensure_ascii=False)}.

La matriz se genera leyendo el estado real de cada prueba y su resultado pytest.
observaciones_e9.json conserva pedidos, versiones, reservas, eventos, auditoria
y excepciones observados; complementarias_e9.json registra las observaciones de
persistencia y mocks. resumen_e9.json identifica el codigo con SHA-256.
"""
    (salida / "resumen_cobertura.md").write_text(nota, encoding="utf-8")
    # Coverage crea .gitignore dentro del HTML: retirar solo ese archivo generado
    # permite versionar los reportes. Las bases .coverage_* quedan como intermedios.
    for carpeta in ("htmlcov", "htmlcov_global"):
        (salida / carpeta / ".gitignore").unlink(missing_ok=True)
    if completa:
        (salida / "arranque_postgres_pendiente.txt").unlink(missing_ok=True)
    sufijo = "_para_U5.zip" if completa else "_avance_para_U5.zip"
    paquete = salida.parent / (salida.name + sufijo)
    guia = (ROOT / "docs/E9_INTEGRACION_U5.md").read_text(encoding="utf-8")
    with ZipFile(paquete, "w", compression=ZIP_DEFLATED) as archivo:
        for p in sorted(salida.rglob("*")):
            if p.is_file() and not p.name.startswith("."):
                archivo.write(p, str(p.relative_to(salida)))
        archivo.writestr("LEEME.md", guia.replace("../evidencias/e9/", ""))
    otro = salida.parent / (salida.name + ("_avance_para_U5.zip" if completa else "_para_U5.zip"))
    otro.unlink(missing_ok=True)
    print(f"E9: {resumen['e9']['aprobados']}/9 PASSED; cobertura declarada: {porcentaje:.2f}%")
    print(f"Regresion: {cantidades['passed']} PASSED, {cantidades['skipped']} SKIPPED; todo src: {global_pct:.2f}%")
    print("Resultados:", salida)
    print("PostgreSQL real:", resumen['persistencia']['aprobadas'], "/6; mocks:",
          resumen['ejercicio_simulado']['aprobadas'], "/3")
    print("Estado:", "E9 COMPLETA" if completa else "AVANCE; pendientes explicitados")
    print("Paquete para U5:", paquete)
    if codigo_e9 or regresion.returncode or resumen["e9"]["aprobados"] != 9 or porcentaje < 80:
        return 1
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--salida", default="evidencias/e9")
    parser.add_argument("--postgres-temporal", action="store_true",
                        help="Crear PostgreSQL temporal real y cerrar al finalizar")
    args = parser.parse_args()
    if not args.postgres_temporal:
        return generar(args)
    from postgres_temporal import postgres_temporal
    anterior = os.environ.get("TEST_DATABASE_URL")
    try:
        with postgres_temporal(ROOT / "tests/sql/ferremax_pruebas.sql") as (uri, info):
            os.environ["TEST_DATABASE_URL"] = uri
            return generar(args, info)
    except RuntimeError as exc:
        salida = Path(args.salida).resolve()
        salida.mkdir(parents=True, exist_ok=True)
        (salida / "arranque_postgres_pendiente.txt").write_text(str(exc) + "\n", encoding="utf-8")
        print(str(exc), file=sys.stderr)
        print("La persistencia NO se ha acreditado. Revisar el error y ejecutar desde la terminal normal.", file=sys.stderr)
        return 2
    finally:
        if anterior is None:
            os.environ.pop("TEST_DATABASE_URL", None)
        else:
            os.environ["TEST_DATABASE_URL"] = anterior


if __name__ == "__main__":
    raise SystemExit(main())
