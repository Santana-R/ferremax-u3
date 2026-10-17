# Diagramas UML del informe final de FerreMax

Estas cinco vistas corresponden al PDF final del equipo, `docs/U3Ferremax_Informe.pdf` (29 páginas).

| ID | Vista | Página del informe |
| --- | --- | --- |
| D01 | Mapa general del dominio | 12 |
| D02 | Clases del dominio | 17 |
| D03 | Aplicación y persistencia | 18 |
| D04 | Confirmación y reserva: flujo principal | 19 |
| D05 | Rechazo por última unidad ya comprometida | 20 |

## Procedencia de los archivos

- `.png`: imagen extraída del PDF, con el contenido y la distribución que aparecen en el informe.
- `.pdf`: recorte de la misma vista, separado del resto de la página.
- `.puml`: fuente editable reconstruida visualmente a partir de esa vista. El PDF no incluye el código PlantUML original; estas fuentes reproducen sus clases, métodos, relaciones y mensajes.
- `.svg`: vista vectorial generada desde la fuente `.puml`. Su distribución puede variar frente a la imagen del informe; la información representada es la misma.
- `fuentes_informe.json`: páginas de origen y hashes SHA-256 para comprobar las exportaciones.

Las fuentes anteriores en Mermaid y los archivos técnicos de segmentación se sustituyen por estas vistas UML; siguen disponibles en el historial Git.

## Reproducir las exportaciones

Desde la raíz del repositorio:

```bash
python -m pip install -r requirements-artifacts.txt
python scripts/export_diagrams_from_report.py
```

Para los SVG se utilizó PlantUML 1.2026.2 con Java 17. D01–D03 usan el motor Smetana incluido en PlantUML, sin instalar Graphviz. Con una copia local de `plantuml.jar`:

```bash
java -Djava.awt.headless=true -jar /ruta/plantuml.jar -checkonly -failfast2 diagrams/*.puml
java -Djava.awt.headless=true -jar /ruta/plantuml.jar -tsvg -failfast2 diagrams/*.puml
```

No se necesita una conexión a la base para revisar estos diagramas. Las secuencias expresan el diseño transaccional; no certifican un ensayo de concurrencia sobre PostgreSQL.
