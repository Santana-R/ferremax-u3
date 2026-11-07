# Cierre del PIA FerreMax

Equipo 17: Roberto Santana Trujillo e Isaías Leonardo Salazar Torres. Fecha de entrega: 6 de noviembre de 2026.

## Versión e integración

La referencia histórica `u3-entrega` conserva el commit `eb71b6625c957b9dbfe7e4ed54f7c9f8ad08f365`. La rama final es `main`, integrada mediante el [PR #1](https://github.com/Santana-R/ferremax-u3/pull/1), commit `000616af6331b2af46665a9215b856ca85121551`. `pia-entrega` conserva la preparación. Blueprint y servicio Render siguen `main`. El [registro de verificación](../../evidencias/pia/cierre_main_verificacion.json) identifica el despliegue y las consultas comprobadas; las actualizaciones posteriores exclusivamente documentales conservan ese código funcional.

| Elemento | Estado comprobado al cerrar la integración |
| --- | --- |
| U3 conservada y documentos históricos | Verificados sin cambios. |
| Swagger y contrato del núcleo | Base funcional `c4876ef`; seis operaciones; vista sencilla y detalles técnicos opcionales. |
| CI de main integrado | 249 aprobadas, 0 omitidas, 97.38%; [ejecución 42328579928](https://github.com/Santana-R/ferremax-u3/actions/runs/42328579928). El informe conserva también la evidencia previa identificada por su commit. |
| Arquitectura y trazabilidad PIA | Modelo, cinco diagramas, siete ADR, patrones/SOLID y matriz arquitectural. |
| Documentos de entrega | [Informe PDF](../../reporte/PIA_FerreMax_Informe.pdf), [Word](../../reporte/PIA_FerreMax_Informe.docx), [presentación](../../reporte/PIA_FerreMax_Presentacion.pptx) y [PDF de apoyo](../../reporte/PIA_FerreMax_Presentacion.pdf). |
| Integración y Render | PR #1 fusionado; deploy `dep-dbn8lgi7k9oc739a6va0` live desde main; mismos IDs de servicio y base. |
| Consulta pública posterior | Swagger/OpenAPI/inventario/pedido HTTP 200; seis operaciones; contrato igual al versionado; datos iguales antes/después. |

## Acceso para la revisión

- [Repositorio](https://github.com/Santana-R/ferremax-u3).
- [Swagger público](https://ferremax-api-w5kd.onrender.com/docs).
- [OpenAPI](https://ferremax-api-w5kd.onrender.com/openapi.json).
- [Informe y presentación](../../reporte/README.md).

En GitHub Desktop: **Fetch origin → Current Branch → main → Pull origin**. No arrastrar ni descartar cambios locales que no se hayan revisado. Las ramas de desarrollo se conservan; no es necesario fusionar cada rama antigua ni borrarlas para entregar. La etiqueta histórica permite consultar U3 después de actualizar main.

## Límites y pendientes reales

La [matriz](MATRIZ_CUMPLIMIENTO.md) conserva R16 Parcial. La aplicación demuestra el núcleo contado: disponibilidad, cotización versionada, creación de pedido, confirmación con reserva y cancelación con liberación. Actores y pago son simulados. Crédito integral, emisión inicial operativa, reducción, transferencias, multiorigen, parciales, surtido, entrega, devolución y panel no cuentan con todos sus flujos implementados. Documentarlos no equivale a completarlos ni a una aceptación del profesor.

La revisión de los documentos por el equipo, su carga en NetAcad y la demostración/defensa del 9 al 20 de noviembre siguen siendo actividades del equipo. No se afirma una entrega en la plataforma ni una calificación.
