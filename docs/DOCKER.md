# FerreMax con Docker Compose: DB, App y Tests

## Componentes

| Servicio | Responsabilidad | Datos y acceso |
| --- | --- | --- |
| `db` | PostgreSQL 16.15, esquema de seis tablas. | Conserva `postgres_data`; puerto local 5433 por defecto. |
| `app` | API y Swagger con Python 3.12 y las dependencias fijadas. | Conecta a `db:5432`; Swagger local en puerto 8000 por defecto. |
| `tests` | Suite completa con PostgreSQL real y cobertura mínima de 80 %. | Base temporal por ejecución; reportes locales en `reports/docker/`. |

La API local de VS Code puede seguir utilizándose como alternativa. Para usar el
contenedor App en el mismo puerto 8000 hay que detener antes Uvicorn con Ctrl+C.
El `.env` actual basta: `APP_PORT` es opcional y su valor por defecto es 8000.
Compose fija el host interno `db` y el puerto interno 5432; el puerto 5433 es
para conexiones desde la Mac, no para conexiones entre contenedores.

`Dockerfile` tiene un base compartido y dos destinos: `app` y `tests`. La API
corre con un usuario sin privilegios. Las dependencias de pruebas se instalan
solo en el destino `tests`. `.dockerignore` limita el contexto al código,
dependencias y recursos necesarios: las credenciales `.env`, el entorno local,
Git, documentos y evidencias quedan fuera de la construcción de las imágenes.
Compose entrega las credenciales por variables al arrancar los contenedores.

## Paso 1: arrancar App con la base existente

Desde GitHub Desktop, actualizar y seleccionar la rama `pia-compose-app-tests`.
Mantener Docker Desktop abierto. Detener la API de la terminal con Ctrl+C y,
desde la raíz del repositorio, ejecutar:

```bash
docker compose config --quiet
docker compose up -d --build --wait app
docker compose ps
```

La primera construcción descarga Python e instala las dependencias. App depende
de la salud de `db`, por lo que el comando levanta también PostgreSQL si hace
falta. La configuración y el volumen del servicio `db` no cambian; no se borran
ni se reinicializan los datos de la práctica anterior.

En Docker Desktop deben verse `db-1` y `app-1` dentro de `ferremax`. El indicador
de salud de App comprueba que responde su OpenAPI por HTTP. El de DB comprueba
PostgreSQL; para verificar el acceso real a datos se usa la consulta de abajo.

Abrir [Swagger local](http://127.0.0.1:8000/docs) y ejecutar
`GET /pedidos/{pedido_id}` con el pedido de la práctica. Debe conservar estado
Cancelado, cotización de origen versión 2 y total 240.00 MXN. Esta vez Uvicorn
corre dentro de Docker; no hace falta dejar una terminal de VS Code ocupada.

Si se eligió otro `APP_PORT`, ajustar el enlace al puerto elegido. Si la API
no arranca, revisar la salida de la construcción y los logs:

```bash
docker compose logs --tail 80 app
docker compose logs --tail 80 db
```

No usar `docker compose config` sin `--quiet` al compartir capturas: su salida
expandida incluye la configuración local de las credenciales.

## Paso 2: ejecutar las pruebas

Después de comprobar App, ejecutar desde la raíz:

```bash
docker compose run --build --rm tests
```

`tests` tiene un perfil opcional: no se ejecuta al levantar App. Seleccionarlo
directamente con `run` activa ese servicio y su dependencia DB sin tener que
levantar manualmente el perfil. El contenedor termina y se elimina al finalizar;
es una tarea de pruebas, no un servidor que deba permanecer encendido.

El ejecutor `docker/run_tests.py` realiza lo siguiente:

1. Crea una base nueva con nombre aleatorio `ferremax_test_...` en la misma
   instancia PostgreSQL. No ejecuta la suite sobre la base de demostración.
2. Inicializa el esquema y fija `TEST_DATABASE_URL` y `DATABASE_URL` de pytest
   a esa base temporal, aunque existieran otros valores de entrada.
3. Ejecuta la suite con cobertura, HTML y JUnit. Exige al menos una prueba,
   cero errores/fallos/omisiones y cobertura mínima de 80 %.
4. Elimina únicamente la base que creó, también si pytest rechaza la ejecución.
   Conserva la base y el volumen de la demostración.

Cada ejecución usa su propia base y carpeta de reportes. El usuario local
creado por la imagen PostgreSQL debe poder crear y eliminar bases temporales;
el usuario actual del entorno local tiene esos permisos. Las pruebas HTTP usan
TestClient y PostgreSQL real, sin depender del proceso del servicio App.

La salida muestra el resultado y la carpeta de la ejecución. El montaje
`/reports/<ejecucion>` del contenedor corresponde a
`reports/docker/<ejecucion>` en la Mac. Abrir
`htmlcov/index.html` dentro de esa carpeta para ver la cobertura. También se
conservan `coverage.json` y `junit.xml`. La carpeta `reports/` está excluida de
Git y no reemplaza las evidencias históricas de E9.

## Arranques posteriores y conservación de datos

Para iniciar de nuevo los servicios sin reconstruir la imagen:

```bash
docker compose up -d --wait app
```

Después de cambiar código, usar de nuevo `docker compose up -d --build --wait app`.
Reiniciar un contenedor no incorpora por sí solo cambios del código: este se
copia a la imagen al construirla.

Para detenerlos conservando los datos:

```bash
docker compose stop app db
```

También se pueden detener e iniciar desde Docker Desktop. No se necesita
recrear el volumen. `docker compose down` conserva el volumen; añadir
`--volumes` elimina los datos y no forma parte de esta práctica.

En un entorno nuevo, el SQL montado inicializa las tablas. Para cargar los datos
ficticios de la demostración, ejecutar explícitamente:

```bash
docker compose exec app python scripts/cargar_cotizacion_demo.py
```

La carga incluye el inventario ficticio y la versión 1 vencida sin sobrescribir
registros existentes. En la Mac que ya tiene los datos no es necesario repetirla;
tampoco restaura el estado de un pedido ni reinicia una cotización revalidada.

## Estado de verificación de este bloque

La configuración de los tres servicios se validó con Docker Compose. El ejecutor
se probó en el entorno local Python 3.9 con PostgreSQL real: 235 pruebas
aprobadas, cero omitidas y cobertura 97.24 %. Se comprobó que la base temporal se
retira, incluidos fallos/omisiones simulados, y que las seis tablas de la base
de demostración quedan intactas.

La construcción de las imágenes Python 3.12, el arranque de App y la ejecución
de Tests dentro de los contenedores quedan pendientes de comprobar en Docker
Desktop. El entorno que preparó este bloque no tiene acceso al socket del motor;
la validación local anterior no se presenta como una ejecución de contenedores.
Las comprobaciones de los pasos 1 y 2 completan esa evidencia.

## Referencias de Docker

- [Orden de arranque y salud de dependencias](https://docs.docker.com/compose/how-tos/startup-order/).
- [Perfiles y selección explícita de servicios](https://docs.docker.com/compose/how-tos/profiles/).
- [Ejecución de tareas con Compose run](https://docs.docker.com/reference/cli/docker/compose/run/).
