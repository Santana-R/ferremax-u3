# Integración continua de FerreMax

El workflow [FerreMax - CI](https://github.com/Santana-R/ferremax-u3/actions/workflows/ci.yml)
está definido en `.github/workflows/ci.yml`. Se ejecuta al recibir un push o un
pull request; también admite ejecución manual cuando el workflow esté disponible
en la rama predeterminada del repositorio.

## Qué verifica

El job `Docker, API y pruebas` utiliza un runner Ubuntu 24.04 de GitHub:

1. Obtiene el código del commit, prepara las carpetas de reportes con el usuario
   del runner y valida la configuración de Compose.
2. Construye las imágenes de App y Tests con el mismo Dockerfile utilizado
   en la Mac. Levanta App y PostgreSQL y espera sus comprobaciones de salud.
   En CI se habilitan la inicialización y la carga inicial del nuevo arranque;
   la carga repetida de datos ficticios conserva los registros existentes.
3. Carga los datos ficticios en la base nueva de CI y ejecuta
   `scripts/comprobar_api_ci.py` por HTTP real, desde el runner hacia App.
   Comprueba las seis operaciones, la versión vencida, la aceptación, el pago
   rechazado y el recorrido Pendiente → Confirmado → Cancelado. Verifica el
   total de 240.00 MXN y la reserva 0 → 2 → 0 sin duplicaciones.
4. Ejecuta `docker compose run --rm --no-deps tests`. El ejecutor crea otra
   base temporal para la suite y exige pruebas aprobadas sin omisiones y
   cobertura >=80 %. Los fallos de construcción, HTTP, tests o cobertura
   producen una ejecución fallida; no se ocultan con `continue-on-error`.
5. Conserva reportes y logs y retira los contenedores y el volumen del runner.

Las pruebas de la suite usan TestClient y PostgreSQL real. El recorrido HTTP
adicional prueba la aplicación que realmente está escuchando dentro de App;
ambas verificaciones son complementarias. El script HTTP requiere una base
ficticia recién inicializada y no se utiliza para repetir la práctica sobre la
base que conserva el historial de Roberto.

## Aislamiento y configuración

El workflow no lee el `.env` de la Mac. Define credenciales ficticias para un
PostgreSQL exclusivo de su runner. No conecta a bases externas ni necesita
secrets de despliegue. La limpieza `down --volumes` se realiza únicamente dentro
del runner desechable de GitHub, donde no existen los datos de la práctica local.

El token del workflow tiene `contents: read`, y checkout no conserva sus
credenciales. Las acciones checkout y upload-artifact están fijadas a sus SHA
completos, correspondientes a v7.0.1 y v7.0.2 respectivamente. El job tiene un
límite de 20 minutos y cancela ejecuciones anteriores del mismo workflow/ref
cuando llegan nuevos cambios.

## Cómo revisar el resultado, sin comandos Git

1. Abrir el repositorio en GitHub y seleccionar **Actions**.
2. Abrir **FerreMax - CI** y elegir la ejecución de la rama y commit deseados.
3. Revisar que el job **Docker, API y pruebas** termine en verde. Dentro del job
   se puede abrir cada paso y ver la salida de la comprobación HTTP y de pytest.
4. En **Artifacts**, descargar `ferremax-ci-<run_id>-<intento>`. Contiene los
   reportes de esa ejecución y los logs de Compose. Abrir `htmlcov/index.html`
   para consultar la cobertura, y `junit.xml` o `coverage.json` para los
   resultados estructurados.

Los artefactos se conservan 30 días según la configuración del workflow. No se
guardan ZIP ni copias de estos reportes en el historial del código. Si falla la
construcción antes de producir cobertura, los logs ayudan a revisar el motivo;
la ausencia de un reporte no acredita que las pruebas hayan pasado.

El resultado válido es la ejecución de Actions asociada al commit, no solo la
presencia del archivo YAML. Render está configurado para esperar estos checks
antes de desplegar la rama final `main`; el workflow de CI no contiene tokens
ni credenciales de Render. Ver [servicio público y despliegue](RENDER.md).

## Referencias

- [Sintaxis de workflows de GitHub Actions](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax).
- [Reportes como artefactos de una ejecución](https://docs.github.com/en/actions/tutorials/store-and-share-data).
- [Checkout v7.0.1](https://github.com/actions/checkout/releases/tag/v7.0.1).
- [Upload-artifact v7.0.2](https://github.com/actions/upload-artifact/releases/tag/v7.0.2).
