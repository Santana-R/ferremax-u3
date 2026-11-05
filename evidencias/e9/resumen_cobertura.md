# Resultado de E9 de FerreMax

Generado: 2026-11-05T06:40:12.676057+00:00. Codigo ejecutado: [07d7ac04aab6372526269c7800e2bb22a547a297](https://github.com/Santana-R/ferremax-u3/tree/07d7ac04aab6372526269c7800e2bb22a547a297).

## Medicion

| Ejecucion y alcance | Lineas cubiertas | Lineas medibles | Cobertura |
| --- | ---: | ---: | ---: |
| Nueve pruebas E9; dominio, servicios y Memory completos | 276 | 293 | 94.20% |
| Nueve pruebas E9; todo src como contraste | 276 | 465 | 59.35% |
| Suite de regresion; todo src | 338 | 465 | 72.69% |

E9: 9/9 casos aprobados.
Regresion: 29 aprobadas, 1 omitida(s),
0 fallidas y 0 errores.

El alcance E9 se declara en scripts/generar_e9.py: incluye sin recortar lineas
model.py, services.py y memory.py, que ejecutan las tres reglas con sus nueve
pruebas. No se omiten ramas de esos archivos. Es cobertura de lineas, no de ramas.
Los JSON completos y htmlcov_global permiten revisar tambien todo src. El
porcentaje E9 no acredita el 80% global que exigira el PIA.

Abrir htmlcov/index.html para E9 y htmlcov_global/index.html para el total.
PostgreSQL sigue pendiente; una prueba omitida no acredita persistencia.
Tampoco existe una pasarela externa: los pagos actuales son autorizaciones
simuladas. Falta justificarlo y completar el ejercicio separado correspondiente.

La matriz se genera leyendo el estado real de cada prueba y su resultado pytest.
observaciones_e9.json conserva pedidos, versiones, reservas, eventos, auditoria
y excepciones observados; resumen_e9.json identifica el codigo con SHA-256.
