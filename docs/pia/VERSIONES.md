# Versiones conservadas para el cierre de FerreMax

Registro del 6 de noviembre de 2026. Este documento acompaña el primer bloque de cierre; no reemplaza la entrega histórica U3 ni declara integrado el PIA a main.

| Referencia | Commit de partida | Propósito |
| --- | --- | --- |
| `u3-entrega` (etiqueta anotada) | `eb71b6625c957b9dbfe7e4ed54f7c9f8ad08f365` | Identifica exactamente el main de U3 anterior a la integración del PIA. |
| `main` al iniciar este cierre | `eb71b6625c957b9dbfe7e4ed54f7c9f8ad08f365` | U3 conservada; su calificación todavía no aparecía en NetAcad según Roberto. |
| `pia-render` al iniciar este cierre | `52863c9f938f6aa89e34c59b62c7e13ce78f0d4d` | Último avance técnico y evidencia CI/CD disponible. |
| `pia-entrega` | Parte de `52863c9f938f6aa89e34c59b62c7e13ce78f0d4d` | Única rama para matriz, análisis, arquitectura y entregables del cierre. Los commits posteriores de esta rama no mueven la etiqueta U3. |

## Acceso a las versiones

- [U3 conservada](https://github.com/Santana-R/ferremax-u3/tree/u3-entrega).
- [Código y documentos del cierre](https://github.com/Santana-R/ferremax-u3/tree/pia-entrega).
- [Matriz de cumplimiento](MATRIZ_CUMPLIMIENTO.md) y [CSV de los 36 requisitos](matriz_cumplimiento.csv).

La etiqueta fija una referencia consultable al commit de U3. Crear una etiqueta no constituye una nueva evaluación ni cambia la calificación en NetAcad.

## Comprobaciones de conservación

- Se verificaron los heads remotos de main y pia-render mediante consulta de GitHub antes de preparar el cierre: coinciden con los commits de esta tabla.
- `main...pia-render` devolvió 0 commits exclusivos de main y 25 exclusivos del avance PIA. La historia U3 es ancestro de la rama PIA.
- La comparación de `reference/`, `diagrams/` y los PDF históricos de `docs/` entre main y pia-render no mostró cambios. Este bloque solo añade `docs/pia/`.
- Las ramas locales de avance son ancestros de la base de pia-entrega; no necesitan fusiones individuales. No se borraron ramas.
- Render conserva su seguimiento a `pia-render`; cambiarlo a main corresponde al bloque de integración posterior.

## Huellas de los documentos históricos

SHA-256 calculado sobre los archivos originales al preparar el cierre. Permite contrastarlos sin generar copias adicionales.

| Archivo | SHA-256 |
| --- | --- |
| [docs/ADR_Trazabilidad_BitacoraIA.pdf](<../../docs/ADR_Trazabilidad_BitacoraIA.pdf>) | `1e87ece05b26b27370aa0a8c6e977009134f3fd3248604548790d6a747c47935` |
| [docs/U3Ferremax_Informe.pdf](<../../docs/U3Ferremax_Informe.pdf>) | `dd2398f256c533fd3e05666a3034aa35a554186297ff38330ac5f5c347b4359d` |
| [reference/EQ17FerreMax_BPMN(1).pdf](<../../reference/EQ17FerreMax_BPMN(1).pdf>) | `faf4451e566722a5be03bdd6fa98ad911081aeb2f90e3d151eeaf643f38ab59a` |
| [reference/EQ17FerreMax_BRD(1).pdf](<../../reference/EQ17FerreMax_BRD(1).pdf>) | `2fa9e01bea9f9c29c7848b9b22e334cc740ffad1bfa6cd54a2781fee22eb81fb` |
| [reference/EQ17FerreMax_Glosario(1).pdf](<../../reference/EQ17FerreMax_Glosario(1).pdf>) | `7facdb47907b7fcabfdda074490fc32564484d5afa02cd235780b7542f8df61b` |
| [reference/EQ17FerreMax_UserStories(1).pdf](<../../reference/EQ17FerreMax_UserStories(1).pdf>) | `4b5130485d34fae46d1d46eb5548aadbc6ac21f478d033ae8153eff971c262a3` |

## Cómo continuar desde GitHub Desktop

En el clon habitual de Roberto: **Fetch origin**, abrir **Current Branch**, seleccionar **pia-entrega** y usar **Pull origin** si hay cambios disponibles. La etiqueta `u3-entrega` también permite consultar la versión histórica desde la página de GitHub.

El clon de trabajo de este bloque está en `/Users/robertosantana/Documents/ChatGPT/CLNEG/ferremax-u3`; el clon habitual de Desktop está en `/Users/robertosantana/Documents/GitHub/ferremax-u3`. Ambos apuntan al mismo repositorio remoto. No se copian archivos ni se modifican manualmente los datos del clon habitual.

La integración final se realizará conservando el historial y la referencia a U3; no se ha realizado en este bloque.
