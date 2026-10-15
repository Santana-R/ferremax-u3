## Datos de la actividad
**Empresa:** FerreMax. **Unidad:** 3. **Actividad:** Diseño arquitectural del sistema con IA. **Profesor:** Miguel Ángel Gómez Marroquín.
**Integrantes:** Roberto Santana Trujillo, 2227084; Isaías Leonardo Salazar Torres, 2227016.
**Versión de trabajo:** 2026-10-14. **Revisión:** 2026-10-16.
## 1 Propósito y conclusión del diseño
FerreMax necesita que cotizaciones, pedidos e inventario compartan información coherente y que las decisiones comerciales sean trazables. La propuesta organiza el software alrededor de las reglas de la Unidad 2, con Domain Model como patrón principal, una capa de aplicación que coordina casos de uso y adaptadores de persistencia para PostgreSQL alojado en Supabase.
La operación crítica es confirmar un pedido y registrar sus reservas. Ambos cambios, junto con su auditoría y el evento pendiente de publicación, se guardan en una sola transacción. Si una partida no tiene disponibilidad suficiente, la confirmación y cualquier reserva provisional se revierten.
La base de código demuestra un subconjunto del sistema: cotizaciones, confirmación de contado, consulta de disponibilidad y cancelación. El mapa general conserva crédito, transferencias, parciales, surtido, entrega y devolución. La guía permite código parcial; por ello, cada sección distingue diseño de negocio, implementación existente y trabajo posterior.
## 2 Fuentes y continuidad con U2
<table fit-page-width="true" header-row="true">
<tr>
<td>Fuente</td>
<td>Uso en U3</td>
</tr>
<tr>
<td>EQ17FerreMax_BRD(1).pdf</td>
<td>Contexto de tres sucursales y almacén central; BN01–BN10, BR01–BR16, RNF01–RNF08, alcance y supuestos.</td>
</tr>
<tr>
<td>EQ17FerreMax_UserStories(1).pdf</td>
<td>US01–US20 y sus Gherkin; casos normales y rechazos; reserva atómica y competencia por última unidad.</td>
</tr>
<tr>
<td>EQ17FerreMax_Glosario(1).pdf</td>
<td>Lenguaje: SKU, física, comprometida, disponible, tránsito, cotización, pedido, reserva, crédito, transferencia y entrega.</td>
</tr>
<tr>
<td>EQ17FerreMax_BPMN(1).pdf</td>
<td>BPMN cotejado visualmente en el entorno cloud. Se registra H07: la reserva aparece antes del procesamiento del pago o la validación del crédito.</td>
</tr>
<tr>
<td>Actividad_Unidad_3_CLN_ArquitecturaAlumnos(1).docx</td>
<td>Ruta de nueve etapas, requisitos mínimos, criterios de integridad y rúbrica.</td>
</tr>
<tr>
<td>Captura de NetAcad</td>
<td>Reporte FIME con screenshots y conclusiones; revisión previa del profesor; fecha de entrega.</td>
</tr>
<tr>
<td>Apuntes de las clases de 9 y 14 de septiembre</td>
<td>Service Layer, DDD, Repository, Unit of Work, CQRS y SOLID. Se corroboraron en Notion.</td>
</tr>
</table>
### Hallazgos de continuidad
**H01:** US01 usa AC-US01-01 para dos escenarios distintos. La matriz U3 propone identificar el escenario «SKU inexistente» como AC-US01-02, conservando la referencia al ID original repetido. No se alteraron los PDFs.
**H02:** OB01 plantea reducir 80% las ventas sin mercancía; CE01 exige eliminarlas. Se propone conservar OB01 como meta de mejora frente a la línea base y tratar CE01 como aspiración; la arquitectura protege el invariante de no reservar mercancía inexistente. La redacción definitiva de los indicadores requiere revisión del equipo y del profesor.
**H03:** la guía menciona una matriz y un modelo de dominio de U2 que no aparecen como archivos separados entre los cuatro PDFs proporcionados. Se construyen para U3 a partir de los IDs existentes, sin fingir una matriz anterior no recibida.
**H04:** los criterios US18–US20 usan el prefijo CA, a diferencia de AC en las historias anteriores. Se conservan los IDs originales para no perder vínculos.
**H05:** no se especifica qué resultado financiero corresponde cuando Caja registra un pago autorizado y después la reserva falla. El código revierte pedido y reserva; la atención del pago ya autorizado queda pendiente de política comercial. No se simula una devolución automática.
**H06:** se corrigió y fortaleció el ensayo de rollback; se amplió la auditoría con cantidades, precios y condiciones antes/después.
**H07:** el BPMN dibuja «Reservar para pedido confirmado» antes de «Procesar pago» o «Validar crédito» y del gateway «¿Autorizado?». U3 sigue BR05 y US06/US09: autorización registrada, confirmación y reserva atómicas. Los originales de U2 se conservan sin cambios.
## 3 Alcance y casos de uso
El proceso detallado va desde la disponibilidad y la cotización hasta la confirmación del pedido y la liberación de su reserva. Todos los casos aparecen en historias de U2. Los demás procesos se representan para conservar el panorama de FerreMax y sus vínculos, pero no se implementa una aplicación completa.
<table fit-page-width="true" header-row="true">
<tr>
<td>ID</td>
<td>Caso</td>
<td>Actor</td>
<td>Entrada</td>
<td>Evidencia U2</td>
<td>Resultado</td>
</tr>
<tr>
<td>CU01</td>
<td>Consultar disponibilidad global</td>
<td>Vendedor</td>
<td>SKU</td>
<td>BN01; BR04; US01/US02</td>
<td>DTO por ubicación con física, comprometida, tránsito y disponible; SKU inexistente sin existencias inventadas.</td>
</tr>
<tr>
<td>CU02</td>
<td>Revalidar cotización vencida</td>
<td>Vendedor</td>
<td>Folio/ID y versión, partidas y precios revisados, condiciones y vigencia</td>
<td>BN03; BR01–03; US04</td>
<td>Nueva versión vigente; versión anterior conservada; no crea reserva.</td>
</tr>
<tr>
<td>CU03</td>
<td>Convertir cotización aceptada en pedido</td>
<td>Vendedor</td>
<td>ID y versión de cotización; aceptación del cliente</td>
<td>BN03/BN04; BR01/BR03; US05</td>
<td>Pedido pendiente ligado al folio y versión; disponibilidad consultada nuevamente. Vencida: rechazo y solicitud de revalidación.</td>
</tr>
<tr>
<td>CU04</td>
<td>Confirmar pedido de contado y reservar</td>
<td>Caja</td>
<td>Pedido, referencia de pago autorizado y ubicación de surtido</td>
<td>BN02; BR04/BR05; RNF02; US06/US09</td>
<td>Pedido confirmado y reserva como una operación. Pago rechazado o stock insuficiente: no confirma y no reserva.</td>
</tr>
<tr>
<td>CU05</td>
<td>Cancelar pedido antes del surtido</td>
<td>Vendedor con permiso de cancelación</td>
<td>Pedido y motivo</td>
<td>BN02; BR06/BR16; RNF03; US10</td>
<td>Pedido cancelado, reserva liberada y modificación auditada. Pedido surtido: rechazo.</td>
</tr>
</table>
### Límite de la demostración
La confirmación ejecutable es de contado y usa una ubicación por pedido. Esto delimita el prototipo, no cambia las reglas del negocio sobre surtido multiorigen, crédito o parciales. Las consultas sí devuelven las cuatro ubicaciones de demostración. Los datos, referencias de pago y actores del demo son simulados.
La vigencia de siete días proviene de un acuerdo simulado del BRD y se pasa como parámetro. La definición exacta del instante de vencimiento requiere validación: el código usa un intervalo que incluye emisión y excluye vencimiento. La moneda MXN del demo no constituye una política nueva; Dinero conserva explícitamente la moneda.
## 4 Comparación del patrón de lógica de negocio
<table fit-page-width="true" header-row="true">
<tr>
<td>Criterio</td>
<td>Transaction Script</td>
<td>Table Module</td>
<td>Domain Model</td>
<td>Evidencia</td>
</tr>
<tr>
<td>Cotizaciones con vigencia y versiones</td>
<td>Validaciones por procedimiento; riesgo de repetirlas en convertir y revalidar.</td>
<td>Organiza versiones como filas; invariantes por conjunto pueden quedar dispersas.</td>
<td>Cotizacion protege vigencia y produce otra versión sin borrar la anterior.</td>
<td>BR01–03; US03–05</td>
</tr>
<tr>
<td>Confirmación, inventario y concurrencia</td>
<td>Una transacción puede resolverlo, pero la coordinación y reglas tienden a mezclarse.</td>
<td>Procesamiento por tablas adecuado para lotes; debe reconstruir vínculos entre pedido y reservas.</td>
<td>Pedido e InventarioUbicacion protegen sus invariantes; UoW coordina su guardado.</td>
<td>BR04–06; RNF02; AC-US09-01/02</td>
</tr>
<tr>
<td>Estado y ciclo de vida</td>
<td>Cambios de estado repartidos entre scripts; exige disciplina para evitar caminos contradictorios.</td>
<td>Estados expresados en filas; comportamiento separado de conceptos del negocio.</td>
<td>Métodos confirmar y cancelar expresan transiciones permitidas y rechazos.</td>
<td>US06/US10/US15; BR05/BR06</td>
</tr>
<tr>
<td>Variantes comerciales</td>
<td>Cada variante añade condiciones a los procedimientos existentes.</td>
<td>Cambia módulos centrados en datos; puede ser útil si predominan operaciones por conjunto.</td>
<td>Políticas de crédito y devolución pueden evolucionar con contratos propios.</td>
<td>BR09–11/BR15; BN05/BN09</td>
</tr>
<tr>
<td>Costo para este equipo</td>
<td>Menor estructura inicial; apropiado si el caso se redujera a operaciones simples.</td>
<td>Costo intermedio; natural en aplicaciones organizadas alrededor de datasets.</td>
<td>Más clases, interfaces y revisión de límites; exige explicar responsabilidades y evitar clases sin comportamiento.</td>
<td>Guía U3; 16 reglas BR y excepciones documentadas</td>
</tr>
<tr>
<td>Consultas operativas</td>
<td>Consulta directa por procedimiento.</td>
<td>Buena afinidad con agregación y reportes por tablas.</td>
<td>Modelo de lectura independiente: no obliga a reconstruir agregados para cada consulta.</td>
<td>BN01/BN10; RNF01; CQRS básico</td>
</tr>
</table>
### Evaluación de Transaction Script
Transaction Script puede implementar correctamente las operaciones seleccionadas. Su ventaja es la estructura inicial sencilla: consultar, verificar condiciones, actualizar y devolver un resultado. También puede usar una transacción para evitar cambios parciales. Por lo tanto, se descarta como patrón principal por su costo de mantenimiento en este caso, no porque sea incapaz de proteger el inventario.
En FerreMax, la regla «una cotización no reserva» aparece en la emisión, la revalidación y la conversión; la disponibilidad se consulta y se comprueba otra vez al confirmar; la cancelación afecta pedido y reservas. Si cada procedimiento conserva sus propias validaciones, una corrección debe repetirse en varios lugares. Puede mantenerse coherente, pero requiere controles continuos para evitar divergencia. El riesgo crece con crédito excepcional, transferencias y parciales.
### Evaluación de Table Module
Table Module concentra comportamiento sobre conjuntos de registros y resulta razonable cuando la aplicación gira alrededor de datasets. Podría facilitar reportes operativos y procesamiento por ubicación. Su costo en FerreMax sería expresar el comportamiento de cotizaciones, pedidos y reservas mediante relaciones entre filas, mientras su ciclo de vida y reglas se distribuyen en módulos centrados en tablas.
La consulta global necesita una proyección eficiente, pero eso no obliga a usar Table Module como patrón de negocio. Se propone una consulta SQL de solo lectura para el DTO de disponibilidad. La separación entre un modelo de lectura y los agregados de escritura resuelve esa necesidad sin adoptar un segundo patrón principal artificial.
### Evaluación y selección de Domain Model
Domain Model permite ubicar la vigencia en Cotizacion, las transiciones en Pedido y el compromiso de cantidades en InventarioUbicacion. Las operaciones públicas expresan intenciones del negocio: revalidar, convertir, confirmar, reservar, liberar y cancelar. La identidad y el estado se conservan, y el servicio de aplicación coordina objetos que ya conocen sus reglas.
La decisión se apoya especialmente en BR01–03, BR04–06 y RNF02/AC-US09-02. Estas evidencias exigen conservar versiones, distinguir compromiso de compra de compromiso de inventario y proteger una última unidad frente a dos pedidos. La claridad de responsabilidades importa más que la cantidad de clases.
El costo aceptado es una estructura mayor: objetos, contratos, adaptadores y pruebas de colaboración. Se controla concentrando el desarrollo en cinco casos y evitando capas que no resuelvan una necesidad. Domain Model no sustituye las transacciones ni los bloqueos de PostgreSQL: las reglas se verifican sobre datos recuperados de manera consistente.
**Estado de la decisión:** propuesta técnicamente revisada; pendiente de defensa y validación humana del equipo. La preferencia por Python y PostgreSQL en Supabase sí fue confirmada por Roberto.
## 5 Mapa de dominio y lenguaje ubicuo
<table fit-page-width="true" header-row="true">
<tr>
<td>Aggregate</td>
<td>Raíz y contenido</td>
<td>Responsabilidades</td>
<td>Invariantes</td>
<td>Eventos</td>
<td>Estado del código</td>
</tr>
<tr>
<td>Cotizacion</td>
<td>Cotizacion; partidas y Vigencia</td>
<td>Revalidar; emitir versiones; validar conversión.</td>
<td>Tiene folio, versión, vigencia y estado; no reserva; vencida requiere revalidación.</td>
<td>CotizacionRevalidada; conversión origina PedidoCreado.</td>
<td>Implementado revalidar/convertir; emisión inicial es dato de demostración.</td>
</tr>
<tr>
<td>Pedido</td>
<td>Pedido; PartidaPedido y referencias de cotización</td>
<td>Confirmar, cancelar, conservar procedencia y aceptación.</td>
<td>Reserva ligada a pedido confirmado; cancelar antes del surtido libera; parcial requiere aceptación.</td>
<td>PedidoCreado, PedidoConfirmado, PedidoCancelado.</td>
<td>Contado y cancelación implementados; parciales y reducción modelados para extensión.</td>
</tr>
<tr>
<td>InventarioUbicacion</td>
<td>InventarioUbicacion; reservas por pedido</td>
<td>Reservar, liberar y calcular disponible por SKU y ubicación.</td>
<td>Disponible = física − comprometida; no negativo; tránsito no es stock utilizable en destino antes de recibir.</td>
<td>ReservaRegistrada/ReservaLiberada como candidatos; prototipo usa eventos de Pedido que describen la operación conjunta.</td>
<td>Implementado reserva/liberación; movimientos por transferencia diseñados.</td>
</tr>
<tr>
<td>CuentaCredito</td>
<td>CuentaCredito; condiciones y decisión excepcional</td>
<td>Evaluar condición normal y registrar excepción autorizada.</td>
<td>Cliente empresarial activo, sin bloqueo y con crédito suficiente; excepción requiere responsable y motivo.</td>
<td>CreditoEvaluado, ExcepcionCreditoResuelta.</td>
<td>Evaluación normal implementada como política de dominio; persistencia y autorización excepcional pendientes.</td>
</tr>
<tr>
<td>Transferencia</td>
<td>Transferencia; partidas y estados</td>
<td>Solicitar, autorizar/rechazar, despachar y recibir.</td>
<td>Origen, destino, responsable y estado obligatorios; recepción actualiza tránsito y destino con trazabilidad.</td>
<td>TransferenciaSolicitada, Despachada, Recibida o ConIncidencia.</td>
<td>Diseño de dominio; fuera del código detallado U3.</td>
</tr>
<tr>
<td>Entrega</td>
<td>Entrega; dirección, asignación y evidencia</td>
<td>Programar, registrar resultado e incidencia.</td>
<td>Salida requiere datos completos; cierre conserva receptor, fecha/hora y evidencia; incidencia no equivale a entregado.</td>
<td>EntregaProgramada, EntregaCompletada, IncidenciaEntregaRegistrada.</td>
<td>Diseño de dominio; sin optimización de rutas.</td>
</tr>
<tr>
<td>Devolucion</td>
<td>Devolucion; partidas y evaluación</td>
<td>Evaluar elegibilidad y registrar destino financiero y físico.</td>
<td>Comprobante, categoría, condición y política configurable; no inventar plazos o porcentajes.</td>
<td>DevolucionAutorizada o Rechazada.</td>
<td>Diseño de dominio; política exacta pendiente de FerreMax según BRD.</td>
</tr>
</table>
Los siete límites evitan que FerreMax se convierta en un único objeto gigante. Cada raíz protege sus propios cambios; las referencias a otras raíces se conservan por identidad. La transacción de confirmación coordina Pedido e InventarioUbicacion, pero no elimina sus límites conceptuales.
Producto, Categoria, Ubicacion y ClienteEmpresarial son conceptos con identidad del catálogo o datos maestros. SKU identifica el producto; no se convierte automáticamente en una entidad adicional. Las decisiones sobre repositorios de maestros quedan fuera del código detallado.
### Value Objects y entidades
**Value Objects:** SKU, Dinero, Vigencia y, en el diseño general, DireccionEntrega y evidencia estructurada del resultado. No tienen una identidad de negocio independiente de sus valores. Dinero conserva importe y moneda; Vigencia conserva emisión y vencimiento.
**Entidades:** las raíces anteriores, ClienteEmpresarial, Producto, Ubicacion, PartidaPedido y Reserva. Una partida se identifica dentro de su pedido y puede conservar cantidades solicitadas, surtidas y pendientes. El código mínimo usa un registro Partida inmutable con número local, SKU, cantidad y precio; los estados por partida del proceso completo quedan modelados y pendientes de implementación.
**Domain Services:** PoliticaCredito para evaluación normal y PoliticaSurtidoMultiorigen para priorizar ubicación local, almacén central y otras sucursales según BR07. PoliticaDevolucion evalúa categoría y condición cuando FerreMax defina sus parámetros. La última y la de surtido son propuestas de diseño, no clases ya ejecutables.
### Glosario actualizado
<table fit-page-width="true" header-row="true">
<tr>
<td>Término</td>
<td>Definición y responsabilidad</td>
</tr>
<tr>
<td>InventarioUbicacion</td>
<td>Estado del inventario de un SKU en una ubicación; raíz que controla sus reservas.</td>
</tr>
<tr>
<td>Reserva</td>
<td>Cantidad comprometida para un pedido confirmado; no equivale a cotización ni a existencia en tránsito.</td>
</tr>
<tr>
<td>Invariante</td>
<td>Condición del negocio que debe quedar verdadera al finalizar una operación válida.</td>
</tr>
<tr>
<td>Aggregate y raíz</td>
<td>Límite de consistencia y objeto por el que se solicitan sus modificaciones.</td>
</tr>
<tr>
<td>Evento de dominio</td>
<td>Hecho ocurrido y confirmado; por ejemplo PedidoConfirmado. No es una orden para confirmar.</td>
</tr>
<tr>
<td>Application Service</td>
<td>Coordina un caso de uso y solicita acciones al dominio; no decide todas las reglas.</td>
</tr>
<tr>
<td>Repository</td>
<td>Contrato para recuperar o guardar objetos del negocio; su implementación contiene SQL.</td>
</tr>
<tr>
<td>Unit of Work</td>
<td>Límite que confirma juntos los cambios de la operación o los revierte ante fallo.</td>
</tr>
<tr>
<td>Command</td>
<td>Intención de cambiar estado, con datos suficientes para la operación.</td>
</tr>
<tr>
<td>Query y DTO</td>
<td>Solicitud de solo lectura y estructura de respuesta apropiada para la consulta.</td>
</tr>
<tr>
<td>Outbox</td>
<td>Registro técnico del evento en la misma transacción; su publicación externa requiere un consumidor posterior.</td>
</tr>
<tr>
<td>ADR</td>
<td>Registro de una decisión, su contexto, alternativas, consecuencias y trazabilidad.</td>
</tr>
</table>
## 6 Service Layer
<table fit-page-width="true" header-row="true">
<tr>
<td>Servicio</td>
<td>Método</td>
<td>Entrada</td>
<td>Colaboradores</td>
<td>Salida</td>
<td>Reglas delegadas</td>
</tr>
<tr>
<td>CotizacionService</td>
<td>revalidar</td>
<td>Actor, ID, versión, vigencia, partidas, condiciones y motivo</td>
<td>UnitOfWork; CotizacionRepository; InventarioRepository; Cotizacion</td>
<td>Nueva versión y folio</td>
<td>BR01–03; validación de partidas y vigencia.</td>
</tr>
<tr>
<td>CotizacionService</td>
<td>convertir</td>
<td>Actor, ID, versión y aceptación</td>
<td>CotizacionRepository; InventarioRepository; PedidoRepository; Cotizacion</td>
<td>ID, estado, folio/versión y disponibilidad consultada</td>
<td>Vigencia y aceptación en Cotizacion; no reserva.</td>
</tr>
<tr>
<td>PedidoService</td>
<td>confirmar</td>
<td>Actor Caja, pedido, AutorizacionPago y ubicación</td>
<td>PedidoRepository; InventarioRepository; UnitOfWork; Pedido; InventarioUbicacion</td>
<td>ID, estado, referencia y ubicación</td>
<td>Pago y transición en Pedido; disponibilidad y reserva en InventarioUbicacion.</td>
</tr>
<tr>
<td>PedidoService</td>
<td>cancelar</td>
<td>Actor con permiso, pedido y motivo</td>
<td>PedidoRepository; InventarioRepository; UnitOfWork; Pedido</td>
<td>ID y estado</td>
<td>Estado y surtido en Pedido; liberación en InventarioUbicacion.</td>
</tr>
<tr>
<td>Handlers de consulta</td>
<td>handle</td>
<td>Actor y SKU o ID de pedido</td>
<td>DisponibilidadReader o PedidoReader</td>
<td>DTO independiente</td>
<td>Autorización de acceso; consultas de solo lectura.</td>
</tr>
</table>
El control de rol pertenece a la frontera de aplicación. El demo recibe un Actor suministrado por la composición de la prueba; todavía no verifica sesiones reales de usuarios. Los nombres de perfiles del prototipo ilustran permisos separados y deben traducirse a permisos nominales definidos por FerreMax, conforme a las restricciones del BRD.
El reloj y la fábrica de UnitOfWork se inyectan. Así, la vigencia se puede probar de forma determinista y la aplicación puede trabajar con memoria o PostgreSQL sin trasladar SQL al dominio.
## 7 Repository y Unit of Work
<table fit-page-width="true" header-row="true">
<tr>
<td>Contrato</td>
<td>Necesidad</td>
<td>Operaciones</td>
<td>Implementación</td>
</tr>
<tr>
<td>CotizacionRepository</td>
<td>Recuperar una versión exacta y conservar otra nueva</td>
<td>obtener; guardar_nueva_version</td>
<td>Tabla cotizacion_version; clave ID/versión; rechaza versión duplicada.</td>
</tr>
<tr>
<td>PedidoRepository</td>
<td>Recuperar y guardar el pedido</td>
<td>obtener; guardar</td>
<td>Tabla pedido; lectura para actualización con bloqueo de la fila.</td>
</tr>
<tr>
<td>InventarioRepository</td>
<td>Recuperar inventario consistente y sus reservas</td>
<td>obtener_para_actualizar; guardar; ubicacion_reserva</td>
<td>Inventario por SKU/ubicación y reservas; bloqueo del padre y actualización conjunta.</td>
</tr>
<tr>
<td>DisponibilidadReader</td>
<td>Información global sin materializar agregados</td>
<td>consultar_disponibilidad</td>
<td>SELECT parametrizado; devuelve cuatro cantidades por ubicación.</td>
</tr>
<tr>
<td>PedidoReader</td>
<td>Resumen apropiado para lectura</td>
<td>consultar_pedido</td>
<td>Proyección de ID, estado, cotización y total.</td>
</tr>
</table>
Los contratos se definen en application/[ports.py](http://ports.py) y hablan en términos del dominio. Su ubicación es un límite de dependencias de la aplicación; el modelo de negocio no importa las implementaciones. PostgreSQL y Memory cumplen los contratos; el ensayo real debe verificar esa sustitución.
### Transacción de confirmación
1. La aplicación comprueba el rol y abre UnitOfWork.
2. Recupera el pedido para actualización.
3. Recupera las filas de inventario involucradas con FOR UPDATE en un orden uniforme por SKU.
4. Pedido valida el pago y cambia provisionalmente a Confirmado.
5. Cada InventarioUbicacion verifica disponible y registra la reserva.
6. Guarda pedido y reservas, auditoría y evento en outbox.
7. Hace COMMIT; solo entonces devuelve el resultado confirmado.
8. Si cualquiera de esos pasos falla, hace ROLLBACK y no devuelve confirmación.
La fila de inventario bloqueada evita que dos transacciones decidan sobre la misma última unidad a partir de valores incompatibles. Los bloqueos se toman siempre en orden consistente; no se prometen objetivos de rendimiento sin medirlos. La lectura de disponibilidad es informativa y puede cambiar antes de la confirmación.
La cancelación aplica la misma unidad transaccional para cambiar el estado y liberar todas las reservas incluidas. La revalidación agrega una versión y su auditoría sin reservar stock. Cada consulta de lectura usa una transacción de solo lectura.
### Eventos y auditoría
La outbox conserva el evento dentro de la transacción del negocio; un fallo no deja un evento de confirmación persistido para una operación revertida. El código no incluye aún un consumidor externo: no afirma haber enviado notificaciones.
La auditoría guarda actor, momento, acción, valores anterior/nuevo y motivo. La aplicación dispone de INSERT y SELECT, pero no UPDATE ni DELETE sobre esa tabla. Esto protege frente al usuario operativo; no pretende impedir la administración legítima de la base por su propietario.
## 8 CQRS básico
<table fit-page-width="true" header-row="true">
<tr>
<td>Tipo</td>
<td>Operación</td>
<td>Handler</td>
<td>Dependencias</td>
<td>Resultado</td>
</tr>
<tr>
<td>Command</td>
<td>ConfirmarPedido</td>
<td>ConfirmarPedidoHandler</td>
<td>PedidoService; UoW; repositorios de pedido e inventario</td>
<td>Confirmación y reserva, o error de negocio.</td>
</tr>
<tr>
<td>Command</td>
<td>CancelarPedido</td>
<td>CancelarPedidoHandler</td>
<td>PedidoService; UoW; repositorios de pedido e inventario</td>
<td>Cancelación y liberación, o rechazo.</td>
</tr>
<tr>
<td>Query</td>
<td>ConsultarDisponibilidad</td>
<td>ConsultarDisponibilidadHandler</td>
<td>DisponibilidadReader</td>
<td>SKU, encontrado y lista de ubicaciones con cantidades.</td>
</tr>
<tr>
<td>Query</td>
<td>ConsultarPedido</td>
<td>ConsultarPedidoHandler</td>
<td>PedidoReader</td>
<td>ID, estado, folio/versión de cotización, total y moneda.</td>
</tr>
</table>
Se conserva una sola base PostgreSQL. Los DTO son estructuras de lectura y no se usan para modificar automáticamente entidades. Los comandos delegan al servicio para conservar un único recorrido de reglas y transacción; no duplican la lógica en el handler.
La emisión y revalidación pueden exponerse inicialmente como métodos del servicio. No es necesario añadir handlers idénticos solo para incrementar clases. La separación obligatoria queda demostrada con los dos comandos y las dos consultas seleccionados.
## 9 Revisión SOLID
<table fit-page-width="true" header-row="true">
<tr>
<td>Principio</td>
<td>Evidencia</td>
<td>Impacto</td>
<td>Cambio o control</td>
</tr>
<tr>
<td>S</td>
<td>Las reglas de vigencia y reserva están en Cotizacion e InventarioUbicacion; el servicio coordina.</td>
<td>Mezclarlas con SQL haría cambiar el servicio por políticas y por almacenamiento.</td>
<td>Separar [model.py](http://model.py), [services.py](http://services.py) y [postgres.py](http://postgres.py); mover ubicacion_reserva al repositorio de inventario.</td>
</tr>
<tr>
<td>O</td>
<td>PoliticaCredito expresa evaluación normal; devolución y surtido tienen variaciones pendientes.</td>
<td>Una cadena creciente de condiciones mezclaría políticas distintas.</td>
<td>Mantener políticas separadas; añadir implementaciones solo cuando haya variantes justificadas, sin inventar categorías.</td>
</tr>
<tr>
<td>L</td>
<td>Repositorios Memory y PostgreSQL ofrecen operaciones equivalentes y rechazos de negocio.</td>
<td>Una implementación que pierde versiones o permite reservas duplicadas rompería el contrato.</td>
<td>Conservar versiones, rechazar SKU inexistente y aplicar rollback. Prueba de contrato PostgreSQL pendiente de conexión.</td>
</tr>
<tr>
<td>I</td>
<td>DisponibilidadReader y PedidoReader no obligan a una consulta a guardar o eliminar.</td>
<td>Una interfaz universal expondría métodos irrelevantes al lado lector.</td>
<td>Contratos pequeños para consultas y repositorios especializados por agregado.</td>
</tr>
<tr>
<td>D</td>
<td>Servicios reciben una fábrica UnitOfWork y un reloj; el dominio no importa SQL ni Psycopg.</td>
<td>Dependencia directa del backend impediría revisar el dominio sin una conexión.</td>
<td>Adaptadores PostgreSQL y Memory; consultas parametrizadas y composición externa de dependencias.</td>
</tr>
</table>
## 10 Persistencia PostgreSQL en Supabase
La decisión tecnológica conserva las responsabilidades anteriores. Supabase aloja PostgreSQL y aporta administración del proyecto. La aplicación Python utiliza una conexión PostgreSQL para coordinar las transacciones de UnitOfWork.
Se propone el esquema privado ferremax_u3, con cotizacion_version, pedido, inventario, reserva, auditoria y outbox. Las claves y relaciones reflejan el prototipo; los agregados no se deducen mecánicamente de esas seis tablas. Las versiones se insertan y se conservan; las reservas referencian pedido e inventario.
El esquema no se expone a anon ni authenticated de la Data API. Se habilita RLS y se concede acceso al grupo de backend confiable. La conexión de aplicación debe usar un usuario con ese rol y privilegios limitados; la conexión administrativa se utiliza para preparar el esquema. La contraseña nunca pertenece al repositorio.
**Estado:** Roberto eligió un proyecto nuevo en Santana’s Org. La creación está pendiente porque get_cost no está disponible en la conexión actual. No se asumió un importe ni se activó un servicio de pago. También está pendiente el ensayo con conexiones reales; los resultados de Memory no se presentan como resultados de Supabase.
## 11 Validación y resultados
El núcleo final ejecutó 20 pruebas locales correctamente: rechazo de cotización vencida; conservación de versiones; aceptación obligatoria; confirmación con reserva, auditoría y evento; pago rechazado; reversión de todas las partidas al fallar una; acumulación de partidas con el mismo SKU; dos pedidos para una última unidad; liberación por cancelación; rechazo de cancelación después del surtido; consulta sin cambios; control de rol; evaluación de crédito; distinción entre tránsito y disponible; valores inválidos.
La prueba de competencia en Memory usa un bloqueo de proceso. Se corrigió el fixture a ZZ-SIN-STOCK y se agregó una observación que confirma el guardado provisional de SKU-DEMO antes del fallo. Luego se comprueba la reversión completa. Las 20 pruebas locales pasaron; una prueba PostgreSQL fue omitida por falta de TEST_DATABASE_URL. Falta ejecutar la prueba PostgreSQL con conexiones separadas para verificar los bloqueos de la base y la sustitución del adaptador.
<table fit-page-width="true" header-row="true">
<tr>
<td>Control</td>
<td>Resultado</td>
</tr>
<tr>
<td>Trazabilidad de los cinco casos</td>
<td>Relacionados con BN, BR, US y escenarios existentes.</td>
</tr>
<tr>
<td>Lenguaje</td>
<td>Términos del glosario conservados; vocabulario técnico añadido con definición.</td>
</tr>
<tr>
<td>Responsabilidad</td>
<td>Reglas en dominio; coordinación en servicios; SQL en infraestructura.</td>
</tr>
<tr>
<td>Atomicidad local</td>
<td>Probada la reversión del pedido y de una primera reserva guardada provisionalmente antes del fallo de otra partida.</td>
</tr>
<tr>
<td>Persistencia PostgreSQL</td>
<td>Adaptador preparado; prueba conectada pendiente.</td>
</tr>
<tr>
<td>Diagramas</td>
<td>Cinco fuentes Mermaid y vistas vectoriales SVG, PDF y PNG. BPMN de U2 verificado; hallazgo H07 documentado.</td>
</tr>
<tr>
<td>IA</td>
<td>Iteraciones y correcciones registradas; revisión técnica IA diferenciada de revisión humana.</td>
</tr>
<tr>
<td>Rendimiento RNF01</td>
<td>Objetivos conservados; no medidos ni declarados cumplidos.</td>
</tr>
<tr>
<td>Paquete y GitHub</td>
<td>Informe FIME y paquete preparados; publicación en GitHub pendiente de disponibilidad de la conexión.</td>
</tr>
</table>
## 12 Conclusiones propuestas para revisión del equipo
La arquitectura conecta las necesidades de FerreMax con componentes concretos: Cotizacion conserva vigencia y versiones; Pedido expresa confirmación y cancelación; InventarioUbicacion protege la disponibilidad. La Service Layer coordina esos componentes y el Unit of Work evita que una confirmación quede guardada sin las reservas correspondientes.
Domain Model se propone por la interacción entre reglas y estados, y acepta como costo una estructura mayor que Transaction Script. CQRS se mantiene básico, con una sola base y modelos de lectura propios. PostgreSQL en Supabase permite continuar el proyecto y revisar persistencia compartida, aunque añade configuración y requiere validar sus transacciones de forma real.
La prueba del diseño incluye también los rechazos. La cotización vencida, el pago rechazado y la disponibilidad insuficiente deben tener resultados comprensibles y conservar un estado coherente. Los procesos no implementados y las políticas pendientes se identifican expresamente para mantener la continuidad con U2.
Estas conclusiones son un borrador propuesto por IA. Roberto e Isaías deben revisarlas y explicar las decisiones con sus propias palabras antes de entregar; no se registra como realizada una defensa que todavía no ocurrió.
## 13 Referencias
Gómez Marroquín, M. Á. (2026). Clases de Componentes de lógica de negocio de 9 y 14 de septiembre. Material del curso y apuntes corroborados en Notion.
Equipo 17. (2026). FerreMax: BRD, User Stories, Glosario y BPMN. Documentos de Unidad 2 corregidos.
Guía de trabajo para alumnos. (2026). Diseño arquitectural del sistema con IA. Actividad de Unidad 3.
Fowler, M. (s. f.). Patterns of Enterprise Application Architecture. [Catálogo](https://martinfowler.com/eaaCatalog/).
Supabase. (s. f.). [Database](https://supabase.com/docs/guides/database/overview) y [Connect to your database](https://supabase.com/docs/guides/database/connecting-to-postgres). Consulta: 2026-10-14.
PostgreSQL Global Development Group. (s. f.). [Explicit locking](https://www.postgresql.org/docs/current/explicit-locking.html).
Microsoft. (s. f.). [CQRS pattern](https://learn.microsoft.com/en-us/azure/architecture/patterns/cqrs).