# API de conversión de cotización en pedido

## Regla y recorrido

`POST /cotizaciones/{cotizacion_id}/versiones/{version}/convertir` expone
`CotizacionService.convertir()`: US05, AC-US05-01 y BR01/BR03/BR05.
El vendedor selecciona una versión vigente y registra su aceptación por el
cliente. La Specification combina vigencia y aceptación; el dominio crea
un pedido Pendiente ligado al identificador, folio y versión de la cotización.

Las partidas, cantidades y precios provienen de esa versión guardada. El cuerpo
solo acepta un booleano explícito; precios, totales y partidas enviados por el
cliente se rechazan. El total se calcula en `Pedido.total` y el servicio lo
incluye en el resultado y la auditoría/evento dentro de la misma transacción,
sin realizar una lectura adicional después del commit.

La conversión vuelve a consultar disponibilidad en S1, sin modificar inventario
ni crear reservas. Un disponible de cero permite crear un pedido Pendiente:
la reserva corresponde a la confirmación posterior. Un producto sin registro
de inventario en S1 provoca rechazo, como en el servicio U3 existente.

## Preparación local

Usar la versión 2 que ya se creó en la práctica de revalidación. Detener la API
anterior con Ctrl+C, cambiar a esta rama y volver a arrancar:

```bash
.venv/bin/python -m uvicorn ferremax.api.main:app --app-dir src --env-file .env --host 127.0.0.1 --port 8000
```

Si se parte de una base nueva, seguir primero la
[carga ficticia y revalidación](REVALIDACION.md) para obtener la versión 2
vigente. No se modifican las entregas originales ni se reinicia el historial.

La API mantiene el actor Vendedor simulado del servidor para el prototipo local;
esto no implementa autenticación de usuarios.

## Prueba en Swagger

En [Swagger local](http://127.0.0.1:8000/docs), seleccionar el POST que termina
en `/convertir` y pulsar **Try it out**. Introducir:

- `cotizacion_id`: `11111111-1111-4111-8111-111111111111`.
- `version`: `2`.

Primero se puede comprobar el rechazo con `{"aceptada": false}`: HTTP 409,
sin crear pedido. Para la conversión válida enviar:

```json
{
  "aceptada": true
}
```

Ejemplo de respuesta 201 con los datos de la práctica anterior:

```json
{
  "mensaje": "Pedido creado y pendiente de confirmación.",
  "pedido_id": "22222222-2222-4222-8222-222222222222",
  "estado": "Pendiente",
  "cotizacion_id": "11111111-1111-4111-8111-111111111111",
  "cotizacion_folio": "COT-API-DEMO",
  "cotizacion_version": 2,
  "total": "240.00",
  "moneda": "MXN",
  "disponibilidad_consultada": [
    {"sku": "FER-API-DEMO", "solicitada": "2", "disponible": "10"}
  ]
}
```

El `pedido_id` real será generado por el dominio. Conservarlo para las siguientes
operaciones del pedido. El disponible depende del inventario al consultar; no
representa una promesa ni una reserva. Después de convertir, el GET de inventario
debe conservar las mismas cantidades de antes.

Cada solicitud válida crea un pedido nuevo, como en el servicio existente.
Este endpoint no implementa idempotencia: repetir el POST puede crear otro
pedido Pendiente. Para inspeccionar el pedido creado se usará su identificador;
la consulta de pedidos se incorporará en otro bloque.

## Respuestas y verificación

| Situación | HTTP | Resultado |
| --- | --- | --- |
| Versión vigente y aceptación verdadera | 201 | Pedido Pendiente, partidas/precios copiados y disponibilidad consultada. |
| Cotización o versión inexistente | 404 | Mensaje de cotización o versión no encontrada. |
| Versión no vigente, incluso exactamente al vencer, o falta de aceptación | 409 | Rechazo con su motivo; no crea pedido ni evento de éxito. |
| Aceptación ausente/no booleana, ruta inválida, campos extra o producto sin inventario en S1 | 422 | Mensaje para corregir la solicitud. |
| PostgreSQL no disponible | 503 | Creación del pedido temporalmente no disponible, sin detalles internos. |

`tests/test_api_conversion.py` verifica HTTP con el servicio real y Memory:
versión/precio correctos, total del dominio, límites temporales, aceptación,
rechazos, agrupación de cantidades y conservación del inventario.

`tests/test_api_conversion_postgres.py` comprueba persistencia mediante otra
conexión, auditoría/evento de creación, rechazos sin pedidos parciales y un
pedido Pendiente sin stock ni reserva. Requiere `TEST_DATABASE_URL` hacia una
base de pruebas separada; sin conexión se omite visiblemente.

El [OpenAPI versionado](openapi.json) documenta las tres operaciones actuales.
Los resultados de las nuevas pruebas corresponden a esta versión del código;
las evidencias históricas de E9 conservan su propio commit medido.
