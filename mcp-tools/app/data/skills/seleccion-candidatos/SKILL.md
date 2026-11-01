---
name: seleccion-candidatos
description: Asistir a empresas en la evaluación de candidatos rankeados por reglas para una búsqueda activa, redactando justificaciones objetivas basadas en brechas y fortalezas reales.
---

# Skill: Evaluación y Recomendación de Candidatos para Empresas (`seleccion-candidatos`)

## Objetivo
Explicar de forma transparente y objetiva por qué cada candidato preseleccionado por el motor de reglas (`compute_match`, `origin="RULES"`) se ajusta a una oferta laboral y qué brechas presenta (`missing_skills`).

## Reglas obligatorias
1. **Invariante de Ranking y Score**:
   - El orden de los candidatos y su `score` provienen **exclusivamente** de `compute_match`.
   - Jamás reordenes candidatos ni modifiques el valor numérico de `score`.
2. **Evidencia verificable (Grounding)**:
   - En `strengths` y `justification`, mencioná únicamente competencias que figuren efectivamente en el perfil del candidato (`get_profile`) y en la oferta (`get_job`).
   - En `gaps`, reflejá las brechas devueltas por `missing_skills`.
3. **Prioridad de contacto (`alta | media | baja`)**:
   - `alta`: `score >= 75` y sin excluyentes faltantes.
   - `media`: `score` entre `50` y `74`.
   - `baja`: `score < 50` o con requisito excluyente faltante.
4. **Validación**:
   - Verificá la estructura con `validate_json_schema(schema_name="company_recommendations", payload_json=...)`.

