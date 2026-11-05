# E9 de FerreMax: integración en la entrega U5

Responsables: Roberto desarrolla y revisa las reglas de FerreMax; Isaías integra
esta evidencia con su laboratorio U5. El código se conserva en el repositorio
[FerreMax](https://github.com/Santana-R/ferremax-u3), rama `e9-ferremax`.

**Estado: avance verificable; E9 todavía no está cerrada.** Ya se ejecutan nueve
casos sobre tres reglas. Siguen pendientes la prueba de persistencia real y el
ejercicio separado con un adaptador simulado, con su justificación.

## Qué incorporar en el repositorio U5

Copiar los archivos de evidencia, conservando juntas las carpetas de cobertura:

| Archivo o carpeta | Contenido |
| --- | --- |
| [matriz_e9.csv](../evidencias/e9/matriz_e9.csv) | Nueve casos, reglas e historias, entradas, expectativas, resultados observados, estado pytest y versión del código. |
| [observaciones_e9.json](../evidencias/e9/observaciones_e9.json) | Objetos realmente observados al terminar cada prueba: pedidos, cotizaciones, reservas, eventos, auditoría y rechazos. |
| [resumen_cobertura.md](../evidencias/e9/resumen_cobertura.md) | Resultados numéricos y alcance explícito de cada medición. |
| [resumen_e9.json](../evidencias/e9/resumen_e9.json) | Commit ejecutado, enlace permanente, hashes de los archivos y conteos. |
| [htmlcov/](../evidencias/e9/htmlcov/index.html) | HTML de cobertura de los tres componentes de E9, generado usando sus nueve pruebas. |
| [htmlcov_global/](../evidencias/e9/htmlcov_global/index.html) | HTML de todo src, usando la suite de regresión. |
| ejecucion_e9.txt, ejecucion_regresion.txt, regresion.xml | Salidas reales y resultados de las ejecuciones. |
| cobertura_e9.json, cobertura_e9_todo_src.json, cobertura_global.json | Datos que respaldan los porcentajes publicados. |

El generador también crea `evidencias/e9_avance_para_U5.zip`: contiene estos
archivos y una copia de estas instrucciones. Es un paquete de avance, con los
pendientes indicados; no es una declaración de E9 completa.

En el apartado E9 del README/reporte de U5, incorporar las reglas, los resultados
y el enlace permanente `url_codigo` que aparece en resumen_e9.json. Ese enlace
identifica el commit ejecutado. Las capturas de terminal pueden acompañar las
salidas, pero no sustituyen los archivos ni las instrucciones reproducibles.

**No es necesario duplicar todo el código del PIA en U5:** la entrega debe enlazar
el commit ejecutado y explicar cómo obtener y ejecutar las pruebas en FerreMax.
Si se entrega un ZIP sin acceso a GitHub, habrá que adjuntar el código necesario.

## Reglas, fuentes y decisiones

| Regla operativa | Trazabilidad U2/U3 | Pruebas |
| --- | --- | --- |
| La confirmación reserva solo lo disponible; no compromete mercancía inexistente. | BR04/BR05; US09 | E9-INV-01 a 03: reservar 2, rechazar 4 y reservar exactamente 3, sobre 10 físicas y 7 comprometidas. |
| Una cotización vencida se revalida antes de convertirla, conservando su historial. | BR02/BR03; US04/US05 | E9-COT-01 a 03: revalidar y convertir la versión nueva; rechazar después del vencimiento y exactamente al vencer. |
| Cancelar antes del surtido libera únicamente la reserva propia. | BR06; US10 | E9-CAN-01 a 03: liberar 2 y conservar 7 ajenas; rechazar si ya fue surtido; rechazar una cancelación repetida. |

El BRD y las historias originales están en `reference/`; las decisiones previas y
la trazabilidad están en `docs/`. No se adoptaron automáticamente los descuentos
VIP ni los estados ilustrativos del paquete de datos.

- Los casos usan fechas fijas con zona UTC, Decimal y datos ficticios. La vigencia
  de siete días es el parámetro simulado documentado por el equipo.
- El instante de vencimiento está excluido, conforme a Vigencia.esta_vigente.
- El pedido conserva folio y versión de la cotización aceptada. La versión
  anterior se compara completa con una copia previa.
- Revalidar o convertir no reserva inventario. Confirmar y reservar se coordinan
  mediante Unit of Work; un rechazo conserva los datos anteriores.
- Se comprueban estados y cantidades, además de eventos y auditoría. La prueba
  de cancelación repetida detectó un error de orden: primero se buscaba una
  reserva ya liberada. Se corrigió validando el pedido antes de buscarla; la
  auditoría sigue registrando Confirmado como estado anterior.

## Cómo reproducir

Leer el commit de código en `resumen_e9.json`; clonar FerreMax y cambiar a ese
commit para repetir exactamente la versión entregada. Para seguir trabajando,
usar la rama `e9-ferremax`. Desde la raíz del repositorio, en macOS/Linux:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python scripts/generar_e9.py
```

Si el entorno ya existe, basta con instalar/actualizar las dependencias indicadas
y ejecutar el generador. En Windows, sustituir `.venv/bin/python` por
`.venv\Scripts\python.exe`.

El generador ejecuta las nueve pruebas, observa sus objetos reales y exporta la
matriz. Después ejecuta toda la suite como regresión. Devuelve error si falla una
prueba, si faltan casos o si la cobertura de E9 está por debajo de 80%.

Para leer el HTML hay que descargar la carpeta completa y abrir `index.html`
en el navegador. GitHub muestra su código fuente; no lo ejecuta como página web.

## Alcance de la cobertura

El HTML principal de E9 mide los archivos completos `domain/model.py`,
`application/services.py` e `infrastructure/memory.py`: son los componentes que
ejecutan las tres reglas en estas nueve pruebas. No se recortan sus líneas ni
se excluyen sus validaciones. La métrica es cobertura de líneas.

También se instrumenta y publica todo src. El resumen distingue tres cifras:
alcance E9 con nueve pruebas, todo src con esas mismas nueve y todo src con la
suite completa. La cobertura de E9 no acredita la cobertura global del PIA.
El HTML señala las líneas restantes sin ejecutar; el porcentaje no mide cuántos
defectos se detectaron ni sustituye casos de negocio adecuados.

## Pendientes explícitos

1. Ejecutar una prueba real de persistencia y transacciones. MemoryStore y el
   rollback simulado en memoria no acreditan una base de datos. La prueba
   PostgreSQL se omite sin TEST_DATABASE_URL y no cuenta como prueba aprobada.
2. Documentar la ausencia de un servicio externo real y completar el ejercicio
   separado con adaptador simulado que pide la guía. AutorizacionPago con un
   booleano no es una prueba de interacción con una pasarela externa.
3. Tras completar esos pasos, regenerar y revisar la evidencia antes de presentar
   E9 como terminada.
