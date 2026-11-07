# ADR-P05 - Auditoría y outbox en la misma transacción

Fecha: 6 de noviembre de 2026. Estado: decisión reflejada en la implementación y contrastada con las fuentes indicadas. Este registro describe el estado técnico; no atribuye una aprobación formal adicional del profesor o del equipo.

**Antecedente:** ADR005. Los ADR U3 se conservan en `docs/adr/`; esta versión actualiza su lectura para el PIA, sin reescribirlos.

## Contexto

BR16 requiere qué cambió, quién, cuándo y por qué. Un registro o publicación por separado puede perder el hecho o anunciar éxito antes de confirmar los datos.

## Alternativas

Auditar después del commit puede perder registros. Publicar antes puede anunciar un éxito que se revierte. Incorporar un broker sin consumidor definido agregaría operación y obligaciones de entrega que el proyecto no implementa.

## Decisión

Los servicios construyen EventoDominio y llaman UnitOfWork.registrar con actor, acción, antes/después y motivo. PostgreSQL inserta auditoría y outbox dentro de la transacción del negocio. Los eventos corresponden a revalidación, creación de pedido, confirmación y cancelación.

## Consecuencias y límites

Beneficio: coherencia entre cambio y registro durable. Costo: tablas y definición futura de publicación/idempotencia. No hay consumidor externo ni garantía de entrega exactamente una vez. El actor HTTP es ficticio y no hay API de bitácora. A diferencia del supuesto U3, no se acredita una política de permisos operativos que impida UPDATE/DELETE de auditoría. EventoDominio es congelado, pero su payload dict no es profundamente inmutable.

## Evidencia identificable

- [application/services.py](../../../src/ferremax/application/services.py)
- [infrastructure/postgres.py](../../../src/ferremax/infrastructure/postgres.py)
- [tests/test_e9_persistencia.py](../../../tests/test_e9_persistencia.py)
- [tests/test_api_confirmacion_postgres.py](../../../tests/test_api_confirmacion_postgres.py)
- [tests/test_api_cancelacion_postgres.py](../../../tests/test_api_cancelacion_postgres.py)

## Trazabilidad

BR16; RNF04; US20 parcial; AC-US20-02; R08/R10/R16. Ver [matriz de arquitectura](../trazabilidad_arquitectura.csv) y [requisitos del PIA](../../pia/MATRIZ_CUMPLIMIENTO.md).
