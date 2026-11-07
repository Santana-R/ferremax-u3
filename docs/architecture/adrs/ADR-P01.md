# ADR-P01 - Domain Model y servicios de aplicación

Fecha: 6 de noviembre de 2026. Estado: decisión reflejada en la implementación y contrastada con las fuentes indicadas. Este registro describe el estado técnico; no atribuye una aprobación formal adicional del profesor o del equipo.

**Antecedente:** ADR001. Los ADR U3 se conservan en `docs/adr/`; esta versión actualiza su lectura para el PIA, sin reescribirlos.

## Contexto

Cotizaciones versionadas, disponibilidad y estados deben conservar las mismas reglas desde pruebas y HTTP. Guardar datos y decidir validez son responsabilidades diferentes.

## Alternativas

Transaction Script por endpoint sería breve al inicio, pero repetiría vigencia, reserva y transiciones. Table Module organizaría SQL por conjunto sin proteger por sí mismo el ciclo de vida de cada pedido. Domain Model concentra comportamiento y exige más objetos.

## Decisión

Mantener Cotizacion, Pedido, InventarioUbicacion y Value Objects en dominio. CotizacionService/PedidoService coordinan actor, reloj, repositorios y UoW. La API valida el contrato y traduce a HTTP. La lógica de crédito aislada no se presenta como proceso comercial completo.

## Consecuencias y límites

Beneficio: las reglas se reutilizan con Memory y PostgreSQL. Costo: contratos y coordinación explícita. Los agregados actuales conservan colecciones públicas; no se atribuye encapsulación profunda ni se oculta que una transacción abarca varios agregados.

## Evidencia identificable

- [domain/model.py](../../../src/ferremax/domain/model.py)
- [application/services.py](../../../src/ferremax/application/services.py)
- [tests/test_architecture.py](../../../tests/test_architecture.py)
- [tests/test_state_machine.py](../../../tests/test_state_machine.py)

## Trazabilidad

BN02/BN03; BR01-BR06; US04/US05/US06/US09/US10; R06/R08/R19. Ver [matriz de arquitectura](../trazabilidad_arquitectura.csv) y [requisitos del PIA](../../pia/MATRIZ_CUMPLIMIENTO.md).
