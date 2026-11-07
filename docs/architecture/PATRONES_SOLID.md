# Patrones y aplicación de SOLID - FerreMax PIA

Las decisiones siguientes se justifican por el código actual y los casos de FerreMax. Las pruebas funcionales apoyan el diseño, pero no constituyen una certificación automática de SOLID. [Los ADRs](DECISIONES.md) registran alternativas y consecuencias.

## Patrones utilizados

| Patrón | Problema que resuelve | Aplicación concreta | Evidencia y costo |
| --- | --- | --- | --- |
| Domain Model | Vigencia, estado y disponibilidad reaparecen en varias operaciones | `Cotizacion`, `Pedido`, `InventarioUbicacion` y valores en `domain/model.py` | Pruebas de dominio/E9 y API; agrega objetos y exige cuidar encapsulación de colecciones públicas. |
| Service Layer | Coordinar roles, transacción y colaboradores sin introducir HTTP en el dominio | `CotizacionService`, `PedidoService` | Mismos servicios usados con Memory/PostgreSQL; coordina más de un agregado en una transacción local. |
| Repository | Recuperar/guardar agregados sin SQL dentro del caso de uso | Protocols y adaptadores Memory/Pg de cotizaciones, pedidos e inventarios | Integración PostgreSQL y pruebas de servicios; la interfaz debe conservar semántica de errores y bloqueos. |
| Unit of Work | Confirmar estado y reserva, o cancelar/liberar, de manera atómica | `PostgresUnitOfWork` y `MemoryUnitOfWork` | Segunda partida fallida revierte; añade conexiones, límites de transacción y contención. |
| CQRS básico | Separar consultas de comandos con responsabilidades y DTO distintos | Cuatro mensajes/handlers en `cqrs.py`; `DisponibilidadReader` y `PedidoReader` | Consultas no escriben; misma base, sin Event Sourcing ni réplica de lectura. Revalidar/convertir usan servicio directamente. |
| Specification | Nombrar y componer condiciones de elegibilidad puras | Vigencia AND aceptación antes de convertir | `test_specifications.py` prueba AND/OR/NOT, fronteras y ausencia de cambios; solo AND compone la regla comercial actual. |
| Máquina de estados | Restringir cambios de ciclo de vida | Enum y guardas en `Pedido.confirmar/cancelar` | Tabla de tres estados × dos acciones. Es una máquina explícita; no se afirma una jerarquía de clases del patrón GoF State. |
| Registro outbox transaccional | Conservar el hecho de negocio junto a su cambio | `UnitOfWork.registrar` escribe auditoría y `EventoDominio` en outbox | No hay publicador/consumidor ni garantía de entrega externa; ese trabajo sigue pendiente. |

## Principios SOLID con ejemplos reales

| Principio | Cómo se demuestra aquí | Referencia concreta | Límite reconocido |
| --- | --- | --- | --- |
| S - responsabilidad única | El dominio determina validez; el servicio coordina; el adaptador persiste; la API traduce a HTTP | `Pedido.confirmar`, `PedidoService.confirmar`, `PgInventarios.guardar`, `api/pedidos.py` | Los archivos agrupan varias clases; el principio se evalúa por responsabilidades, no por número de archivos. El servicio también arma snapshots/eventos y debe evitar absorber más reglas. |
| O - abierto a extensión | Las Specifications compuestas y los adaptadores permiten extender condiciones/infraestructura mediante colaboradores | `Specification.__and__/__or__/__invert__`; Memory/Pg | Agregar una condición todavía requiere decidir cómo se compone y qué mensaje produce; no se promete cero cambios en todo el sistema. |
| L - sustitución | Servicios y handlers usan operaciones esperadas de UoW/repositorios/lectores, con implementaciones Memory y PostgreSQL | Pruebas de API con Memory y archivos `test_api_*_postgres.py` con DB real | Las pruebas ofrecen evidencia de escenarios comunes, no una demostración formal universal. `RLock` global y bloqueos de filas no son mecanismos equivalentes ni rinden igual. |
| I - segregación de interfaces | Consultar no obliga a exponer métodos de guardar; repositorios se separan por agregado | `DisponibilidadReader`, `PedidoReader`, `CotizacionRepository`, `PedidoRepository`, `InventarioRepository` | UoW agrupa los colaboradores necesarios para coordinar, pero `ubicacion_reserva` pertenece al repositorio de inventario y no se duplica como operación del UoW. |
| D - inversión de dependencias | Servicios reciben fábrica de UoW y reloj; el detalle PostgreSQL se elige en la frontera de API | `CotizacionService.__init__`, `PedidoService.__init__`, `application/ports.py`, proveedores `Depends` | Las fábricas usan duck typing y no están anotadas con Protocol en cada firma. La API sí importa infraestructura porque es el punto de composición. |

### Un ejemplo de responsabilidad y sustitución

El endpoint de confirmación arma el comando y un actor de demo. El handler llama al servicio; el servicio invoca `Pedido.confirmar` y `InventarioUbicacion.reservar`. La misma operación de aplicación se usa en pruebas con un UoW Memory y en producción con PostgreSQL. Cambiar el transporte HTTP no obliga a reescribir las reglas; cambiar persistencia sí exige cumplir los contratos y verificar integridad/concurrencia del adaptador nuevo.

### Un ejemplo de extensión de una regla

La vigencia no se calcula en el controller: `CotizacionVigente.is_satisfied_by` delega al Value Object. `AceptacionDelCliente` aporta otra condición. `AndSpec` combina ambas sin guardar pedidos, reservar inventario ni consultar PostgreSQL. La creación del pedido permanece en `Cotizacion.convertir`, y el commit en el servicio/UoW.

## Evidencia y riesgos que el diseño no elimina

| Comprobación | Evidencia existente |
| --- | --- |
| Condiciones puras y composición | `tests/test_specifications.py` |
| Dominio y rollback con Memory | `tests/test_architecture.py`, E9 y `test_state_machine.py` |
| Misma intención de API con persistencia real | `tests/test_api_revalidacion_postgres.py`, conversión, confirmación, cancelación y consulta PostgreSQL |
| Consultar sin escrituras | `test_api_consulta_pedido_postgres.py::test_http_consulta_estado_persistido_sin_escrituras` |
| Doble confirmación/cancelación y última unidad | Pruebas PostgreSQL de repetición/concurrencia |

Hay colecciones públicas mutables en agregados y payload mutable dentro de `EventoDominio` congelado. La API usa actores y pago simulados; la auditoría no acredita permisos de usuario real. Los mensajes de ciertos rechazos se seleccionan comparando texto de excepciones, una dependencia frágil que debe revisarse si cambian los mensajes del dominio. Reconocer estos límites evita atribuir a la arquitectura garantías que el código aún no aporta.
