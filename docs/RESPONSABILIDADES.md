# Responsabilidades de cada integrante

> Grupo 1 · Bolsa de Trabajo. Armado a partir del historial de Git y de [PROMPTS.md](../PROMPTS.md) al 12/11/2026. **Revisar y completar antes de entregar** (apellidos, roles acordados y lo que no haya quedado registrado en Git).

## Detalle por integrante

### Andres Allievi
- Plan inicial del MVP y reglas de desarrollo con IA (AGENTS.md).
- Contenedores, `docker-compose.yml`, volúmenes externos, arranque de n8n (`bootstrap.sh`), gateway y pipeline de CI.
- `profile-service`: perfil del estudiante y de la empresa, subida del CV a n8n, borrador de la IA, generación del CV en PDF/DOCX.
- `matching-service`: puntaje por reglas, competencias faltantes, diccionario de competencias, pedidos de recomendaciones a la IA.
- `mcp-tools` y los 10 workflows de n8n (agentes, verificador, router de modelos y notificaciones).
- Panel de administración: endpoints de admin en `auth-service`, eventos de cuenta y pantallas del front.
- Pantallas del front de estudiante y empresa conectadas a los contratos (alta de perfil, ofertas, formación, diseño del CV).

### Dario Calvo
- Primera maqueta de la SPA, cliente HTTP desacoplado y modo con datos de prueba.
- Flujos de autenticación en el front: recuperar contraseña, confirmar cambio de correo, configuración de la cuenta.
- Desglose del puntaje por reglas y perfil público de la empresa desde una oferta.
- Correcciones: errores 422 al guardar el perfil, persistencia del aviso de sugerencias de la IA, manejo de 404, parpadeo del asistente de CV, navegación.
- Integración de ramas del front (panel de admin + autenticación) y etiquetado de los tests de Vitest.

### Elian Nahuel
- Plan de implementación de `jobs-service` a partir de los contratos.
- Implementación por capas (dominio, aplicación, infraestructura, API), 12 ofertas de ejemplo y tests.
- Revisión y correcciones: bloqueo optimista (409), validaciones, límites de entrada.
- Contrato de búsquedas consolidado para el front, matching, auth y n8n.

### Luciano Dato
- Servicio de autenticación en NestJS: entidades, registro, login, rotación de refresh token, validación de CUIT, mails de recuperación.
- Documento de respuestas de la API de auth, que luego pasó a `contracts/auth.md`.
- **Revisión y aprobación de los Pull Requests:** verifica que cada cambio cumpla la plantilla de PR (`.github/pull_request_template.md`), que el CI pase, que respete los contratos y las reglas de AGENTS.md y que el prompt usado esté registrado en PROMPTS.md, antes de aprobar el merge a `dev`.