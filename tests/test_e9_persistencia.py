"""Integracion real con el adaptador PostgreSQL de FerreMax.

Ejecutar con scripts/generar_e9.py --postgres-temporal. Si no hay conexion,
se omiten explicitamente; nunca se sustituyen por memoria ni por mocks.
"""

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import os
from uuid import uuid4
import pytest

from ferremax.application.services import Actor, CotizacionService, PedidoService
from ferremax.domain.model import (
    AutorizacionPago, Cotizacion, Dinero, DisponibilidadInsuficiente,
    ErrorNegocio, Partida, SKU, Vigencia,
)
from ferremax.infrastructure.postgres import PostgresReader, PostgresUnitOfWork


AHORA = datetime(2026, 11, 4, 18, 0, tzinfo=timezone.utc)


@pytest.fixture
def pg_url():
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Persistencia PostgreSQL pendiente: falta TEST_DATABASE_URL")
    pytest.importorskip("psycopg")
    return url


def cotizacion(vencida=False):
    sku = SKU("TEST-" + uuid4().hex)
    vigencia = (Vigencia(AHORA-timedelta(days=8), AHORA-timedelta(days=1))
                if vencida else Vigencia(AHORA-timedelta(days=1), AHORA+timedelta(days=6)))
    return Cotizacion(str(uuid4()), "E9-" + uuid4().hex, 1, "CLIENTE-FICTICIO", vigencia,
                      [Partida(1, sku, Decimal("2"), Dinero(Decimal("100.00")))],
                      "Condiciones originales")


def sembrar(url, c, p=None, sin_stock=None):
    with PostgresUnitOfWork(url) as uow:
        uow.cotizaciones.guardar_nueva_version(c)
        if p is not None:
            uow.pedidos.guardar(p)
        for partida in c.partidas:
            cantidad = 0 if partida.sku.valor == sin_stock else 10
            uow.conn.execute(
                "INSERT INTO ferremax_u3.inventario(sku,ubicacion_id,existencia_fisica) VALUES(%s,'S1',%s)",
                (partida.sku.valor, cantidad),
            )
        uow.commit()


def consultar(url, sql, parametros):
    import psycopg
    with psycopg.connect(url, connect_timeout=5) as conn:
        return conn.execute(sql, parametros).fetchall()


def evidencia(request, **datos):
    request.node.user_properties.append(("evidencia", {"motor": "PostgreSQL real", **datos}))


def test_e9_pg_01_commit_recuperable_desde_otra_conexion(pg_url, request):
    c = cotizacion()
    p = c.convertir(AHORA, True)
    sembrar(pg_url, c, p)
    # PostgresReader abre una conexion distinta de la que realizo el commit.
    resultado = PostgresReader(pg_url).consultar_pedido(p.id)
    assert resultado["pedido_id"] == p.id
    assert resultado["estado"] == "Pendiente"
    assert resultado["cotizacion_folio"] == c.folio
    assert resultado["cotizacion_version"] == 1
    assert Decimal(resultado["total"]) == Decimal("200.00")
    evidencia(request, conexion_nueva=True, pedido=resultado)


def test_e9_pg_02_sin_commit_rollback_no_conserva_cotizacion(pg_url, request):
    c = cotizacion()
    with PostgresUnitOfWork(pg_url) as uow:
        uow.cotizaciones.guardar_nueva_version(c)
        # Cerrar sin commit solicita rollback al adaptador real.
    filas = consultar(pg_url,
        "SELECT count(*) FROM ferremax_u3.cotizacion_version WHERE id=%s::uuid", (c.id,))[0][0]
    assert filas == 0
    with PostgresUnitOfWork(pg_url) as uow:
        with pytest.raises(ErrorNegocio, match="inexistente"):
            uow.cotizaciones.obtener(c.id, 1)
    evidencia(request, filas_despues_del_rollback=filas)


def test_e9_pg_03_fallo_en_segundo_sku_revierte_estado_y_primera_reserva(pg_url, request):
    c = cotizacion()
    segundo = SKU("ZZ-" + uuid4().hex)
    c.partidas.append(Partida(2, segundo, Decimal("1"), Dinero(Decimal("20.00"))))
    p = c.convertir(AHORA, True)
    sembrar(pg_url, c, p, sin_stock=segundo.valor)
    servicio = PedidoService(lambda: PostgresUnitOfWork(pg_url), lambda: AHORA)
    with pytest.raises(DisponibilidadInsuficiente):
        servicio.confirmar(Actor("CAJA-TEST", "Caja"), p.id,
                           AutorizacionPago("PAGO-FICTICIO", True), "S1")
    lector = PostgresReader(pg_url)
    pedido = lector.consultar_pedido(p.id)
    primero = lector.consultar_disponibilidad(c.partidas[0].sku.valor)[0]
    reservas = consultar(pg_url, "SELECT count(*) FROM ferremax_u3.reserva WHERE pedido_id=%s::uuid", (p.id,))[0][0]
    eventos = consultar(pg_url, "SELECT count(*) FROM ferremax_u3.outbox WHERE agregado_id=%s", (p.id,))[0][0]
    auditorias = consultar(pg_url, "SELECT count(*) FROM ferremax_u3.auditoria WHERE agregado_id=%s", (p.id,))[0][0]
    assert pedido["estado"] == "Pendiente"
    assert Decimal(primero["disponible"]) == Decimal("10")
    assert Decimal(primero["comprometida"]) == 0
    assert reservas == eventos == auditorias == 0
    evidencia(request, estado=pedido["estado"], disponible_primero=primero["disponible"],
              reservas=reservas, eventos=eventos, auditorias=auditorias)


def test_e9_pg_04_confirmar_y_cancelar_persisten_reservas_y_auditoria(pg_url, request):
    c = cotizacion()
    p = c.convertir(AHORA, True)
    sembrar(pg_url, c, p)
    servicio = PedidoService(lambda: PostgresUnitOfWork(pg_url), lambda: AHORA)
    lector = PostgresReader(pg_url)
    servicio.confirmar(Actor("CAJA-TEST", "Caja"), p.id,
                       AutorizacionPago("PAGO-FICTICIO", True), "S1")
    confirmado = lector.consultar_pedido(p.id)
    reservado = lector.consultar_disponibilidad(c.partidas[0].sku.valor)[0]
    assert confirmado["estado"] == "Confirmado"
    assert Decimal(reservado["disponible"]) == 8
    servicio.cancelar(Actor("VENDEDOR-TEST", "VendedorAutorizadoCancelacion"), p.id, "Cliente cancela")
    cancelado = lector.consultar_pedido(p.id)
    liberado = lector.consultar_disponibilidad(c.partidas[0].sku.valor)[0]
    auditoria = consultar(pg_url,
        "SELECT antes->>'estado',despues->>'estado' FROM ferremax_u3.auditoria WHERE agregado_id=%s AND accion='CancelarPedido'", (p.id,))
    eventos = [fila[0] for fila in consultar(pg_url,
        "SELECT tipo FROM ferremax_u3.outbox WHERE agregado_id=%s", (p.id,))]
    assert cancelado["estado"] == "Cancelado"
    assert Decimal(liberado["disponible"]) == 10
    assert auditoria == [("Confirmado", "Cancelado")]
    assert sorted(eventos) == ["PedidoCancelado", "PedidoConfirmado"]
    evidencia(request, confirmado=confirmado["estado"], cancelado=cancelado["estado"],
              disponible_antes=reservado["disponible"], disponible_despues=liberado["disponible"],
              auditoria=auditoria, eventos=eventos)


def test_e9_pg_05_revalidacion_conserva_versiones_y_pedido_vinculado(pg_url, request):
    c = cotizacion(vencida=True)
    sembrar(pg_url, c)
    servicio = CotizacionService(lambda: PostgresUnitOfWork(pg_url), lambda: AHORA)
    vendedor = Actor("VENDEDOR-TEST", "Vendedor")
    nuevas = [replace(c.partidas[0], precio=Dinero(Decimal("120.00")))]
    servicio.revalidar(vendedor, c.id, 1, 7, nuevas, "Condiciones revalidadas", "Actualizar cotizacion vencida")
    resultado = servicio.convertir(vendedor, c.id, 2, True)
    with PostgresUnitOfWork(pg_url) as uow:
        original = uow.cotizaciones.obtener(c.id, 1)
        nueva = uow.cotizaciones.obtener(c.id, 2)
    pedido = PostgresReader(pg_url).consultar_pedido(resultado["pedido_id"])
    assert original == c
    assert nueva.folio == original.folio
    assert nueva.version == 2 and nueva.partidas[0].precio.importe == Decimal("120.00")
    assert pedido["cotizacion_version"] == 2 and Decimal(pedido["total"]) == Decimal("240.00")
    versiones = [r[0] for r in consultar(pg_url,
        "SELECT version FROM ferremax_u3.cotizacion_version WHERE id=%s::uuid ORDER BY version", (c.id,))]
    assert versiones == [1, 2]
    evidencia(request, versiones=versiones, precio_original=str(original.partidas[0].precio.importe),
              precio_nuevo=str(nueva.partidas[0].precio.importe), pedido=pedido)
