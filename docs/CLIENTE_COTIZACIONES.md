# Renovación de cotizaciones: primera vista de atención

La pantalla `/cliente` permite seleccionar una cotización por folio, revisar cantidades y precios, indicar vigencia, condiciones y motivo, y renovar sin escribir JSON, identificadores ni versiones. La confirmación presenta el folio, la fecha guardada de vencimiento (hora de Monterrey) y la conservación del historial.

Es la primera operación de la vista de atención; las otras operaciones siguen en Swagger. La aplicación continúa siendo una demostración con datos ficticios y actores simulados. No introduce autenticación ni pagos reales.

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
- Las tres rutas de presentación (`/cliente`, `/cliente/acciones.js`, `/cliente/cotizaciones`) se excluyen de Swagger; las seis operaciones de negocio mantienen su documentación y contratos.

## Validación

`tests/test_cliente.py` verifica carga de la vista sin DB, errores comprensibles, lista vacía, límites de vigencia y consulta/renovación con PostgreSQL, incluyendo conservación del historial y del demo.

CI prueba además la pantalla con Chromium contra App y PostgreSQL desechables. Recorre selección por folio, bloqueo de una cotización vigente, renovación real, comprobante, fallo recuperable de consulta, cotización sin emitir, comunicación incierta al guardar, lista vacía y distribución móvil. Los PNG de comprobación quedan en `reports/ci` dentro del artefacto de la ejecución, sin versionar capturas generadas en Git.

Esta rama todavía debe revisarse e integrarse en la entrega antes de cambiar la versión publicada en Render.
