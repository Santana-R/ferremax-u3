# FerreMax Unidad 3

Propuesta académica de arquitectura de Componentes de lógica de negocio. Equipo 17: Roberto Santana Trujillo e Isaías Leonardo Salazar Torres. Profesor Miguel Ángel Gómez Marroquín.

## Empresa: FerreMax
La empresa FerreMax opera tres sucursales y un almacén central dedicados a la venta de herramientas y materiales de construcción. El análisis previo evidenció serias inconsistencias, como el riesgo de confirmar ventas contra mercancía ya comprometida, el uso de cotizaciones vencidas (gestionadas en hojas de cálculo) y una visibilidad limitada de inventario, lo que derivaba en promesas de mercancía sin sustento.
FerreMax requiere coordinar cotizaciones, pedidos e inventario sin comprometer mercancía inexistente. La arquitectura propuesta organiza las reglas del negocio con Domain Model, una Service Layer y adaptadores de persistencia. El recorrido detallado cubre la consulta de disponibilidad, la revalidación de cotizaciones, la conversión a pedido, la confirmación con reserva y la cancelación antes del surtido.

### Alcances
El proceso detallado va desde la disponibilidad y la cotización hasta la confirmación del pedido y la liberación de su reserva. Todos los casos aparecen en User Stories de la unidad 2. Los demás procesos se representan para conservar el panorama de FerreMax y sus vínculos.
La confirmación ejecutable es de contado y usa una ubicación por pedido. Esto delimita el prototipo, no cambia las reglas del negocio sobre surtido multiorigen, crédito o parciales. Las consultas sí devuelven las cuatro ubicaciones de demostración. Los datos, referencias de pago y actores del demo son simulados.
La vigencia de siete días proviene de un acuerdo simulado del BRD y se pasa como parámetro. 

## Instrucciones

1. Leer el **[informe final del equipo](docs/U3Ferremax_Informe.pdf)**. Es el PDF integrado por el equipo. `docs/FerreMax_U3_Informe.pdf` conserva el mismo PDF como alias para enlaces anteriores.
2. Ver los **[diagramas UML del informe final](docs/Diagramas.md)**: cinco vistas con fuente PlantUML (`.puml`), SVG, PDF y PNG.
3. Leer `docs/ADR_Trazabilidad_BitacoraIA.md`.

Cinco casos detallados: consultar disponibilidad, revalidar cotización, convertirla en pedido, confirmar contado con reserva y cancelar antes del surtido. 

### Enlaces a entregables
1. Informe de arquitectura: **[U3FerreMax_Informe](docs/U3Ferremax_Informe.pdf)**
2. Diagrama de dominio y clases: **[Diagrama de dominio](diagrams/D01_MapaDominio.pdf)** y **[Diagrama de Clases](diagrams/D02_DiagramaClases.pdf)**
3. Diagramas de secuencia: **[Diagrama de Secuencia completa](diagrams/D04_Diagrama_Seuencia_Completa.pdf)** y **[Diagrama de Secuencia Interrumpida](diagrams/D05_Diagrama_Secuencia_Interrumpida.pdf)**
4. Matriz de trazabilidad: **[Incluida con ADR y Bitácora de IA](docs/ADR_Trazabilidad_BitacoraIA.pdf)**
5. Bitácora de IA:**[Incluida con ADR y matriz de trazabilidad](docs/ADR_Trazabilidad_BitacoraIA.pdf)**
6. Código Base: **[Tests](tests/)** 

## Avance PIA: E9 de inventario, cotizaciones y cancelación

La rama `e9-ferremax` incorpora el primer bloque de E9: tres pruebas de BR04/BR05
y US09 en [tests/test_e9_inventario.py](tests/test_e9_inventario.py).
Cada caso inicia con 10 unidades físicas, 7 comprometidas y 5 en tránsito:

| Caso | Solicitud | Resultado esperado |
| --- | --- | --- |
| E9-INV-01: éxito | 2 unidades | Pedido confirmado, comprometida 9 y disponible 1. |
| E9-INV-02: error | 4 unidades | Pedido pendiente y datos sin cambios; sin reserva ni evento de confirmación nuevos. |
| E9-INV-03: límite | 3 unidades | Pedido confirmado, comprometida 10 y disponible 0. |

El segundo bloque verifica BR02/BR03 y US04/US05 en
[tests/test_e9_cotizaciones.py](tests/test_e9_cotizaciones.py). El reloj de prueba
es fijo, con zona UTC; cada caso inicia con datos nuevos.

| Caso | Situación | Resultado esperado |
| --- | --- | --- |
| E9-COT-01: éxito | Revalidar versión 1 vencida y convertir versión 2 aceptada. | Conserva versión 1 intacta; versión 2 mantiene folio y actualiza vigencia, precio y condiciones; el pedido usa versión 2 y total 240.00 MXN. |
| E9-COT-02: error | Convertir versión 1 a las 12:01, habiendo vencido a las 12:00. | Rechaza sin crear pedido, evento ni auditoría de éxito; conserva los datos. |
| E9-COT-03: límite | Convertir exactamente a las 12:00 de vencimiento. | Rechaza sin crear pedido ni modificar los datos. |

Revalidar o convertir una cotización no reserva inventario. La reserva corresponde
a la confirmación del pedido, probada en el primer bloque.

El tercer bloque verifica BR06 y US10 en
[tests/test_e9_cancelacion.py](tests/test_e9_cancelacion.py). Cada prueba confirma
un pedido de dos unidades sobre un inventario de 10 físicas, siete reservadas
para otro pedido y cinco en tránsito: antes de cancelar queda una disponible.

| Caso | Situación | Resultado esperado |
| --- | --- | --- |
| E9-CAN-01: éxito | Cancelar con autorización y motivo, antes del surtido. | Pedido cancelado; libera sus dos unidades, conserva las siete ajenas y deja tres disponibles. Registra motivo, actor, cambio de estado y evento. |
| E9-CAN-02: error | Intentar cancelar cuando el pedido ya fue surtido. | Rechaza por la regla de cancelación; conserva estado, reservas, auditoría y eventos. |
| E9-CAN-03: límite | Intentar cancelar de nuevo después de una cancelación exitosa. | Rechaza por el estado del pedido; mantiene tres disponibles y un solo evento de cancelación. |

La prueba de cancelación repetida detectó que se buscaba la reserva antes de
validar el estado del pedido. El servicio ahora aplica primero la regla del
dominio dentro del Unit of Work y conserva el estado anterior para la auditoría.
Así, el rechazo expresa la regla de cancelación en lugar de un error técnico
de ubicación. La prueba de éxito comprueba ambos estados de la auditoría.

Los nueve casos de negocio usan Memory. Se añadieron cinco casos de persistencia
PostgreSQL y el caso existente de concurrencia, además de tres casos de un
ejercicio separado con proveedor de pago simulado. Las omisiones no acreditan
persistencia. El estado comprobable se conserva en `evidencias/e9/resumen_e9.json`.
Para ejecutar el bloque completo y generar evidencia con un PostgreSQL temporal:

```bash
python -m pip install -r requirements-e9.txt
python scripts/generar_e9.py --postgres-temporal
```

Consultar [las instrucciones de integración en U5](docs/E9_INTEGRACION_U5.md).
El resultado se escribe en `evidencias/e9/`. Solo se crea `evidencias/e9_para_U5.zip`
cuando se verifican todos los requisitos del bloque; si falta persistencia u otra
verificación se conserva el paquete de avance, con los pendientes explícitos.
Ambos ZIP son paquetes locales excluidos de Git; las evidencias se conservan
descomprimidas en el repositorio.
El HTML E9 declara cuatro componentes completos: dominio, servicios, Memory y
PostgreSQL. Se publica además el HTML de todo src con la suite completa.

Desde la raíz del repositorio, en macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m pytest tests/test_e9_inventario.py tests/test_e9_cotizaciones.py tests/test_e9_cancelacion.py -v
python -m pytest -v
```

Las nueve pruebas también se pueden ejecutar sin dependencias externas:

```bash
PYTHONPATH=src python3 -m unittest tests.test_e9_inventario tests.test_e9_cotizaciones tests.test_e9_cancelacion -v
```

La prueba existente de PostgreSQL se omite mientras no se configure
`TEST_DATABASE_URL`; una omisión no acredita persistencia ni concurrencia reales.

## PIA: PostgreSQL con Docker Compose — primer bloque

Este bloque prepara únicamente la base de datos. La aplicación y el contenedor
de pruebas se incorporarán después para completar DB + App + Tests del PIA.
El arranque y la conservación de datos deben comprobarse en Docker Desktop;
validar el archivo Compose no acredita esas verificaciones.

Archivos:

- `docker-compose.yml`: servicio `db`, PostgreSQL 16.15, comprobación de salud y volumen.
- `.env.example`: plantilla de configuración. La copia `.env` queda excluida de Git.
- `tests/sql/ferremax_pruebas.sql`: se reutiliza el esquema que ya verificó E9.

Con Docker Desktop abierto, desde la raíz del repositorio:

1. Copiar `.env.example` como `.env` y cambiar `POSTGRES_PASSWORD` por una clave local.
   Conservar los otros valores para seguir estos ejemplos.
2. Validar la configuración y arrancar la base:

   ```bash
   docker compose config --quiet
   docker compose up -d --wait db
   docker compose ps
   ```

   `db` debe aparecer como `healthy`. La primera ejecución descarga la imagen.
3. Comprobar que existen las seis tablas:

   ```bash
   docker compose exec db psql -U ferremax -d ferremax -c "\dt ferremax_u3.*"
   ```

El puerto `5433` de tu equipo se conecta al `5432` del contenedor; se publica
solo en `127.0.0.1`. Dentro de Compose, los futuros servicios usarán `db:5432`.
La plantilla separa la configuración de Compose; la conexión de la aplicación
y de las pruebas se preparará en sus respectivos bloques.

`postgres_data` conserva los datos al detener o recrear el contenedor. Para parar
la base sin borrar el volumen, usar `docker compose stop db`; para volver a
arrancarla, `docker compose up -d --wait db`. La persistencia se comprueba guardando
datos, deteniendo y arrancando la base y consultándolos de nuevo.

El SQL de inicialización se ejecuta solo cuando el volumen está vacío. Cambiar
la contraseña en `.env` después de inicializar el volumen no cambia la del usuario
ya creado. `docker compose down` conserva el volumen; añadir `--volumes` lo borra
junto con sus datos. Si falla el arranque, revisar `docker compose logs db`.

## PIA: Specification para convertir cotizaciones

`domain/specifications.py` expresa las condiciones de vigencia y aceptación de
BR02/BR03 y US04/US05. `ContextoConversion` reúne la cotización, el instante
actual y la aceptación de esa versión. Las Specifications son evaluaciones
puras: devuelven un booleano sin crear pedidos ni modificar la cotización.

```python
COTIZACION_CONVERTIBLE = COTIZACION_VIGENTE & ACEPTACION_DEL_CLIENTE
```

La combinación AND se usa en `Cotizacion.convertir()`. El dominio conserva la
responsabilidad de crear el pedido y expresar el motivo del rechazo: primero
vigencia y luego aceptación. La emisión está incluida y el vencimiento excluido.
El contrato también permite OR y NOT, probados como operadores generales;
la regla de conversión de FerreMax utiliza AND.

`tests/test_specifications.py` comprueba límites temporales, aceptación,
composición, ausencia de modificaciones y prioridad del rechazo. Las pruebas
anteriores de E9 siguen verificando el flujo completo. Para ejecutar este bloque:

```bash
python -m pytest tests/test_specifications.py tests/test_e9_cotizaciones.py -v
```

Las evidencias E9 guardadas identifican su ejecución anterior mediante commit y
hashes; los resultados de una nueva ejecución deben distinguirse de esa entrega.

## PIA: máquina de estados del pedido

El modelo actual controla `Pendiente → Confirmado → Cancelado` mediante
`EstadoPedido` y las guardas de `Pedido.confirmar()` / `Pedido.cancelar()`.
El servicio coordina el cambio de estado y la reserva en la misma transacción.
Un fallo de inventario conserva el pedido Pendiente mediante rollback.

El documento de [máquina de estados](docs/architecture/STATE_MACHINE.md) contiene
el diagrama, la matriz de transiciones y su trazabilidad. `tests/test_state_machine.py` comprueba las seis
combinaciones de estado y acción, las guardas y los roles; E9 verifica además
los límites de disponibilidad y la reversión transaccional.

```bash
python -m pytest tests/test_state_machine.py tests/test_e9_inventario.py tests/test_e9_cancelacion.py -v
```

## PIA: API REST y Swagger — primera consulta

La API ofrece `GET /inventario/{sku}` y reutiliza el handler CQRS y el lector
PostgreSQL existentes. Consulta por ubicación sin modificar inventario. Una
respuesta 200 incluye un mensaje y las cantidades; un producto inexistente
devuelve 404 y un mensaje comprensible. La falta de conexión devuelve 503.

Con `.env` preparado y PostgreSQL en Docker, desde la raíz del proyecto:

```bash
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python scripts/cargar_inventario_demo.py
.venv/bin/python -m uvicorn ferremax.api.main:app --app-dir src --env-file .env --host 127.0.0.1 --port 8000
```

Abrir [Swagger](http://127.0.0.1:8000/docs) y consultar `FER-API-DEMO` o un código
inexistente. La carga es manual, ficticia e idempotente. La API permanece en la
terminal; Ctrl+C la detiene. PostgreSQL permanece en Docker.

Ver [contrato, ejemplos y pruebas](docs/api/INVENTARIO.md) y
[OpenAPI versionado](docs/api/openapi.json). Este bloque usa un actor Vendedor
simulado del lado del servidor. La autenticación y las operaciones de escritura
no forman parte de esta primera consulta. App y Tests se añadirán a Compose
en sus respectivos bloques.

## PIA: revalidación de cotizaciones desde Swagger

`POST /cotizaciones/{cotizacion_id}/versiones/{version}/revalidar` conecta el
servicio existente con PostgreSQL. Crea una nueva versión con HTTP 201,
conservando la anterior, el folio y el identificador. Audita y registra el evento;
no crea pedidos ni reservas. La API devuelve mensajes claros para rechazos por
datos, versión inexistente, versión vigente o revalidación repetida.

Con PostgreSQL encendido, detener la API anterior con Ctrl+C y ejecutar:

```bash
.venv/bin/python scripts/cargar_cotizacion_demo.py
.venv/bin/python -m uvicorn ferremax.api.main:app --app-dir src --env-file .env --host 127.0.0.1 --port 8000
```

La carga crea una cotización ficticia vencida sin sobrescribir versiones
existentes. Ver [cuerpo de la solicitud, respuestas y comprobación del historial](docs/api/REVALIDACION.md).
Este bloque conserva el actor Vendedor simulado del servidor; la autenticación
permanece fuera de estas operaciones de demostración local.

## PIA: convertir una versión aceptada en pedido

`POST /cotizaciones/{cotizacion_id}/versiones/{version}/convertir` recibe solo
`{"aceptada": true}`. El servicio existente verifica vigencia y aceptación,
crea un pedido Pendiente con las partidas y precios guardados y consulta
disponibilidad. El total proviene del dominio y se devuelve con el identificador
del pedido. No reserva inventario; esa operación corresponde a confirmar.

Usar la versión 2 de la práctica anterior, detener la API con Ctrl+C y reiniciar
el mismo comando Uvicorn después de actualizar la rama. Ver la
[guía de conversión y sus casos de Swagger](docs/api/CONVERSION.md).
Cada solicitud válida crea un pedido nuevo; conservar su identificador para las
siguientes operaciones. La confirmación se describe en el bloque siguiente.

## PIA: confirmar el pedido y reservar inventario

`POST /pedidos/{pedido_id}/confirmar` reutiliza el comando CQRS y el servicio
de confirmación existentes. Recibe referencia de pago, autorización booleana y
ubicación; verifica el pedido Pendiente, el pago y la disponibilidad. Confirma
estado, referencia, reservas, auditoría y evento en una transacción. Ante falta
de stock conserva el pedido Pendiente, sin reserva parcial.

En Swagger, usar el identificador del pedido creado en la conversión. La
confirmación válida responde 200; repetirla responde 409 sin duplicar reservas.
Ver [cuerpo, respuestas y comprobación del inventario](docs/api/CONFIRMACION.md).
El actor Caja y la autorización son simulados, sin cobros ni pasarela real.
El esquema de PostgreSQL y las dependencias son los mismos del bloque anterior.

## PIA: cancelar el pedido y liberar su reserva

`POST /pedidos/{pedido_id}/cancelar` recibe solo el motivo y reutiliza el comando
CQRS y `PedidoService.cancelar()`. Exige un pedido Confirmado aún no surtido;
cancela, libera su reserva y registra auditoría y evento en una transacción.
Conserva las reservas ajenas y rechaza una segunda cancelación sin aumentar
el disponible. El actor autorizado está simulado en el servidor.

Usar en Swagger el identificador del pedido confirmado, después de actualizar
la rama y reiniciar Uvicorn. Ver [cuerpo, respuestas y pruebas de liberación](docs/api/CANCELACION.md).
El esquema y las dependencias se conservan. Las pruebas incluyen PostgreSQL,
cancelaciones concurrentes y rollback ante una falla durante la liberación.

## PIA: consultar el pedido guardado

`GET /pedidos/{pedido_id}` reutiliza la consulta CQRS y el lector PostgreSQL
existentes. Devuelve el estado actual, el folio y la versión de origen, el total
del pedido y la moneda. Usa solo lectura; no cambia inventario, auditoría ni
eventos, y permite consultar el pedido después de cancelarlo.

Después de actualizar la rama y reiniciar Uvicorn, usar el identificador del
pedido anterior en Swagger. Ver [respuestas y pruebas de consulta](docs/api/CONSULTA_PEDIDO.md).
El actor Vendedor es simulado. Con esta consulta se completan las seis operaciones
del recorrido principal de la API; Compose con App/Tests, CI/CD, despliegue y
documentos finales se completarán en los siguientes bloques del PIA.

