# ADR-P06 - Specification combinable y máquina mediante enum/guardas

Fecha: 6 de noviembre de 2026. Estado: decisión reflejada en la implementación y contrastada con las fuentes indicadas. Este registro describe el estado técnico; no atribuye una aprobación formal adicional del profesor o del equipo.

**Antecedente:** Nuevos componentes PIA. Los ADR U3 se conservan en `docs/adr/`; esta versión actualiza su lectura para el PIA, sin reescribirlos.

## Contexto

El curso exige Specification y State Machine. La conversión necesita vigencia y aceptación puras; el pedido debe restringir confirmaciones y cancelaciones de forma reproducible.

## Alternativas

Condiciones dispersas en controllers duplicarían la regla. Un motor externo o una clase State por estado añadirían estructura innecesaria para las tres situaciones actuales. El contrato Specification y guardas del agregado expresan el alcance actual.

## Decisión

Usar Specification[ContextoConversion], CotizacionVigente y AceptacionDelCliente combinadas con AND. Mantener AND/OR/NOT como operadores probados. EstadoPedido y los métodos confirmar/cancelar definen Pendiente → Confirmado → Cancelado, con validaciones antes de un efecto durable.

## Consecuencias y límites

Beneficio: condiciones nombradas, límites temporales claros y matriz completa de estados/acciones. Costo: mantener mensajes, guardas y documentación consistentes. OR/NOT no representan reglas adicionales de FerreMax; la máquina no tiene aún Surtido/Entregado/Devuelto y un rollback no es Confirmado → Pendiente. No se afirma una implementación GoF State mediante clases.

## Evidencia identificable

- [domain/specifications.py](../../../src/ferremax/domain/specifications.py)
- [domain/model.py](../../../src/ferremax/domain/model.py)
- [tests/test_specifications.py](../../../tests/test_specifications.py)
- [tests/test_state_machine.py](../../../tests/test_state_machine.py)
- [docs/architecture/STATE_MACHINE.md](../../../docs/architecture/STATE_MACHINE.md)

## Trazabilidad

BR02/BR03/BR05/BR06; US04/US05/US09/US10; R20/R21. Ver [matriz de arquitectura](../trazabilidad_arquitectura.csv) y [requisitos del PIA](../../pia/MATRIZ_CUMPLIMIENTO.md).
