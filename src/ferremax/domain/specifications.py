"""Condiciones de negocio puras y componibles para la conversion de cotizaciones."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Generic, TypeVar

if TYPE_CHECKING:
    from .model import Cotizacion

T = TypeVar("T")


class Specification(ABC, Generic[T]):
    @abstractmethod
    def is_satisfied_by(self, contexto: T) -> bool:
        """Evaluar sin modificar el contexto ni realizar operaciones de IO."""
        raise NotImplementedError

    def __and__(self, otra: Specification[T]) -> Specification[T]:
        return AndSpec(self, otra)

    def __or__(self, otra: Specification[T]) -> Specification[T]:
        return OrSpec(self, otra)

    def __invert__(self) -> Specification[T]:
        return NotSpec(self)


@dataclass(frozen=True)
class AndSpec(Specification[T]):
    izquierda: Specification[T]
    derecha: Specification[T]

    def is_satisfied_by(self, contexto: T) -> bool:
        return (self.izquierda.is_satisfied_by(contexto)
                and self.derecha.is_satisfied_by(contexto))


@dataclass(frozen=True)
class OrSpec(Specification[T]):
    izquierda: Specification[T]
    derecha: Specification[T]

    def is_satisfied_by(self, contexto: T) -> bool:
        return (self.izquierda.is_satisfied_by(contexto)
                or self.derecha.is_satisfied_by(contexto))


@dataclass(frozen=True)
class NotSpec(Specification[T]):
    especificacion: Specification[T]

    def is_satisfied_by(self, contexto: T) -> bool:
        return not self.especificacion.is_satisfied_by(contexto)


@dataclass(frozen=True)
class ContextoConversion:
    cotizacion: Cotizacion
    ahora: datetime
    aceptada: bool


class CotizacionVigente(Specification[ContextoConversion]):
    def is_satisfied_by(self, contexto: ContextoConversion) -> bool:
        return contexto.cotizacion.vigencia.esta_vigente(contexto.ahora)


class AceptacionDelCliente(Specification[ContextoConversion]):
    def is_satisfied_by(self, contexto: ContextoConversion) -> bool:
        return bool(contexto.aceptada)


COTIZACION_VIGENTE = CotizacionVigente()
ACEPTACION_DEL_CLIENTE = AceptacionDelCliente()
COTIZACION_CONVERTIBLE = COTIZACION_VIGENTE & ACEPTACION_DEL_CLIENTE
