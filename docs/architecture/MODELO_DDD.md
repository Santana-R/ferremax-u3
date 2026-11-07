# Modelo DDD implementado - FerreMax PIA

Este modelo describe el código de `src/ferremax`, separado del mapa completo de negocio U2/U3. Los [diagramas PIA](DIAGRAMAS.md) y la [trazabilidad](trazabilidad_arquitectura.csv) muestran esas mismas responsabilidades.

## Entidades y límites de agregados del núcleo

| Elemento | Identidad y contenido | Comportamiento y límite |
| --- | --- | --- |
| `Cotizacion` | ID y versión, folio, cliente, vigencia, partidas y condiciones | `revalidar` devuelve una versión nueva; `convertir` comprueba vigencia/aceptación y crea Pedido. Cada versión se persiste con PK compuesta; no se sobreescribe la anterior. |
| `Pedido` | ID, cliente, referencia a ID/folio/versión de cotización, snapshot de partidas, estado, surtido y referencia de pago | `confirmar`, `cancelar`, cantidades por SKU y total derivado. Referencia la cotización por identidad, no la posee como objeto hijo. |
| `InventarioUbicacion` | SKU + ubicación, física, tránsito y diccionario de reservas por ID de pedido | Calcula comprometida/disponible, valida integridad, reserva y libera. La reserva es una entrada del diccionario y una fila SQL; no existe una clase Python `Reserva` que deba dibujarse. |

Cotización, pedido e inventario se tratan como límites distintos del núcleo. Confirmar/cancelar necesitan consistencia entre más de uno; el servicio abre una transacción local que los coordina. Esta decisión práctica del prototipo no los convierte en un único agregado ni en una garantía de consistencia distribuida.

La copia de partidas conserva las condiciones de la versión aceptada. Las listas del pedido y la cotización son distintas; sus miembros son Value Objects congelados. Los agregados siguen siendo dataclasses públicas con listas/diccionarios mutables: la disciplina de la aplicación usa métodos y repositorios, pero no hay encapsulación profunda que impida cualquier mutación Python directa.

## Value Objects y datos sin identidad operativa propia

| Clase | Datos | Invariante o uso real |
| --- | --- | --- |
| `SKU` | valor | Texto no vacío; identifica producto sin implementar un catálogo maestro completo. |
| `Dinero` | importe Decimal, moneda | Importe finito no negativo y moneda presente; las partidas de un documento requieren moneda homogénea. |
| `Vigencia` | emisión y vencimiento con zona horaria | Vencimiento posterior; vigente en emisión <= ahora < vencimiento. |
| `Partida` | número, SKU, cantidad, precio | Número/cantidad positivos, cantidad finita. Validación del conjunto impide números repetidos o mezcla de monedas. |
| `AutorizacionPago` | referencia y autorizada | Portador congelado de la decisión simulada. `Pedido.confirmar` exige autorización verdadera y referencia no vacía; el objeto no conecta a una pasarela. |
| `ContextoConversion` | cotización, ahora y aceptada | Contexto congelado que reciben las Specifications. No realiza IO ni crea pedidos. |

No se denomina inmutabilidad profunda a una dataclass `frozen=True` que contiene un diccionario u otro objeto mutable. Este límite aplica a `EventoDominio.datos` y a la cotización referenciada por `ContextoConversion`.

## Reglas, servicios y Specifications

`CotizacionVigente` y `AceptacionDelCliente` heredan de `Specification[ContextoConversion]`. `AndSpec`, `OrSpec` y `NotSpec` permiten composición. La regla comercial actual utiliza:

```python
COTIZACION_CONVERTIBLE = COTIZACION_VIGENTE & ACEPTACION_DEL_CLIENTE
```

La evaluación es pura. La cotización conserva el motivo del rechazo y crea el pedido solo después de cumplir la regla. OR/NOT están implementados y probados como operadores; no se les atribuyen condiciones comerciales adicionales.

`CotizacionService` y `PedidoService` son servicios de **aplicación**: verifican actor, abren UoW, coordinan repositorios, invocan el dominio y registran auditoría/eventos. El reloj y la fábrica de UoW se inyectan. Crear versiones, determinar vigencia y proteger transiciones/reserva son responsabilidades del dominio.

`PoliticaCredito` representa una política de dominio aislada; usa `CuentaCredito` para condición activa, bloqueo, límite/saldo y moneda. No existe todavía un flujo de crédito, un repositorio de cuenta o una autorización excepcional persistida. La clase no acredita el agregado operativo completo de crédito del diseño U3.

## Estados y eventos

La máquina usa `EstadoPedido` y guardas de métodos, sin una clase State por estado. Sus transiciones ejecutables son Pendiente → Confirmado → Cancelado. `surtido` es una guarda de cancelación, no una operación de surtido ni un cuarto estado implementado. Ver [tabla completa](STATE_MACHINE.md).

| Evento | Construcción y persistencia | Referencia |
| --- | --- | --- |
| `CotizacionRevalidada` | El servicio construye `EventoDominio` con snapshot de la nueva versión y lo registra junto a auditoría | US04; BR02/BR03/BR16 |
| `PedidoCreado` | Se guarda con el pedido Pendiente derivado de cotización | US05; BR01/BR16 |
| `PedidoConfirmado` | Se registra con estado, reserva y referencia tras las validaciones; todo se hace durable al commit | US06/US09; BR05/BR16 |
| `PedidoCancelado` | Se registra con la liberación propia y estado Cancelado en la misma transacción | US10; BR06/BR16 |

Los servicios construyen estos eventos; los agregados no mantienen una lista propia de eventos. Outbox conserva los registros, sin publicador externo. Un fallo antes del commit no deja un hecho durable de éxito. La auditoría conserva los valores previos/nuevos y el motivo, con actor de demo en HTTP.

## Relación entre clases, almacenamiento y API

| Concepto | Clase/contrato | Persistencia / entrada |
| --- | --- | --- |
| Versiones | `Cotizacion`, `CotizacionRepository` | `cotizacion_version`: clave id/version y snapshot JSONB |
| Pedido | `Pedido`, `PedidoRepository`, `PedidoReader` | `pedido`: FK a versión, estado y snapshot JSONB |
| Inventario y reservas | `InventarioUbicacion`, `InventarioRepository` | `inventario` y `reserva`, con claves compuestas y cantidades |
| Dinero/partidas/vigencia | Value Objects | Se serializan dentro de snapshots; no hay una tabla por cada clase |
| Auditoría/eventos | `UnitOfWork.registrar`, `EventoDominio` | `auditoria` y `outbox` dentro de la misma transacción |
| Actores | `Actor` en aplicación | Roles ficticios construidos por los endpoints; no hay tabla de usuarios |

Los modelos Pydantic de `api/schemas.py` validan el contrato externo; no son raíces de agregados. No se dibuja `Producto`, `Cliente`, `Transferencia`, `Entrega` o `Devolucion` como clase operativa de este código si todavía no existe.

## Verificación identificable

| Comportamiento | Prueba existente |
| --- | --- |
| Vigencia, aceptación y composición sin mutar | `tests/test_specifications.py` |
| Copia de versión/origen y ausencia de reserva al convertir | `tests/test_api_conversion_postgres.py` y `tests/test_api_revalidacion_postgres.py` |
| Seis combinaciones de estado/acción y guardas | `tests/test_state_machine.py` |
| Reserva, última unidad, segunda partida y rollback | `tests/test_api_confirmacion_postgres.py` |
| Liberación propia, repeticiones y fallo de segunda liberación | `tests/test_api_cancelacion_postgres.py` |
| Total del pedido separado de posteriores precios de cotización | `tests/test_api_consulta_pedido_postgres.py` |

Las pruebas respaldan el comportamiento del núcleo. Las necesidades diseñadas del [BRD](../BRD.md) y los criterios sin prueba integral de [US01-US20](../analysis/USER_STORIES.md) conservan su estado pendiente.
