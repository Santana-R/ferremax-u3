# Primera API de FerreMax: consulta de inventario

## Alcance y recorrido

`GET /inventario/{sku}` consulta la disponibilidad por ubicación. El recorrido es:

1. El adaptador HTTP valida que el código no esté en blanco.
2. `ConsultarDisponibilidadHandler` ejecuta la consulta CQRS existente.
3. `PostgresReader` lee PostgreSQL con una transacción de solo lectura.
4. La API entrega cantidades decimales y un mensaje comprensible para el cliente.

La disponibilidad es existencia física menos comprometida. El inventario en
tránsito se informa por separado. Un producto existente con disponible cero
responde 200; no se confunde con un código sin registros, que responde 404.
Esta consulta corresponde a US01/US02 y al recorrido de disponibilidad de U3.

La API se ejecuta en Python en el equipo; PostgreSQL se ejecuta en Docker.
La [guía de Docker](../DOCKER.md) describe App y Tests en Compose y las
comprobaciones de construcción y arranque en Docker Desktop.
La consulta usa un actor Vendedor simulado del lado del servidor, como el demo
académico; este bloque no implementa autenticación de usuarios.

## Arranque desde la raíz del proyecto

Con Docker Desktop abierto y el archivo `.env` ya preparado:

```bash
.venv/bin/python -m pip install -r requirements-dev.txt
docker compose up -d --wait db
.venv/bin/python scripts/cargar_inventario_demo.py
.venv/bin/python -m uvicorn ferremax.api.main:app --app-dir src --env-file .env --host 127.0.0.1 --port 8000
```

El script de carga crea únicamente el SKU ficticio `FER-API-DEMO` en S1 y S2.
Puede repetirse: no duplica ni sobrescribe filas existentes. En una carga nueva,
S1 tiene 10 físicas, cero comprometidas, cinco en tránsito y 10 disponibles;
S2 tiene todas las cantidades en cero. La consulta GET nunca carga estos datos.

La API usa las variables POSTGRES de `.env`; el host predeterminado es
`127.0.0.1` y el puerto `5433`. Si existe `DATABASE_URL`, tiene prioridad.
La contraseña se pasa al driver con escape de valores y no se incluye en
respuestas ni en el documento OpenAPI. Las versiones de dependencias se fijan
para que este bloque funcione con el Python 3.9 del entorno actual.

Abrir [Swagger local](http://127.0.0.1:8000/docs), expandir la consulta,
seleccionar **Try it out**, introducir el SKU y pulsar **Execute**.
Para detener el servidor usar Ctrl+C en su terminal; PostgreSQL sigue ejecutándose.

## Casos para Swagger

| Entrada o situación | HTTP | Resultado |
| --- | --- | --- |
| `FER-API-DEMO` después de la carga | 200 | Disponibilidad por ubicación; incluye S2 con cero unidades. |
| `PRODUCTO-INEXISTENTE` | 404 | `Producto no encontrado en el inventario.` |
| Un código formado solo por espacios | 400 | `Escribe el código del producto.` |
| Base detenida o configuración incompleta | 503 | `Por el momento no podemos consultar el inventario. Inténtalo de nuevo más tarde.` |

Ejemplo 200 después de una carga nueva:

```json
{
  "mensaje": "Disponibilidad del producto consultada.",
  "sku": "FER-API-DEMO",
  "encontrado": true,
  "ubicaciones": [
    {"ubicacion_id": "S1", "existencia_fisica": "10", "comprometida": "0", "en_transito": "5", "disponible": "10"},
    {"ubicacion_id": "S2", "existencia_fisica": "0", "comprometida": "0", "en_transito": "0", "disponible": "0"}
  ]
}
```

Las cantidades se serializan como cadenas decimales para conservar su precisión.
Los fallos de conexión se traducen a un mensaje de servicio no disponible;
el cliente no recibe credenciales ni detalles internos de SQL.

## Contrato y pruebas

El contrato se obtiene en `/openapi.json`; la copia versionada está en
[`openapi.json`](openapi.json). Después de cambiar rutas o modelos, regenerarla:

```bash
PYTHONPATH=src .venv/bin/python -c 'import json; from pathlib import Path; from ferremax.api.main import app; Path("docs/api/openapi.json").write_text(json.dumps(app.openapi(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")'
```

Pruebas HTTP con lector Memory inyectado y pruebas de configuración:

```bash
.venv/bin/python -m pytest tests/test_api_inventario.py tests/test_api_settings.py -v
```

`tests/test_api_postgres.py` verifica HTTP y PostgreSQL real, conservación de
inventario, producto inexistente, consulta parametrizada y carga idempotente.
Requiere `TEST_DATABASE_URL` y el esquema en una base de pruebas separada;
si falta la conexión, las pruebas se omiten visiblemente. El comando completo
de E9 con PostgreSQL temporal también ejecuta esas pruebas en su regresión.
