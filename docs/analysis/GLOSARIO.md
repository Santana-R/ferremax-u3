# Glosario de dominio - FerreMax PIA

Integración del 6 de noviembre de 2026. Se conserva el vocabulario de U2 y se precisa su relación con el código. Un término del negocio puede estar diseñado sin tener una clase o endpoint implementado.

## Términos conservados de U2

| Término | Significado compartido | Relación y estado actual |
| --- | --- | --- |
| SKU | Identificador de un producto de FerreMax | `SKU`; consulta HTTP por código. El inventario consultable no es un catálogo maestro independiente. |
| Producto | Herramienta o material que se cotiza, vende, transfiere o devuelve | Las partidas usan SKU; no hay mantenimiento de un catálogo completo. |
| Categoría | Agrupación comercial que puede determinar una política | Diseñada, por ejemplo para devoluciones. |
| Ubicación | Una de las tres sucursales o el almacén central donde se controla inventario | `ubicacion_id`. Los registros de un SKU pueden existir en algunas ubicaciones; no se generan existencias ficticias en las demás. |
| Existencia física | Cantidad contabilizada físicamente en una ubicación | `InventarioUbicacion.existencia_fisica`. |
| Cantidad comprometida | Suma de reservas activas de pedidos confirmados sobre un inventario | `InventarioUbicacion.comprometida`; la base guarda también una columna consistente con sus reservas. |
| Inventario disponible | Cantidad vendible: física menos comprometida, sobre movimientos confirmados | `InventarioUbicacion.disponible`. No suma tránsito ni permite sobrecomprometer. |
| Inventario en tránsito | Cantidad despachada por transferencia que todavía no se recibe | `en_transito` se informa; el flujo de despacho/recepción sigue pendiente. |
| Stock mínimo | Nivel configurado que genera alerta de reabastecimiento | Diseñado; no existe el panel de alertas. |
| Cotización | Propuesta con cliente, folio, versión, vigencia, partidas y condiciones | `Cotizacion`. No crea reserva. Emisión inicial operativa pendiente; revalidación/conversión implementadas. |
| Vigencia | Intervalo durante el cual puede aceptarse una versión sin revalidarla | `Vigencia`: emisión <= instante < vencimiento. En el vencimiento exacto ya no está vigente. Fechas con zona horaria. |
| Revalidación | Nueva revisión de precio, disponibilidad y condiciones de una versión vencida | `CotizacionService.revalidar`: crea otra versión sin cambiar la anterior. El vendedor suministra precios/condiciones y se consulta S1. |
| Pedido | Compromiso de compra; en el núcleo deriva de una versión de cotización aceptada | `Pedido`, con identidad, partidas, origen y estado. La venta directa del análisis no tiene un caso de uso independiente. |
| Partida | Renglón numerado que identifica producto, cantidad y precio cuando corresponde | `Partida`: cantidad positiva y finita; números distintos y moneda homogénea en un documento. |
| Reserva de inventario | Cantidad comprometida para un pedido confirmado | `InventarioUbicacion.reservas`, por pedido. Se guarda junto con la confirmación; no por crear una cotización ni un Pendiente. |
| Surtido | Preparación y verificación física de partidas reservadas | Diseñado; `Pedido.surtido` solo funciona como guarda de cancelación en el núcleo. |
| Surtido parcial | Surtido de menos cantidad de la solicitada con aceptación explícita | Diseñado; requiere cantidades surtibles/pendientes por partida y consentimiento diferente de la aceptación de cotización. |
| Transferencia | Movimiento trazable entre dos ubicaciones | Diseñada; no se acredita por mostrar el campo de tránsito. |
| Cliente empresarial | Organización registrada que puede tener cuenta de crédito | Diseñado como actor del negocio; no existe registro empresarial operativo completo. |
| Cuenta de crédito | Límite, saldo, bloqueo y condiciones de un cliente empresarial | `CuentaCredito` evalúa condiciones básicas; no tiene repositorio ni API integral. |
| Crédito disponible | Importe que puede utilizarse sin exceder límite y sujeto a bloqueo/condiciones | La evaluación usa límite menos saldo y moneda compatible. Crédito no equivale a inventario disponible. |
| Excepción de crédito | Decisión motivada de Caja/Crédito fuera de autorización normal | Diseñada; no existe un monto máximo acordado en el caso. |
| Entrega a domicilio | Traslado de un pedido surtido a dirección validada mediante unidad y operador | Diseñada; no se implementa optimización de rutas. |
| Evidencia de entrega | Receptor, fecha/hora y soporte del resultado de una entrega | Diseñada; una incidencia no equivale a entrega completada. |
| Devolución | Solicitud de retorno evaluada contra comprobante, categoría, condición y política | Diseñada; faltan valores de la política y flujo ejecutable. |
| Bitácora de auditoría | Historial de cambios con actor, fecha/hora, acción, antes/después y motivo | Registro transaccional implementado; consulta protegida e inalterabilidad por permisos operativos pendientes. |
| Lenguaje ubicuo | Significado consistente entre BRD, historias, BPMN, dominio, API y pruebas | Este glosario y los identificadores compartidos evitan usar términos distintos para la misma regla. |

## Precisiones incorporadas al integrar el PIA

| Término | Significado | Código o evidencia |
| --- | --- | --- |
| Versión de cotización | Revisión identificada por el mismo ID/folio y un número de versión | `Cotizacion.version`; tabla `cotizacion_version`. El pedido conserva su versión de origen. |
| Pendiente | Pedido creado que aún no pudo confirmarse | `EstadoPedido.PENDIENTE`; puede existir con disponible en 0, pero no reserva. |
| Confirmado | Pedido cuyo cambio de estado y reserva se confirmaron tras validar autorización y existencias | `EstadoPedido.CONFIRMADO`; el Unit of Work hace persistentes los efectos juntos. |
| Cancelado | Pedido confirmado cuya cancelación válida liberó su reserva propia | `EstadoPedido.CANCELADO`; terminal para las operaciones actuales. |
| Autorización de pago simulada | Referencia y booleano que representan una decisión externa de pago para el ejercicio | `AutorizacionPago`; no procesa dinero, ni acredita pasarela real. |
| Reserva propia | Reserva vinculada al ID del pedido que se opera | Cancelar libera esa reserva, sin liberar las de otros pedidos. |
| Transacción / Unit of Work | Unidad que confirma o revierte conjuntamente los cambios de negocio | `PostgresUnitOfWork`: pedido, inventario, reservas, auditoría y outbox en una transacción. |
| Rollback | Reversión de una operación que no pudo confirmarse | Si falla stock, el pedido persistido sigue Pendiente; no es una transición comercial nueva Confirmado → Pendiente. |
| Evento de dominio | Hecho del negocio registrado después de una operación válida | `CotizacionRevalidada`, `PedidoCreado`, `PedidoConfirmado`, `PedidoCancelado`. |
| Outbox | Registro técnico de eventos guardado junto al cambio de negocio | Tabla `outbox`; sin publicador/consumidor externo implementado. No equivale a una notificación enviada. |
| Specification | Condición de negocio evaluable y combinable sin efectos secundarios | Vigencia AND aceptación en conversión. OR/NOT son operadores probados, no reglas comerciales adicionales. |
| Actor de demo | Identificador y rol ficticios que el endpoint proporciona al servicio | `Actor.exigir` prueba guardas internas; no es una sesión autenticada. |
| Criterio de aceptación | Condición Given/When/Then que define comportamiento esperado | Archivo `aceptacion.feature`; es contrato del análisis. No acredita ejecución BDD sin un runner y resultados reales. |

## Correspondencias y distinciones de uso

- Una **cotización** conserva condiciones; un **pedido Pendiente** conserva la intención aceptada; una **reserva** aparece al confirmar transaccionalmente.
- **Disponible**, **físico**, **comprometido** y **tránsito** son cantidades distintas. Con físico 10 y comprometido 7, disponible es 3 aunque exista mercancía en tránsito.
- **Aceptar cotización**, **autorizar pago**, **autorizar crédito** y **aceptar un parcial** son decisiones distintas; ninguna sustituye automáticamente a otra.
- **Cancelación** libera todo lo reservado por ese pedido; **reducción** libera una diferencia. Solo la primera está implementada.
- **Evento**, **auditoría** y **log técnico** tienen propósitos distintos; registrar outbox no prueba envío externo ni una interfaz de auditoría.

Fuentes: [glosario U2](<../../reference/EQ17FerreMax_Glosario(1).pdf>), [BRD integrado](../BRD.md), [historias](USER_STORIES.md), `src/ferremax/domain/model.py`, servicios y pruebas del núcleo. El original U2 permanece intacto.
