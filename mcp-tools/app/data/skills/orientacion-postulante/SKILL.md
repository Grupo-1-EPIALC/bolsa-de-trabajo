---
name: orientacion-postulante
description: Generar recomendaciones accionables de cursos, proyectos y mejoras de perfil para un estudiante frente a una oferta laboral, respetando el puntaje por reglas.
---

# Skill: Orientación de Carrera para Postulantes (`orientacion-postulante`)

## Objetivo
Asistir al estudiante con hasta 5 recomendaciones concretas y priorizadas (`alta`, `media`, `baja`) para mejorar su empleabilidad frente a ofertas activas, manteniendo la separación estricta entre el motor de reglas (`origin="RULES"`) y las sugerencias de IA (`origin="AI"`).

## Flujo de trabajo con herramientas MCP
1. Consultar el perfil (`get_profile`) y la oferta (`get_job` o `list_active_jobs`).
2. Obtener el puntaje determinístico con `compute_match(profile_id, job_id)` y las brechas con `missing_skills(profile_id, job_id)`.
   - **Prohibido recalcular, redondear o alterar `score`**.
3. Buscar cursos reales en el catálogo con `search_courses(skills=[...])` para cubrir las competencias faltantes obligatorias (`required` / `excluding`) y deseables (`desired`).
4. Construir hasta 5 ítems (`type`: `"course" | "project" | "profile_tip"`, `skill`, `text`, `priority`: `"alta" | "media" | "baja"`):
   - Prioridad `alta`: competencias excluyentes u obligatorias faltantes.
   - Prioridad `media`: brechas de nivel en competencias obligatorias o competencias deseables.
   - Prioridad `baja`: mejoras de redacción del perfil o proyectos complementarios.
5. Validar el JSON con `validate_json_schema(schema_name="student_recommendations", payload_json=...)`.

