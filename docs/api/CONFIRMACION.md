# API de confirmación de pedidos y reserva

## Regla y recorrido

`POST /pedidos/{pedido_id}/confirmar` expone el comando `ConfirmarPedido`, su
handler CQRS y `PedidoService.confirmar()` existentes. Corresponde a US06/US09,
BR04/BR05 y la transición `Pendiente → Confirmado` de la máquina de estados.

El servidor toma cantidades y precios del pedido guardado; el cuerpo solo
indica la referencia de pago, la autorización y la ubicación. El servicio
verifica el rol Caja, obtiene el pedido y bloquea los inventarios en orden.
Valida el estado y pago, reserva las cantidades y guarda pedido, referencia,
auditoría y `PedidoConfirmado` en una transacción.

Si falta disponibilidad, se revierten también el estado, la referencia y las
reservas parciales: el pedido almacenado permanece Pendiente. Una confirmación
repetida se rechaza y conserva la reserva y referencia del primer éxito.

El actor Caja y la autorización de pago son simulados en este prototipo local.
El booleano no representa una conexión a una pasarela ni un cobro real; no se
afirma que el rollback de PostgreSQL pueda deshacer un pago externo. Este bloque
reutiliza las reglas existentes y no agrega autenticación de usuarios.

## Preparación y prueba en Swagger

Usar el `pedido_id` generado por la conversión de la versión 2, no el identificador
de la cotización. Detener el servidor anterior con Ctrl+C, actualizar la rama y
arrancar desde la raíz del proyecto, con PostgreSQL encendido:

```bash
.venv/bin/python -m uvicorn ferremax.api.main:app --app-dir src --env-file .env --host 127.0.0.1 --port 8000
```

En [Swagger local](http://127.0.0.1:8000/docs), expandir el POST que termina
en `/confirmar`, pulsar **Try it out** e introducir el identificador del pedido.

Antes del primer éxito se puede enviar `pago_autorizado: false`: devuelve 409,
conservando el pedido Pendiente y el inventario. Para confirmar, usar:

```json
{
  "referencia_pago": "PAGO-DEMO-001",
  "pago_autorizado": true,
  "ubicacion_id": "S1"
}
```

Ejemplo de respuesta 200; el identificador real es el de la conversión anterior:

```json
{
  "mensaje": "Pedido confirmado e inventario reservado.",
  "pedido_id": "22222222-2222-4222-8222-222222222222",
  "estado": "Confirmado",
  "referencia_pago": "PAGO-DEMO-001",
  "ubicacion_id": "S1"
}
```

El 200 corresponde a la actualización de un pedido existente. Con el ejemplo
de dos unidades y sin otras reservas, el GET de `FER-API-DEMO` en S1 debe mostrar
10 físicas, dos comprometidas, cinco en tránsito y ocho disponibles. La existencia
física y el tránsito se conservan; reservar aumenta lo comprometido.

Repetir el POST sobre el pedido confirmado debe devolver 409 sin duplicar la
reserva ni el evento. Si se intenta enviar un pago rechazado después de confirmar,
la operación se rechaza por el estado del pedido: ese intento no revierte la
confirmación anterior.

## Respuestas

| Situación | HTTP | Resultado |
| --- | --- | --- |
| Pendiente, pago autorizado y stock suficiente | 200 | Confirmado, reserva propia, auditoría y evento. |
| Pedido inexistente | 404 | `Pedido no encontrado.` |
| Pago no autorizado | 409 | Mensaje de pago rechazado; conserva el pedido Pendiente. |
| Disponibilidad insuficiente | 409 | Conserva el pedido Pendiente, sin reservas parciales. |
| Pedido ya confirmado o cancelado | 409 | Rechaza el cambio de estado. |
| Referencia vacía, autorización no booleana, ubicación vacía o campos extra | 422 | Mensaje para corregir la solicitud. |
| Producto sin registro en la ubicación | 422 | Indica el problema de ubicación/inventario. |
| PostgreSQL no disponible | 503 | Confirmación temporalmente no disponible; no expone detalles internos. |

## Verificación automatizada

`tests/test_api_confirmacion.py` usa el servicio real y Memory. Comprueba éxito,
reserva propia conservando reservas ajenas, límite de disponibilidad, falta de
stock, pago rechazado, confirmación repetida, pedido cancelado, errores de entrada
y reversión cuando falla la reserva de un segundo producto.

`tests/test_api_confirmacion_postgres.py` verifica persistencia, auditoría/evento,
reversión total, confirmación repetida y dos pedidos que compiten por la última
unidad: uno confirma y el otro queda Pendiente. Requiere `TEST_DATABASE_URL` y
el esquema del proyecto en una base de pruebas separada; sin conexión se omite
visiblemente. La verificación de este bloque se realizó en una base temporal
separada de la demostración.

El [OpenAPI versionado](openapi.json) documenta las operaciones actuales.
La [cancelación](CANCELACION.md) permite liberar la reserva antes del surtido.
La consulta del pedido se incorporará en su siguiente bloque.
