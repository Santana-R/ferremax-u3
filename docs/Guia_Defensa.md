## Qué debes poder explicar
El trabajo transforma las necesidades de FerreMax en responsabilidades del software. Debes poder recorrer un caso: qué solicita el actor, qué servicio lo coordina, dónde se valida cada regla, qué cambia, qué se guarda junto y qué respuesta recibe.
La decisión tecnológica por sí sola no justifica la arquitectura. La evidencia central es que una cotización no reserva, una vencida necesita revalidación y un pedido confirmado debe tener reservas coherentes.
## Lectura de preparación
1. Leer los cinco casos de uso del informe y localizar sus IDs de U2.
2. Leer D02 y señalar Cotizacion, Pedido e InventarioUbicacion.
3. Recorrer D04 y explicar por qué la confirmación y la reserva comparten transacción.
4. Recorrer D05 y explicar el rollback frente a disponibilidad insuficiente.
5. Leer ADR001 y ADR003, incluyendo los costos aceptados.
6. Revisar la bitácora y registrar las correcciones que efectivamente valide cada integrante.
## Exposición breve propuesta
<table fit-page-width="true" header-row="true">
<tr>
<td>Tiempo</td>
<td>Integrante sugerido</td>
<td>Qué explicar</td>
</tr>
<tr>
<td>0:00–1:00</td>
<td>Isaías</td>
<td>FerreMax, problema de última unidad, proceso elegido y continuidad con U2.</td>
</tr>
<tr>
<td>1:00–2:00</td>
<td>Isaías</td>
<td>Comparación de patrones y costo aceptado de Domain Model.</td>
</tr>
<tr>
<td>2:00–3:00</td>
<td>Isaías</td>
<td>Mapa de dominio, raíz, invariante y lenguaje ubicuo.</td>
</tr>
<tr>
<td>3:00–4:30</td>
<td>Roberto</td>
<td>Service Layer, repositorios y secuencia de confirmación.</td>
</tr>
<tr>
<td>4:30–5:30</td>
<td>Roberto</td>
<td>Excepción, rollback, CQRS y evidencia de pruebas.</td>
</tr>
<tr>
<td>5:30–6:00</td>
<td>Ambos</td>
<td>Correcciones SOLID, ADR, límites reales y siguiente validación.</td>
</tr>
</table>
Es una propuesta de reparto, no un acuerdo ya realizado. Ambos deben poder responder sobre las decisiones principales. Conviene practicar una explicación breve usando los diagramas en lugar de leer el informe completo.
## Preguntas para la defensa y respuestas base
<table fit-page-width="true" header-row="true">
<tr>
<td>Pregunta</td>
<td>Respuesta que deben comprender</td>
</tr>
<tr>
<td>¿Qué evidencia pesó más en el patrón?</td>
<td>BR01–03 y BR04–06 conectan cotizaciones, pedidos y reservas; RNF02 y AC-US09-02 exigen proteger la última unidad. Domain Model reúne comportamiento e invariantes; UoW protege el guardado conjunto.</td>
</tr>
<tr>
<td>¿Por qué no basta con consultar stock antes?</td>
<td>La consulta puede quedar desactualizada. Al confirmar se recupera nuevamente el inventario con bloqueo dentro de la transacción y se valida disponible actual.</td>
</tr>
<tr>
<td>¿Por qué PedidoService no calcula disponible?</td>
<td>El servicio coordina. InventarioUbicacion conoce física, reservas y su invariante; evita duplicar la regla en varios servicios.</td>
</tr>
<tr>
<td>¿Pedido cambia antes de reservar?</td>
<td>En el objeto provisional sí; el estado y las reservas se confirman en un único COMMIT. Si la reserva falla, el cambio no queda persistido.</td>
</tr>
<tr>
<td>¿Por qué son agregados distintos?</td>
<td>Pedido protege su ciclo de vida; inventario por SKU/ubicación protege cantidades y reservas. Una transacción puede coordinarlos sin hacer de todo FerreMax una sola raíz.</td>
</tr>
<tr>
<td>¿Qué significa Repository?</td>
<td>Un contrato para recuperar y guardar objetos del negocio. SQL pertenece al adaptador Pg; el dominio no conoce consultas ni conexiones.</td>
</tr>
<tr>
<td>¿Qué aporta CQRS?</td>
<td>Distingue intención de cambiar e intención de consultar. Los DTO de lectura no se reutilizan como entidades modificables. Se mantiene una sola base.</td>
</tr>
<tr>
<td>¿Qué cambió con SOLID?</td>
<td>ubicacion_reserva se ubicó en InventarioRepository; lectores tienen contratos pequeños; servicios reciben fábrica UoW y reloj. Las reglas quedaron en dominio.</td>
</tr>
<tr>
<td>¿Qué propuesta de IA se corrigió?</td>
<td>La responsabilidad ubicada inicialmente en UoW y el orden de bloqueos de revalidación. También se distinguió la prueba Memory de la integración PostgreSQL.</td>
</tr>
<tr>
<td>¿Cuál es el costo de esta decisión?</td>
<td>Más clases y contratos, más coordinación y configuración de PostgreSQL. Se acepta por claridad de reglas y se limita el código a cinco casos.</td>
</tr>
<tr>
<td>¿Se probaron Supabase y todos los requisitos?</td>
<td>No se debe decir eso. Pasaron 20 pruebas locales; faltan el ensayo real PostgreSQL, el rendimiento, la publicación de recursos. El BPMN ya fue revisado.</td>
</tr>
<tr>
<td>¿Qué ocurre con un pago autorizado si no hay stock?</td>
<td>Pedido y reservas se revierten. La solución financiera requiere una política pendiente H05; no se inventó reembolso automático.</td>
</tr>
</table>
## Ejecutar la demostración local
El código existente está en la carpeta ferremax-u3. El núcleo y las pruebas Memory usan la biblioteca estándar; la ejecución final pasó con Python 3.12.14. La conexión PostgreSQL se preparó para Python 3.10 o posterior y Psycopg 3.3.6; su ensayo conectado sigue pendiente.
### macOS o Linux
```bash
cd ferremax-u3
PYTHONPATH=src python3 -m ferremax.demo
PYTHONPATH=src python3 -m unittest discover -s tests -v
```
### PowerShell
```powershell
cd ferremax-u3
$env:PYTHONPATH = "src"
python -m ferremax.demo
python -m unittest discover -s tests -v
```
La demostración consulta cuatro ubicaciones, revalida una cotización vencida, la convierte en pedido, confirma con un pago simulado y cancela antes del surtido. Usa datos simulados y no ejecuta cobros reales.
## Preparar PostgreSQL cuando vuelva la conexión
1. Crear FerreMax U3 en Santana’s Org después de conocer y confirmar el costo del proyecto.
2. Aplicar el esquema privado ferremax_u3 en ese proyecto académico.
3. Crear un usuario de aplicación con el rol ferremax_u3_backend y permisos limitados.
4. Copiar la conexión apropiada desde Connect, conservar SSL y guardarla en una variable de entorno local.
5. Instalar la dependencia fijada y cargar datos simulados.
6. Ejecutar el ensayo de competencia con dos conexiones y documentar su salida real.
7. Revisar RLS, permisos y asesores de seguridad del proyecto.
**Requisito de conexión:** desde una red IPv4 puede usarse el pooler en modo sesión; la documentación de Supabase explica la elección de conexión. No colocar contraseñas ni DATABASE_URL reales en README, código, screenshots o commits.
```plain text
psycopg[binary]==3.3.6
```
**Estado verificable:** no se creó el proyecto FerreMax y no se obtuvo una conexión; esta sección es el procedimiento preparado, no una instalación concluida.
## Organización final del repositorio
<table fit-page-width="true" header-row="true">
<tr>
<td>Ruta</td>
<td>Contenido y propósito</td>
</tr>
<tr>
<td>README.md</td>
<td>Empresa, alcance, instalación, demostración, límites y enlaces reales a entregables.</td>
</tr>
<tr>
<td>docs/</td>
<td>Informe, ADR, matriz, bitácora, glosario actualizado y guía de defensa.</td>
</tr>
<tr>
<td>diagrams/</td>
<td>Fuentes D01–D05 y exportaciones legibles.</td>
</tr>
<tr>
<td>src/ferremax/domain/</td>
<td>Objetos y reglas de negocio.</td>
</tr>
<tr>
<td>src/ferremax/application/</td>
<td>Servicios, comandos, consultas y contratos.</td>
</tr>
<tr>
<td>src/ferremax/infrastructure/</td>
<td>Adaptadores Memory y PostgreSQL.</td>
</tr>
<tr>
<td>database/</td>
<td>Esquema SQL y preparación del rol de aplicación.</td>
</tr>
<tr>
<td>tests/</td>
<td>Escenarios del dominio y colaboración; integración PostgreSQL separada.</td>
</tr>
<tr>
<td>scripts/</td>
<td>Carga de datos simulados y herramientas de generación.</td>
</tr>
<tr>
<td>.env.example y .gitignore</td>
<td>Ejemplo sin secretos y exclusión de credenciales y archivos temporales.</td>
</tr>
</table>
El repositorio nuevo corresponde a la cuenta Santana-R. No existe todavía una URL de FerreMax y no se inventa un enlace. El usuario de Isaías identificado en la conversación es ileosalazar; el correo no necesita aparecer en los documentos académicos ni en el código.
## Comprobación de entregables
<table fit-page-width="true" header-row="true">
<tr>
<td>Entregable de la guía</td>
<td>Situación actual</td>
</tr>
<tr>
<td>Informe de arquitectura</td>
<td>Informe FIME generado y revisado visualmente; copia editable en Markdown.</td>
</tr>
<tr>
<td>Dominio y clases</td>
<td>D01-D03: fuentes Mermaid y vistas SVG, PDF y PNG revisadas.</td>
</tr>
<tr>
<td>Dos secuencias</td>
<td>D04 y D05 con fuente Mermaid y exportaciones SVG, PDF y PNG.</td>
</tr>
<tr>
<td>Trazabilidad</td>
<td>Matrices por necesidad y por regla preparadas, con cobertura y límites.</td>
</tr>
<tr>
<td>Bitácora de IA</td>
<td>Diez iteraciones documentadas; errores, correcciones y decisiones identificados.</td>
</tr>
<tr>
<td>Código base</td>
<td>Código empaquetado y 20 pruebas locales correctas; ensayo PG pendiente.</td>
</tr>
<tr>
<td>GitHub</td>
<td>Creación y publicación pendientes.</td>
</tr>
<tr>
<td>Presentación y defensa</td>
<td>Guion y respuestas base preparados; práctica y revisión humana pendientes.</td>
</tr>
</table>
## Cierre de entrega
La revisión del profesor es el 2026-10-16. La captura indica entrega el 2026-10-17 y exige revisión antes de subir.
El reporte FIME final debe conservar los datos académicos del equipo, presentar vistas legibles de los diagramas y ADR y cerrar con conclusiones que el equipo haya revisado. Las capturas no sustituyen las fuentes en GitHub. No se ha enviado nada a NetAcad.