# Contrato · mcp-tools

> **Para:** quien mantiene los workflows de n8n y mcp-tools.
> **Servicio:** `mcp-tools` 0.4.0 (Python, SDK oficial MCP · `ProfiledFastMCP`). **Interno:** sólo lo consume n8n por la red `mcp_internal`; nunca pasa por el gateway.
> **Partes:** 1. Conexión y seguridad · 2. Perfiles de herramientas · 3. Herramientas · 4. Endpoints HTTP · 5. Configuración (`get_agent_settings`) · 6. Datos reales o mocks · 7. Errores. Los `§` de cada parte se refieren a esa parte.
> Los documentos de los que sale este contrato están en [`historico/`](historico/). Todos los ejemplos usan datos ficticios.

---

## 1. Conexión y seguridad

- **URL:** `http://mcp-tools:8000/mcp` (transporte `streamable-http` en Docker; `stdio` en desarrollo local, `MCP_TRANSPORT`).
- **Autenticación** en `/mcp` y `/router/*`: `X-Service-Token`, `X-API-Key`, `Authorization: Bearer` o `?key=` con el `SERVICE_TOKEN`. Los logs enmascaran `key=***`.
- **Parámetros de la conexión:** `?perfil=<perfil>` (qué herramientas ve el agente, §2), `&sesion=<id>` (protección anti-bucle de `leer_skill`) y `&agente=<id>`.
- Hacia los servicios usa `X-Service-Token`: `PROFILE_SERVICE_URL`, `JOBS_SERVICE_URL` y `MATCHING_SERVICE_URL`.
- Todas las herramientas son **de sólo lectura**, salvo `save_recommendation`.
- El puntaje lo calcula matching-service (`compute_match`, `rank_*`): ningún agente lo calcula ni lo modifica (AGENTS §2.2).

## 2. Perfiles de herramientas (`?perfil=`)

| Perfil | Herramientas |
|---|---|
| `planificador` | `get_agent_settings`, `fecha_hora` |
| `cv` | `get_agent_settings`, `leer_skill`, `list_skills`, `validate_json_schema`, `check_grounding`, `fecha_hora` |
| `postulante` | `get_agent_settings`, `leer_skill`, `list_skills`, `get_profile`, `get_job`, `list_active_jobs`, `compute_match`, `missing_skills`, `rank_jobs_for_student`, `search_courses`, `save_recommendation`, `validate_json_schema`, `check_grounding`, `fecha_hora` |
| `empresa` | `get_agent_settings`, `leer_skill`, `list_skills`, `get_job`, `get_profile`, `list_candidate_profiles`, `compute_match`, `missing_skills`, `rank_candidates_for_job`, `save_recommendation`, `validate_json_schema`, `check_grounding`, `fecha_hora` |
| `verificador` | `get_agent_settings`, `leer_skill`, `list_skills`, `validate_json_schema`, `check_grounding`, `fecha_hora` |
| `adjuntos` | `parse_cv_file`, `parse_cv_text`, `leer_archivo` |

## 3. Herramientas

La descripción de cada herramienta es lo que lee el LLM (docstring en `mcp-tools/app/tools/registry.py`).

| Herramienta | Parámetros | Qué hace |
|---|---|---|
| `get_agent_settings` | — | Devuelve la configuración vigente de los agentes (modelos NVIDIA por rol, límites RPM, reintentos del verificador, topes de recomendaciones, formatos de CV y mails de notificación: `notifications.min_score`… |
| `fecha_hora` | — | Devuelve la fecha (`today`) y hora actual (`iso_now`) en UTC. |
| `list_skills` | — | Lista las skills del proyecto disponibles para leer con `leer_skill`. |
| `leer_skill` | `id`, `archivo`, `desde` | Devuelve las instrucciones completas de una skill del proyecto (de tu lista 'Skills del proyecto'). Leé solo las 1 a 2 más relevantes, una vez cada una, y respondé. |
| `parse_cv_file` | `content_base64`, `filename`, `mime_type` | Convierte un CV en base64 (PDF, DOCX, DOC o MD; máx. configurado en CV_MAX_SIZE_MB) a texto plano para estructurar sin inventar información. |
| `parse_cv_text` | `content_base64`, `filename`, `mime_type` | Alias de `parse_cv_file` compatible con AGENTS.md §4.6: extrae texto plano de un CV. |
| `leer_archivo` | `contenido_base64`, `nombre`, `mime` | Alias compatible con el nodo MCP Client de n8n (`agentes`): convierte a texto un archivo en base64 (PDF, DOCX, DOC o MD) y devuelve `{archivo, tipo, truncado, texto}`. |
| `get_profile` | `profile_id` | Obtiene el perfil completo de un estudiante por su `profile_id`. |
| `list_candidate_profiles` | `skills`, `limit` | Lista perfiles de candidatos filtrando opcionalmente por competencias (`skills`). |
| `get_job` | `job_id` | Obtiene los detalles y requisitos de una oferta laboral por su `job_id`. |
| `list_active_jobs` | `limit` | Lista las ofertas laborales activas hasta el tope configurado. |
| `compute_match` | `profile_id`, `job_id` | Calcula el puntaje de compatibilidad por reglas (`origin="RULES"`). El LLM NUNCA debe recalcular ni modificar este puntaje. |
| `rank_jobs_for_student` | `profile_id`, `limit` | Ranking por reglas (`origin="RULES"`) de las ofertas compatibles para un estudiante, ya ordenado y filtrado por condiciones laborales. Cada ítem trae `rank`, el snapshot de la oferta (`job`) y el `match` (score… |
| `rank_candidates_for_job` | `job_id`, `limit` | Ranking por reglas (`origin="RULES"`) de los candidatos compatibles para una oferta, sin datos personales. Cada ítem trae `rank`, el snapshot del candidato (`candidate`) y el `match`. `limit=0` usa la cantidad… |
| `missing_skills` | `profile_id`, `job_id` | Devuelve las competencias faltantes y brechas de nivel entre un perfil y una oferta, ordenadas por prioridad (`alta`, `media`, `baja`). |
| `search_courses` | `skills`, `limit` | Busca cursos de formación para cubrir las competencias indicadas en `skills`. |
| `save_recommendation` | `profile_id`, `job_id`, `items`, `model`, `prompt_version`, `disclaimer` | Guarda una recomendación generada por IA sellando `origin="AI"`, modelo, versión de prompt y fecha. Única herramienta MCP de escritura. |
| `validate_json_schema` | `schema_name`, `payload_json` | Valida determinísticamente un JSON contra un schema registrado (`cv_standard`, `cv_design`, `student_recommendations`, `company_recommendations`). |
| `check_grounding` | `terms`, `source_text`, `expected_score`, `reported_score` | Verifica que cada competencia/término en `terms` exista en `source_text` (no inventar) y que `reported_score` coincida con `expected_score` (reglas vs. IA). |
| `router_reserve` | `role`, `tried` | Reserva de forma atómica el primer modelo NVIDIA disponible para el rol (`default`, `cv`, `verifier`) respetando el límite RPM y los cooldowns. |
| `router_report_failure` | `model`, `error` | Registra el fallo de un modelo NVIDIA y le aplica cooldown exponencial según el error. |
| `router_report_success` | `model` | Limpia los strikes de fallo de un modelo NVIDIA tras una respuesta exitosa. |
| `router_status` | — | Devuelve el estado actual de usos por minuto/día y cooldowns del router NVIDIA. |

`validate_json_schema` valida contra los schemas registrados en `mcp-tools/app/data/schemas/`: `company_recommendations`, `cv_design`, `cv_standard`, `match_company_recommendations`, `match_student_recommendations`, `student_recommendations`, `verifier_verdict`.

### `cv_design` y la skill `diseno-cv` (desde 0.5.0)

- **Para qué:** el agente `cv_designer` de n8n (WF-07) elige el diseño del CV que genera profile-service. Lee la skill `diseno-cv` con `leer_skill` (perfil `cv`) y valida su salida contra `cv_design`.
- **Forma:** `{"layout": "cronologico" | "primer_empleo" | "competencias", "section_order": [<secciones sin repetir>], "rationale": "<10 a 600 caracteres>"}`. Sin campos extra.
- **Secciones válidas:** `summary`, `skills`, `experience`, `projects`, `education`, `languages`, `certifications`, `volunteering`.
- **Fuente de verdad:** el catálogo vive en profile-service (`app/domain/cv_design.py`). Las enumeraciones del schema y la tabla de la skill se actualizan en el mismo PR si cambia, y profile-service vuelve a validar la respuesta contra su catálogo.

## 4. Endpoints HTTP

| Método y ruta | Para qué |
|---|---|
| `GET /health` | Estado, versión y perfiles disponibles (sin token) |
| `GET /reglas` | Reglas de uso de herramientas (`app/data/reglas.md`) |
| `POST /router/reserve` · `/router/reservar` | Reserva atómica del primer modelo NVIDIA disponible para un rol |
| `POST /router/failure` · `/router/fallo` | Registra el fallo de un modelo (cooldown exponencial) |
| `POST /router/success` · `/router/exito` | Limpia los fallos de un modelo |
| `GET /router/status` · `/router/estado` | Usos por minuto/día y cooldowns |

## 5. Configuración (`get_agent_settings`)

Devuelve `{ "ok": true, ... }` con:

| Bloque | Campos | Variables |
|---|---|---|
| Modelos | `models.default`, `models.cv`, `models.verifier`, `nvidia_base_url` | `AGENT_MODELS`, `AGENT_MODELS_CV`, `AGENT_MODELS_VERIFIER`, `NVIDIA_BASE_URL` |
| Límites | `rpm_limit`, `llm_timeout_seconds`, `temperature`, `max_verify_retries` | `NVIDIA_RPM_LIMIT`, `AGENT_LLM_TIMEOUT_SECONDS`, `AGENT_TEMPERATURE`, `AGENT_MAX_VERIFY_RETRIES` |
| `recommendations` | `max_jobs_per_student`, `max_profiles_per_job`, `max_items_per_job`, `min_score` | `RECO_*` |
| `cv` | `max_size_mb`, `allowed_extensions`, `max_text_chars` | `CV_MAX_SIZE_MB`, `CV_ALLOWED_EXTENSIONS`, `CV_MAX_TEXT_CHARS` |
| `notifications` | `enabled`, `min_score`, `max_per_event`, `admin_email`, `frontend_url` | `NOTIFY_ENABLED`, `NOTIFY_MIN_SCORE`, `NOTIFY_MAX_PER_EVENT`, `NOTIFY_ADMIN_EMAIL`, `FRONTEND_URL` |

Fuente: `AGENT_SETTINGS_SOURCE=env` (hoy) o `panel` (un panel HTTP, con respaldo en env). Las cantidades de recomendaciones que ve el usuario las define un admin en matching-service (`/api/v1/matches/settings`).

## 6. Datos reales o mocks

- `MCP_USE_MOCKS=false` (default): `HttpProfileGateway`, `HttpJobsGateway`, `HttpMatchingGateway` y `HttpRecommendationStore` llaman a los servicios reales. Tiene que coincidir con `MATCHING_USE_MOCKS`: WF-06 rankea por MCP los IDs que manda matching-service.
- `MCP_USE_MOCKS=true`: datos ficticios detrás de los mismos puertos, para probar mcp-tools aislado. Los contratos de los mocks están en [`historico/mock_endpoints.yaml`](historico/mock_endpoints.yaml).

## 7. Errores

Cada herramienta devuelve `{ "ok": false, "error": { "code", "message" } }` con un mensaje legible (`not_found`, `invalid_input`, `upstream_error`, …). Los endpoints HTTP responden `401` sin token válido.
