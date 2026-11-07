# BRD integrado - FerreMax PIA

| Dato | Valor |
| --- | --- |
| Curso | Componentes de Lógica de Negocios |
| Profesor | Miguel Ángel Gómez Marroquín |
| Equipo | 17 |
| Integrantes | Roberto Santana Trujillo, 2227084; Isaías Leonardo Salazar Torres, 2227016 |
| Fecha de integración | 6 de noviembre de 2026 |
| Base | BRD, historias/Gherkin, BPMN y glosario de U2; arquitectura de U3; implementación PIA |

## 1. Propósito y visión

FerreMax necesita coordinar cotizaciones, pedidos e inventario para ofrecer mercancía disponible, conservar las condiciones aceptadas por el cliente y registrar las decisiones que afectan una venta. El análisis abarca también crédito, transferencias, parciales, surtido, entregas, devoluciones y control operativo.

Este BRD integra los documentos de U2/U3 y los relaciona con la solución actual. Mantiene las necesidades del negocio aunque una función todavía no esté implementada. La [trazabilidad por criterio](analysis/trazabilidad_analisis.csv) distingue lo implementado, simulado, parcial y diseñado; documentar una limitación no elimina el requisito ni acredita por sí mismo el cumplimiento del PIA.

## 2. Contexto del negocio y operación actual

FerreMax vende herramientas y materiales eléctricos, de plomería y construcción. Opera tres sucursales y un almacén central; atiende mostrador y clientes empresariales que pueden solicitar crédito. Sus productos se identifican por SKU y se controlan por ubicación.

En la operación descrita en U2, el vendedor consulta existencias y ofrece surtido local, desde almacén central o mediante otras sucursales. Las cotizaciones se manejan en hojas de cálculo, con riesgo de aplicar condiciones vencidas o versiones distintas. El crédito requiere revisar la cuenta y separar una autorización normal de una excepción. Los pedidos grandes pueden necesitar unidad, operador y evidencia de entrega.

| Problema identificado | Consecuencia | Necesidades relacionadas |
| --- | --- | --- |
| Prometer mercancía ya comprometida | Ventas que no pueden surtirse, retrasos y cancelaciones | BN01/BN02/BN04 |
| Cotizaciones dispersas o vencidas | Precios, condiciones y versiones inconsistentes | BN03 |
| Visibilidad limitada de otras ubicaciones y tránsito | Alternativas de surtido sin respaldo | BN01/BN06/BN07 |
| Crédito excepcional sin decisión trazable | Riesgo comercial y falta de responsables | BN05/BN10 |
| Entregas y devoluciones sin evidencia suficiente | Incidencias y ajustes difíciles de explicar | BN08/BN09/BN10 |

## 3. Objetivos y forma de medición

Los objetivos son metas del negocio heredadas de U2, con acuerdos simulados para el ejercicio académico. No se presentan como resultados operativos obtenidos.

| ID | Objetivo conservado | Medición y estado |
| --- | --- | --- |
| OB01 | Reducir al menos 80% las ventas confirmadas sin mercancía durante los primeros tres meses frente a la línea base | Comparar incidencias del periodo con una línea base depurada. No hay medición de operación real; el núcleo sí prueba rechazo de sobreventa. |
| OB02 | Conseguir que el 100% de cotizaciones tengan folio, versión, estado y vigencia; usar siete días como valor de referencia del caso | Comprobar campos y vigencia configurada. La emisión operativa inicial está pendiente; revalidar recibe el número de días, no impone siete. |
| OB03 | Lograr que el 100% de autorizaciones excepcionales de crédito sean trazables | Revisar cada decisión con responsable, fecha, motivo y condición. Flujo pendiente. |
| OB04 | Consultar disponibilidad global en <=3 s para al menos 95% de consultas normales | Ensayo de rendimiento con carga y condiciones declaradas. Aún sin medición. |
| OB05 | Mantener estado y responsables visibles en todas las transferencias y entregas activas | Conciliar movimientos y evidencia por folio. Flujos pendientes. |

En U2, CE01 prometía eliminación total de ventas sin disponibilidad mientras OB01 fijaba una reducción de 80%; CE04 omitía el percentil de OB04. Esta integración alinea los criterios operativos a los objetivos medibles de U2. La prohibición de sobrecomprometer inventario se conserva como regla de integridad del núcleo, distinta del indicador operativo de tres meses.

## 4. Stakeholders y responsabilidades

| Actor | Responsabilidad en el negocio | Situación en la aplicación |
| --- | --- | --- |
| Cliente | Solicita productos, acepta una versión de cotización, decide parciales, paga y recibe | La aceptación y el pago se proporcionan como datos de demostración; no hay portal de cliente. |
| Vendedor | Consulta disponibilidad, emite/revalida cotizaciones, crea pedidos y propone alternativas | Consulta, revalidación y conversión implementadas con actor simulado; emisión inicial y alternativas pendientes. |
| Caja/Crédito | Registra pagos, evalúa crédito y resuelve excepciones | Confirmación de contado con autorización simulada; crédito integral pendiente. |
| Almacén | Controla inventario, surte, transfiere y recibe | Reserva/liberación automáticas del núcleo; surtido y transferencias pendientes. |
| Compras | Atiende bajo mínimo y reabastecimiento | Participación informativa del análisis; integración con proveedores fuera del alcance original. |
| Coordinador y operador de entrega | Programan, trasladan y capturan evidencia o incidencia | Diseñado. |
| Gerente de operaciones | Define prioridades y consulta indicadores | Panel diseñado; objetivos operativos sin medir. |
| Auditor/administrador | Consulta cambios y administra parámetros autorizados | Se registra auditoría de los casos implementados; consulta protegida y permisos nominales pendientes. |

Los roles del código son guardas de servicios. Los endpoints construyen actores ficticios: no acreditan autenticación de personas ni autorización real de un usuario conectado.

## 5. Alcance del negocio y alcance ejecutable actual

### 5.1 Necesidades conservadas

Se conserva el alcance de U2: disponibilidad global y reservas; cotizaciones, venta y crédito; transferencias, parciales y surtido; entregas y devoluciones; alertas y auditoría. Se mantienen las veinte historias y sus criterios en [USER_STORIES.md](analysis/USER_STORIES.md).

Permanecen fuera del alcance original: comercio electrónico público general, contabilidad general y nóminas, optimización de rutas e integración con proveedores. Esta lista no incluye funciones pendientes que sí pertenecían a U2.

### 5.2 Recorrido que se puede ejecutar y demostrar

| Operación | Regla y resultado | Historias |
| --- | --- | --- |
| `GET /inventario/{sku}` | Consulta por ubicación física, comprometida, tránsito y disponible; no modifica datos | US01/US02 |
| `POST /cotizaciones/{id}/versiones/{version}/revalidar` | Revalida una versión vencida y conserva su historial; no reserva | US04 |
| `POST /cotizaciones/{id}/versiones/{version}/convertir` | Exige vigencia y aceptación; crea pedido Pendiente ligado a la versión; no reserva | US05 |
| `POST /pedidos/{id}/confirmar` | Exige autorización de pago y existencias; guarda Confirmado y reserva en una transacción | US06/US09 |
| `POST /pedidos/{id}/cancelar` | Exige Confirmado, aún no surtido y motivo; libera la reserva propia y guarda Cancelado | Parte de US10 |
| `GET /pedidos/{id}` | Recupera el estado, folio/versión de origen, total y moneda persistidos | Apoya US05/US06/US09/US10 |

### 5.3 Límites concretos de ese recorrido

- La confirmación ejecutable es de contado, con un booleano y una referencia que simulan autorización; no procesa dinero ni ejecuta crédito.
- La reserva utiliza una sola ubicación por pedido. Revalidación y conversión consultan S1, fijada en el servicio. La consulta global devuelve las ubicaciones que realmente tienen un registro para el SKU; el demo público no completa necesariamente las cuatro ubicaciones del negocio.
- La emisión inicial de cotizaciones se prepara mediante semilla ficticia; no existe un endpoint de emisión ni de consulta independiente de cotización.
- Cancelar está implementado; reducir cantidades aún no. El indicador `surtido` permite probar una guarda, pero no existe una operación para surtir ni estados Entregado/Devuelto en la máquina actual.
- Crédito tiene una política básica aislada; faltan solicitud, autorización excepcional, persistencia e integración. Transferencias, parciales, surtido, entrega, devolución y panel siguen diseñados.
- La auditoría del núcleo guarda actor, fecha, antes/después, acción y motivo; la identidad es ficticia. No hay API de consulta de bitácora ni evidencia de permisos de BD que impidan edición a un usuario operativo.

U3 detalló cinco casos de uso y la aplicación añadió una consulta de pedido. No existe evidencia en este repositorio de una dispensa del profesor para las demás historias del PIA. Por ello las limitaciones se mantienen como trabajo pendiente de cumplimiento, con su trazabilidad visible.

## 6. Necesidades del negocio

| ID | Necesidad | Prioridad U2 | Historias | Estado actual |
| --- | --- | --- | --- | --- |
| BN01 | Disponibilidad confiable de las tres sucursales y almacén | Alta | US01/US02 | Consulta implementada sobre registros disponibles; objetivo temporal sin medir. |
| BN02 | Reservar y liberar sin prometer mercancía comprometida | Alta | US09/US10 | Reserva y cancelación implementadas; reducción pendiente. |
| BN03 | Cotizaciones controladas y versionadas | Alta | US03/US04/US05 | Revalidación/conversión implementadas; emisión inicial operativa pendiente. |
| BN04 | Venta y surtido local, multiorigen o parcial con consentimiento | Alta | US05/US06/US11/US14/US15 | Núcleo de contado local; resto pendiente. |
| BN05 | Crédito empresarial normal y excepcional | Alta | US07/US08 | Evaluación básica en dominio; flujo integral pendiente. |
| BN06 | Transferencias con responsables, cantidades y estado | Alta | US11/US12/US13 | Diseñado. |
| BN07 | Cantidades surtidas y pendientes por partida | Media | US14/US15 | Diseñado. |
| BN08 | Entrega programada con receptor y evidencia o incidencia | Media | US16/US17 | Diseñado. |
| BN09 | Devoluciones según comprobante, categoría y condición | Media | US18 | Diseñado; política comercial aún por precisar. |
| BN10 | Alertas, reportes y auditoría | Alta | US19/US20 | Registro transaccional en el núcleo; panel y consulta protegida pendientes. |

## 7. Reglas de negocio

| ID | Regla conservada y precisión PIA | Historias | Estado |
| --- | --- | --- | --- |
| BR01 | Una cotización y su revalidación/conversión no reservan inventario | US03/US04/US05 | Verificada en revalidación/conversión; emisión operativa pendiente. |
| BR02 | Cotización con folio, versión, vigencia y estado. Vigente cuando emisión <= instante < vencimiento | US03/US04/US05 | Modelo/versionado implementados; emisión operativa pendiente. |
| BR03 | Una versión vencida se revalida antes de convertirse; la nueva conserva la anterior | US04/US05 | Implementada. |
| BR04 | Disponible = existencia física - comprometida, sobre movimientos confirmados. Tránsito no se suma | US01/US02/US09 | Implementada para inventario y reservas del núcleo. |
| BR05 | Solo un pedido Confirmado puede crear reserva; estado y reserva se confirman juntos después de autorización y validaciones | US06/US09/US15 | Implementada en contado local. |
| BR06 | Cancelar o reducir antes del surtido libera la cantidad propia que corresponde, con autorización y motivo | US10 | Cancelación completa implementada; reducción pendiente. |
| BR07 | Ante faltante local se consulta primero almacén central y después otras sucursales | US11/US15 | Diseñada; no hay selección automática multiorigen. |
| BR08 | Un parcial exige aceptación explícita de cantidades surtibles/pendientes | US14 | Diseñada; aceptar una cotización no basta. |
| BR09 | Solo clientes empresariales activos pueden solicitar crédito | US07 | Política básica parcial; sin flujo ni registro empresarial completo. |
| BR10 | Crédito normal no excede disponible ni ignora bloqueo; importes deben tener moneda compatible | US07 | Evaluación aislada parcial; sin autorización integral. |
| BR11 | Toda excepción de crédito registra decisión, responsable, fecha, condición y motivo de Caja/Crédito | US08 | Diseñada. |
| BR12 | Transferencia con origen, destino, partidas, responsable y estado | US11/US12 | Diseñada. |
| BR13 | Recepción de transferencia actualiza tránsito/inventario de destino conservando diferencias como incidencias | US13 | Diseñada. |
| BR14 | Entrega con receptor, fecha/hora y evidencia; una incidencia no cierra el pedido como entregado | US16/US17 | Diseñada. |
| BR15 | Devolución según política configurable por categoría y condición del producto | US18 | Diseñada; valores de política pendientes. |
| BR16 | Toda modificación sensible registra actor, fecha/hora, acción, valores anteriores/nuevos y motivo | US19/US20 y operaciones sensibles | Registro implementado en el núcleo; consulta, permisos e identidad real pendientes. |

**Atomicidad y estados:** si falta stock durante una confirmación, se revierte toda la transacción y el pedido persistido permanece Pendiente. Esto no añade una transición comercial Confirmado → Pendiente. Repetir confirmación o cancelación se rechaza sin duplicar efectos. Con tres disponibles, dos o exactamente tres son válidos; cuatro no.

## 8. Requisitos no funcionales

| ID | Requisito | Evidencia o condición pendiente |
| --- | --- | --- |
| RNF01 | Consulta global <=3 s en 95% de consultas normales; reserva <=5 s | Se requiere ensayo declarado de carga, entorno y percentiles. Aún sin medir. |
| RNF02 | La última unidad no se asigna a dos pedidos concurrentes | Pruebas con PostgreSQL real, bloqueos y rollback; también concurrencia de revalidación/cancelación. |
| RNF03 | Acceso por rol y autorización separada para crédito, cancelación y devolución | Guardas de servicio verificadas con actores ficticios; autenticación y permisos operativos pendientes. |
| RNF04 | Historial de cambios con quién, cuándo, qué y por qué | Auditoría transaccional en el núcleo; identidad real y consulta protegida pendientes. |
| RNF05 | Operación durante el horario de las cuatro ubicaciones | Nivel exacto de servicio y medición pendientes; Render Free puede suspender por inactividad. |
| RNF06 | Estados, causas y siguientes acciones en lenguaje del negocio | Mensajes HTTP en español verificados para el núcleo. No hay estudio de usabilidad de usuarios. |
| RNF07 | No confirmar pedidos, transferencias ni entregas con datos obligatorios incompletos | Datos y transacciones del pedido verificados; los otros procesos siguen pendientes. |
| RNF08 | Vigencias, políticas y umbrales comerciales no confirmados parametrizados | Días de revalidación son parámetro; políticas completas de crédito/devolución pendientes. Conexión y arranque usan variables de entorno. |

## 9. Proceso propuesto y correspondencia con BPMN

El [BPMN integrado](analysis/BPMN.md) tiene siete vistas relacionadas: cotización/pedido; confirmación/cancelación; crédito; transferencias/parciales; surtido/entrega; devoluciones; auditoría/reportes. Incluye el proceso del negocio completo y marca cada actividad según su soporte actual. Es un modelo BPMN descriptivo, no un motor de ejecución.

La vista de contado se puede seguir en Swagger: consultar disponibilidad, revalidar una cotización vencida, registrar aceptación y crear Pendiente, autorizar el pago de demo, confirmar/reservar y, antes del surtido, cancelar/liberar. La consulta del pedido verifica el estado persistido entre operaciones.

Se corrige la secuencia del diagrama U2 que colocaba reserva antes del pago. En PIA, una cotización no reserva y un pago rechazado deja el pedido Pendiente. El fallo de stock tampoco crea una reserva parcial. La cancelación requiere Confirmado y aún no surtido.

## 10. Datos y lenguaje del dominio

El [glosario integrado](analysis/GLOSARIO.md) conserva los términos U2 y precisa cotización, versión, vigencia, pedido Pendiente, autorización simulada, reserva propia, tránsito, auditoría, Specification y transacción.

Los importes utilizan `Decimal` y moneda; cantidades deben ser positivas y finitas. La cotización identifica al cliente y conserva partidas numeradas; el pedido mantiene folio/versión de origen y su propio total. Las fechas incluyen zona horaria y los instantes técnicos se registran en UTC. La comparación de vigencia incluye emisión y excluye vencimiento.

## 11. Supuestos, restricciones y cuestiones abiertas

| Tema | Tratamiento |
| --- | --- |
| Caso académico | Los acuerdos de siete días y metas operativas son simulados; no se atribuyen entrevistas nuevas ni resultados reales a FerreMax. |
| Datos maestros | Son ficticios; las cuatro ubicaciones del negocio no implican registros de cada SKU en todas ellas. No existe catálogo maestro independiente en la API. |
| Precios y condiciones | El vendedor aporta datos al revalidar; no hay proveedor externo de precios. |
| Crédito | Deben definirse responsables nominales, condiciones y límites de excepción antes de implementar el flujo completo. |
| Devoluciones | Faltan política por categoría/condición, plazos y decisiones financieras. No se inventan valores. |
| Identidad y pago | Simulados en la demostración. La validación interna de un rol no equivale a autenticación externa. |
| Infraestructura | PostgreSQL local/Compose y servicio público en Render; la evidencia debe distinguir ejecuciones y commits. |
| Entrega PIA | La integración documental conserva todos los requisitos. Las funciones diseñadas siguen pendientes; cualquier recorte deberá constar como decisión explícita, no inferirse de la revisión U3. |

## 12. Criterios de éxito

| ID | Criterio refinado | Comprobación actual |
| --- | --- | --- |
| CE01 | Cumplir OB01: reducir >=80% las incidencias de venta sin mercancía en tres meses frente a la línea base | Sin medición operativa. La suite prueba rechazo de sobreventa/rollback en el núcleo. |
| CE02 | Cada cotización tiene folio, versión, vigencia y estado; la vigencia de referencia de siete días puede configurarse | Revalidación/versionado verificados; emisión inicial operativa pendiente. |
| CE03 | Toda decisión de crédito, normal o excepcional, conserva trazabilidad suficiente | Pendiente en el flujo integral. |
| CE04 | Cumplir OB04 y RNF01: <=3 s en al menos 95% de consultas normales | Pendiente de medición. |
| CE05 | Transferencias y entregas activas tienen estados y responsables consultables | Diseñado. |
| CE06 | Devoluciones se resuelven según política de categoría/condición y auditoría | Diseñado; política pendiente. |
| CE07 | Entregas conservan operador, receptor y evidencia o incidencia; una incidencia no se cuenta como entrega | Diseñado. |
| CE08 | Transferencias concilian origen, tránsito, recepción y diferencias | Diseñado. |

## 13. Trazabilidad y aceptación verificable

- [Veinte historias y criterios](analysis/USER_STORIES.md), con identificadores históricos y correcciones explícitas.
- [Contrato Gherkin](analysis/aceptacion.feature): cuarenta y seis escenarios de aceptación, sin presentarlos como pruebas BDD ejecutadas.
- [Matriz por criterio](analysis/trazabilidad_analisis.csv): necesidad, regla, actividad BPMN, componente, prueba y límite.
- [Matriz de los requisitos del profesor](pia/MATRIZ_CUMPLIMIENTO.md): diagnóstico general del cierre.

La ejecución registrada para `947aeae` obtuvo 242 pruebas aprobadas, 0 omitidas y 97.24% de cobertura. [La evidencia](../evidencias/pia/render_cd_verificacion.json) incluye CI, despliegue automático y conservación de datos. Es una medida de las líneas y casos ejecutados de esa versión, no de todas las necesidades del negocio ni del cumplimiento total de las veinte historias.

## 14. Control de cambios y fuentes

| Refinamiento PIA | Razón |
| --- | --- |
| Unificar AC y corregir el identificador repetido de US01 | Mantener trazabilidad inequívoca. |
| Separar cancelación y reducción de US10 | Mostrar la diferencia real de implementación sin eliminar la operación pendiente. |
| Precisar vigencia, reserva y rollback | Expresar los límites que verifican código y pruebas. |
| Alinear CE01/CE04 con OB01/OB04 | Evitar metas contradictorias dentro del BRD. |
| Corregir orden de pago/confirmación/reserva en BPMN | Respetar BR01/BR05 y el comportamiento transaccional. |
| Conservar alcance amplio y señalar pendientes | Evitar presentar una vista de diseño como una aplicación completa. |

Fuentes: [BRD U2](<../reference/EQ17FerreMax_BRD(1).pdf>), [historias U2](<../reference/EQ17FerreMax_UserStories(1).pdf>), [BPMN U2](<../reference/EQ17FerreMax_BPMN(1).pdf>), [glosario U2](<../reference/EQ17FerreMax_Glosario(1).pdf>), [informe U3](U3Ferremax_Informe.pdf) y código/pruebas de la base `d1eebde`. Los archivos históricos y la etiqueta [u3-entrega](https://github.com/Santana-R/ferremax-u3/tree/u3-entrega) se conservan sin cambios.
