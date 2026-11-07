# Vista de atención: inventario, cotizaciones y pedidos

La pantalla `/cliente` permite seleccionar una cotización por folio, revisar cantidades y precios, indicar vigencia, condiciones y motivo, y renovar sin escribir JSON, identificadores ni versiones. La confirmación presenta el folio, la fecha guardada de vencimiento (hora de Monterrey) y la conservación del historial.

La navegación también permite consultar inventario, crear pedidos desde cotizaciones aceptadas y vigentes, consultar pedidos, confirmarlos y cancelarlos. Las seis operaciones conservan su API y su documentación en Swagger. La aplicación continúa siendo una demostración con datos ficticios y actores simulados. No introduce autenticación ni pagos reales.

## Ejecutar desde GitHub Desktop y Docker

1. Traer la rama `pia-cliente-cotizaciones` con **Fetch origin** y seleccionarla en **Current Branch**. Los cambios de documentación de `pia-entrega` permanecen separados.
2. Mantener Docker Desktop abierto. En la terminal de VS Code, desde la raíz del repositorio:

```bash
docker compose up -d --build --wait app
docker compose exec -T app python scripts/cargar_cotizacion_cliente_demo.py
```

3. Abrir <http://127.0.0.1:8000/cliente> (usar el puerto `APP_PORT` si se configuró otro). La documentación técnica continúa en `/docs`.
4. Elegir **COT-RENOVAR-DEMO**, revisar sus productos, cambiar el precio por unidad a 120.00, escribir un motivo y las condiciones acordadas y pulsar **Renovar cotización**. Para dos unidades, el total estimado será 240.00 MXN.
5. Comprobar el mensaje de renovación, la fecha y que ahora se informa que la cotización está vigente y no permite renovarla otra vez.

El cargador agrega una cotización ficticia separada de COT-API-DEMO. Es idempotente: no modifica ni elimina cotizaciones, pedidos, reservas o versiones existentes. Si ya renovaste COT-RENOVAR-DEMO, seguirá vigente; volver a ejecutar el cargador no reinicia su historial. No es necesario ni correcto borrar la base para repetir una demostración.

## Comportamiento y límites

- La lista muestra la versión más reciente de cada cotización. La consulta es una transacción de solo lectura.
- Una cotización vencida, incluido el instante exacto del vencimiento, admite renovación; una vigente o aún no emitida muestra una explicación y bloquea el envío.
- La pantalla mantiene internamente el identificador y la versión para invocar el POST de revalidación existente. La API conserva su contrato; el dominio sigue validando la operación.
- Los productos proceden de la cotización guardada; se editan cantidad y precio. Esta primera vista no permite añadir o eliminar productos ni cambiar la moneda.
- El total es una estimación visual. Los importes persistidos se siguen validando con Decimal en el servidor.
- Se deshabilitan los controles mientras se guarda. Si se interrumpe la comunicación durante el envío, se solicita recargar antes de reintentar: no se afirma que hubo rollback ni se repite el POST automáticamente.
- El comprobante usa la fecha leída de la cotización persistida después de renovar. Si falla esa lectura, conserva la confirmación del guardado y solicita actualizar para conocer la nueva vigencia.
- Las rutas de presentación y selección bajo `/cliente` se excluyen de Swagger; las seis operaciones de negocio mantienen su documentación y contratos.

## Validación

`tests/test_cliente.py` verifica carga de la vista sin DB, errores comprensibles, lista vacía, límites de vigencia y consulta/renovación con PostgreSQL, incluyendo conservación del historial y del demo.

CI prueba además la pantalla con Chromium contra App y PostgreSQL desechables. Recorre selección por folio, bloqueo de una cotización vigente, renovación real, comprobante, fallo recuperable de consulta, cotización sin emitir, comunicación incierta al guardar, lista vacía y distribución móvil. Los PNG de comprobación quedan en `reports/ci` dentro del artefacto de la ejecución, sin versionar capturas generadas en Git.

## Recorrido completo de atención

1. **Consultar inventario:** seleccionar el código del producto y consultar sus unidades físicas, reservadas, disponibles y en traslado por ubicación.
2. **Renovar cotizaciones:** elegir el folio vencido, revisar el formulario y guardar. La vista evita renovar cotizaciones vigentes o aún no emitidas.
3. **Crear pedido:** seleccionar una cotización vigente, revisar sus productos, precios y condiciones, y registrar su aceptación. Se crea Pendiente y todavía no reserva unidades.
4. **Consultar y atender pedidos:** elegir una referencia de pantalla (PED-...), consultar su estado e importe y realizar la operación permitida. Las referencias son abreviaturas de presentación, no un nuevo folio comercial; los identificadores completos permanecen internos. Si dos prefijos coinciden se amplía la abreviatura para distinguirlos.
5. **Confirmar:** introducir la referencia del pago simulado, indicar si está autorizado y elegir la sucursal. Un pago no autorizado o inventario insuficiente conserva el pedido pendiente. Un pago autorizado y existencias suficientes permiten confirmar y reservar.
6. **Cancelar:** escribir el motivo y confirmar la liberación de los productos. Un pedido cancelado ya no muestra controles de confirmación ni cancelación. Un pedido surtido no admite cancelación.

`scripts/comprobar_atencion_ci.cjs` recorre estas operaciones en navegador y verifica inventario 10 → 8 → 10, pago rechazado sin cambio de estado, confirmación, cancelación y consulta. También verifica el diseño móvil y que los UUID internos no aparezcan como texto para el usuario.

Las mutaciones no se reintentan automáticamente tras un corte de comunicación. La vista pide consultar el estado o los pedidos antes de volver a intentarlo. Una cotización puede dar origen a varios pedidos según el comportamiento existente; la pantalla no impone una regla de unicidad nueva.
