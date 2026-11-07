"""Prueba HTTP del Compose de CI, con datos ficticios en una base recien creada."""

from decimal import Decimal
import json
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


COTIZACION = "11111111-1111-4111-8111-111111111111"


def comprobar(base_url):
    def solicitar(metodo, ruta, cuerpo=None, esperado=200):
        data = json.dumps(cuerpo).encode() if cuerpo is not None else None
        req = Request(base_url.rstrip("/") + ruta, data=data, method=metodo,
                      headers={"Content-Type": "application/json", "Accept": "application/json"})
        try:
            with urlopen(req, timeout=10) as response:
                estado, contenido = response.status, response.read()
        except HTTPError as exc:
            with exc:
                estado, contenido = exc.code, exc.read()
        if estado != esperado:
            raise AssertionError(f"{metodo} {ruta}: se esperaba {esperado}, se obtuvo {estado}")
        return json.loads(contenido)

    def inventario():
        body = solicitar("GET", "/inventario/FER-API-DEMO")
        return next(i for i in body["ubicaciones"] if i["ubicacion_id"] == "S1")

    spec = solicitar("GET", "/openapi.json")
    rutas = {
        "/inventario/{sku}", "/cotizaciones/{cotizacion_id}/versiones/{version}/revalidar",
        "/cotizaciones/{cotizacion_id}/versiones/{version}/convertir",
        "/pedidos/{pedido_id}/confirmar", "/pedidos/{pedido_id}/cancelar", "/pedidos/{pedido_id}",
    }
    assert rutas <= set(spec["paths"]), "Faltan operaciones del recorrido en OpenAPI"
    inicial = inventario()
    assert Decimal(inicial["disponible"]) == 10 and Decimal(inicial["comprometida"]) == 0
    quote = f"/cotizaciones/{COTIZACION}/versiones"
    solicitar("POST", quote + "/1/convertir", {"aceptada": True}, esperado=409)
    revalidada = solicitar("POST", quote + "/1/revalidar", {
        "dias_vigencia": 7,
        "partidas": [{"numero": 1, "sku": "FER-API-DEMO", "cantidad": "2",
                      "precio_unitario": "120.00", "moneda": "MXN"}],
        "condiciones": "Precios y condiciones revalidados para la demostracion CI",
        "motivo": "Comprobar el recorrido completo en una base ficticia de CI",
    }, esperado=201)
    assert revalidada["version"] == 2 and revalidada["version_anterior"] == 1
    solicitar("POST", quote + "/2/convertir", {"aceptada": False}, esperado=409)
    creado = solicitar("POST", quote + "/2/convertir", {"aceptada": True}, esperado=201)
    pedido = "/pedidos/" + creado["pedido_id"]

    def consultar(estado):
        body = solicitar("GET", pedido)
        assert body["estado"] == estado and body["cotizacion_version"] == 2
        assert body["cotizacion_folio"] == "COT-API-DEMO"
        assert Decimal(body["total"]) == Decimal("240.00") and body["moneda"] == "MXN"

    consultar("Pendiente")
    pago = {"referencia_pago": "PAGO-FICTICIO-CI", "pago_autorizado": True, "ubicacion_id": "S1"}
    solicitar("POST", pedido + "/confirmar", {**pago, "pago_autorizado": False}, esperado=409)
    consultar("Pendiente")
    assert inventario() == inicial
    solicitar("POST", pedido + "/confirmar", pago)
    consultar("Confirmado")
    reservado = inventario()
    assert Decimal(reservado["comprometida"]) == 2 and Decimal(reservado["disponible"]) == 8
    assert reservado["existencia_fisica"] == inicial["existencia_fisica"]
    assert reservado["en_transito"] == inicial["en_transito"]
    solicitar("POST", pedido + "/confirmar", pago, esperado=409)
    assert inventario() == reservado
    motivo = {"motivo": "El cliente ficticio de CI cancela antes del surtido"}
    solicitar("POST", pedido + "/cancelar", motivo)
    consultar("Cancelado")
    assert inventario() == inicial
    solicitar("POST", pedido + "/cancelar", motivo, esperado=409)
    assert inventario() == inicial
    print("CI HTTP: seis operaciones comprobadas; Pendiente -> Confirmado -> Cancelado; reserva 0 -> 2 -> 0; total 240.00 MXN.")


def main():
    try:
        comprobar(os.environ.get("CI_API_URL", "http://127.0.0.1:8000"))
    except (AssertionError, URLError, OSError, ValueError, KeyError, StopIteration) as exc:
        print("Fallo en la comprobacion HTTP de CI:", str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
