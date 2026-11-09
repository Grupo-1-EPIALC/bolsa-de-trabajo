# Contrato · n8n (workflows y agentes de IA)

> **Para:** quien mantiene n8n (workflows, agentes, prompts) y los servicios que lo llaman.
> **Servicio:** n8n con los workflows de `n8n/workflows/` (generados con `python n8n/generate_workflows.py` e importados y publicados por `n8n-init`). Toda la IA del sistema corre acá; no existe `ai-service`.
> **Partes:** 1. Workflows · 2. Webhooks · 3. Extracción de CV (WF-01) · 4. Recomendaciones (WF-06) · 5. Salidas de IA y verificación · 6. Configuración y credenciales · 7. Notificaciones por mail (WF-02 a WF-05). Los `§` de cada parte se refieren a esa parte.
> Los documentos de los que sale este contrato están en [`historico/`](historico/). Todos los ejemplos usan datos ficticios.

---

## 1. Workflows

| Workflow | Qué hace |
|---|---|
| `WF-0R` Agente especialista y Router NVIDIA | Ejecuta al agente pedido con el modelo que reserva el router (`router_*` de mcp-tools) |
| `WF-0V` Verificador | JSON Schema (`validate_json_schema`) + grounding (`check_grounding`) + integridad de score + agente verificador |
| `WF-00` Orquestador | Coordina especialista → verificador, con reintento si rechaza (`AGENT_MAX_VERIFY_RETRIES`) |
| `WF-01` Procesar CV | `POST /webhook/cv-extract`: extrae el CV con el agente CV Structurer (§3) |
| `WF-06` Recomendador | `POST /webhook/recommendations`: análisis de IA sobre el ranking por reglas (§4) |
| `WF-02` a `WF-05` | Notificaciones por mail y errores (§7) |

Todos tienen a `WF-05` como *error workflow*.

## 2. Webhooks

| Ruta | Lo llama | Auth | Respuesta |
|---|---|---|---|
| `POST /webhook/cv-extract` | profile-service | `X-Service-Token` | Síncrona: `cv_suggestions` (§3) |
| `POST /webhook/recommendations` | matching-service | `X-Service-Token` | Guarda el resultado en matching (`/recommendations/batch`) |
| `POST /webhook/job-created` | jobs-service (`job.created`) | `X-Service-Token` | `202` enseguida (§7) |
| `POST /webhook/profile-updated` | profile-service (`profile.updated`) | `X-Service-Token` | `202` enseguida (§7) |
| `POST /webhook/student-offer` | WF-02 (interno) | `X-Service-Token` | `202` |
| `POST /webhook/company-alerts` | WF-03 (interno) | `X-Service-Token` | `202` |

También se acepta `X-Webhook-Token` con `N8N_WEBHOOK_TOKEN`. Sin token válido: `401` con el formato común de error. n8n no pasa por el gateway: los servicios lo llaman por la red interna (`N8N_WEBHOOK_BASE_URL=http://n8n:5678/webhook`).

## 3. Extracción de CV (WF-01)

`POST /webhook/cv-extract` desde profile-service (`services/profile-service/app/infrastructure/n8n_client.py`):

```json
{ "profile_id": "prof-…", "filename": "cv.pdf", "stored_filename": "…", "mime_type": "application/pdf", "content_base64": "…" }
```

- El agente lee el adjunto con mcp-tools (`perfil=adjuntos`: `parse_cv_file`) y devuelve `cv_suggestions` con la forma de `cv_standard`. **Sin `null`:** `"COMPLETAR_MANUALMENTE"` en los escalares que faltan y `[]` en las listas vacías. No inventa competencias que no estén en el CV.
- Lo extraído es una **sugerencia**: profile-service la guarda en `cv_suggestions` y le agrega `profile_draft` + `review_fields` para el front ([`profile.md`](profile.md), parte A §6 y parte D).

## 4. Recomendaciones (WF-06)

`POST /webhook/recommendations` desde matching-service:

```json
{ "mode": "student", "request_id": "req-…", "limit": 5, "profile_id": "prof-…" }
```

- `mode=student` (`profile_id`): ranking con `rank_jobs_for_student` y agente `match_advisor` (`perfil=postulante`).
- `mode=company` (`job_id`): ranking con `rank_candidates_for_job` y `match_advisor` (`perfil=empresa`).
- `mode=training` (`profile_id` + `job_id`): formación con `training_advisor` (`perfil=postulante`) sobre `compute_match` + `missing_skills` + `search_courses`. Lo pide el estudiante desde matching-service. Se guarda con `mode=training` en `/recommendations/batch` (hasta 5 ítems `{type, skill, text, priority}`, sin score) ([`matching.md`](matching.md), parte B §B.2).
- El resultado se guarda con `POST /api/v1/matches/recommendations/batch`, separando `rule_based` (`origin: "RULES"`) de `ai_recommendations` (`origin: "AI"`, `model`, `generated_at`, `prompt_version`, `disclaimer`). Nunca se devuelve un score propio ([`matching.md`](matching.md), parte B).

## 5. Salidas de IA y verificación

- Los agentes responden **sólo JSON** que cumpla su schema: `cv_standard`, `match_student_recommendations`, `match_company_recommendations`, `company_recommendations`, `student_recommendations` y `verifier_verdict`. Los schemas vigentes son los de `mcp-tools/app/data/schemas/` (los usa `validate_json_schema`); las copias anteriores quedaron en [`historico/`](historico/).
- `WF-0V` rechaza una salida si no cumple el schema, si menciona competencias que no están en la fuente (`check_grounding`) o si el score reportado no es el del motor. El orquestador reintenta con la instrucción del verificador.
- Catálogo de agentes en `n8n/agentes/*.json` y prompts versionados en `n8n/prompts/*.md`.

## 6. Configuración y credenciales

- Variables de n8n (`docker-compose.yml`): `MCP_URL`, `PROFILE_SERVICE_URL`, `JOBS_SERVICE_URL`, `MATCHING_SERVICE_URL`, `SERVICE_TOKEN`, `N8N_WEBHOOK_TOKEN`, `SMTP_*`, `N8N_INTERNAL_WEBHOOK_URL`. Los parámetros dinámicos se leen con `get_agent_settings` ([`mcp_tools.md`](mcp_tools.md) §5), nunca con valores fijos.
- `n8n-init` crea en cada arranque las credenciales "OpenAI account" (NVIDIA NIM, desde `NVIDIA_API_KEY`), "SMTP Bolsa" y "Postgres n8n (avisos)", y la tabla `bolsa.notifications_sent`. Después importa y publica los workflows. El repo es la fuente de verdad: los cambios hechos sólo en la UI se pisan al reiniciar.

## 7. Notificaciones por mail (WF-02 a WF-05)

> Fuente: [`historico/notificaciones_n8n.md`](historico/notificaciones_n8n.md).

### 1. Qué workflow manda qué

| Workflow | Disparador | A quién | Qué recibe |
|---|---|---|---|
| **WF-02** · Oferta nueva | `POST /webhook/job-created` (jobs-service, `job.created`) | — | Detecta los candidatos por reglas de la oferta y se los pasa a WF-03. No manda mails |
| **WF-03** · Mails a estudiantes | `POST /webhook/profile-updated` (profile-service, `profile.updated`) | Estudiante | Un **resumen** con las ofertas activas compatibles, cuando su perfil queda buscable |
| | `POST /webhook/student-offer` (interno, desde WF-02) | Estudiante | Un mail por **oferta nueva** compatible |
| **WF-04** · Candidato nuevo | `POST /webhook/company-alerts` (interno, desde WF-03) | Contacto de RR. HH. de la empresa | Aviso de un candidato compatible con una búsqueda activa, **sin nombre ni datos de contacto** |
| **WF-05** · Errores | *Error workflow* de todos los demás | `notifications.admin_email` | Workflow, nodo y error de la ejecución que falló, con link a n8n |

Todos los mails a estudiantes salen de WF-03: así una oferta avisada como "nueva" no se repite en el resumen cuando el estudiante edita su perfil.

---

### 2. Eventos de entrada

Los dos llegan con `X-Service-Token` (también se acepta `X-Webhook-Token` con `N8N_WEBHOOK_TOKEN`). Los servicios publican **best-effort** con un timeout de 3 s, así que cada workflow responde enseguida y manda los mails después.

| Respuesta | Cuándo |
|---|---|
| `202` `{ "accepted": true, "event": "...", "skipped": null }` | Evento válido. `skipped: "not_searchable"` si el perfil no es buscable (WF-03 no sigue) |
| `400` `{ "error": { "code": "INVALID_INPUT", ... } }` | Falta `event`/`job_id`/`profile_id` o el evento no es el esperado |
| `401` `{ "error": { "code": "UNAUTHORIZED", ... } }` | Sin token o token inválido |

#### `job.created` (jobs-service → WF-02)

```json
{ "event": "job.created", "occurred_at": "2026-11-08T14:00:00Z", "job_id": "…", "company_id": "…", "title": "…", "status": "active" }
```

#### `profile.updated` (profile-service → WF-03)

```json
{ "event": "profile.updated", "occurred_at": "…", "profile_id": "prof-…", "user_id": "…", "status": "complete", "version": 3, "searchable": true }
```

Los webhooks internos (`student-offer`, `company-alerts`) son sólo para n8n. No pasan por el gateway, como todo n8n.

---

### 3. Datos que usan (todo por REST con `X-Service-Token`)

| Dato | Servicio |
|---|---|
| Oferta (título, empresa, lugar, `status`) | jobs-service `GET /api/v1/jobs/{id}` |
| Candidatos de una oferta y ofertas de un estudiante, con puntaje por reglas | matching-service `GET /api/v1/matches/jobs/{id}/candidates` y `GET /api/v1/matches/students/{id}/jobs` |
| Puntaje de una oferta nueva para un estudiante | matching-service `POST /api/v1/matches` (se recalcula; nunca se confía en un puntaje que venga en el evento) |
| Email, nombre y **permiso de contacto** del estudiante | profile-service `GET /api/v1/profiles/{id}` → `personal.email`, `personal.name`, `contact_by_email` |
| Contacto de RR. HH. de la empresa | profile-service `GET /api/v1/profiles/companies/{company_id}` → `contact.email` |
| Configuración | mcp-tools `get_agent_settings` → `notifications` (§4) |

#### Reglas

1. **Estudiantes:** sólo reciben mails si `contact_by_email = true` (consentimiento del paso de privacidad). Todos los mails lo recuerdan y explican cómo desactivarlo.
2. **Empresas:** el aviso lleva sólo el snapshot que ya arma matching-service (titular, zona, años de experiencia y competencias) y el puntaje. Nunca el nombre, el email ni el teléfono del candidato. Sin `contact.email` cargado en el perfil de empresa, no hay aviso.
3. **Umbral:** sólo matches con `score ≥ notifications.min_score`, y como mucho `notifications.max_per_event` mails (o ofertas por resumen) por evento.
4. Ofertas cerradas (`status != active`) no se avisan.

---

### 4. Configuración (`get_agent_settings` → `notifications`)

| Campo | Variable (mcp-tools) | Default | Para qué |
|---|---|---|---|
| `enabled` | `NOTIFY_ENABLED` | `true` | Apaga todos los mails de WF-02 a WF-04 |
| `min_score` | `NOTIFY_MIN_SCORE` | `70` | Puntaje mínimo por reglas para avisar (0–100) |
| `max_per_event` | `NOTIFY_MAX_PER_EVENT` | `10` | Tope de mails por evento |
| `admin_email` | `NOTIFY_ADMIN_EMAIL` | vacío | Destino de WF-05. Vacío = no avisa errores |
| `frontend_url` | `FRONTEND_URL` | `http://localhost:8080` | Link de los botones del mail |

SMTP: `n8n-init` crea la credencial **SMTP Bolsa** desde `SMTP_HOST`/`SMTP_PORT`, con `SMTP_USER`/`SMTP_PASSWORD`/`SMTP_SECURE` opcionales para un servidor real. En dev los mails van a Mailpit (http://localhost:8025). El remitente es `Bolsa de Trabajo <SMTP_FROM>`.

---

### 5. Sin mails repetidos (AGENTS §4.6)

- Cada mail tiene un `notification_key`:
  - `profile:{profile_id}|job:{job_id}`: oferta avisada a un estudiante, por WF-03 en cualquiera de sus dos entradas;
  - `job:{job_id}|profile:{profile_id}`: candidato avisado a la empresa (WF-04);
  - `execution:{workflow_id}|{execution_id}`: error avisado (WF-05).
- Antes de mandar, un nodo Postgres **reserva** la clave en `bolsa.notifications_sent` (base propia de n8n) con `INSERT … ON CONFLICT DO NOTHING RETURNING`. Sólo sale el mail cuya clave se reservó. Aunque lleguen varios eventos a la vez, una sola ejecución gana cada clave: se probó con 6 avisos simultáneos de la misma oferta y salió un solo mail.
- La reserva es previa al envío: si el SMTP falla, ese mail no se reintenta (preferimos perder un aviso a duplicarlo) y WF-05 avisa del error.
- La tabla la crea `n8n-init` (`CREATE TABLE IF NOT EXISTS`). Sobrevive a reinicios y a la reimportación de los workflows.

```sql
-- Qué se avisó (base n8n)
SELECT workflow, notification_key, created_at FROM bolsa.notifications_sent ORDER BY created_at DESC LIMIT 50;
```

---

### 6. Cómo probarlo

1. `docker compose up -d --build` (n8n-init importa y publica WF-02 a WF-05).
2. Un estudiante completa su perfil aceptando "contacto por email" → en Mailpit llega "Tenés N ofertas compatibles…". Las empresas de esas ofertas reciben "Nuevo candidato compatible…".
3. Una empresa publica una oferta compatible → el estudiante recibe "Nueva oferta para vos: …".
4. Repetir el evento o editar el perfil no reenvía nada.
5. Con `NOTIFY_ADMIN_EMAIL` cargado, apagar matching-service y publicar una oferta → llega "[n8n] Falló "WF-02 …"".
