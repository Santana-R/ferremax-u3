# ADR-P02 - PostgreSQL local y en Render, con snapshots JSONB

Fecha: 6 de noviembre de 2026. Estado: decisión reflejada en la implementación y contrastada con las fuentes indicadas. Este registro describe el estado técnico; no atribuye una aprobación formal adicional del profesor o del equipo.

**Antecedente:** ADR002. Los ADR U3 se conservan en `docs/adr/`; esta versión actualiza su lectura para el PIA, sin reescribirlos.

## Contexto

U3 propuso Supabase, pero el PIA implementado y verificado usa PostgreSQL en Compose y una base de Render por red interna. La documentación vigente debe describir los recursos utilizados.

## Alternativas

SQLite reduciría instalación pero no reproduciría los bloqueos de PostgreSQL. Supabase fue una alternativa de alojamiento; no es la base activa de este PIA. Un ORM agregaría otra capa de mapeo; el adaptador actual usa psycopg y SQL explícito.

## Decisión

Usar una única base PostgreSQL para comandos y consultas. Persistir seis tablas: cotizacion_version, pedido, inventario, reserva, auditoria y outbox. Snapshots JSONB conservan el contenido de cotización/pedido; columnas tipadas y claves expresan relaciones, estados y cantidades. Conservar el esquema ferremax_u3 para no romper datos existentes.

## Consecuencias y límites

Beneficio: transacciones, claves compuestas y bloqueos reales, más una preparación de esquema compartida. Costo: mapear JSONB/Decimal/fechas explícitamente y mantener coherencia de columnas y snapshots. No existe un catálogo maestro completo ni una tabla por cada Value Object. No se acredita 3FN sobre el snapshot JSONB ni un sistema general de migraciones.

## Evidencia identificable

- [infrastructure/postgres.py](../../../src/ferremax/infrastructure/postgres.py)
- [tests/sql/ferremax_pruebas.sql](../../../tests/sql/ferremax_pruebas.sql)
- `tests/test_api_*_postgres.py`
- [evidencias/pia/render_cd_verificacion.json](../../../evidencias/pia/render_cd_verificacion.json)

## Trazabilidad

RNF02/RNF08; BR02/BR04/BR05/BR16; R07/R10/R23/R29. Ver [matriz de arquitectura](../trazabilidad_arquitectura.csv) y [requisitos del PIA](../../pia/MATRIZ_CUMPLIMIENTO.md).
