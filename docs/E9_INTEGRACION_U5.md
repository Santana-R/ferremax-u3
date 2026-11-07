# E9 de FerreMax: evidencia e incorporación por Roberto en U5

**Reparto acordado:** Isaías desarrolla el laboratorio U5. Roberto desarrolla y
revisa E9 en FerreMax y, cuando Isaías comparta el repositorio U5, Roberto subirá
allí las evidencias y el enlace al código mediante sus commits. Esta guía sirve
como referencia técnica y de reproducción; no cambia ese reparto.

El código permanece en [FerreMax](https://github.com/Santana-R/ferremax-u3), rama
`e9-ferremax`. La versión exacta ejecutada aparece como `url_codigo` en el
[resumen de ejecución](../evidencias/e9/resumen_e9.json).

## Estado verificable

Consultar `e9_completa` y `pendientes` en el resumen. Una prueba SKIPPED no cuenta
como aprobada. El generador solo produce `e9_para_U5.zip` cuando se verifican
los nueve casos de negocio, las seis pruebas PostgreSQL, los tres casos del
simulado, la regresión y el umbral de cobertura. En otro caso produce un ZIP de
avance con los pendientes visibles.

El entorno restringido desde el que puede ejecutarse el agente puede impedir
el arranque de PostgreSQL (`shmget: Operation not permitted`). En ese caso no se
acredita persistencia: ejecutar el comando completo desde la terminal normal y
revisar su resultado. El diagnóstico queda en `arranque_postgres_pendiente.txt`.

## Contenido para el repositorio U5

| Archivo o carpeta | Contenido |
| --- | --- |
| [matriz_e9.csv](../evidencias/e9/matriz_e9.csv) | Nueve casos de negocio, trazabilidad, entradas, expectativas, resultados observados, estado y commit. |
| [observaciones_e9.json](../evidencias/e9/observaciones_e9.json) | Estado real de pedidos, versiones, reservas, eventos, auditoría y rechazos. |
| [complementarias_e9.json](../evidencias/e9/complementarias_e9.json) | Resultados y observaciones de persistencia, concurrencia y mocks. |
| [resumen_cobertura.md](../evidencias/e9/resumen_cobertura.md) | Alcance, porcentajes y pendientes. |
| [resumen_e9.json](../evidencias/e9/resumen_e9.json) | Commit, hashes, conteos y estado comprobable. |
| [htmlcov/](../evidencias/e9/htmlcov/index.html) | HTML de los cuatro componentes pertinentes de E9. |
| [htmlcov_global/](../evidencias/e9/htmlcov_global/index.html) | HTML de todo src con la suite completa. |
| ejecucion_e9.txt, ejecucion_regresion.txt, regresion.xml | Salidas reales de las ejecuciones. |
| cobertura_e9.json, cobertura_e9_todo_src.json, cobertura_global.json | Datos que respaldan los porcentajes. |

El ZIP es un paquete local de transporte: reúne las evidencias y estas
instrucciones y queda excluido de Git mediante `.gitignore`. En FerreMax se
versionan las evidencias descomprimidas. Cuando esté disponible el repo U5,
Roberto incorporará una carpeta E9 con esas evidencias descomprimidas y el
enlace permanente en su README/reporte. Las capturas acompañan esos archivos,
no los sustituyen. La incorporación queda pendiente hasta que Roberto lo avise.

## Reglas y decisiones

| Regla | Fuente U2/U3 | Nueve casos |
| --- | --- | --- |
| Confirmar reserva solo lo disponible. | BR04/BR05; US09 | Reservar 2, rechazar 4 y reservar exactamente 3, con 10 físicas y 7 comprometidas. |
| Revalidar una cotización vencida conservando historial. | BR02/BR03; US04/US05 | Crear versión 2 y convertirla; rechazar después y exactamente al vencer. |
| Cancelar antes del surtido libera la reserva propia. | BR06; US10 | Liberar 2 y conservar 7 ajenas; rechazar ya surtido; rechazar una cancelación repetida. |

Se usan fechas UTC fijas, Decimal, datos ficticios y un contexto nuevo por caso.
Siete días es un parámetro simulado del BRD. El vencimiento es un extremo excluido.
El pedido conserva folio y versión aceptados; la versión anterior se compara
completa. Revalidar o convertir no reserva inventario. El Unit of Work coordina
confirmación, reservas, auditoría y eventos; los rechazos conservan los datos.

La prueba de cancelación repetida detectó que se buscaba la reserva ya liberada
antes de validar el pedido. Se corrigió el orden y se conserva el estado anterior
para la auditoría. BRD e historias están en `reference/`; decisiones y trazabilidad
en `docs/`. No se adoptaron las reglas VIP ilustrativas del paquete de datos.

## Persistencia real

`tests/test_e9_persistencia.py` verifica el adaptador PostgreSQL existente:

1. Commit y recuperación del pedido desde otra conexión.
2. Rollback al cerrar sin commit; la cotización no queda almacenada.
3. Fallo en un segundo SKU sin stock: revierte estado y primera reserva.
4. Confirmación y cancelación persistidas, liberación, auditoría y eventos.
5. Revalidación: ambas versiones y pedido ligado a la nueva sobreviven al commit.

`tests/test_postgres.py` aporta el sexto caso: dos conexiones compiten por la
última unidad y solo una confirma. El esquema está en
`tests/sql/ferremax_pruebas.sql`. Si falta la conexión, las pruebas se omiten de
forma visible; no se sustituyen por memoria ni mocks.

## Ausencia de integración externa y ejercicio simulado

FerreMax recibe AutorizacionPago con referencia y booleano; no hay contrato ni
conexión a un proveedor real. Por ello, la exigencia de la guía se trabaja como
un ejercicio separado en `examples/e9_pago_simulado.py`.

El adaptador usa el puerto ProveedorPago. En `tests/test_e9_adaptador_simulado.py`,
Mock sustituye al proveedor. Se verifica una sola llamada por 200.00 MXN y tres
resultados: aprobación confirma/reserva; rechazo y TimeoutError dejan el pedido
Pendiente y todos sus datos intactos. No hay cobros ni llamadas de red. El ejemplo
no agrega una regla comercial ni acredita una pasarela operativa del PIA.

## Reproducción completa

Desde la raíz del repositorio en macOS/Linux, con Python 3.9 a 3.12 compatible
con las ruedas de pgserver (el curso recomienda Python 3.11 o superior):

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-e9.txt
.venv/bin/python scripts/generar_e9.py --postgres-temporal
```

Si el entorno existe, no hace falta crearlo de nuevo. En Windows sustituir el
intérprete por `.venv/Scripts/python.exe`; esa ruta debe comprobarse en el equipo.
Los binarios temporales vienen en pgserver: no se configura un servicio permanente
ni se usa Supabase. En Unix solo se abre un socket privado, con TCP desactivado;
en Windows se usa loopback con credencial temporal. El servidor se detiene al salir.

También se puede configurar TEST_DATABASE_URL hacia una base PostgreSQL de
pruebas, crear el esquema SQL indicado y ejecutar el generador sin la opción
temporal. La URI no se incluye en las evidencias. Sin conexión, el comando sin
opción temporal sirve para generar un avance honesto con omisiones explícitas.

El generador observa los objetos ejecutados: no copia expectativas como resultados.
Para reproducir exactamente una entrega, usar el commit identificado en el resumen.

## Cobertura

El HTML E9 mide los archivos completos `domain/model.py`,
`application/services.py`, `infrastructure/memory.py` y
`infrastructure/postgres.py`. Se publica además todo src como contraste global.
El ejercicio separado se mantiene en examples/ y no se presenta como código
operativo del PIA. La métrica es cobertura de líneas, no garantía de corrección.

Descargar las carpetas HTML completas y abrir `index.html` en un navegador.
GitHub muestra el fuente, no ejecuta la página. El informe distingue los nueve
casos de negocio de las pruebas complementarias y conserva las omisiones.
