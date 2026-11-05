# Resultado de E9 de FerreMax

Generado: 2026-11-05T07:27:30.643744+00:00. Codigo ejecutado: [60a218a6d67559156fd9b339ca0253a13db6518d](https://github.com/Santana-R/ferremax-u3/tree/60a218a6d67559156fd9b339ca0253a13db6518d).

## Medicion

| Ejecucion y alcance | Lineas cubiertas | Lineas medibles | Cobertura |
| --- | ---: | ---: | ---: |
| Bloque E9: nueve casos, persistencia y ejercicio simulado; cuatro componentes | 312 | 389 | 80.21% |
| Mismo bloque E9; todo src como contraste | 353 | 465 | 75.91% |
| Suite de regresion; todo src | 374 | 465 | 80.43% |

E9: 9/9 casos de negocio aprobados.
PostgreSQL real: 0/6 aprobadas.
Ejercicio separado con mocks: 3/3 aprobadas.
Estado: AVANCE; persistencia o verificaciones pendientes.
Regresion: 32 aprobadas, 6 omitida(s),
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

Pendientes de esta ejecucion: ["Ejecutar las seis pruebas reales PostgreSQL: cinco de persistencia y una de concurrencia"].

La matriz se genera leyendo el estado real de cada prueba y su resultado pytest.
observaciones_e9.json conserva pedidos, versiones, reservas, eventos, auditoria
y excepciones observados; complementarias_e9.json registra las observaciones de
persistencia y mocks. resumen_e9.json identifica el codigo con SHA-256.
