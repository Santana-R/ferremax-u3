# Decisiones técnicas del PIA

Registros del 6 de noviembre de 2026. La implementación actual es la fuente para describir las decisiones vigentes. Los antecedentes U3 se mantienen intactos; su condición histórica evita interpretar Supabase, PostgreSQL pendiente o permisos no acreditados como características actuales.

| Registro PIA | Decisión vigente | Antecedente |
| --- | --- | --- |
| [ADR-P01](adrs/ADR-P01.md) | Domain Model y servicios de aplicación | [ADR001](../adr/ADR001.md) |
| [ADR-P02](adrs/ADR-P02.md) | PostgreSQL local y en Render, con snapshots JSONB | [ADR002](../adr/ADR002.md) |
| [ADR-P03](adrs/ADR-P03.md) | Unit of Work, bloqueos y rollback del núcleo | [ADR003](../adr/ADR003.md) |
| [ADR-P04](adrs/ADR-P04.md) | CQRS básico con una sola base | [ADR004](../adr/ADR004.md) |
| [ADR-P05](adrs/ADR-P05.md) | Auditoría y outbox en la misma transacción | [ADR005](../adr/ADR005.md) |
| [ADR-P06](adrs/ADR-P06.md) | Specification combinable y máquina mediante enum/guardas | Nuevos componentes PIA |
| [ADR-P07](adrs/ADR-P07.md) | Compose DB/App/Tests y despliegue después de CI | Nuevos componentes PIA |

Cada registro contiene contexto, alternativas, decisión, consecuencias, evidencia y trazabilidad. Las decisiones delimitan el sistema existente; las historias de negocio todavía diseñadas conservan sus pendientes en el [BRD](../BRD.md).

## Correcciones respecto a supuestos anteriores

| Tema | Lectura vigente |
| --- | --- |
| Alojamiento | PostgreSQL local/Compose y Render; Supabase queda como alternativa histórica de U3. |
| Persistencia/concurrencia | Pruebas con PostgreSQL real y CI registradas; no se marcan como pendientes por textos antiguos. |
| Auditoría | Se registra transaccionalmente, con actor de demo; no se atribuyen permisos de BD ni consulta protegida que no se implementaron. |
| Estados | Enum y guardas de tres estados; no existe una clase State por estado ni surtido operativo. |
| CQRS | Separación básica en una base; revalidar/convertir siguen usando servicio directamente. |
| Despliegue | CI/CD inicialmente verificado en pia-render; la configuración final sigue main. El registro de cierre identifica las verificaciones efectivas. |

La [arquitectura](README.md), los [diagramas](DIAGRAMAS.md), la [aplicación de SOLID](PATRONES_SOLID.md) y la [matriz arquitectural](trazabilidad_arquitectura.csv) usan estas decisiones.
