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

Las pruebas coordinan dominio y servicio con el adaptador en memoria. No conectan
PostgreSQL ni realizan cobros reales. Estos bloques no constituyen E9 completo:
siguen pendientes la persistencia real y el ejercicio separado con adaptador
simulado. La matriz y los reportes de cobertura se generan con:

```bash
python -m pip install -r requirements-dev.txt
python scripts/generar_e9.py
```

Consultar [las instrucciones de integración en U5](docs/E9_INTEGRACION_U5.md).
El resultado se escribe en `evidencias/e9/` y se empaqueta en
`evidencias/e9_avance_para_U5.zip`. El HTML principal declara el alcance de E9
(dominio, servicios y Memory); se publica además el HTML de todo src con la
suite completa. El porcentaje de E9 no acredita la cobertura global del PIA.

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

