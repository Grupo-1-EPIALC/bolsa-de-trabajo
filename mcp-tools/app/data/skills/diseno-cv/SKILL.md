---
name: diseno-cv
description: Elegir, del catálogo cerrado de profile-service, el diseño de CV legible por ATS e IA que mejor presenta el contenido de un estudiante, con el orden de secciones y una justificación breve (contrato cv_design).
---

# Skill: Diseño de CV legible por ATS e IA (`diseno-cv`)

## Objetivo
Elegir el diseño del CV que profile-service genera con los datos confirmados del estudiante. Hay que elegir **uno del catálogo** que viene en el pedido, ordenar las secciones para que lo más fuerte del perfil quede arriba y explicar la elección en una o dos oraciones. El CV lo arma profile-service por reglas: vos **no escribís contenido**, sólo elegís cómo se presenta.

## Qué tienen en común todos los diseños del catálogo
Ya cumplen las prácticas que los sistemas de selección (ATS) y los modelos de IA leen mejor. No hace falta pedirlas ni justificarlas:
- una sola columna, texto real seleccionable y orden de lectura de arriba hacia abajo;
- títulos de sección estándar ("Experiencia", "Educación", "Competencias", "Proyectos"…);
- sin tablas, cuadros de texto, íconos ni gráficos con información;
- datos de contacto en el cuerpo del documento, no en encabezados ni pies de página;
- fechas en un formato único y orden cronológico inverso dentro de cada sección;
- palabras clave en los metadatos del PDF y del DOCX.

Lo único que cambia entre diseños es **el orden de las secciones** y qué se destaca primero.

## Catálogo (lo manda profile-service en cada pedido)
| id | Cuándo conviene | Orden base |
|---|---|---|
| `cronologico` | Tiene experiencia laboral relevante (≥ 12 meses o ≥ 2 puestos). Es el formato que los ATS leen con más precisión. | perfil → experiencia → proyectos → educación → competencias → certificaciones → idiomas → voluntariado |
| `primer_empleo` | Estudiante o recién recibido con poca o ninguna experiencia: la formación y los proyectos sostienen el CV. | perfil → educación → proyectos → competencias → experiencia → voluntariado → certificaciones → idiomas |
| `competencias` | Perfil técnico con muchas competencias y proyectos o certificaciones que las respaldan. Es un híbrido: arriba las competencias, pero la experiencia sigue en orden cronológico. | perfil → competencias → proyectos → experiencia → certificaciones → educación → idiomas → voluntariado |

Si el pedido trae un catálogo distinto a esta tabla, **manda el del pedido**.

## Cómo elegir
1. Leé el resumen del contenido del pedido: meses y cantidad de experiencias, títulos de los puestos, proyectos, competencias, certificaciones, situación académica y puestos buscados.
2. Partí de la elección por reglas que viene en el pedido (`rule_based`). Cambiala sólo si el contenido lo justifica. Por ejemplo:
   - dos pasantías cortas que no tienen relación con los puestos buscados → `primer_empleo` en vez de `cronologico`;
   - pocas competencias, pero proyectos muy alineados con el puesto buscado → `primer_empleo` con proyectos antes que educación.
3. Ajustá `section_order` sólo cuando mejore la lectura: la sección más fuerte para el puesto buscado va arriba.
   - `summary` va siempre primero.
   - Usá únicamente las claves del catálogo y no repitas ninguna.
   - Podés omitir las secciones vacías: profile-service las agrega al final y no las muestra.
4. Escribí `rationale` en español, en segunda persona, en una o dos oraciones (máx. 600 caracteres). Mencioná el dato del contenido que decidió la elección, sin copiar datos personales.

## Lo que nunca hay que hacer
- **No elijas un diseño de dos columnas, con tablas o con gráficos**, ni propongas uno fuera del catálogo: el ATS mezclaría el orden de lectura.
- **No uses el diseño funcional puro** (sólo competencias, sin fechas). Los ATS y quienes seleccionan desconfían de él. Para destacar competencias está `competencias`, que conserva la cronología.
- **No inventes ni completes contenido:** no agregues competencias, puestos ni fechas que no estén en el pedido.
- **No incluyas datos personales:** el pedido no trae nombre, email ni teléfono, y la respuesta tampoco.
- **No recalcules puntajes de compatibilidad:** no forman parte de esta tarea.

## Formato de salida (`cv_design`)
Respondé **sólo** con este JSON y validalo con `validate_json_schema(schema_name="cv_design", payload_json=...)`:

```json
{
  "layout": "primer_empleo",
  "section_order": ["summary", "education", "projects", "skills", "experience"],
  "rationale": "Todavía no tenés experiencia laboral, pero sí tres proyectos con las tecnologías que buscás: conviene mostrar primero tu formación y esos proyectos."
}
```

## Fuentes de las prácticas
Consenso de guías de carrera y de herramientas de CV (2025-2026): una columna, títulos estándar, sin tablas ni cuadros, DOCX o PDF con texto real; el formato cronológico es el más legible para un ATS y el híbrido es el recomendado para estudiantes con poca experiencia; el funcional puro es el de mayor riesgo. Ver `contracts/mcp_tools.md` §cv_design.
