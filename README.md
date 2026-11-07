# FerreMax - PIA de Componentes de Lógica de Negocios

Equipo 17: Roberto Santana Trujillo e Isaías Leonardo Salazar Torres. Profesor: Miguel Ángel Gómez Marroquín.

API académica para consultar inventario, revalidar cotizaciones, convertir una versión aceptada en pedido y confirmar/cancelar con reserva transaccional. Integra Domain Model, Specification, máquina de estados, repositorios, Unit of Work, PostgreSQL, Docker Compose y CI/CD.

**[Swagger público](https://ferremax-api-w5kd.onrender.com/docs)** · **[OpenAPI público](https://ferremax-api-w5kd.onrender.com/openapi.json)** · **[Repositorio](https://github.com/Santana-R/ferremax-u3)**

## Versión de trabajo y estado de la entrega

En GitHub Desktop, usar **Fetch origin**, seleccionar **main** y hacer **Pull origin**. `main` es la rama de la entrega PIA; `pia-entrega` conserva su preparación. La etiqueta **[u3-entrega](https://github.com/Santana-R/ferremax-u3/tree/u3-entrega)** permite consultar U3 intacta. El Blueprint final sigue `main`; el [registro de cierre](docs/pia/CIERRE.md) identifica las verificaciones efectivas.

| Parte | Estado comprobable |
| --- | --- |
| Núcleo de seis operaciones, PostgreSQL, Docker y CI/CD | Implementado, con evidencia identificada por commit. |
| Análisis y arquitectura PIA | Documentados y trazados al código y a los procesos pendientes. |
| Reporte y presentación | [Informe PDF](reporte/PIA_FerreMax_Informe.pdf), [Word editable](reporte/PIA_FerreMax_Informe.docx), [presentación](reporte/PIA_FerreMax_Presentacion.pptx) y [PDF de apoyo](reporte/PIA_FerreMax_Presentacion.pdf). |
| Integración y despliegue final | Rama final `main`; comprobar el estado efectivo en el [registro de cierre](docs/pia/CIERRE.md). |
| Procesos amplios de U2 que no tienen flujo ejecutable completo | Conservados como pendientes en el BRD y las matrices. |

## Documentación de la solución

| Documento | Contenido |
| --- | --- |
| [BRD](docs/BRD.md) | Contexto, objetivos, necesidades, reglas, RNF y alcance real. |
| [Historias y criterios](docs/analysis/USER_STORIES.md) | US01-US20 y 46 criterios; [contrato Gherkin](docs/analysis/aceptacion.feature). |
| [BPMN](docs/analysis/BPMN.md) y [glosario](docs/analysis/GLOSARIO.md) | Proceso completo, marcas de implementación y términos comunes. |
| [Arquitectura PIA](docs/architecture/README.md) | DDD/UML, [diagramas editables](docs/architecture/DIAGRAMAS.md), [patrones/SOLID](docs/architecture/PATRONES_SOLID.md) y [ADRs](docs/architecture/DECISIONES.md). |
| [API](docs/api/README.md) | Seis operaciones y [OpenAPI versionado](docs/api/openapi.json). |
| [Docker](docs/DOCKER.md), [CI](docs/CI.md) y [Render](docs/RENDER.md) | Ejecución, pruebas aisladas, despliegue y evidencia. |
| [Trazabilidad de análisis](docs/analysis/trazabilidad_analisis.csv) y [arquitectura](docs/architecture/trazabilidad_arquitectura.csv) | Necesidad/regla/criterio → actividad → código → decisión → prueba. |
| [Matriz de cumplimiento](docs/pia/MATRIZ_CUMPLIMIENTO.md) | Requisitos del profesor y pendientes de la entrega. |
| [Versiones](docs/pia/VERSIONES.md) | U3 conservada, ramas y documentos históricos. |

## Alcance ejecutable

| Operación | Resultado principal |
| --- | --- |
| `GET /inventario/{sku}` | Física, comprometida, tránsito y disponible por ubicación registrada. |
| `POST /cotizaciones/{cotizacion_id}/versiones/{version}/revalidar` | Nueva versión vigente; conserva la anterior sin reservar. |
| `POST /cotizaciones/{cotizacion_id}/versiones/{version}/convertir` | Versión vigente/aceptada → pedido Pendiente ligado al origen, sin reserva. |
| `POST /pedidos/{pedido_id}/confirmar` | Pago de demo autorizado y disponibilidad → Confirmado con reserva atómica. |
| `POST /pedidos/{pedido_id}/cancelar` | Confirmado, sin surtir y con motivo → Cancelado; libera solo su reserva. |
| `GET /pedidos/{pedido_id}` | Estado persistido, folio/versión, total y moneda. |

Con 3 unidades disponibles se pueden reservar 2 o exactamente 3, pero no 4. Disponible es físico menos comprometido, sin sumar tránsito. Un fallo de la segunda partida revierte toda la confirmación; un fallo de liberación revierte toda la cancelación. Las repeticiones inválidas no duplican efectos.

La confirmación es de contado y una ubicación por pedido. Pago y actores HTTP son simulados. Revalidación/conversión consultan S1. Emisión inicial operativa, crédito integral, reducción, multiorigen, transferencias, parciales, surtido, entrega, devolución y panel siguen total o parcialmente pendientes. Registrar auditoría no acredita todavía consulta protegida ni autenticación real. Ver los límites por historia en el BRD.

## Ejecutar con Docker Compose

Requisitos: Docker Desktop abierto, rama de entrega seleccionada y una terminal en la raíz del repositorio. La imagen utiliza Python 3.12 y PostgreSQL 16; el esquema incluye seis tablas.

Si todavía no existe `.env`, crear una copia de la plantilla y definir una contraseña local propia. Si ya existe, conservar su configuración:

```bash
cp .env.example .env
```

Después, con el servidor Uvicorn de VS Code detenido si usa el mismo puerto:

```bash
docker compose config --quiet
docker compose up -d --build --wait app
docker compose ps
```

Abrir [Swagger local](http://127.0.0.1:8000/docs). App conecta a `db:5432`; desde la Mac se usa `127.0.0.1:5433` por defecto. `APP_PORT` y `POSTGRES_PORT` permiten cambiar los puertos publicados. OpenAPI saludable comprueba el servidor; un GET de inventario/pedido comprueba también el acceso a datos.

En una base nueva, cargar explícitamente los datos ficticios:

```bash
docker compose exec app python scripts/cargar_cotizacion_demo.py
```

La carga conserva inventarios, versiones y pedidos ya existentes. No reinicia el recorrido ni reemplaza una cotización revalidada. En una base con la práctica previa se continúa desde su estado real; las guías de API indican las precondiciones de cada operación.

Para detener servicios y conservar el volumen de demostración:

```bash
docker compose stop app db
```

Para volver a iniciarlos:

```bash
docker compose up -d --wait app
```

Después de cambiar código se reconstruye App con `--build`. Ver [persistencia, logs y preparación de datos](docs/DOCKER.md).

## Pruebas y cobertura

Con la DB de Compose disponible:

```bash
docker compose run --build --rm tests
```

El ejecutor crea una base temporal propia, ejecuta la suite con PostgreSQL real y exige cero fallos/errores/omisiones y cobertura >=80%. Elimina solo esa base y conserva la del demo. Los reportes quedan en `reports/docker/<ejecucion>/`, con `junit.xml`, `coverage.json` y `htmlcov/index.html`; están excluidos de Git.

La evidencia de CI/CD de `947aeae` registró **242 pruebas aprobadas, 0 omitidas y 97.24% de cobertura**. No equivale a que las veinte historias estén implementadas. Los resultados E9 y las 235 pruebas del bloque Docker anterior tienen sus propios commits; no se mezclan métricas de ejecuciones distintas.

GitHub Actions construye App/Tests, levanta DB/App, comprueba seis operaciones por HTTP y ejecuta la suite. Conserva reportes como artefactos durante 30 días. Render espera los checks del commit de su rama; [la actualización automática y conservación de datos están verificadas](evidencias/pia/render_cd_verificacion.json).

## Alternativa desde VS Code

Con Python y PostgreSQL disponibles, crear el entorno si aún no existe e instalar dependencias:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
docker compose up -d --wait db
python -m uvicorn ferremax.api.main:app --app-dir src --env-file .env --host 127.0.0.1 --port 8000
```

Detener Uvicorn con Ctrl+C antes de usar App en el mismo puerto. La suite local `python -m pytest -q` omite pruebas PostgreSQL si falta `TEST_DATABASE_URL`; una omisión no acredita integración. La ruta Compose Tests prepara una base separada automáticamente y es la opción reproducible para la suite completa.

| Configuración | Uso |
| --- | --- |
| `DATABASE_URL` | Tiene prioridad para conexión cuando está definida. |
| `POSTGRES_DB/USER/PASSWORD/HOST/PORT` | Conexión local cuando no hay DATABASE_URL; Compose fija host/puerto internos. |
| `APP_PORT` | Puerto de App publicado por Compose. |
| `PORT` | Puerto de escucha del arranque Docker/Render; por defecto 8000. |
| `FERREMAX_INIT_DB`, `FERREMAX_SEED_DEMO` | Flags explícitos de preparación del esquema/semilla; no borran el historial. |

La plantilla `.env.example` contiene ejemplos de reemplazo; `.env` queda excluido de Git y de la imagen.

## Demostración y despliegue

El [Swagger público](https://ferremax-api-w5kd.onrender.com/docs) corresponde a la API 0.6.0. La última evidencia funcional registrada conserva el pedido `4d7b5b3e-926e-4856-9a1e-d1a433ef5cfd`, Cancelado, origen versión 2 y total 240.00 MXN. Puede consultarse sin crear otro pedido. El GET de `FER-API-DEMO` permite revisar inventario; las cantidades actuales dependen de las operaciones posteriores al registro.

Para recorrer escrituras con datos nuevos: consultar, revalidar la versión vencida correcta, convertir una versión vigente/aceptada, conservar el ID devuelto, confirmar y después cancelar. Cada conversión válida crea un pedido nuevo; la semilla no lo elimina ni restablece versiones. No debe ejecutarse el script HTTP de CI sobre una base con historial, porque está preparado para un runner nuevo. Ver [contrato y guías](docs/api/README.md) y [estado del despliegue](docs/RENDER.md).

Render usa API Docker y PostgreSQL por conexión interna. En Free puede haber espera al despertar el servicio; comprobar el acceso antes de una defensa. El reporte y la presentación deberán corresponder a la versión de código que finalmente se integre y despliegue.

## Antecedentes conservados

Los cuatro documentos originales U2 están en [reference/](reference/). El [informe U3](docs/U3Ferremax_Informe.pdf), su [índice de diagramas](docs/Diagramas.md), fuentes en `diagrams/`, matrices antiguas y ADR de `docs/adr/` son antecedentes históricos. La documentación vigente PIA es la enlazada arriba. Las [evidencias E9](evidencias/e9/) y su [integración con U5](docs/E9_INTEGRACION_U5.md) conservan su ejecución original; no se versionan ZIP de transporte.
