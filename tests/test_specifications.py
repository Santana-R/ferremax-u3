"""Specification de FerreMax: BR02/BR03 y conversion de la version aceptada."""

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from ferremax.domain.model import (
    Cotizacion, CotizacionVencida, Dinero, Partida, SKU, Vigencia,
)
from ferremax.domain.specifications import (
    AceptacionDelCliente, ContextoConversion, CotizacionVigente,
    COTIZACION_CONVERTIBLE,
)


EMISION = datetime(2026, 11, 1, 12, tzinfo=timezone.utc)
VENCIMIENTO = EMISION + timedelta(days=7)


@pytest.fixture
def cotizacion():
    return Cotizacion(
        "COT-SPEC", "COT-001", 2, "CLIENTE-SPEC",
        Vigencia(EMISION, VENCIMIENTO),
        [Partida(1, SKU("SKU-SPEC"), Decimal("2"), Dinero(Decimal("100")))],
        "Condiciones de la version aceptada",
    )


@pytest.mark.parametrize("ahora,esperado", [
    (EMISION - timedelta(microseconds=1), False),
    (EMISION, True),
    (VENCIMIENTO - timedelta(microseconds=1), True),
    (VENCIMIENTO, False),
    (VENCIMIENTO + timedelta(microseconds=1), False),
])
def test_vigencia_incluye_emision_y_excluye_vencimiento(cotizacion, ahora, esperado):
    contexto = ContextoConversion(cotizacion, ahora, True)
    assert CotizacionVigente().is_satisfied_by(contexto) is esperado


@pytest.mark.parametrize("aceptada", [True, False])
def test_aceptacion_de_la_version(cotizacion, aceptada):
    contexto = ContextoConversion(cotizacion, EMISION, aceptada)
    assert AceptacionDelCliente().is_satisfied_by(contexto) is aceptada


@pytest.mark.parametrize("ahora,aceptada,esperado", [
    (EMISION - timedelta(microseconds=1), True, False),
    (EMISION, True, True),
    (VENCIMIENTO - timedelta(microseconds=1), True, True),
    (VENCIMIENTO, True, False),
    (EMISION, False, False),
    (VENCIMIENTO, False, False),
])
def test_conversion_exige_vigencia_y_aceptacion(cotizacion, ahora, aceptada, esperado):
    contexto = ContextoConversion(cotizacion, ahora, aceptada)
    assert COTIZACION_CONVERTIBLE.is_satisfied_by(contexto) is esperado


@pytest.mark.parametrize("vigente,aceptada,and_esperado,or_esperado", [
    (True, True, True, True),
    (True, False, False, True),
    (False, True, False, True),
    (False, False, False, False),
])
def test_operadores_and_or_not(cotizacion, vigente, aceptada, and_esperado, or_esperado):
    # OR y NOT prueban la composicion general; convertir usa exclusivamente AND.
    contexto = ContextoConversion(cotizacion, EMISION if vigente else VENCIMIENTO, aceptada)
    vigencia = CotizacionVigente()
    aceptacion = AceptacionDelCliente()
    assert (vigencia & aceptacion).is_satisfied_by(contexto) is and_esperado
    assert (vigencia | aceptacion).is_satisfied_by(contexto) is or_esperado
    assert (~vigencia).is_satisfied_by(contexto) is (not vigente)


@pytest.mark.parametrize("ahora,esperado", [(EMISION, True), (VENCIMIENTO, False)])
def test_evaluacion_repetible_sin_modificar_cotizacion(cotizacion, ahora, esperado):
    contexto = ContextoConversion(cotizacion, ahora, True)
    antes = deepcopy(contexto)
    assert COTIZACION_CONVERTIBLE.is_satisfied_by(contexto) is esperado
    assert COTIZACION_CONVERTIBLE.is_satisfied_by(contexto) is esperado
    assert contexto == antes


def test_dominio_conserva_prioridad_del_rechazo_si_fallan_ambas(cotizacion):
    antes = deepcopy(cotizacion)
    with pytest.raises(CotizacionVencida, match="Revalide precio, disponibilidad y condiciones"):
        cotizacion.convertir(VENCIMIENTO, False)
    assert cotizacion == antes
