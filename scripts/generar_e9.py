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
PRUEBAS = [f"tests/test_e9_{tema}.py" for tema in (
    "inventario", "cotizaciones", "cancelacion"
)]
# Alcance funcional de E9: archivos completos invocados por sus nueve casos.
# Todo src se instrumenta y tambien se publica sin filtrar como contraste.
ALCANCE = [
    "src/ferremax/domain/model.py",
    "src/ferremax/application/services.py",
    "src/ferremax/infrastructure/memory.py",
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
        self.nombres = {c[1] for c in CASOS}

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_makereport(self, item, call):
        outcome = yield
        report = outcome.get_result()
        if item.name not in self.nombres:
            return
        if report.when != "call" and not (report.when == "setup" and not report.passed):
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--salida", default="evidencias/e9")
    args = parser.parse_args()
    os.chdir(ROOT)
    salida = Path(args.salida).resolve()
    salida.mkdir(parents=True, exist_ok=True)
    fecha = datetime.now(timezone.utc).isoformat()
    commit = git("rev-parse", "HEAD")
    fuentes = sorted([
        *ROOT.glob("src/**/*.py"), *ROOT.glob("tests/**/*.py"),
        ROOT / "scripts/generar_e9.py", ROOT / "pytest.ini", ROOT / "requirements-dev.txt",
        ROOT / ".coveragerc",
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

    cov = coverage.Coverage(data_file=str(salida / ".coverage_e9"))
    cov.load()
    cov.json_report(outfile=str(salida / "cobertura_e9.json"), include=ALCANCE)
    cov.html_report(directory=str(salida / "htmlcov"), include=ALCANCE, precision=2,
                    title="FerreMax E9: dominio, servicios y adaptador Memory (9 pruebas)")
    reporte_e9 = json.loads((salida / "cobertura_e9.json").read_text())
    if set(reporte_e9["files"]) != set(ALCANCE):
        raise RuntimeError("El reporte no contiene exactamente los tres archivos declarados")

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
    resumen = {
        "fecha_utc": fecha, "commit_codigo": commit,
        "url_codigo": "https://github.com/Santana-R/ferremax-u3/tree/" + commit,
        "sha256_archivos_medidos": hashes,
        "e9": {"casos": len(filas), "aprobados": sum(f["estado"] == "PASSED" for f in filas),
               "archivos_alcance": ALCANCE, "cobertura": reporte_e9["totals"],
               "umbral_lineas": 80, "cumple_umbral": porcentaje >= 80,
               "todo_src_solo_nueve_pruebas": nueve_src["totals"]},
        "regresion": {**cantidades, "cobertura_todo_src": global_json["totals"]},
        "pendientes": ["Prueba de persistencia real", "Justificacion de ausencia de servicio externo y ejercicio separado con adaptador simulado"],
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
| Nueve pruebas E9; dominio, servicios y Memory completos | {reporte_e9['totals']['covered_lines']} | {reporte_e9['totals']['num_statements']} | {porcentaje:.2f}% |
| Nueve pruebas E9; todo src como contraste | {nueve_src['totals']['covered_lines']} | {nueve_src['totals']['num_statements']} | {nueve_src['totals']['percent_covered']:.2f}% |
| Suite de regresion; todo src | {global_json['totals']['covered_lines']} | {global_json['totals']['num_statements']} | {global_pct:.2f}% |

E9: {resumen['e9']['aprobados']}/9 casos aprobados.
Regresion: {cantidades['passed']} aprobadas, {cantidades['skipped']} omitida(s),
{cantidades['failures']} fallidas y {cantidades['errors']} errores.

El alcance E9 se declara en scripts/generar_e9.py: incluye sin recortar lineas
model.py, services.py y memory.py, que ejecutan las tres reglas con sus nueve
pruebas. No se omiten ramas de esos archivos. Es cobertura de lineas, no de ramas.
Los JSON completos y htmlcov_global permiten revisar tambien todo src. El
porcentaje E9 no acredita el 80% global que exigira el PIA.

Abrir htmlcov/index.html para E9 y htmlcov_global/index.html para el total.
PostgreSQL sigue pendiente; una prueba omitida no acredita persistencia.
Tampoco existe una pasarela externa: los pagos actuales son autorizaciones
simuladas. Falta justificarlo y completar el ejercicio separado correspondiente.

La matriz se genera leyendo el estado real de cada prueba y su resultado pytest.
observaciones_e9.json conserva pedidos, versiones, reservas, eventos, auditoria
y excepciones observados; resumen_e9.json identifica el codigo con SHA-256.
"""
    (salida / "resumen_cobertura.md").write_text(nota, encoding="utf-8")
    # Coverage crea .gitignore dentro del HTML: retirar solo ese archivo generado
    # permite versionar los reportes. Las bases .coverage_* quedan como intermedios.
    for carpeta in ("htmlcov", "htmlcov_global"):
        (salida / carpeta / ".gitignore").unlink(missing_ok=True)
    paquete = salida.parent / (salida.name + "_avance_para_U5.zip")
    guia = (ROOT / "docs/E9_INTEGRACION_U5.md").read_text(encoding="utf-8")
    with ZipFile(paquete, "w", compression=ZIP_DEFLATED) as archivo:
        for p in sorted(salida.rglob("*")):
            if p.is_file() and not p.name.startswith("."):
                archivo.write(p, str(p.relative_to(salida)))
        archivo.writestr("LEEME.md", guia.replace("../evidencias/e9/", ""))
    print(f"E9: {resumen['e9']['aprobados']}/9 PASSED; cobertura declarada: {porcentaje:.2f}%")
    print(f"Regresion: {cantidades['passed']} PASSED, {cantidades['skipped']} SKIPPED; todo src: {global_pct:.2f}%")
    print("Resultados:", salida)
    print("Paquete de avance para U5:", paquete)
    if codigo_e9 or regresion.returncode or resumen["e9"]["aprobados"] != 9 or porcentaje < 80:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
