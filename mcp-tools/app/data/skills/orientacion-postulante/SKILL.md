---
name: orientacion-postulante
description: Recomendar al estudiante qué competencias sumar o mejorar, en general, a partir de su perfil y de las ofertas más parecidas, respetando el puntaje por reglas y sin pedir portfolios ni proyectos.
---

# Skill: Orientación de Carrera para Postulantes (`orientacion-postulante`)

## Objetivo
Darle al estudiante hasta 5 recomendaciones concretas y priorizadas (`alta`, `media`, `baja`) para mejorar su empleabilidad **en general**, no para una oferta puntual. Se mantiene la separación estricta entre el motor de reglas (`origin="RULES"`) y las sugerencias de IA (`origin="AI"`).

## Qué pesa en el matching (para orientar bien)
- Lo que más pesa son las **competencias técnicas** (obligatorias, deseables y su nivel) y la **experiencia**: años y, sobre todo, haber usado en el trabajo las competencias que piden las ofertas (`skills_used`).
- Las **condiciones laborales** (modalidad, horario, ubicación, disponibilidad) pesan poco. No las conviertas en recomendaciones de formación.

## Entrada
- `skill_gaps` (calculado por reglas en matching-service): competencias que faltan o quedan cortas en las ofertas activas **más parecidas** al perfil, con `jobs_count`, `share`, `required_in`, `current_level`, `required_level`, `priority` y `similar_to` (una herramienta similar que el estudiante ya sabe y le facilita aprenderla, ej. GitHub para GitLab).
- `similar_jobs`: títulos y score de esas ofertas (sólo como contexto; no los repitas ni los recalcules).
- Un resumen del perfil sin datos personales y los cursos del catálogo (`available_courses`, de `search_courses`).

## Herramientas parecidas y nombres distintos
- Las brechas por reglas ya usan el diccionario de competencias: `Posgres` es PostgreSQL, PostgreSQL implica SQL y MySQL equivale a MariaDB. No recomiendes algo que el estudiante ya tiene con otro nombre.
- Si dudás, llamá a `resolver_skills(skills=[...], profile_skills=[...])`: `covered_by` te dice si ya la cubre y con cuál.
- Si una brecha trae `similar_to`, usala como puente: "como ya usás GitHub, GitLab te va a resultar fácil; empezá por …". Ese aprendizaje es más corto, así que podés proponer algo puntual (la documentación oficial o un curso corto) en vez de un curso largo.

## Cómo armar las recomendaciones
1. Partí de `skill_gaps` en su orden. **Prohibido recalcular, redondear o alterar `score`**.
2. Hasta 5 ítems (`type`: `"course" | "skill" | "profile_tip"`, `skill`, `text`, `priority`):
   - `course`: un curso de `available_courses` (título y proveedor) para una competencia de `skill_gaps`.
   - `skill`: una competencia para sumar o subir de nivel, con una forma concreta de practicarla (ejercicios, documentación oficial, un curso corto). Si `status` es `improve`, decí de qué nivel a qué nivel.
   - `profile_tip`: cómo mostrar mejor algo que ya tiene (por ejemplo, cargar en su experiencia las competencias que usó, `skills_used`, porque la experiencia relevante pesa mucho).
3. Prioridad: respetá la de `skill_gaps` (`alta` si es obligatoria en al menos la mitad de las ofertas parecidas).
4. Agrupá por área cuando varias competencias van juntas (por ejemplo, "frontend: React y TypeScript").
5. Validá el JSON con `validate_json_schema(schema_name="student_recommendations", payload_json=...)`.

## Prohibido
- Pedir **portfolios**, proyectos personales, repositorios de muestra, apps de ejemplo ni nada similar.
- Recomendar algo "para la oferta X": la formación es general.
- Inventar competencias que no estén en `skill_gaps` o en el perfil.
- Recomendar cambiar condiciones laborales (modalidad, horario, ubicación) o el sueldo pretendido.
- Incluir datos personales.

## Salida (`student_recommendations`)
```json
{
  "summary": "Las ofertas más parecidas a tu perfil piden sobre todo React y Docker.",
  "items": [
    { "type": "course", "skill": "React", "text": "Hacé el curso … de …", "priority": "alta" },
    { "type": "skill", "skill": "Docker", "text": "Practicá … para pasar de nivel 1 a 3.", "priority": "media" },
    { "type": "profile_tip", "skill": "Git", "text": "Cargá Git en las competencias que usaste en tu experiencia.", "priority": "baja" }
  ]
}
```
