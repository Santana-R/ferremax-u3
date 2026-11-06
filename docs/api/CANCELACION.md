# API de cancelación de pedidos y liberación de reserva

## Regla y recorrido

`POST /pedidos/{pedido_id}/cancelar` expone `CancelarPedido`, su handler CQRS y
`PedidoService.cancelar()` existentes. Corresponde a BR06, US10 y la transición
`Confirmado → Cancelado` de la máquina de estados. Reutiliza la regla de E9:
solo se permite cancelar antes del surtido y con un motivo.

El servidor busca la ubicación de la reserva guardada. El cliente envía solo el
motivo; no proporciona ubicación, cantidades ni estado. El servicio comprueba el
rol, bloquea el pedido y los inventarios, libera únicamente las reservas propias
y guarda estado, auditoría y evento `PedidoCancelado` en una transacción.
Las reservas de otros pedidos, la existencia física, las unidades en tránsito
y las versiones de la cotización se conservan.

Una cancelación repetida devuelve 409 sin liberar unidades adicionales ni
duplicar el evento. Si falla la liberación de un producto, la transacción revierte
también cualquier liberación anterior y conserva el pedido Confirmado.

El actor `VendedorAutorizadoCancelacion` está simulado del lado del servidor;
el prototipo no autentica usuarios. La guarda `surtido` ya existe en el dominio,
pero este bloque no implementa un proceso de surtido. Cancelar libera reservas;
no ejecuta un reembolso. La referencia del pago simulado se conserva como historial.

## Prueba guiada en Swagger

Usar el identificador del pedido ya confirmado en el paso anterior. Con
PostgreSQL encendido, detener la API con Ctrl+C, actualizar a la rama
`pia-api-cancelacion` desde GitHub Desktop y reiniciar desde la raíz del repo:

```bash
.venv/bin/python -m uvicorn ferremax.api.main:app --app-dir src --env-file .env --host 127.0.0.1 --port 8000
```

En [Swagger local](http://127.0.0.1:8000/docs), expandir el POST que termina en
`/cancelar`, pulsar **Try it out** e introducir el identificador del pedido.

```json
{
  "motivo": "El cliente solicita cancelar el pedido antes del surtido"
}
```

Respuesta 200, con el identificador real del pedido:

```json
{
  "mensaje": "Pedido cancelado y su inventario reservado liberado.",
  "pedido_id": "22222222-2222-4222-8222-222222222222",
  "estado": "Cancelado"
}
```

Consultar `GET /inventario/FER-API-DEMO`: si solo ese pedido reservó dos unidades
de las diez físicas de S1, la comprometida baja de 2 a 0 y la disponible sube de
8 a 10. Las cinco unidades en tránsito siguen sin sumarse al disponible.
Si existen reservas de otros pedidos, se conservan y el disponible será menor.

Repetir el POST debe responder 409 y conservar el inventario obtenido después
del primer éxito. El pedido permanece guardado como Cancelado para su historial.

## Respuestas

| Situación | HTTP | Resultado |
| --- | --- | --- |
| Confirmado, sin surtir y con motivo | 200 | Cancelado; libera su reserva, registra motivo, actor y evento. |
| Pedido inexistente | 404 | `Pedido no encontrado.` |
| Pedido Pendiente, ya Cancelado o surtido | 409 | Rechaza y conserva los datos. |
| Reserva ausente o inconsistente | 409 | Solicita revisión; revierte la operación. |
| Identificador inválido, motivo ausente/vacío o campos extra | 422 | Mensaje para corregir la solicitud. |
| PostgreSQL no disponible o fallo de persistencia | 503 | Mensaje de cancelación temporalmente no disponible, sin detalles internos. |

## Verificación automatizada

`tests/test_api_cancelacion.py` comprueba la liberación propia conservando
reservas ajenas, auditoría, evento, cancelación repetida, límite de disponible,
guardas de estado y surtido, validación de entrada y errores comprensibles.

`tests/test_api_cancelacion_postgres.py` verifica persistencia con otro pedido
reservado, rechazos sin cambios y dos cancelaciones concurrentes: una tiene éxito
y la otra se rechaza. Incluye una falla simulada al liberar el segundo producto
para comprobar el rollback real de las escrituras anteriores en PostgreSQL.

Estas pruebas de PostgreSQL requieren `TEST_DATABASE_URL` y el esquema en una
base de pruebas separada. Una omisión no acredita persistencia. La verificación
de este bloque usa una base temporal distinta de la demostración.

El [OpenAPI versionado](openapi.json) contiene las operaciones del recorrido.
La [consulta del pedido](CONSULTA_PEDIDO.md) permite comprobar su estado guardado.
