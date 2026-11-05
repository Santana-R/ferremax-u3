# Resultado de E9 de FerreMax

Generado: 2026-11-05T07:36:03.923267+00:00. Codigo ejecutado: [cda5b32905c63567767b426a3c9777ef9d2cb027](https://github.com/Santana-R/ferremax-u3/tree/cda5b32905c63567767b426a3c9777ef9d2cb027).

## Medicion

| Ejecucion y alcance | Lineas cubiertas | Lineas medibles | Cobertura |
| --- | ---: | ---: | ---: |
| Bloque E9: nueve casos, persistencia y ejercicio simulado; cuatro componentes | 366 | 389 | 94.09% |
| Mismo bloque E9; todo src como contraste | 414 | 465 | 89.03% |
| Suite de regresion; todo src | 428 | 465 | 92.04% |

E9: 9/9 casos de negocio aprobados.
PostgreSQL real: 6/6 aprobadas.
Ejercicio separado con mocks: 3/3 aprobadas.
Estado: E9 completa tecnicamente; pendiente incorporacion en U5 por Roberto.
Regresion: 38 aprobadas, 0 omitida(s),
0 fallidas y 0 errores.

El alcance E9 se declara en scripts/generar_e9.py: incluye sin recortar lineas
model.py, services.py, memory.py y postgres.py completos. Se ejecutan los nueve
casos de negocio y las nueve pruebas complementarias (persistencia y mocks).
Las omisiones, si existen, aparecen en las salidas. No se recortan esos archivos.
Es cobertura de lineas, no de ramas.
Los JSON completos y htmlcov_global permiten revisar tambien todo src. El
porcentaje E9 no acredita el 80% global que exigira el PIA.

Abrir htmlcov/index.html para E9 y htmlcov_global/index.html para el total.
Una prueba omitida no acredita persistencia. Las pruebas PostgreSQL usan el
adaptador real y conexiones distintas. Las pruebas con Mock son un ejercicio
separado porque no existe una pasarela externa operativa en FerreMax. No se
realizan cobros ni llamadas de red a proveedores.

Pendientes de esta ejecucion: [].

La matriz se genera leyendo el estado real de cada prueba y su resultado pytest.
observaciones_e9.json conserva pedidos, versiones, reservas, eventos, auditoria
y excepciones observados; complementarias_e9.json registra las observaciones de
persistencia y mocks. resumen_e9.json identifica el codigo con SHA-256.
