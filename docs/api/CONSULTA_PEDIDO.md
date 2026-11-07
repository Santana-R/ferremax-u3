# API de consulta del pedido

## Qué consulta

`GET /pedidos/{pedido_id}` reutiliza `ConsultarPedidoHandler`, el puerto
`PedidoReader` y `PostgresReader.consultar_pedido()`. Devuelve el estado actual,
el folio y versión de la cotización de origen, el total calculado con las
partidas guardadas del pedido y su moneda.

El lector usa una transacción de solo lectura en PostgreSQL. Consultar no cambia
el estado, no reserva ni libera inventario y no agrega auditoría ni eventos de
negocio. Un pedido Cancelado permanece disponible para consulta. Una versión
posterior de la cotización no cambia el origen ni el total del pedido existente.

El actor Vendedor está simulado del lado del servidor; el prototipo no autentica
usuarios ni implementa permisos por cliente. Esta consulta devuelve un resumen;
no es una consulta de todas las partidas, pagos o entradas de auditoría.

## Prueba en Swagger

Con PostgreSQL encendido y la versión de entrega actual seleccionada, detener la API anterior con Ctrl+C y reiniciar desde la raíz del repo:

```bash
.venv/bin/python -m uvicorn ferremax.api.main:app --app-dir src --env-file .env --host 127.0.0.1 --port 8000
```

Actualizar [Swagger local](http://127.0.0.1:8000/docs), expandir el GET de pedidos,
pulsar **Try it out** y escribir el identificador del pedido utilizado en la
práctica anterior. No se envía cuerpo ni se usa el identificador de la cotización.

Ejemplo de respuesta 200 después de cancelar; el identificador real corresponde
al pedido creado en la conversión:

```json
{
  "mensaje": "Pedido consultado.",
  "pedido_id": "22222222-2222-4222-8222-222222222222",
  "estado": "Cancelado",
  "cotizacion_folio": "COT-API-DEMO",
  "cotizacion_version": 2,
  "total": "240.00",
  "moneda": "MXN"
}
```

El total no representa un cobro ni un reembolso: es el valor de las partidas
conservadas del pedido. Repetir la consulta mantiene el estado Cancelado y el
inventario. Para probar un identificador válido inexistente se puede utilizar
un UUID nuevo; debe devolver 404 sin crear registros.

## Respuestas

| Situación | HTTP | Resultado |
| --- | --- | --- |
| Pedido existente, en cualquiera de los tres estados | 200 | Resumen con estado, origen, total y moneda. |
| Identificador válido pero inexistente | 404 | `Pedido no encontrado.` |
| Identificador inválido | 422 | `Indica un identificador válido de pedido.` |
| PostgreSQL o configuración no disponibles | 503 | Consulta temporalmente no disponible; sin detalles internos. |

## Verificación automatizada

`tests/test_api_consulta_pedido.py` comprueba los tres estados preparados con
operaciones del servicio, repetición sin cambios, pedido inexistente, UUID
inválido y mensajes de error. También verifica que el total proviene del pedido
guardado, no del precio actual de la cotización.

`tests/test_api_consulta_pedido_postgres.py` comprueba esos estados persistidos,
la consulta después de crear una versión posterior de la cotización y la
ausencia de cambios en las seis tablas antes y después de consultar. Requiere
`TEST_DATABASE_URL` y el esquema en una base de pruebas separada; las omisiones
no acreditan persistencia real.

El [OpenAPI versionado](openapi.json) contiene las seis operaciones del recorrido
principal. Esto completa ese bloque de la API. La [guía de Docker](../DOCKER.md)
describe App y Tests en Compose y la validación realizada en Docker Desktop;
[CI/CD](../CI.md) y el [despliegue](../RENDER.md) ya tienen evidencia. El reporte final, presentación e integración a main conservan su estado en la [matriz de cumplimiento](../pia/MATRIZ_CUMPLIMIENTO.md).
