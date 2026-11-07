# Contrato de API - FerreMax PIA

API 0.6.0 con seis operaciones. El [OpenAPI versionado](openapi.json) se contrastó con `create_app().openapi()` al actualizar la documentación técnica: coincide con el contrato generado por el código. Swagger utiliza el mismo OpenAPI en tiempo de ejecución.

**[Swagger público](https://ferremax-api-w5kd.onrender.com/docs)** · **[OpenAPI público](https://ferremax-api-w5kd.onrender.com/openapi.json)** · **[Swagger local](http://127.0.0.1:8000/docs)**

| Método y ruta | Caso y guía | Resultado válido |
| --- | --- | --- |
| `GET /inventario/{sku}` | [Disponibilidad](INVENTARIO.md), US01/US02 | 200: cantidades por ubicación registrada; sin escrituras. |
| `POST /cotizaciones/{cotizacion_id}/versiones/{version}/revalidar` | [Revalidación](REVALIDACION.md), US04 | 201: siguiente versión vigente; conserva la anterior. |
| `POST /cotizaciones/{cotizacion_id}/versiones/{version}/convertir` | [Conversión](CONVERSION.md), US05 | 201: pedido Pendiente con origen/total y sin reserva. |
| `POST /pedidos/{pedido_id}/confirmar` | [Confirmación](CONFIRMACION.md), US06/US09 | 200: Confirmado y reserva en la misma transacción. |
| `POST /pedidos/{pedido_id}/cancelar` | [Cancelación](CANCELACION.md), parte de US10 | 200: Cancelado y reserva propia liberada. |
| `GET /pedidos/{pedido_id}` | [Consulta](CONSULTA_PEDIDO.md) | 200: estado, folio/versión, total y moneda persistidos. |

## Presentación de Swagger

Swagger conserva sus operaciones y formularios. La vista sencilla presenta títulos de negocio y un mensaje comprensible por respuesta. **Mostrar detalles técnicos** recupera rutas, métodos y el JSON completo, incluido el ID del pedido necesario para continuar el recorrido. El contrato HTTP y los datos persistidos no cambian al alternar esta vista. `Server response` muestra una ejecución real; `Example Value` es un ejemplo de documentación.

## Entradas y errores

Los importes/cantidades usan representación decimal; las solicitudes rechazan tipos/campos inválidos y campos extra según su modelo Pydantic. El cliente no decide estado, total ni cantidades a reservar al confirmar: el servidor los recupera del pedido guardado. Cancelar recibe motivo, no unidades que el cliente pretenda liberar.

| HTTP | Uso en el contrato |
| --- | --- |
| 400 | SKU vacío después de recortar espacios, cuando la ruta sí contiene un valor. |
| 404 | Identificador válido inexistente o SKU no encontrado en inventario. |
| 409 | Vigencia, aceptación, estado, pago o disponibilidad impiden el comando; se conserva el estado previo durable. |
| 422 | Datos/UUID/versiones/campos inválidos o problemas de ubicación/partidas según la operación. |
| 503 | Conexión o persistencia temporalmente no disponible; mensaje sin detalles internos. |

El cuerpo comunica `mensaje` en español y, cuando corresponde, el identificador. Abrir `/docs` o `/openapi.json` no abre por sí mismo una conexión de datos; para comprobar PostgreSQL se ejecuta además una consulta de inventario o pedido.

## Datos de demostración y repetición del recorrido

La cotización ficticia base tiene ID `11111111-1111-4111-8111-111111111111`, versión 1 vencida. La semilla incluye inventario ficticio y conserva registros existentes. En una base nueva, la guía de revalidación crea versión 2. En una base que ya contiene esa versión, no debe repetirse la operación suponiendo que el historial esté vacío: primero se identifica la versión/estado real. La vigencia es temporal; una versión creada durante la práctica puede vencer después.

Cada conversión válida crea un pedido nuevo. El ID se toma de la respuesta, no se sustituye por el ID de la cotización ni por el UUID ilustrativo de las guías. Confirmación/cancelación repetidas se rechazan sin duplicar efectos; esto no vuelve idempotente a la conversión. El script HTTP de CI está preparado para una base ficticia nueva del runner y no se utiliza para repetir el demo sobre la base con historial.

La [evidencia pública registrada](../../evidencias/pia/render_cd_verificacion.json) conserva el pedido `4d7b5b3e-926e-4856-9a1e-d1a433ef5cfd`, Cancelado, origen versión 2 y total 240.00 MXN. Sus consultas permiten comprobar datos sin crear otro pedido. El [despliegue](../RENDER.md) distingue datos locales y públicos.

## Alcance y trazabilidad

Los actores Vendedor/Caja/Cancelación son fijos de demo y el pago es una referencia/booleano ficticios. No existe autenticación de personas, pasarela, reembolso, surtido operativo ni consulta de auditoría en estos endpoints. Las condiciones comerciales y pendientes siguen en el [BRD](../BRD.md).

Las pruebas HTTP con Memory y PostgreSQL identificadas en [trazabilidad de análisis](../analysis/trazabilidad_analisis.csv) y [arquitectura](../architecture/trazabilidad_arquitectura.csv) comprueban contrato, reglas y persistencia. El archivo Gherkin expresa criterios del análisis; no se presenta como suite BDD ejecutada.
