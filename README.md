# FerreMax Unidad 3

Propuesta académica de arquitectura de Componentes de lógica de negocio. Equipo 17: Roberto Santana Trujillo e Isaías Leonardo Salazar Torres. Profesor Miguel Ángel Gómez Marroquín.

## Empezar

1. Leer `docs/FerreMax_U3_Informe.pdf`, con el formato de la guía práctica del profesor. La versión editable está en `docs/FerreMax_U3_Informe.docx`.
2. Ver `diagrams/` y sus archivos `.mmd`, `.svg`, PDF y PNG.
3. Leer `docs/ADR_y_Trazabilidad.md` y `docs/Guia_Defensa.pdf`.
4. Ejecutar el demo y las pruebas.

## Demostración reproducible

Python 3.10 o posterior. Memory usa biblioteca estándar y datos simulados; permite revisar el proyecto sin credenciales.

macOS/Linux:

```bash
PYTHONPATH=src python -m ferremax.demo
PYTHONPATH=src python -m unittest discover -s tests -v
```

PowerShell:

```powershell
$env:PYTHONPATH = "src"
python -m ferremax.demo
python -m unittest discover -s tests -v
```

Resultado verificado: 20 pruebas correctas y una integración PostgreSQL omitida por falta de `TEST_DATABASE_URL`. Los registros están en `docs/evidence/`. Esta ejecución no certifica una conexión real con Supabase.

Cinco casos detallados: consultar disponibilidad, revalidar cotización, convertirla en pedido, confirmar contado con reserva y cancelar antes del surtido. El código usa una ubicación por pedido. Crédito normal se evalúa en dominio; crédito excepcional, multiorigen, parciales, transferencias, entregas y devoluciones están diseñados y tienen límites explícitos en el informe.

## PostgreSQL en Supabase

Proyecto nuevo previsto en Santana’s Org. La creación y la prueba conectada permanecen pendientes; no se afirma que Supabase esté configurado ni que la integración haya pasado.

1. Crear un proyecto académico después de verificar su costo.
2. Ejecutar `database/001_schema.sql` mediante administración de ese proyecto.
3. Crear un usuario LOGIN de aplicación y asignarle el rol `ferremax_u3_backend`; usar ese usuario en la conexión de la aplicación. Su contraseña se define fuera del repositorio.
4. Obtener la conexión desde **Connect**. Usar pooler en modo sesión si la red solo ofrece IPv4. Mantener `sslmode=require`.
5. Instalar la dependencia fijada y exportar `DATABASE_URL` en el entorno. `.env.example` es una guía; el código no carga automáticamente archivos `.env`.

```bash
python -m pip install -r requirements.txt
PYTHONPATH=src python scripts/seed_postgres.py
```

Para el ensayo real, definir `TEST_DATABASE_URL` con el usuario de aplicación del proyecto dedicado y ejecutar `tests.test_postgres`. Crea datos sintéticos con IDs únicos y los conserva como evidencia.

```bash
PYTHONPATH=src python -m unittest tests.test_postgres -v
```

El esquema es privado, con RLS y privilegios limitados del backend. No exponerlo a la Data API ni incorporar conexiones reales o claves al Git. La autenticación de personas es una integración posterior; `Actor` en el demo es un contexto confiable simulado.

## Responsabilidades

- `domain/`: reglas, estados y Value Objects.
- `application/`: servicios, contratos, commands, queries y DTO.
- `infrastructure/`: adaptadores Memory y PostgreSQL.
- `database/`: esquema, relaciones y permisos.
- `tests/`: comportamiento, rechazos, rollback y ensayo real separado.
- `docs/`: informe, decisiones, trazabilidad, bitácora y defensa.

Las pruebas Memory no certifican bloqueos ni rendimiento de PostgreSQL. Los eventos se guardan en outbox; el consumidor externo no está implementado. El pago es una autorización registrada de demostración, no un cobro real. El tratamiento financiero de un pago autorizado cuya reserva falle es política pendiente.

## Hallazgo importante en U2

El BPMN dibuja «Reservar para pedido confirmado» antes de procesar el pago/validar crédito. U3 sigue BR05 y US06/US09: primero autorización, después confirmación y reserva atómicas. Los originales de U2 se incluyen sin cambios y el hallazgo se documenta en el informe.

## Entrega

Revisión el 16 de octubre de 2026; NetAcad señala 17 de octubre a las 23:59. Subir el reporte después de revisión del profesor. Todos los integrantes deben revisar y poder defender las decisiones. Los ADR propuestos no simulan una revisión humana ya realizada.

## Regenerar los documentos

Las dependencias de generación están separadas de las del prototipo. En Linux con las fuentes DejaVu instaladas:

```bash
python -m pip install -r requirements-artifacts.txt
python scripts/build_artifacts.py
python scripts/build_report_from_guide.py
```

El primer script genera diagramas y la guía de defensa. El segundo usa el Word original como plantilla para el informe de FerreMax, retirando las instrucciones al alumno, la rúbrica y los ejemplos de otras empresas. El informe editable puede exportarse a PDF desde Word o LibreOffice. `reference/` contiene los documentos originales de U2 y la guía de U3 sin modificaciones.
