# ADR-P04 - CQRS básico con una sola base

Fecha: 6 de noviembre de 2026. Estado: decisión reflejada en la implementación y contrastada con las fuentes indicadas. Este registro describe el estado técnico; no atribuye una aprobación formal adicional del profesor o del equipo.

**Antecedente:** ADR004. Los ADR U3 se conservan en `docs/adr/`; esta versión actualiza su lectura para el PIA, sin reescribirlos.

## Contexto

Consultar disponibilidad o un resumen de pedido no debe exponer operaciones de escritura. Confirmar/cancelar requieren reglas y transacciones diferentes de una lectura.

## Alternativas

Una interfaz única mezclaría guardar y consultar. Separar bases añadiría sincronización y operación sin necesidad demostrada. Separar contratos/handlers y conservar la misma base resuelve la intención actual.

## Decisión

Usar ConfirmarPedido/CancelarPedido como comandos, ConsultarDisponibilidad/ConsultarPedido como consultas y handlers de aplicación. Los comandos delegan a la Service Layer y los lectores devuelven DTO. PostgresReader abre una transacción READ ONLY. Revalidar/convertir siguen invocando CotizacionService directamente.

## Consecuencias y límites

Beneficio: intención y permisos de las interfaces visibles, consultas sin efectos y una sola fuente de datos. Costo: mensajes y DTO adicionales. No implica Event Sourcing, un bus de mensajes, dos bases ni un handler por cada método.

## Evidencia identificable

- [application/cqrs.py](../../../src/ferremax/application/cqrs.py)
- [application/ports.py](../../../src/ferremax/application/ports.py)
- [infrastructure/postgres.py](../../../src/ferremax/infrastructure/postgres.py)
- [tests/test_api_consulta_pedido_postgres.py](../../../tests/test_api_consulta_pedido_postgres.py)
- [tests/test_api_postgres.py](../../../tests/test_api_postgres.py)

## Trazabilidad

US01/US02/US09/US10; RNF06; R08/R09/R22. Ver [matriz de arquitectura](../trazabilidad_arquitectura.csv) y [requisitos del PIA](../../pia/MATRIZ_CUMPLIMIENTO.md).
