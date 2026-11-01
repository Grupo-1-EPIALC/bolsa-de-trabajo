---
name: verificacion-grounding
description: Auditar salidas de los agentes especialistas verificando cumplimiento de JSON Schema, grounding anti-alucinación, integridad del score por reglas y ausencia de datos sensibles.
---

# Skill: Verificación de Calidad, Schema y Grounding (`verificacion-grounding`)

## Objetivo
Actuar como juez de calidad (`Verificador`) antes de entregar cualquier salida de un agente especialista (`cv_structurer`, `training_advisor`, `company_advisor`).

## Checklist de auditoría
1. **Cumplimiento de JSON Schema**:
   - Ejecutar `validate_json_schema(schema_name, payload_json)` con el schema correspondiente (`cv_standard`, `student_recommendations`, `company_recommendations`).
2. **Grounding anti-alucinación**:
   - Ejecutar `check_grounding(terms, source_text, expected_score, reported_score)` para comprobar que todas las competencias citadas existan en el CV o perfil/oferta fuente.
3. **Separación Reglas vs. IA**:
   - Verificar que el score no haya sido alterado respecto del calculado por `compute_match` (`origin="RULES"`).
4. **Privacidad**:
   - Confirmar que no se filtren DNI, dirección postal ni datos sensibles.
5. **Formato de veredicto**:
   - Responder únicamente con JSON válido: `{"cumple": true|false, "faltantes": [...], "instruccion": "..."}`.

