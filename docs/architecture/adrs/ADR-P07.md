# ADR-P07 - Compose DB/App/Tests y despliegue después de CI

Fecha: 6 de noviembre de 2026. Estado: decisión reflejada en la implementación y contrastada con las fuentes indicadas. Este registro describe el estado técnico; no atribuye una aprobación formal adicional del profesor o del equipo.

**Antecedente:** Nuevos componentes PIA. Los ADR U3 se conservan en `docs/adr/`; esta versión actualiza su lectura para el PIA, sin reescribirlos.

## Contexto

Se necesita reproducir API, PostgreSQL y pruebas sin reutilizar ni destruir la base de demostración. La entrega pública debe tener OpenAPI y conservar los datos después de actualizar.

## Alternativas

Una API sin contenedor dependería más del entorno local. Probar sobre la base del demo alteraría evidencia y estados. Desplegar sin checks podría publicar código cuya suite o recorrido HTTP falló.

## Decisión

Conservar Dockerfile multietapa, servicios db/app/tests, configuración por variables y base temporal propia por suite. CI construye, levanta App/DB, prueba las seis operaciones por HTTP y ejecuta pytest con cobertura >=80% y ninguna omisión. La configuración final de Render despliega desde main después de checksPass; su conexión de DB es interna. El arranque admite flags explícitos de esquema/semilla y conserva datos existentes.

## Consecuencias y límites

Beneficio: repetición aislada y evidencia vinculada al commit. Costo: construir imágenes y operar PostgreSQL/Render; el plan Free puede dormir y tiene límites temporales. El healthcheck de OpenAPI no sustituye una consulta de datos. La semilla idempotente no reinicia el demo y el DDL no es un sistema general de migraciones. El registro de versiones y la evidencia de cierre distinguen la configuración declarada de su aplicación efectiva.

## Evidencia identificable

- [Dockerfile](../../../Dockerfile)
- [docker-compose.yml](../../../docker-compose.yml)
- [docker/run_tests.py](../../../docker/run_tests.py)
- [.github/workflows/ci.yml](../../../.github/workflows/ci.yml)
- [render.yaml](../../../render.yaml)
- [tests/test_arranque_render.py](../../../tests/test_arranque_render.py)
- [tests/test_container_runner.py](../../../tests/test_container_runner.py)
- [evidencias/pia/render_cd_verificacion.json](../../../evidencias/pia/render_cd_verificacion.json)

## Trazabilidad

RNF08; R15/R24-R29/R33. Ver [matriz de arquitectura](../trazabilidad_arquitectura.csv) y [requisitos del PIA](../../pia/MATRIZ_CUMPLIMIENTO.md).
