## Estado y autoría
Los ADR distinguen decisiones confirmadas por Roberto, propuestas de diseño y partes pendientes. Isaías y Roberto deben revisarlos para la defensa. La bitácora registra interacciones reales y revisiones técnicas internas; no inventa una revisión humana ni sesiones anteriores.
## ADR001 Domain Model como patrón principal
**Estado:** Propuesta para revisión del equipo.
### Contexto
Las cotizaciones conservan versiones y vigencia; el pedido cambia de estado; inventario y reservas deben mantenerse consistentes. Esas reglas reaparecen en varios casos de uso.
### Alternativas
Transaction Script ofrece menor estructura inicial, con riesgo de duplicar reglas. Table Module organiza conjuntos de datos, pero coloca el ciclo de vida del pedido fuera de los objetos que representan el negocio. Domain Model encapsula reglas y conserva identidad y comportamiento.
### Decisión
Proponer Domain Model en la escritura y consultas SQL con DTO propios en la lectura. No clasificar cualquier SELECT como Table Module ni introducir una combinación de patrones sin delimitarla.
### Consecuencias
Beneficio: responsabilidades visibles y reglas reutilizables. Costo: más objetos, contratos y validación de límites. Riesgo: clases anémicas o servicios que absorban el dominio. Control: métodos de negocio y cinco hallazgos SOLID.
### Trazabilidad
BN02/BN03; BR01–06; RNF02; US04/US05/US09/US10; CU02–CU05.
## ADR002 Python y PostgreSQL alojado en Supabase
**Estado:** Tecnología y organización confirmadas por Roberto; proyecto aún no creado.
### Contexto
El profesor permite elegir tecnología. Roberto propuso PostgreSQL en Supabase y autorizó continuar con esa opción; eligió Santana’s Org para un proyecto nuevo.
### Alternativas
SQLite simplifica una demostración local. PostgreSQL local conserva las funciones del motor pero requiere instalación/operación. Supabase aloja PostgreSQL y permite administración y persistencia compartida.
### Decisión
Python organiza el dominio y la aplicación. Un adaptador PostgreSQL conserva transacciones y repositorios. Supabase se utiliza inicialmente para alojar la base; se conserva una única base de lectura y escritura.
### Consecuencias
Beneficio: práctica con persistencia compartida y transacciones de PostgreSQL. Costo: conexión, permisos, dependencias y aprovisionamiento. El costo de creación debe verificarse antes de activar un proyecto; no se asume que una organización sea gratuita. No hay proyecto activo de FerreMax ni pruebas conectadas reportadas.
### Trazabilidad
RNF02/03/04/08; BR04/05/16; CU04/CU05; conversación de decisión tecnológica y Release.
## ADR003 Unit of Work para confirmación y reserva
**Estado:** Propuesta implementada y revisada con Memory; validación PostgreSQL pendiente.
### Contexto
AC-US09-01 exige reserva atómica y AC-US09-02 impide asignar la última unidad a dos pedidos. Guardar el estado del pedido separado de la reserva puede producir confirmaciones incoherentes.
### Alternativas
Guardar por separado introduce cambios parciales. Coordinar con consistencia eventual añade recuperación y estados de compensación aún no definidos. Una transacción local puede proteger los cambios requeridos en una misma base.
### Decisión
El servicio abre UoW, bloquea pedido e inventarios en orden, invoca al dominio, guarda pedido/reservas/auditoría/outbox y confirma una sola transacción. Ante error, revierte la operación completa.
### Consecuencias
Beneficio: confirmación y compromiso de inventario quedan juntos. Costo: retención breve de bloqueos y manejo de contención. La transacción abarca más de un agregado sin convertirlos en una sola raíz. Las conexiones y los bloqueos reales necesitan ensayo PostgreSQL; RNF01 no se declara cumplido sin medirlo.
### Trazabilidad
BN02; BR04–06/BR16; RNF02/RNF04; AC-US06-01/02; AC-US09-01/02; CU04/CU05.
## ADR004 CQRS básico sobre una sola base
**Estado:** Propuesta implementada en comandos y consultas seleccionados.
### Contexto
La consulta global debe distinguir física, comprometida, tránsito y disponible. Confirmar y cancelar cambian estado y exigen validaciones diferentes a una consulta.
### Alternativas
Un modelo único para pantallas y escritura simplifica estructuras pero puede permitir modificaciones involuntarias. Bases separadas exigirían sincronización y operación adicional. Separar handlers y modelos conservando PostgreSQL resuelve la necesidad actual.
### Decisión
ConfirmarPedido y CancelarPedido son Commands. ConsultarDisponibilidad y ConsultarPedido son Queries con contratos de lectura y DTO propios. Los commands delegan a la Service Layer; una consulta no recibe métodos para guardar.
### Consecuencias
Beneficio: intención explícita y lectores pequeños. Costo: DTO y handlers adicionales. No implica Event Sourcing, réplicas ni dos bases. La separación se aplica donde aporta claridad y no obliga a crear un handler decorativo por cada método.
### Trazabilidad
BN01/BN02; BR04–06; RNF01/RNF06; US01/US02/US09/US10; CU01/CU04/CU05.
## ADR005 Auditoría y outbox junto con el cambio de negocio
**Estado:** Propuesta implementada como registro; consumidor externo pendiente.
### Contexto
BR16 y RNF04 exigen quién, cuándo, qué cambió y por qué. Publicar un evento antes del COMMIT puede comunicar una confirmación que posteriormente falla.
### Alternativas
Auditar/publicar por separado puede perder registros o emitir hechos no confirmados. Añadir un intermediario de mensajes externo aumenta trabajo sin un consumidor definido. Guardar auditoría y evento junto con el cambio permite conservar evidencia coherente.
### Decisión
Registrar auditoría y evento en la misma transacción. El backend operativo tiene permiso de insertar y leer auditoría, sin actualizarla ni borrarla. Una outbox técnica conserva eventos pendientes para un consumidor posterior.
### Consecuencias
Beneficio: coherencia entre cambio y evidencia. Costo: tabla adicional y necesidad futura de publicación/idempotencia. El prototipo registra eventos, pero no afirma entregar notificaciones ni garantizar exactamente una entrega externa.
### Trazabilidad
BN10; BR16; RNF04; CA-US20-01; CU02–CU05.
## Matriz de trazabilidad por necesidad
<table fit-page-width="true" header-row="true">
<tr>
<td>Necesidad</td>
<td>Reglas y RNF</td>
<td>Historias</td>
<td>Caso o alcance</td>
<td>Componentes</td>
<td>Decisiones</td>
<td>Cobertura</td>
</tr>
<tr>
<td>BN01</td>
<td>BR04; RNF01</td>
<td>US01/US02</td>
<td>CU01</td>
<td>ConsultarDisponibilidadHandler; DisponibilidadReader</td>
<td>ADR004</td>
<td>Consulta implementada; objetivo temporal sin medir.</td>
</tr>
<tr>
<td>BN02</td>
<td>BR04–06; RNF02</td>
<td>US09/US10</td>
<td>CU04/CU05</td>
<td>Pedido; InventarioUbicacion; UnitOfWork</td>
<td>ADR001/003</td>
<td>Reserva y liberación de contado en una ubicación.</td>
</tr>
<tr>
<td>BN03</td>
<td>BR01–03; RNF08</td>
<td>US03–05</td>
<td>CU02/CU03</td>
<td>Cotizacion; CotizacionService; CotizacionRepository</td>
<td>ADR001</td>
<td>Revalidación y conversión implementadas; emisión inicial simulada.</td>
</tr>
<tr>
<td>BN04</td>
<td>BR07/08</td>
<td>US05/US11/US14/US15</td>
<td>CU04 más diseño general</td>
<td>Pedido; PoliticaSurtidoMultiorigen; Transferencia</td>
<td>ADR001/003</td>
<td>Multiorigen y surtido diseñados; prototipo local.</td>
</tr>
<tr>
<td>BN05</td>
<td>BR09–11</td>
<td>US07/US08</td>
<td>Diseño comercial</td>
<td>CuentaCredito; PoliticaCredito</td>
<td>ADR001</td>
<td>Evaluación normal probada; excepciones y persistencia pendientes.</td>
</tr>
<tr>
<td>BN06</td>
<td>BR12/13</td>
<td>US11–13</td>
<td>Diseño logístico</td>
<td>Transferencia; InventarioUbicacion</td>
<td>ADR001/003</td>
<td>Mapeado; sin flujo ejecutable de transferencia.</td>
</tr>
<tr>
<td>BN07</td>
<td>BR08</td>
<td>US14</td>
<td>Diseño comercial</td>
<td>Pedido; PartidaPedido; aceptación del cliente</td>
<td>ADR001</td>
<td>Mapeado; sin aplicación ejecutable de parciales.</td>
</tr>
<tr>
<td>BN08</td>
<td>BR14; RNF07</td>
<td>US16/US17</td>
<td>Diseño logístico</td>
<td>Entrega; DireccionEntrega; EvidenciaEntrega</td>
<td>ADR001</td>
<td>Mapeado; sin programación de unidad ni captura operativa.</td>
</tr>
<tr>
<td>BN09</td>
<td>BR15; RNF08</td>
<td>US18</td>
<td>Diseño de postventa</td>
<td>Devolucion; PoliticaDevolucion; Categoria</td>
<td>ADR001</td>
<td>Política exacta pendiente del negocio.</td>
</tr>
<tr>
<td>BN10</td>
<td>BR16; RNF04</td>
<td>US19/US20</td>
<td>CU02–CU05 y diseño de panel</td>
<td>Auditoria; Outbox; DTO de reportes</td>
<td>ADR005</td>
<td>Auditoría local implementada; panel completo pendiente.</td>
</tr>
</table>
## Matriz de trazabilidad por regla
<table fit-page-width="true" header-row="true">
<tr>
<td>Regla</td>
<td>Escenarios U2</td>
<td>Caso o alcance</td>
<td>Componente responsable</td>
<td>Evidencia o límite</td>
</tr>
<tr>
<td>BR01</td>
<td>US03/US04/US05</td>
<td>CU02/CU03</td>
<td>CotizacionService</td>
<td>No llama reservar durante revalidación/conversión; prueba sin stock comprometido.</td>
</tr>
<tr>
<td>BR02</td>
<td>US03/US04</td>
<td>CU02/CU03</td>
<td>Cotizacion; CotizacionRepository</td>
<td>Folio, versión y vigencia conservados; estado vigente se deriva de Vigencia.</td>
</tr>
<tr>
<td>BR03</td>
<td>AC-US04-01/02</td>
<td>CU02/CU03</td>
<td>Cotizacion.convertir/revalidar</td>
<td>Vencida rechazada; versión anterior conservada.</td>
</tr>
<tr>
<td>BR04</td>
<td>US02; AC-US09-01</td>
<td>CU01/CU04</td>
<td>InventarioUbicacion.disponible</td>
<td>Física menos reservas; tránsito informado por separado.</td>
</tr>
<tr>
<td>BR05</td>
<td>US06; AC-US09-01</td>
<td>CU04</td>
<td>Pedido.confirmar; InventarioUbicacion.reservar</td>
<td>Dominio exige confirmado; UoW guarda estado y reserva juntos.</td>
</tr>
<tr>
<td>BR06</td>
<td>AC-US10-01</td>
<td>CU05</td>
<td>Pedido.cancelar; InventarioUbicacion.liberar</td>
<td>Cancelación antes de surtido libera; reducción es variante futura.</td>
</tr>
<tr>
<td>BR07</td>
<td>US01/US11</td>
<td>Diseño general</td>
<td>PoliticaSurtidoMultiorigen</td>
<td>Prioridad local, almacén, otras sucursales; prototipo no implementa esta selección.</td>
</tr>
<tr>
<td>BR08</td>
<td>AC-US14-01/02</td>
<td>Diseño general</td>
<td>Pedido y PartidaPedido</td>
<td>Aceptación explícita para parciales; no usar excepción de stock como consentimiento.</td>
</tr>
<tr>
<td>BR09</td>
<td>AC-US07-01</td>
<td>Diseño general</td>
<td>CuentaCredito.evaluar</td>
<td>Activo es condición de autorización normal.</td>
</tr>
<tr>
<td>BR10</td>
<td>AC-US07-01/02</td>
<td>Diseño general</td>
<td>PoliticaCredito</td>
<td>Bloqueo o insuficiencia devuelven EnRevision.</td>
</tr>
<tr>
<td>BR11</td>
<td>AC-US08-01/02</td>
<td>Diseño general</td>
<td>CuentaCredito y decisión excepcional</td>
<td>Motivo, responsable, fecha y condición requeridos; no inventar umbrales de excepción.</td>
</tr>
<tr>
<td>BR12</td>
<td>AC-US11-01; US12</td>
<td>Diseño logístico</td>
<td>Transferencia</td>
<td>Origen, destino, partidas, responsable y estado.</td>
</tr>
<tr>
<td>BR13</td>
<td>AC-US13-01/02</td>
<td>Diseño logístico</td>
<td>Transferencia e InventarioUbicacion</td>
<td>Recepción actualiza tránsito/destino; diferencia se conserva como incidencia.</td>
</tr>
<tr>
<td>BR14</td>
<td>AC-US17-01/02</td>
<td>Diseño logístico</td>
<td>Entrega</td>
<td>Evidencia de receptor y resultado; incidencia no cierra como entregado.</td>
</tr>
<tr>
<td>BR15</td>
<td>CA-US18-01</td>
<td>Diseño postventa</td>
<td>Devolucion y PoliticaDevolucion</td>
<td>Evaluación por categoría/condición y política pendiente.</td>
</tr>
<tr>
<td>BR16</td>
<td>CA-US20-01</td>
<td>CU02–CU05</td>
<td>UnitOfWork.registrar; auditoria</td>
<td>Valores anteriores/nuevos, actor, fecha y motivo dentro de la transacción.</td>
</tr>
</table>
## Trazabilidad de los rechazos
<table fit-page-width="true" header-row="true">
<tr>
<td>Escenario</td>
<td>Entrada o situación</td>
<td>Resultado y comprobación</td>
</tr>
<tr>
<td>AC-US04-01</td>
<td>Cotización fuera de vigencia</td>
<td>CotizacionVencida; no crea pedido.</td>
</tr>
<tr>
<td>AC-US06-02</td>
<td>Pago rechazado</td>
<td>Pedido sigue Pendiente; sin reserva ni evento de confirmación.</td>
</tr>
<tr>
<td>AC-US09-02</td>
<td>Dos pedidos intentan la última unidad</td>
<td>Uno confirma; otro recibe DisponibilidadInsuficiente. Memory probado; PostgreSQL pendiente.</td>
</tr>
<tr>
<td>AC-US10-01</td>
<td>Cancelación autorizada antes del surtido</td>
<td>Estado Cancelado y stock disponible restituido.</td>
</tr>
<tr>
<td>AC-US01-02 propuesto</td>
<td>SKU inexistente</td>
<td>encontrado falso y lista vacía; ID original repetido registrado en H01.</td>
</tr>
</table>
## Bitácora de IA
<table fit-page-width="true" header-row="true">
<tr>
<td>Iteración</td>
<td>Objetivo</td>
<td>Prompt o interacción real</td>
<td>Respuesta útil</td>
<td>Error o supuesto detectado</td>
<td>Decisión y autor</td>
</tr>
<tr>
<td>IA01</td>
<td>Entender la guía</td>
<td>Solicitud real de Roberto: revisar Word, captura y cuatro PDFs; comunicar dudas antes de resolver.</td>
<td>Resumen de nueve etapas y mínimos; propuesta de proceso.</td>
<td>BPMN visual no disponible; ID repetido y OB01/CE01 incongruentes.</td>
<td>Roberto informó que no hay repo, hay libertad tecnológica y revisión el viernes. No implica aprobación de cada clase.</td>
</tr>
<tr>
<td>IA02</td>
<td>Elegir persistencia</td>
<td>Propuesta inicial Python/SQLite; pregunta real de Roberto sobre Supabase PostgreSQL.</td>
<td>Comparación de preparación, trabajo compartido y concurrencia; propuesta Python/PostgreSQL.</td>
<td>SQLite se había propuesto por simplicidad; no se había provisionado una base.</td>
<td>Roberto dio Release tras la propuesta Supabase y después eligió Santana’s Org.</td>
</tr>
<tr>
<td>IA03</td>
<td>Revisar límites del código</td>
<td>Revisión técnica interna de la implementación por IA; no se atribuye al equipo un prompt que no escribió.</td>
<td>Interfaces pequeñas, entidades con reglas y adaptadores.</td>
<td>ubicacion_reserva estaba en el UoW y debía estar en InventarioRepository.</td>
<td>IA corrigió contrato, adaptador Memory y llamada del servicio; revisión humana pendiente.</td>
</tr>
<tr>
<td>IA04</td>
<td>Revisar concurrencia y consistencia</td>
<td>Revisión técnica interna de revalidación y confirmación.</td>
<td>Orden uniforme por SKU y agregación de partidas del mismo producto.</td>
<td>Revalidación podía obtener bloqueos según orden de entrada, diferente al de confirmar.</td>
<td>IA ordenó lecturas y probó duplicados de SKU y competencia por última unidad.</td>
</tr>
<tr>
<td>IA05</td>
<td>Comprobar comportamiento</td>
<td>Ejecución real: PYTHONPATH=src python3 -m unittest discover -s tests -v.</td>
<td>15 pruebas locales correctas, incluyendo rollback y liberación.</td>
<td>La prueba Memory serializa con RLock; no certifica los bloqueos PostgreSQL.</td>
<td>Resultado conservado; integración PostgreSQL identificada por separado como pendiente.</td>
</tr>
<tr>
<td>IA06</td>
<td>Conservar evidencia ante interrupción</td>
<td>Continuación autorizada por Release; comprobación de acceso tras cierre de conexión local.</td>
<td>Documentación, diagramas y decisiones conservados en borrador privado de Notion.</td>
<td>Conexión Mac cerrada; get_cost no disponible; no se completaron PDF, GitHub ni Supabase.</td>
<td>IA continuó la documentación; no declaró creados recursos ni aprobada la arquitectura por ambos integrantes.</td>
</tr>
</table>
## Registro de revisión humana pendiente
Confirmar o corregir ADR001 y los límites de agregados; aclarar H02 y H05 sin añadir políticas no documentadas; cotejar los diagramas con el BPMN visible; registrar una revisión real de Isaías y Roberto antes de la entrega. Cuando ocurra, añadir fecha, decisión concreta y versión resultante. No rellenar ese registro retrospectivamente como si ya se hubiera realizado.
## Iteraciones posteriores verificadas
**IA07:** se fortaleció la prueba de dos partidas: faltante ZZ-SIN-STOCK y observación del guardado provisional de SKU-DEMO. El ensayo de rollback pasó.
**IA08:** se revisó visualmente BPMN y se registró H07 sobre reserva previa a autorización.
**IA09:** se reconstruyó el código en cloud, se agregó estado calculado de cotización y auditoría detallada. Pasaron 20 pruebas locales; se omitió una integración PostgreSQL por falta de conexión. El entorno se desconectó antes de confirmar generación de PDFs y empaquetado.
## Cierre de generación y revisión
**IA10:** Tras recuperar el entorno se ejecutaron 21 pruebas: 20 correctas y una PostgreSQL omitida por falta de TEST_DATABASE_URL. Se generaron el informe FIME, la guía y cinco diagramas con fuentes y exportaciones; se revisaron visualmente y se preparó el paquete. La creación del proyecto Supabase sigue bloqueada porque get_cost no está disponible. GitHub requiere una sesión de navegador para crear el repositorio; no se registra publicación ni defensa humana como realizadas.

## Adaptación del informe al formato de la guía
**IA11:** Roberto pidió conservar el formato de la guía práctica y retirar las instrucciones del profesor. Se usó el Word original como plantilla y se generó el informe de FerreMax con su portada, tipografía, encabezados y tablas. Se eliminaron las instrucciones al alumno, la rúbrica, los ejemplos de otras empresas y la etiqueta Cisco Confidential. Los documentos originales permanecen sin cambios. Se solicitó publicar el proyecto en GitHub; la publicación se verifica por separado.
