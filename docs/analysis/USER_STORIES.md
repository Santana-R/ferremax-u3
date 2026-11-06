# Historias de usuario y criterios de aceptación - FerreMax PIA

Versión integrada del 6 de noviembre de 2026. Equipo 17: Roberto Santana Trujillo e Isaías Leonardo Salazar Torres.

Se conservan **US01-US20** de U2. Los criterios siguientes precisan el comportamiento y mantienen los escenarios no implementados como requisitos. El [BRD](../BRD.md) define el alcance del negocio y sus límites de implementación; el [BPMN](BPMN.md) usa los mismos identificadores.

Los escenarios completos están también en [aceptacion.feature](aceptacion.feature). Ese archivo es un contrato Gherkin del análisis, no una suite ejecutada: los resultados reales provienen de las pruebas pytest enlazadas en [trazabilidad_analisis.csv](trazabilidad_analisis.csv).

| Estado | Significado |
| --- | --- |
| Implementada | Hay comportamiento y prueba identificable para el criterio señalado. |
| Simulada | El flujo se verifica con una entrada o actor ficticio; falta la integración real. |
| Parcial | Solo una parte de la historia o criterio tiene soporte. |
| Diseñada | Requisito conservado sin flujo ejecutable completo. |

## Correspondencia de identificadores históricos

| Identificador U2 | Identificador PIA | Motivo |
| --- | --- | --- |
| AC-US01-01, consulta global | AC-US01-01 | Se mantiene. |
| AC-US01-01, SKU inexistente (segundo uso) | AC-US01-02 | Se elimina duplicidad usando el título para desambiguar. |
| AC-US10-01, cancelar o reducir | AC-US10-01 cancelación; AC-US10-02 reducción | Se separan dos operaciones con distinto estado de implementación. |
| CA-US18-01 / CA-US19-01 / CA-US20-01 | AC-US18-01 / AC-US19-01 / AC-US20-01 | Se normaliza el prefijo, conservando contenido y relación. |
| Sin ID en U2 | Nuevos AC descritos como refinamiento PIA | Explicitan límites, concurrencia y ausencia de efectos parciales. |

## US01 - Consultar la disponibilidad global de un producto por sku

Como vendedor, quiero consultar la disponibilidad global de un producto por SKU, para ofrecer una cantidad que realmente pueda surtirse.

**Necesidades:** BN01. **Reglas:** BR04. **Estado de la historia:** Implementada.

**BPMN:** `P01_T01`. **Componente:** [src/ferremax/api/main.py](../../src/ferremax/api/main.py); [src/ferremax/application/cqrs.py](../../src/ferremax/application/cqrs.py); [src/ferremax/infrastructure/postgres.py](../../src/ferremax/infrastructure/postgres.py).

**Límite:** Se devuelven las ubicaciones registradas para el SKU, sin inventar existencias ni sumar tránsito al disponible. La semilla pública tiene menos registros que las cuatro ubicaciones del negocio.

| Criterio | Dado | Cuando | Entonces | Estado |
| --- | --- | --- | --- | --- |
| AC-US01-01 - Consulta global | un SKU con inventario registrado por ubicación | el vendedor consulta su disponibilidad | se muestran existencia física, comprometida, en tránsito y disponible de cada ubicación registrada | Implementada |
| AC-US01-02 - SKU inexistente | un SKU que no tiene registros en el inventario consultable | el vendedor consulta su disponibilidad | se informa que no fue encontrado y no se inventan existencias | Implementada |

**Pruebas y límites de los criterios:**

- `AC-US01-01`: [tests/test_api_postgres.py](../../tests/test_api_postgres.py), método `test_consulta_http_lee_postgres_sin_modificar_inventario`.
- `AC-US01-02`: [tests/test_api_postgres.py](../../tests/test_api_postgres.py), método `test_consulta_http_producto_no_existente_en_postgres`. Se corrige el ID repetido sin cambiar el escenario. No hay catálogo maestro independiente del inventario en la API.

## US02 - Distinguir inventario físico, comprometido y disponible

Como vendedor, quiero distinguir inventario físico, comprometido y disponible, para no confundir mercancía presente con mercancía vendible.

**Necesidades:** BN01/BN02. **Reglas:** BR04. **Estado de la historia:** Implementada.

**BPMN:** `P01_T01`. **Componente:** [src/ferremax/domain/model.py](../../src/ferremax/domain/model.py); [src/ferremax/infrastructure/postgres.py](../../src/ferremax/infrastructure/postgres.py).

**Límite:** El tránsito se informa por separado; una consulta no reserva ni modifica datos.

| Criterio | Dado | Cuando | Entonces | Estado |
| --- | --- | --- | --- | --- |
| AC-US02-01 - Cálculo de disponible | un SKU con 10 unidades físicas y 7 comprometidas en una ubicación | se consulta esa ubicación | el disponible mostrado es 3 unidades | Implementada |
| AC-US02-02 - El tránsito no es vendible | un SKU con 0 unidades disponibles y 5 en tránsito | se consulta su disponibilidad | el disponible permanece en 0 y las 5 unidades se muestran como tránsito | Implementada |

**Pruebas y límites de los criterios:**

- `AC-US02-01`: [tests/test_e9_inventario.py](../../tests/test_e9_inventario.py), método `InventarioE9Test::test_e9_inv_01_exito_reservar_dos_deja_una_disponible`.
- `AC-US02-02`: [tests/test_api_inventario.py](../../tests/test_api_inventario.py), método `test_producto_sin_disponible_existe_y_transito_no_se_suma`.

## US03 - Crear una cotización con vigencia y condiciones comerciales

Como vendedor, quiero crear una cotización con vigencia y condiciones comerciales, para entregar una propuesta controlada al cliente.

**Necesidades:** BN03. **Reglas:** BR01/BR02. **Estado de la historia:** Parcial.

**BPMN:** `P01_T02`. **Componente:** [src/ferremax/domain/model.py](../../src/ferremax/domain/model.py); [scripts/cargar_cotizacion_demo.py](../../scripts/cargar_cotizacion_demo.py).

**Límite:** Hay entidad y carga de datos ficticios; falta un caso de uso y endpoint de emisión inicial por vendedor.

| Criterio | Dado | Cuando | Entonces | Estado |
| --- | --- | --- | --- | --- |
| AC-US03-01 - Emisión inicial | un cliente y partidas válidas con precios y condiciones | el vendedor emite una cotización | se asignan folio, versión, emisión, vencimiento, totales y estado vigente, se conserva la disponibilidad consultada y no se reserva inventario | Diseñada |

**Pruebas y límites de los criterios:**

- `AC-US03-01`: sin prueba integral identificada. La semilla de demostración no acredita una emisión operativa ni almacenamiento de una consulta de disponibilidad.

## US04 - Revalidar una cotización vencida

Como vendedor, quiero revalidar una cotización vencida, para no aplicar precios o existencias desactualizados.

**Necesidades:** BN03. **Reglas:** BR01/BR02/BR03. **Estado de la historia:** Implementada.

**BPMN:** `P01_G01/P01_T03`. **Componente:** [src/ferremax/domain/model.py](../../src/ferremax/domain/model.py); [src/ferremax/application/services.py](../../src/ferremax/application/services.py); [src/ferremax/api/cotizaciones.py](../../src/ferremax/api/cotizaciones.py).

**Límite:** Precios y condiciones los suministra el vendedor en la solicitud; no hay integración con un proveedor de precios. Se consulta S1, fijada en el servicio.

| Criterio | Dado | Cuando | Entonces | Estado |
| --- | --- | --- | --- | --- |
| AC-US04-01 - Conversión de versión vencida | una versión de cotización cuyo vencimiento ya pasó | el vendedor intenta convertirla en pedido | se rechaza la conversión con indicación de revalidación, sin crear pedido ni reserva | Implementada |
| AC-US04-02 - Nueva versión con historial | una cotización vencida y nuevos precios, condiciones y vigencia válidos | el vendedor solicita revalidarla | se guarda una nueva versión vigente conservando intacta la anterior y sin crear pedido ni reserva | Implementada |
| AC-US04-03 - Instante exacto del vencimiento | una cotización cuyo vencimiento es el instante actual | se intenta convertir esa versión | se rechaza por falta de vigencia sin alterar los datos | Implementada |
| AC-US04-04 - Revalidaciones simultáneas | dos solicitudes concurrentes de revalidación para la misma versión vencida | ambas intentan guardar la versión siguiente | solo se conserva una versión nueva y la otra solicitud recibe un rechazo sin duplicar efectos | Implementada |

**Pruebas y límites de los criterios:**

- `AC-US04-01`: [tests/test_api_conversion.py](../../tests/test_api_conversion.py), método `test_version_1_vencida_rechaza_antes_de_crear_pedido`.
- `AC-US04-02`: [tests/test_api_revalidacion_postgres.py](../../tests/test_api_revalidacion_postgres.py), método `test_http_persiste_dos_versiones_auditoria_y_evento_sin_pedido_ni_reserva`.
- `AC-US04-03`: [tests/test_api_conversion.py](../../tests/test_api_conversion.py), método `test_fuera_de_vigencia_rechaza_sin_cambios`.
- `AC-US04-04`: [tests/test_api_revalidacion_postgres.py](../../tests/test_api_revalidacion_postgres.py), método `test_dos_revalidaciones_concurrentes_crean_una_sola_version`.

## US05 - Convertir una cotización aceptada en pedido

Como vendedor, quiero convertir una cotización aceptada en pedido, para evitar recapturar información y mantener trazabilidad.

**Necesidades:** BN03. **Reglas:** BR01/BR02/BR03. **Estado de la historia:** Implementada.

**BPMN:** `P01_T04/P01_G02/P01_T05`. **Componente:** [src/ferremax/domain/model.py](../../src/ferremax/domain/model.py); [src/ferremax/application/services.py](../../src/ferremax/application/services.py); [src/ferremax/api/cotizaciones.py](../../src/ferremax/api/cotizaciones.py).

**Límite:** La conversión crea Pendiente y consulta disponibilidad de S1; una disponibilidad insuficiente no impide crear el pedido pendiente, pero sí su confirmación.

| Criterio | Dado | Cuando | Entonces | Estado |
| --- | --- | --- | --- | --- |
| AC-US05-01 - Conversión válida | una versión vigente de cotización que el cliente acepta | el vendedor solicita convertirla | se crea un pedido Pendiente ligado al folio y versión, conserva partidas y total, consulta disponibilidad y no reserva inventario | Implementada |
| AC-US05-02 - Aceptación obligatoria | una versión vigente que el cliente no ha aceptado | el vendedor solicita convertirla | se rechaza la conversión sin crear pedido ni reserva | Implementada |
| AC-US05-03 - Pendiente sin disponibilidad | una cotización vigente y aceptada con un producto registrado pero sin unidades disponibles | se convierte la cotización | se crea un pedido Pendiente y se informa la disponibilidad en 0 sin crear reserva | Implementada |

**Pruebas y límites de los criterios:**

- `AC-US05-01`: [tests/test_api_conversion_postgres.py](../../tests/test_api_conversion_postgres.py), método `test_pedido_http_persiste_version_2_total_240_y_evento_sin_reserva`.
- `AC-US05-02`: [tests/test_api_conversion.py](../../tests/test_api_conversion.py), método `test_sin_aceptacion_rechaza_una_version_vigente`.
- `AC-US05-03`: [tests/test_api_conversion_postgres.py](../../tests/test_api_conversion_postgres.py), método `test_sin_stock_se_crea_pendiente_pero_no_reserva`.

## US06 - Registrar el pago de una venta de contado

Como Caja, quiero registrar el pago de una venta de contado, para confirmar el pedido solo con un pago autorizado.

**Necesidades:** BN02/BN04. **Reglas:** BR05. **Estado de la historia:** Simulada.

**BPMN:** `P02_T02/P02_G02`. **Componente:** [src/ferremax/domain/model.py](../../src/ferremax/domain/model.py); [src/ferremax/application/services.py](../../src/ferremax/application/services.py); [src/ferremax/api/pedidos.py](../../src/ferremax/api/pedidos.py).

**Límite:** El cuerpo HTTP proporciona pago_autorizado y referencia. No se procesa dinero ni se integra una pasarela; el actor Caja también es de demo.

| Criterio | Dado | Cuando | Entonces | Estado |
| --- | --- | --- | --- | --- |
| AC-US06-01 - Pago autorizado y stock suficiente | un pedido Pendiente, referencia de pago autorizado y disponibilidad suficiente | Caja confirma el pedido desde una ubicación | se guardan Confirmado, su reserva, auditoría y evento en una sola transacción | Simulada |
| AC-US06-02 - Pago rechazado | un pedido Pendiente y un pago no autorizado | Caja intenta confirmarlo | el pedido permanece Pendiente sin reserva ni evento de confirmación nuevo | Simulada |
| AC-US06-03 - Referencia obligatoria | un pedido Pendiente sin referencia de pago válida | Caja intenta confirmarlo | se rechaza la solicitud y se conserva el estado anterior | Simulada |

**Pruebas y límites de los criterios:**

- `AC-US06-01`: [tests/test_api_confirmacion_postgres.py](../../tests/test_api_confirmacion_postgres.py), método `test_confirmacion_http_persiste_estado_reserva_auditoria_y_evento`.
- `AC-US06-02`: [tests/test_api_confirmacion_postgres.py](../../tests/test_api_confirmacion_postgres.py), método `test_pago_no_autorizado_no_reserva_ni_confirma`.
- `AC-US06-03`: [tests/test_api_confirmacion.py](../../tests/test_api_confirmacion.py), método `test_datos_invalidos_se_rechazan_sin_cambios`.

## US07 - Validar automáticamente las condiciones de crédito de un cliente empresarial

Como analista de crédito, quiero validar automáticamente las condiciones de crédito de un cliente empresarial, para reducir riesgos y tiempos de autorización.

**Necesidades:** BN05. **Reglas:** BR09/BR10. **Estado de la historia:** Parcial.

**BPMN:** `P03_T01/P03_G01/P03_T02/P03_G02`. **Componente:** [src/ferremax/domain/model.py](../../src/ferremax/domain/model.py).

**Límite:** CuentaCredito y PoliticaCredito evalúan condiciones básicas, pero no hay flujo de solicitud, persistencia, decisión auditada ni endpoint de crédito.

| Criterio | Dado | Cuando | Entonces | Estado |
| --- | --- | --- | --- | --- |
| AC-US07-01 - Crédito normal suficiente | un cliente empresarial activo, sin bloqueo y con crédito disponible suficiente en la misma moneda | solicita comprar a crédito | se autoriza la condición normal y se registra la evaluación | Diseñada |
| AC-US07-02 - Cliente bloqueado | un cliente empresarial bloqueado | se evalúa una solicitud de crédito | se obtiene EnRevision y no se confirma automáticamente el pedido | Parcial |

**Pruebas y límites de los criterios:**

- `AC-US07-01`: sin prueba integral identificada. El cálculo aislado no acredita registro ni autorización integral de un pedido.
- `AC-US07-02`: [tests/test_architecture.py](../../tests/test_architecture.py), método `ArquitecturaTest::test_credito_bloqueado_insuficiente_inactivo`. La prueba acredita EnRevision en la política aislada, no persistencia del expediente ni un cambio de estado del pedido.

## US08 - Resolver una excepción de crédito con motivo

Como responsable de Caja/Crédito, quiero resolver una excepción de crédito con motivo, para controlar decisiones fuera de la política normal.

**Necesidades:** BN05. **Reglas:** BR11. **Estado de la historia:** Diseñada.

**BPMN:** `P03_T04/P03_G03/P03_T05`. **Componente:** Sin caso de uso implementado.

**Límite:** Faltan permisos nominales y límites de autorización comercial; no se inventan umbrales de excepción.

| Criterio | Dado | Cuando | Entonces | Estado |
| --- | --- | --- | --- | --- |
| AC-US08-01 - Excepción autorizada | una solicitud de crédito en revisión | el responsable autoriza una excepción e indica el motivo | se registran decisión, responsable, fecha y condición autorizada | Diseñada |
| AC-US08-02 - Excepción rechazada | una solicitud de crédito en revisión | el responsable rechaza la excepción con motivo | el pedido no se confirma y el vendedor recibe el motivo | Diseñada |

**Pruebas y límites de los criterios:**

- `AC-US08-01`: sin prueba integral identificada.
- `AC-US08-02`: sin prueba integral identificada.

## US09 - Reservar inventario al confirmar un pedido

Como sistema, quiero reservar inventario al confirmar un pedido, para impedir que otra venta use la misma cantidad.

**Necesidades:** BN02. **Reglas:** BR04/BR05. **Estado de la historia:** Implementada.

**BPMN:** `P02_T03/P02_B01`. **Componente:** [src/ferremax/domain/model.py](../../src/ferremax/domain/model.py); [src/ferremax/application/services.py](../../src/ferremax/application/services.py); [src/ferremax/infrastructure/postgres.py](../../src/ferremax/infrastructure/postgres.py).

**Límite:** Un pedido reserva desde una sola ubicación. La reserva, estado, auditoría y evento comparten transacción; un fallo revierte todos los cambios.

| Criterio | Dado | Cuando | Entonces | Estado |
| --- | --- | --- | --- | --- |
| AC-US09-01 - Reserva atómica | un pedido Pendiente con pago autorizado y unidades suficientes | se confirma el pedido | la reserva propia y el estado Confirmado se guardan juntos y el disponible disminuye por lo reservado | Implementada |
| AC-US09-02 - Competencia por la última unidad | dos pedidos con autorización de pago compiten por la última unidad disponible | ambos intentan confirmarse concurrentemente | solo uno obtiene la reserva y el otro recibe rechazo por disponibilidad, permaneciendo Pendiente | Implementada |
| AC-US09-03 - Reserva exactamente igual al disponible | 3 unidades disponibles y un pedido de 3 unidades con pago autorizado | se confirma ese pedido | se reservan 3 unidades y el disponible queda en 0 | Implementada |
| AC-US09-04 - Solicitud mayor que el disponible | 3 unidades disponibles y un pedido de 4 unidades con pago autorizado | se intenta confirmar el pedido | se rechaza y el pedido almacenado permanece Pendiente sin alterar reservas ni registrar un éxito | Implementada |
| AC-US09-05 - Fallo en la segunda partida | un pedido con dos productos y disponibilidad insuficiente en el segundo | la confirmación intenta reservar ambas partidas | se revierte la reserva del primer producto junto con estado, referencia de pago y efectos de éxito | Implementada |
| AC-US09-06 - Confirmación repetida | un pedido ya Confirmado con su reserva persistida | se vuelve a solicitar su confirmación | se rechaza sin duplicar reserva ni evento ni reemplazar la referencia original | Implementada |

**Pruebas y límites de los criterios:**

- `AC-US09-01`: [tests/test_api_confirmacion_postgres.py](../../tests/test_api_confirmacion_postgres.py), método `test_confirmacion_http_persiste_estado_reserva_auditoria_y_evento`.
- `AC-US09-02`: [tests/test_api_confirmacion_postgres.py](../../tests/test_api_confirmacion_postgres.py), método `test_dos_pedidos_compiten_por_ultima_unidad_desde_http`.
- `AC-US09-03`: [tests/test_e9_inventario.py](../../tests/test_e9_inventario.py), método `InventarioE9Test::test_e9_inv_03_limite_reservar_tres_agota_el_disponible`.
- `AC-US09-04`: [tests/test_e9_inventario.py](../../tests/test_e9_inventario.py), método `InventarioE9Test::test_e9_inv_02_error_pedir_cuatro_conserva_pedido_e_inventario`.
- `AC-US09-05`: [tests/test_api_confirmacion_postgres.py](../../tests/test_api_confirmacion_postgres.py), método `test_segundo_sku_sin_stock_revierte_primera_reserva`.
- `AC-US09-06`: [tests/test_api_confirmacion_postgres.py](../../tests/test_api_confirmacion_postgres.py), método `test_confirmar_dos_veces_no_duplica_reserva_ni_evento`.

## US10 - Cancelar o reducir un pedido antes del surtido

Como vendedor, quiero cancelar o reducir un pedido antes del surtido, para liberar mercancía que ya no necesita el cliente.

**Necesidades:** BN02. **Reglas:** BR06. **Estado de la historia:** Parcial.

**BPMN:** `P02_T05/P02_G04/P02_G05/P02_T06/P02_T08`. **Componente:** [src/ferremax/domain/model.py](../../src/ferremax/domain/model.py); [src/ferremax/application/services.py](../../src/ferremax/application/services.py); [src/ferremax/api/pedidos.py](../../src/ferremax/api/pedidos.py).

**Límite:** Se implementó cancelación completa; no reducción de partidas. El actor autorizado es simulado y surtido es una guarda, sin operación de surtido en la API.

| Criterio | Dado | Cuando | Entonces | Estado |
| --- | --- | --- | --- | --- |
| AC-US10-01 - Cancelación libera solo lo propio | un pedido Confirmado, aún no surtido, con autorización y motivo, cuya reserva es de 2 unidades y comparte inventario con 7 unidades reservadas para otro pedido | se cancela el pedido | se liberan solo sus 2 unidades, se conservan las 7 ajenas y se guarda motivo, auditoría y evento | Implementada |
| AC-US10-02 - Reducción libera diferencia | un pedido Confirmado y aún no surtido con una partida reservada | se autoriza reducir la cantidad de esa partida con motivo | se libera solo la diferencia y se conserva el resto de la reserva y su trazabilidad | Diseñada |
| AC-US10-03 - Rechazo después del surtido | un pedido Confirmado marcado como surtido | se solicita cancelarlo con motivo | se rechaza conservando estado, reservas y registros previos | Implementada |
| AC-US10-04 - Cancelación repetida | un pedido ya Cancelado y sin su reserva activa | se solicita cancelarlo de nuevo | se rechaza sin liberar cantidades adicionales ni duplicar el evento de cancelación | Implementada |
| AC-US10-05 - Liberación fallida revierte todo | un pedido con reserva de dos productos y una inconsistencia que impide liberar el segundo | se intenta cancelar el pedido | se revierte la primera liberación y se conservan estado y registros originales | Implementada |

**Pruebas y límites de los criterios:**

- `AC-US10-01`: [tests/test_api_cancelacion_postgres.py](../../tests/test_api_cancelacion_postgres.py), método `test_cancela_y_persiste_liberacion_conservando_otro_pedido`.
- `AC-US10-02`: sin prueba integral identificada. Es una separación del criterio original; no se elimina ni se declara implementada la reducción.
- `AC-US10-03`: [tests/test_e9_cancelacion.py](../../tests/test_e9_cancelacion.py), método `CancelacionE9Test::test_e9_can_02_error_pedido_surtido_conserva_estado_reservas_y_eventos`.
- `AC-US10-04`: [tests/test_api_cancelacion_postgres.py](../../tests/test_api_cancelacion_postgres.py), método `test_rechazos_conservan_datos_y_no_agregan_cancelaciones`.
- `AC-US10-05`: [tests/test_api_cancelacion_postgres.py](../../tests/test_api_cancelacion_postgres.py), método `test_fallo_al_liberar_segundo_producto_revierte_toda_la_transaccion`.

## US11 - Solicitar una transferencia desde otra ubicación

Como vendedor, quiero solicitar una transferencia desde otra ubicación, para surtir un pedido sin prometer inventario inexistente.

**Necesidades:** BN04/BN06. **Reglas:** BR07/BR12. **Estado de la historia:** Diseñada.

**BPMN:** `P04_T01/P04_T02/P04_T03`. **Componente:** Sin flujo implementado.

**Límite:** Consultar otras ubicaciones no implementa selección de origen, transferencia ni reserva multiorigen.

| Criterio | Dado | Cuando | Entonces | Estado |
| --- | --- | --- | --- | --- |
| AC-US11-01 - Solicitud trazable | una sucursal sin unidades suficientes y otra ubicación con disponible | el vendedor solicita una transferencia tras consultar primero almacén central y después otras sucursales | se registra un folio con origen, destino, partidas, cantidades, pedido relacionado y estado Solicitado | Diseñada |

**Pruebas y límites de los criterios:**

- `AC-US11-01`: sin prueba integral identificada.

## US12 - Autorizar, rechazar y despachar una transferencia

Como responsable de almacén, quiero autorizar, rechazar y despachar una transferencia, para controlar la mercancía que cambia de ubicación.

**Necesidades:** BN06. **Reglas:** BR12. **Estado de la historia:** Diseñada.

**BPMN:** `P04_T04/P04_G03/P04_T05`. **Componente:** Sin flujo implementado.

**Límite:** No se mueven cantidades en tránsito mediante la API actual.

| Criterio | Dado | Cuando | Entonces | Estado |
| --- | --- | --- | --- | --- |
| AC-US12-01 - Despacho autorizado | una transferencia autorizada y preparada | almacén registra su salida | la cantidad se registra en tránsito y se conservan responsable y fecha | Diseñada |
| AC-US12-02 - Rechazo por faltante | una solicitud cuyo origen ya no tiene suficiente disponible | almacén revisa la solicitud | se rechaza con motivo y el pedido relacionado vuelve a evaluación | Diseñada |

**Pruebas y límites de los criterios:**

- `AC-US12-01`: sin prueba integral identificada.
- `AC-US12-02`: sin prueba integral identificada.

## US13 - Confirmar la recepción de una transferencia

Como almacén destino, quiero confirmar la recepción de una transferencia, para actualizar inventario utilizable y cerrar el movimiento.

**Necesidades:** BN06. **Reglas:** BR13. **Estado de la historia:** Diseñada.

**BPMN:** `P04_T06/P04_G04/P04_T07/P04_T08`. **Componente:** Sin flujo implementado.

**Límite:** Los valores de tránsito del demo son datos iniciales; no acreditan recepción de una transferencia.

| Criterio | Dado | Cuando | Entonces | Estado |
| --- | --- | --- | --- | --- |
| AC-US13-01 - Recepción completa | una transferencia en tránsito con todas sus cantidades recibidas | destino confirma la recepción | disminuye tránsito, aumenta existencia física utilizable en destino y queda Recibida sin ocultar reservas ajenas | Diseñada |
| AC-US13-02 - Diferencia de recepción | una transferencia cuya cantidad recibida difiere de la esperada | destino registra lo efectivamente recibido | queda una incidencia trazable y no se oculta la diferencia | Diseñada |

**Pruebas y límites de los criterios:**

- `AC-US13-01`: sin prueba integral identificada.
- `AC-US13-02`: sin prueba integral identificada.

## US14 - Proponer y registrar un surtido parcial

Como vendedor, quiero proponer y registrar un surtido parcial, para permitir que el cliente decida sobre faltantes.

**Necesidades:** BN04/BN07. **Reglas:** BR08. **Estado de la historia:** Diseñada.

**BPMN:** `P04_T09/P04_G05/P04_T10/P04_T11`. **Componente:** Sin flujo implementado.

**Límite:** Aceptar una cotización no equivale a aceptar un parcial; faltan cantidades y estados por partida.

| Criterio | Dado | Cuando | Entonces | Estado |
| --- | --- | --- | --- | --- |
| AC-US14-01 - Aceptación de parcial | un pedido con disponibilidad insuficiente | el cliente acepta expresamente las cantidades surtibles | se separan las cantidades surtibles y pendientes por partida y se conserva la aceptación | Diseñada |
| AC-US14-02 - Rechazo de parcial | un pedido incompleto cuyo cliente no acepta el parcial | se registra su decisión de esperar o cancelar | se conserva la decisión y se libera únicamente lo que corresponda si hay una cancelación autorizada | Diseñada |

**Pruebas y límites de los criterios:**

- `AC-US14-01`: sin prueba integral identificada.
- `AC-US14-02`: sin prueba integral identificada.

## US15 - Generar y completar una orden de surtido

Como responsable de almacén, quiero generar y completar una orden de surtido, para preparar exactamente lo reservado para el pedido.

**Necesidades:** BN04/BN07. **Reglas:** BR05/BR07/BR08. **Estado de la historia:** Diseñada.

**BPMN:** `P05_T01/P05_G01`. **Componente:** Solo existe Pedido.surtido como guarda.

**Límite:** No existe operación para completar surtido. Preparar surtido en una prueba solo verifica la guarda de cancelación.

| Criterio | Dado | Cuando | Entonces | Estado |
| --- | --- | --- | --- | --- |
| AC-US15-01 - Surtido correcto | un pedido Confirmado con reservas | almacén prepara y verifica sus partidas | se registran cantidades surtidas, faltantes, responsable y hora sin exceder lo reservado | Diseñada |

**Pruebas y límites de los criterios:**

- `AC-US15-01`: sin prueba integral identificada.

## US16 - Programar unidad, operador y ventana de entrega

Como coordinador de entrega, quiero programar unidad, operador y ventana de entrega, para organizar pedidos grandes enviados a domicilio.

**Necesidades:** BN08. **Reglas:** BR14. **Estado de la historia:** Diseñada.

**BPMN:** `P05_T03/P05_G03/P05_T04`. **Componente:** Sin flujo implementado.

**Límite:** No se implementan transporte ni optimización de rutas; la segunda permanece fuera del alcance original.

| Criterio | Dado | Cuando | Entonces | Estado |
| --- | --- | --- | --- | --- |
| AC-US16-01 - Programación completa | un pedido surtido con entrega a domicilio y dirección validada | se programa la entrega | se asignan unidad, operador, ventana y estado Programado | Diseñada |
| AC-US16-02 - Datos incompletos | una entrega sin dirección o contacto válido | se intenta programar la salida | se bloquea y se indican los datos faltantes | Diseñada |

**Pruebas y límites de los criterios:**

- `AC-US16-01`: sin prueba integral identificada.
- `AC-US16-02`: sin prueba integral identificada.

## US17 - Registrar la entrega o una incidencia

Como operador de entrega, quiero registrar la entrega o una incidencia, para cerrar el pedido con evidencia.

**Necesidades:** BN08. **Reglas:** BR14. **Estado de la historia:** Diseñada.

**BPMN:** `P05_T05/P05_G04/P05_T06/P05_T07`. **Componente:** Sin flujo implementado.

**Límite:** Los estados del negocio Entregado/Incidencia de esta vista aún no forman parte de EstadoPedido de la aplicación.

| Criterio | Dado | Cuando | Entonces | Estado |
| --- | --- | --- | --- | --- |
| AC-US17-01 - Entrega completada | una entrega en ruta realizada al destinatario | el operador registra receptor, fecha, hora y evidencia | la entrega y el pedido se cierran como entregados con su trazabilidad | Diseñada |
| AC-US17-02 - Incidencia en ruta | una entrega que no pudo realizarse | el operador registra motivo y evidencia | la entrega queda con incidencia y el pedido no se cierra como entregado | Diseñada |

**Pruebas y límites de los criterios:**

- `AC-US17-01`: sin prueba integral identificada.
- `AC-US17-02`: sin prueba integral identificada.

## US18 - Registrar una solicitud de devolución

Como vendedor, quiero registrar una solicitud de devolución, para aplicar la política correcta y mantener trazabilidad.

**Necesidades:** BN09. **Reglas:** BR15. **Estado de la historia:** Diseñada.

**BPMN:** `P06_T01/P06_G01/P06_T02/P06_G02/P06_T03/P06_T04`. **Componente:** Sin flujo implementado.

**Límite:** La política por categoría y condición sigue pendiente de definición comercial; no se inventa un plazo ni un resultado financiero fijo.

| Criterio | Dado | Cuando | Entonces | Estado |
| --- | --- | --- | --- | --- |
| AC-US18-01 - Devolución elegible | un comprobante válido y un producto cuya categoría y condición cumplen la política configurada | se autoriza la devolución | se registran la decisión, el resultado financiero y el destino del inventario | Diseñada |

**Pruebas y límites de los criterios:**

- `AC-US18-01`: sin prueba integral identificada.

## US19 - Consultar alertas y reportes operativos

Como gerente de operaciones, quiero consultar alertas y reportes operativos, para detectar riesgos antes de afectar al cliente.

**Necesidades:** BN10. **Reglas:** BR16. **Estado de la historia:** Diseñada.

**BPMN:** `P07_T04`. **Componente:** Sin panel implementado.

**Límite:** GET de un pedido es una consulta operativa, no el panel agregado de esta historia.

| Criterio | Dado | Cuando | Entonces | Estado |
| --- | --- | --- | --- | --- |
| AC-US19-01 - Panel operativo | operaciones registradas en las cuatro ubicaciones del negocio | el gerente consulta el panel con filtros de fecha y ubicación | ve cotizaciones por vencer, bajo mínimo, transferencias, crédito en revisión, parciales y entregas pendientes | Diseñada |

**Pruebas y límites de los criterios:**

- `AC-US19-01`: sin prueba integral identificada.

## US20 - Consultar la bitácora de una operación

Como auditor, quiero consultar la bitácora de una operación, para saber quién cambió qué, cuándo y por qué.

**Necesidades:** BN10. **Reglas:** BR16. **Estado de la historia:** Parcial.

**BPMN:** `P07_T01/P07_T02/P07_G01/P07_T03`. **Componente:** [src/ferremax/application/services.py](../../src/ferremax/application/services.py); [src/ferremax/infrastructure/postgres.py](../../src/ferremax/infrastructure/postgres.py).

**Límite:** Se almacena auditoría transaccional, pero no hay endpoint de consulta de bitácora, identidad autenticada ni prueba de prohibición de edición por un rol operativo de BD.

| Criterio | Dado | Cuando | Entonces | Estado |
| --- | --- | --- | --- | --- |
| AC-US20-01 - Consulta de bitácora protegida | una operación sensible modificada | un auditor autorizado consulta su folio | se muestran actor, fecha, hora, acción, valores anterior y nuevo y motivo, sin permitir que un usuario operativo altere la bitácora | Diseñada |
| AC-US20-02 - Registro transaccional de cambio | un pedido Pendiente, pago autorizado y disponibilidad suficiente | se confirma el pedido | pedido, reserva, auditoría con actor y valores anterior/nuevo y evento se conservan en la misma transacción | Implementada |

**Pruebas y límites de los criterios:**

- `AC-US20-01`: sin prueba integral identificada. Registrar filas no acredita todavía la consulta protegida completa.
- `AC-US20-02`: [tests/test_api_confirmacion_postgres.py](../../tests/test_api_confirmacion_postgres.py), método `test_confirmacion_http_persiste_estado_reserva_auditoria_y_evento`. Actor de demostración; este criterio acredita el registro, no autenticación ni inalterabilidad por permisos.

## Fuente y evidencia

- Historias y criterios originales de [U2](<../../reference/EQ17FerreMax_UserStories(1).pdf>), conservados sin cambios.
- Evidencia CI/CD del núcleo: [registro de 947aeae](../../evidencias/pia/render_cd_verificacion.json), 242 pruebas, 0 omisiones y 97.24% de cobertura. Esta métrica no acredita los criterios diseñados ni un porcentaje de historias terminadas.
- Las pruebas referenciadas verifican comportamientos concretos; leer los límites de cada criterio antes de extrapolar sus resultados.
