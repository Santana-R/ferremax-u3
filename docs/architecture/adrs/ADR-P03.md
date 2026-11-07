# ADR-P03 - Unit of Work, bloqueos y rollback del núcleo

Fecha: 6 de noviembre de 2026. Estado: decisión reflejada en la implementación y contrastada con las fuentes indicadas. Este registro describe el estado técnico; no atribuye una aprobación formal adicional del profesor o del equipo.

**Antecedente:** ADR003. Los ADR U3 se conservan en `docs/adr/`; esta versión actualiza su lectura para el PIA, sin reescribirlos.

## Contexto

Confirmar separado de reservar permitiría un pedido confirmado sin mercancía. Cancelar separado de liberar permitiría cantidades incoherentes. Dos solicitudes pueden competir por la última unidad o por la misma siguiente versión.

## Alternativas

Escrituras independientes arriesgan efectos parciales. Consistencia eventual requeriría estados y compensaciones aún no definidos. Una transacción local de PostgreSQL puede proteger los cambios que usa este prototipo.

## Decisión

Mantener un UoW por comando. Obtener pedido e inventarios con FOR UPDATE y recorrer SKU ordenados; guardar estado, reservas, auditoría y outbox y hacer un commit. Ante excepción, rollback. En revalidación, la PK id/version decide la colisión de dos inserciones; no se inventa un bloqueo FOR UPDATE de cotización. Memory usa copia y RLock para pruebas en proceso.

## Consecuencias y límites

Beneficio: no quedan reservas parciales ni cambios de estado durables cuando falla una partida. Costo: contención, conexiones y manejo de espera; lock_timeout de 5 s no equivale a medir RNF01. La transacción coordina varios agregados en la misma base. No revierte dinero de un proveedor externo y no acredita consistencia distribuida.

## Evidencia identificable

- [application/services.py](../../../src/ferremax/application/services.py)
- [infrastructure/postgres.py](../../../src/ferremax/infrastructure/postgres.py)
- [tests/test_api_confirmacion_postgres.py](../../../tests/test_api_confirmacion_postgres.py)
- [tests/test_api_cancelacion_postgres.py](../../../tests/test_api_cancelacion_postgres.py)
- [tests/test_api_revalidacion_postgres.py](../../../tests/test_api_revalidacion_postgres.py)

## Trazabilidad

BR04-BR06; RNF02/RNF04; AC-US09-01 a 06; AC-US10-01/03/04/05; R23. Ver [matriz de arquitectura](../trazabilidad_arquitectura.csv) y [requisitos del PIA](../../pia/MATRIZ_CUMPLIMIENTO.md).
