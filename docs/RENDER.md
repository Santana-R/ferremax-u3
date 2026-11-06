# Preparación del despliegue de FerreMax en Render

## Configuración propuesta

`render.yaml` define dos recursos nuevos para la demostración del PIA:

| Recurso | Configuración |
| --- | --- |
| `ferremax-api` | Web Service, Docker, plan Free, región Oregon, rama `pia-render`. |
| `ferremax-db` | PostgreSQL 16, plan Free, región Oregon, base y usuario `ferremax`. |

La API recibe `DATABASE_URL` mediante `fromDatabase.connectionString`, utilizando
la dirección interna de PostgreSQL. No se copian las credenciales locales ni se
guardan contraseñas en el YAML. `ipAllowList: []` limita PostgreSQL a conexiones
internas; el acceso público previsto es la API con Swagger.

El plan gratuito de la API puede suspenderse tras 15 minutos sin tráfico y tardar
aproximadamente un minuto en despertar. PostgreSQL Free vence 30 días después
de su creación. La configuración propone ambos planes Free; el plan real de
creación se revisa en Render antes de aplicarlo. No define recursos de pago.

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

## Aplicación del plan y verificación

El código y `render.yaml` deben estar confirmados y subidos en la rama elegida
antes de planificar el Blueprint. El plugin debe tener confirmado el workspace
de la cuenta, y se deben inspeccionar sus recursos existentes antes de crear
otros. El plan debe crear únicamente los dos recursos descritos, en Free.

El Blueprint se planifica y revisa antes de aplicarlo. La creación o aprobación
de un Blueprint no demuestra que la API funcione: se espera a que el deploy
termine en `live` y se verifican Swagger y las operaciones contra la base real.

El YAML solicita `autoDeployTrigger: checksPass`. Para que Render despliegue
automáticamente después del CI, el proveedor GitHub debe estar conectado a
Render y los checks del commit deben aprobar. El acceso por URL pública a un
repo sin conectar el proveedor no habilita despliegues automáticos. Esta parte
de CD se considera verificada únicamente después de comprobarla en Render.

Después de un despliegue exitoso se registrará aquí su URL real y la evidencia
de funcionamiento. El enlace de Swagger tendrá la forma `URL_DEL_SERVICIO/docs`;
este documento no inventa una URL antes de que Render la asigne.

La base de la nube inicia con datos ficticios propios. El identificador del
pedido de la Mac no existe allí automáticamente. En Swagger se utiliza
`FER-API-DEMO` y la cotización `11111111-1111-4111-8111-111111111111`, versión 1
vencida, y se conserva el nuevo identificador devuelto por la conversión.
El actor y la autorización de pago siguen siendo simulados, como en el
prototipo local; no hay datos de clientes reales ni cobros externos.

## Comprobaciones de preparación

`tests/test_arranque_render.py` comprueba configuración inválida sin exposición
de credenciales, creación de tablas y demo, reinicio conservando historial y
reservas, dos arranques simultáneos y rollback de DDL ante un error.

También se comprobó el proceso real de arranque con un puerto dinámico y una
base vacía: inicialización, recorrido HTTP de las seis operaciones y reinicio
sin perder el pedido. CI habilita las opciones de inicialización al construir
y probar App. La validación de recursos y el despliegue en Render requieren
confirmar el workspace de destino; los resultados locales no se presentan como
un despliegue público ya realizado.

## Referencias

- [Blueprint YAML](https://render.com/docs/blueprint-spec).
- [Docker en Render](https://render.com/docs/docker).
- [Conexiones internas](https://render.com/docs/private-network).
- [Variables de entorno](https://render.com/docs/environment-variables).
- [Despliegues después del CI](https://render.com/docs/deploys#integrating-with-ci).
- [Límites del plan Free](https://render.com/docs/free).
