# Despliegue de FerreMax en Render

## Configuración aplicada

`render.yaml` define los dos recursos de la demostración del PIA. El Blueprint
agregó el sufijo `w5kd` a sus nombres al crearlos como recursos nuevos:

| Recurso | Configuración |
| --- | --- |
| `ferremax-api-w5kd` | Web Service, Docker, plan Free, región Oregon, rama `pia-render`. |
| `ferremax-db-w5kd` | PostgreSQL 16, plan Free, región Oregon, base y usuario `ferremax`. |

La API recibe `DATABASE_URL` mediante `fromDatabase.connectionString`, utilizando
la dirección interna de PostgreSQL. No se copian las credenciales locales ni se
guardan contraseñas en el YAML. `ipAllowList: []` limita PostgreSQL a conexiones
internas; el acceso público previsto es la API con Swagger.

El plan gratuito de la API puede suspenderse tras 15 minutos sin tráfico y tardar
aproximadamente un minuto en despertar. PostgreSQL Free vence 30 días después
de su creación. La configuración propone ambos planes Free; el plan real de
creación se revisó en Render antes de aplicarlo. Ambos recursos quedaron en Free.
Render indica que esta base vence el 6 de diciembre de 2026 a las 16:19 UTC.

## Arranque de la imagen

`Dockerfile` ejecuta `python scripts/iniciar_api.py`. El script:

1. Valida el puerto y las opciones de inicialización.
2. Si se habilita la inicialización, ejecuta el mismo DDL de seis tablas que
   utilizan Compose y las pruebas, con `CREATE IF NOT EXISTS` y transacción.
   Un bloqueo de PostgreSQL serializa dos inicializaciones simultáneas.
3. Si se habilita el demo, inserta el inventario ficticio y la versión 1 vencida
   sin sobrescribir datos existentes. No reinicia pedidos, reservas ni versiones.
4. Reemplaza su proceso con Uvicorn, escuchando en `0.0.0.0` y el puerto indicado.

| Variable | Uso |
| --- | --- |
| `DATABASE_URL` | Conexión interna proporcionada por Render. |
| `PORT` | Puerto proporcionado por Render, normalmente 10000; en local usa 8000 si no se define. |
| `FERREMAX_INIT_DB` | `true` en Render; crea el esquema si falta. Por defecto `false`. |
| `FERREMAX_SEED_DEMO` | `true` en Render; carga inicial idempotente. Por defecto `false`. |

La inicialización se hace antes del arranque, porque el plan Free no admite
pre-deploy commands. No consulta ni modifica la base de la Mac. La salud de la
aplicación se comprueba en `/openapi.json`; las consultas de inventario y pedido
acreditan además el funcionamiento real de la base.

## Enlace público y verificación

- [Swagger público de FerreMax](https://ferremax-api-w5kd.onrender.com/docs).
- [OpenAPI público](https://ferremax-api-w5kd.onrender.com/openapi.json).
- [Servicio en Render](https://dashboard.render.com/web/srv-dbmvse5g1s2s73c2dao0).
- [Blueprint aplicado](https://dashboard.render.com/blueprint/exs-dbmvqjrncjis73alfgq0).

El despliegue inicial `dep-dbmvsedg1s2s73c2dbhg`, del commit `d977e53`, terminó
en `live` el 6 de noviembre de 2026. Se verificaron HTTP 200 en Swagger y
OpenAPI y las seis operaciones contra PostgreSQL en Render. La evidencia
de solicitudes y respuestas está en
[render_verificacion.json](../evidencias/pia/render_verificacion.json).

| Comprobación pública | Resultado |
| --- | --- |
| Consultar disponibilidad inicial | 10 físicas, 0 comprometidas, 5 en tránsito y 10 disponibles en S1. |
| Convertir versión 1 vencida | 409; exige una versión vigente. |
| Revalidar la versión 1 | 201; crea versión 2 conservando la anterior. |
| Convertir sin aceptación | 409; no crea pedido. |
| Convertir la versión 2 aceptada | 201; pedido Pendiente, total 240.00 MXN. |
| Confirmar con pago rechazado | 409; conserva Pendiente e inventario. |
| Confirmar con pago simulado autorizado | 200; Confirmado, 2 comprometidas y 8 disponibles. |
| Repetir confirmación | 409; conserva la reserva. |
| Cancelar antes del surtido | 200; Cancelado, 0 comprometidas y 10 disponibles. |
| Repetir cancelación | 409; conserva 10 disponibles. |
| Consultar el pedido guardado | 200; Cancelado, cotización versión 2 y total 240.00 MXN. |

Pedido creado por esta verificación pública:
`4d7b5b3e-926e-4856-9a1e-d1a433ef5cfd`. Para revisarlo en Swagger basta ejecutar
`GET /pedidos/{pedido_id}` con ese identificador.

La verificación ya creó la versión 2 de la cotización de demostración. Para
crear otro pedido se puede convertir esa versión mientras siga vigente. Si
vence, se revalida la versión más reciente para crear la siguiente; volver a
revalidar la versión 1 no reemplaza la versión 2 existente.

## Reproducción y despliegues posteriores

El código y `render.yaml` deben estar confirmados y subidos en la rama elegida
antes de planificar el Blueprint. El plugin debe tener confirmado el workspace
de la cuenta, y se deben inspeccionar sus recursos existentes antes de crear
otros. El plan debe crear únicamente los dos recursos descritos, en Free.

El Blueprint se planifica y revisa antes de aplicarlo. La creación o aprobación
de un Blueprint no demuestra que la API funcione: se espera a que el deploy
termine en `live` y se verifican Swagger y las operaciones contra la base real.

El Blueprint tiene auto-sync habilitado. El servicio informa auto-deploy
habilitado y `autoDeployTrigger: checksPass` para la rama `pia-render`. Render
debe recibir la conexión de GitHub para detectar cambios y esperar sus checks.
La publicación inicial y las operaciones públicas están verificadas; la
actualización automática todavía requiere comprobar esa conexión.

La actualización documental `bd36c6f` aprobó
[CI](https://github.com/Santana-R/ferremax-u3/actions/runs/42252357106), pero el
historial de Render siguió mostrando únicamente el despliegue inicial `d977e53`.
Esto no se presenta como una actualización automática verificada. El siguiente
paso es revisar **Account Settings → Account Security → Git Deployment
Credentials** y autorizar GitHub para el repositorio `Santana-R/ferremax-u3`.
Si ya existe la conexión, se revisan sus permisos y las Git Credentials del
servicio antes de probar otro cambio. La documentación oficial de
[conexión del proveedor Git](https://render.com/docs/git-provider) describe ese
paso. No se exponen credenciales ni se abre PostgreSQL al público para resolverlo.

La base de la nube inicia con datos ficticios propios. El identificador del
pedido de la Mac no existe allí automáticamente. En Swagger se utiliza
`FER-API-DEMO` y la cotización `11111111-1111-4111-8111-111111111111`. El primer
arranque insertó su versión 1 vencida y la verificación creó la versión 2.
Cada conversión devuelve un identificador nuevo de pedido, que debe conservarse.
El actor y la autorización de pago siguen siendo simulados, como en el
prototipo local; no hay datos de clientes reales ni cobros externos.

## Comprobaciones de preparación

`tests/test_arranque_render.py` comprueba configuración inválida sin exposición
de credenciales, creación de tablas y demo, reinicio conservando historial y
reservas, dos arranques simultáneos y rollback de DDL ante un error.

También se comprobó el proceso real de arranque con un puerto dinámico y una
base vacía: inicialización, recorrido HTTP de las seis operaciones y reinicio
sin perder el pedido. CI habilita las opciones de inicialización al construir
y probar App. La [ejecución previa al despliegue](https://github.com/Santana-R/ferremax-u3/actions/runs/42181411233)
aprobó 242 pruebas, cero omitidas y cobertura 97.24 % en contenedores. El plan
se aplicó en el workspace My Workspace, confirmado para esta cuenta; la
verificación pública es una comprobación adicional a la suite de CI.

## Referencias

- [Blueprint YAML](https://render.com/docs/blueprint-spec).
- [Docker en Render](https://render.com/docs/docker).
- [Conexiones internas](https://render.com/docs/private-network).
- [Variables de entorno](https://render.com/docs/environment-variables).
- [Despliegues después del CI](https://render.com/docs/deploys#integrating-with-ci).
- [Límites del plan Free](https://render.com/docs/free).
