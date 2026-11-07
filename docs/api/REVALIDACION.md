# API de revalidación de cotizaciones

## Regla y alcance

`POST /cotizaciones/{cotizacion_id}/versiones/{version}/revalidar` expone el
servicio `CotizacionService.revalidar()` existente: BR02/BR03, US04/US05.
Se crea la versión siguiente de una cotización vencida, conservando el mismo
identificador y folio. La versión anterior queda intacta. Se actualizan precios,
partidas, vigencia y condiciones; se registra el motivo, auditoría y evento.

La operación consulta los productos en S1 como el prototipo U3. No crea pedidos
ni reservas y no promete disponibilidad futura. La emisión está incluida y el
vencimiento excluido: en el instante exacto del vencimiento ya puede revalidarse.

La respuesta 201 confirma que se creó la nueva versión. Repetir la operación
sobre la misma versión original produce 409 cuando la versión siguiente ya
existe. Intentar revalidar una versión todavía vigente también produce 409.
Los rechazos conservan los datos y no agregan eventos de éxito.

La API usa un Vendedor simulado del lado del servidor, como el bloque anterior;
esto no acredita autenticación de usuarios. La ejecución continúa siendo local,
con Python para la API y PostgreSQL en Docker.

## Datos ficticios y arranque

Detener el servidor anterior con Ctrl+C, cargar la cotización de ejemplo y
arrancar la API desde la raíz del proyecto:

```bash
.venv/bin/python scripts/cargar_cotizacion_demo.py
.venv/bin/python -m uvicorn ferremax.api.main:app --app-dir src --env-file .env --host 127.0.0.1 --port 8000
```

El script reutiliza el producto `FER-API-DEMO` y crea la versión 1 vencida de
`COT-API-DEMO`, con identificador `11111111-1111-4111-8111-111111111111`.
Tiene dos unidades a 100.00 MXN. La carga es manual e idempotente; no reescribe
el historial ni reinicia el ejemplo si ya se revalidó anteriormente.

## Prueba en Swagger

En [Swagger local](http://127.0.0.1:8000/docs), expandir el POST y seleccionar
**Try it out**. Introducir el identificador de ejemplo y `version = 1`.
Usar este cuerpo:

```json
{
  "dias_vigencia": 7,
  "partidas": [
    {
      "numero": 1,
      "sku": "FER-API-DEMO",
      "cantidad": "2",
      "precio_unitario": "120.00",
      "moneda": "MXN"
    }
  ],
  "condiciones": "Precios y condiciones revalidados con el cliente",
  "motivo": "Cliente solicita revalidar la cotizacion vencida"
}
```

La primera revalidación válida del ejemplo devuelve 201:

```json
{
  "mensaje": "Se creó una nueva versión de la cotización y se conservó la anterior.",
  "cotizacion_id": "11111111-1111-4111-8111-111111111111",
  "version_anterior": 1,
  "folio": "COT-API-DEMO",
  "version": 2,
  "estado": "Vigente"
}
```

Para comprobar el historial desde Docker Desktop → db-1 → Exec:

```bash
psql -U ferremax -d ferremax -c "SELECT version, datos->'partidas'->0->'precio'->>'importe' AS precio_unitario FROM ferremax_u3.cotizacion_version WHERE id='11111111-1111-4111-8111-111111111111' ORDER BY version;"
```

La versión 1 conserva 100.00 y la 2 tiene 120.00. Repetir el POST sobre versión 1
debe producir 409 sin agregar otra versión ni evento.

## Respuestas y validación

| Situación | HTTP | Resultado |
| --- | --- | --- |
| Cotización vencida y datos válidos | 201 | Nueva versión; conserva la anterior. |
| Identificador o versión inexistentes | 404 | Cotización o versión no encontrada. |
| Cotización vigente, aún no emitida o siguiente versión ya existente | 409 | Mensaje que explica el impedimento. |
| Datos inválidos, productos ausentes, renglones repetidos o monedas diferentes | 422 | Mensaje para corregir la solicitud; no modifica datos. |
| PostgreSQL no disponible o conexión sin configurar | 503 | Revalidación temporalmente no disponible, sin detalles internos. |

La entrada requiere días enteros positivos, al menos una partida, números de
renglón positivos y diferentes, SKU no vacío, cantidades positivas, precios
finitos no negativos, condiciones y motivo. Las partidas deben compartir moneda.
Los campos desconocidos se rechazan para evitar errores silenciosos al escribir
la solicitud. Siete días es el valor de ejemplo, no un límite comercial nuevo.

## Verificación automatizada

`tests/test_api_revalidacion.py` usa el servicio real con Memory, un reloj fijo
y datos nuevos por caso: éxito, límite temporal, conflictos, campos inválidos,
historial y ausencia de efectos en pedidos e inventario.

`tests/test_api_revalidacion_postgres.py` prueba persistencia mediante HTTP,
auditoría/eventos, rechazos, concurrencia y conservación del historial al repetir
la carga ficticia. Requiere `TEST_DATABASE_URL` hacia una base de pruebas
separada y el esquema del proyecto. Sin conexión, se omite visiblemente.

El [OpenAPI versionado](openapi.json) contiene el contrato de las seis operaciones actuales
y los ejemplos. Las entregas originales de E9 conservan su commit medido;
las nuevas pruebas verifican la versión actual de la API.
