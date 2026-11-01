---
name: extraccion-cv
description: Estructurar el texto extraído de un CV (PDF, DOCX, DOC o MD) en el contrato JSON cv_standard sin inventar competencias ni incluir datos personales sensibles.
---

# Skill: Extracción y Estructuración de CV (`extraccion-cv`)

## Objetivo
Convertir el texto plano de un CV (obtenido mediante `parse_cv_file` / `leer_archivo`) en el bloque estructurado `cv_standard` (`origin="AI"`) para que el estudiante lo revise y confirme antes de actualizar su perfil.

## Reglas obligatorias
1. **Fidelidad estricta al texto fuente (Grounding)**:
   - Extraé **únicamente** competencias (`skills`), experiencias (`experience`), estudios (`education`) e idiomas (`languages`) presentes de forma explícita en el texto del CV.
   - Si un campo no aparece, dejalo vacío (`[]` o `""` / `null`). **Nunca inventes ni deduzcas tecnologías** por asociación.
2. **Estimación de nivel (`level_estimado`)**:
   - Si el CV menciona nivel o seniority para la competencia, mapealo a `1..5` (1: inicial/básico, 2: junior, 3: intermedio/SSR, 4: avanzado/senior, 5: experto/referente).
   - Si sólo nombra la herramienta sin contexto de nivel, devolvé `null`.
3. **Privacidad y exclusión de PII sensible**:
   - No incluyas DNI, CUIL, dirección postal exacta, fecha de nacimiento, estado civil ni datos de salud en ningún campo de salida.
4. **Verificación previa a responder**:
   - Antes de emitir la respuesta final, podés validar tu JSON con `validate_json_schema(schema_name="cv_standard", payload_json=...)` y verificar las competencias con `check_grounding(terms=[...], source_text=...)`.

