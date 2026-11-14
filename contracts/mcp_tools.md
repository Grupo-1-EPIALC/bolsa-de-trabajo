# Contrato · mcp-tools

> **Para:** quien mantiene los workflows de n8n y mcp-tools.
> **Servicio:** `mcp-tools` 0.9.0 (Python, SDK oficial MCP · `ProfiledFastMCP`). **Interno:** sólo lo consume n8n por la red `mcp_internal`; nunca pasa por el gateway.
> **Partes:** 1. Conexión y seguridad · 2. Perfiles de herramientas · 3. Herramientas · 4. Endpoints HTTP · 5. Configuración (`get_agent_settings`) · 6. Datos reales o mocks · 7. Errores. Los `§` de cada parte se refieren a esa parte.
> Los documentos de los que sale este contrato están en [`historico/`](historico/). Todos los ejemplos usan datos ficticios.

---

## 1. Conexión y seguridad

- **URL:** `http://mcp-tools:8000/mcp` (transporte `streamable-http` en Docker; `stdio` en desarrollo local, `MCP_TRANSPORT`).
- **Autenticación** en `/mcp` y `/router/*`: `X-Service-Token`, `X-API-Key`, `Authorization: Bearer` o `?key=` con el `SERVICE_TOKEN`. Los logs enmascaran `key=***`.
- **Parámetros de la conexión:** `?perfil=<perfil>` (qué herramientas ve el agente, §2), `&herramientas=<a,b>` (opcional, §2), `&sesion=<id>` (protección anti-bucle de `leer_skill`) y `&agente=<id>`.
- Hacia los servicios usa `X-Service-Token`: `PROFILE_SERVICE_URL`, `JOBS_SERVICE_URL` y `MATCHING_SERVICE_URL`.
- Todas las herramientas son **de sólo lectura**, salvo `save_recommendation`.
- El puntaje lo calcula matching-service (`compute_match`, `rank_*`): ningún agente lo calcula ni lo modifica (AGENTS §2.2).

## 2. Perfiles de herramientas (`?perfil=`)

| Perfil | Herramientas |
|---|---|
| `planificador` | `get_agent_settings`, `fecha_hora` |
| `cv` | `get_agent_settings`, `resolver_skills`, `leer_skill`, `list_skills`, `validate_json_schema`, `check_grounding`, `fecha_hora` |
| `postulante` | `get_agent_settings`, `resolver_skills`, `leer_skill`, `list_skills`, `get_profile`, `get_job`, `list_active_jobs`, `compute_match`, `missing_skills`, `rank_jobs_for_student`, `search_courses`, `save_recommendation`, `validate_json_schema`, `check_grounding`, `fecha_hora` |
| `empresa` | `get_agent_settings`, `resolver_skills`, `leer_skill`, `list_skills`, `get_job`, `get_profile`, `list_candidate_profiles`, `compute_match`, `missing_skills`, `rank_candidates_for_job`, `save_recommendation`, `validate_json_schema`, `check_grounding`, `fecha_hora` |
| `verificador` | `get_agent_settings`, `resolver_skills`, `leer_skill`, `list_skills`, `validate_json_schema`, `check_grounding`, `fecha_hora` |
| `adjuntos` | `parse_cv_file`, `parse_cv_text`, `leer_archivo` |

**`&herramientas=<a,b>` (opcional):** las herramientas que usa ese agente puntual, separadas por comas. Achica el perfil y nunca lo amplía: una herramienta fuera del perfil se ignora. Vacío (`&herramientas=`) = ninguna herramienta. Sin el parámetro rige el perfil completo. n8n lo arma desde `herramientas` de cada agente (`n8n/agentes/*.json`), así el agente no recibe definiciones que no usa.

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
| `resolver_skills` | `skills` (hasta 50), `profile_skills` (opcional) | Normaliza competencias con el diccionario de matching-service (`POST /api/v1/matches/skills/resolve`, [`matching.md`](matching.md) §5.1). Por cada una: nombre oficial, `implies` (PostgreSQL ⇒ SQL), `equivalents` (MySQL ↔ MariaDB), `similar` (herramientas parecidas que facilitan aprenderla, GitHub ~ GitLab) y, con `profile_skills`, `covered_by` (si el estudiante ya la cubre y con cuál). Sólo lectura. Desde 0.7.0. |
| `search_courses` | `skills`, `limit` | Busca cursos de formación para cubrir las competencias indicadas en `skills`. |
| `save_recommendation` | `profile_id`, `job_id`, `items`, `model`, `prompt_version`, `disclaimer` | Guarda una recomendación generada por IA sellando `origin="AI"`, modelo, versión de prompt y fecha. Única herramienta MCP de escritura. |
| `validate_json_schema` | `schema_name`, `payload_json` | Valida determinísticamente un JSON contra un schema registrado (`cv_standard`, `cv_design`, `student_recommendations`, `company_recommendations`). |
| `check_grounding` | `terms`, `source_text`, `expected_score`, `reported_score` | Verifica que cada competencia/término en `terms` exista en `source_text` (no inventar) y que `reported_score` coincida con `expected_score` (reglas vs. IA). |
| `router_reserve` | `role`, `tried` | Reserva de forma atómica el primer modelo NVIDIA disponible para el rol (`default`, `cv`, `verifier`) respetando el límite RPM y los cooldowns. |
| `router_report_failure` | `model`, `error` | Registra el fallo de un modelo NVIDIA y le aplica cooldown exponencial según el error. |
| `router_report_success` | `model` | Limpia los strikes de fallo de un modelo NVIDIA tras una respuesta exitosa. |
| `router_status` | — | Devuelve el estado actual de usos por minuto/día y cooldowns del router NVIDIA. |

`validate_json_schema` valida contra los schemas registrados en `mcp-tools/app/data/schemas/`: `company_recommendations`, `cv_design`, `cv_standard`, `match_company_recommendations`, `match_student_recommendations`, `student_recommendations`, `verifier_verdict`.

### `cv_standard`: título del perfil (desde 0.9.0)

`cv_standard` suma dos campos opcionales: `headline` (1–140 caracteres) y `headline_source`.
- `headline_source: "cv"`: el título está en el CV (una línea de título u objetivo).
- `headline_source: "suggested"`: el CV no tiene título y la IA lo armó sólo con la carrera, los puestos y las competencias del CV. El estudiante lo revisa antes de guardar.
- Sin contenido para armarlo: `"COMPLETAR_MANUALMENTE"`. Una respuesta sin `headline` sigue siendo válida.

### `cv_design` y la skill `diseno-cv` (desde 0.5.0)

- **Para qué:** el agente `cv_designer` de n8n (WF-07) elige el diseño del CV que genera profile-service. Lee la skill `diseno-cv` con `leer_skill` (perfil `cv`) y valida su salida contra `cv_design`.
- **Forma:** `{"layout": "cronologico" | "primer_empleo" | "competencias", "section_order": [<secciones sin repetir>], "rationale": "<10 a 600 caracteres>"}`. Sin campos extra.
- **Secciones válidas:** `summary`, `skills`, `experience`, `projects`, `education`, `languages`, `certifications`, `volunteering`.
- **Fuente de verdad:** el catálogo vive en profile-service (`app/domain/cv_design.py`). Las enumeraciones del schema y la tabla de la skill se actualizan en el mismo PR si cambia, y profile-service vuelve a validar la respuesta contra su catálogo.

### Formación general: `student_recommendations` y la skill `orientacion-postulante` (desde 0.6.0)

- **Para qué:** el agente `training_advisor` de n8n (WF-06, `mode=training`) recomienda qué competencias sumar o mejorar **en general**. La base son las brechas por reglas de matching-service sobre las ofertas más parecidas al perfil (`skill_gaps`, [`matching.md`](matching.md) parte B §B.2), no una oferta.
- **Forma:** `{"summary"?: "<5 a 600 caracteres>", "items": [{"type": "course" | "skill" | "profile_tip", "skill", "text", "priority": "alta" | "media" | "baja"}]}` con hasta 5 ítems. Ya no existe `type: "project"`: la IA no pide portfolios, proyectos personales ni nada similar.
- **`match_student_recommendations`:** `next_steps` de cada oferta sólo admite `apply` y `profile_tip` (hasta 3). Lo que conviene aprender va en la formación general.

## 4. Endpoints HTTP

| Método y ruta | Para qué |
|---|---|
| `GET /health` | Estado, versión y perfiles disponibles (sin token) |
| `GET /reglas` | Reglas de uso de herramientas (`app/data/reglas.md`) |
| `POST /router/reserve` · `/router/reservar` | Reserva atómica del primer modelo NVIDIA disponible para un rol |
| `POST /router/failure` · `/router/fallo` | Registra el fallo de un modelo (cooldown exponencial) |
| `POST /router/success` · `/router/exito` | Limpia los fallos de un modelo |
| `GET /router/status` · `/router/estado` | Usos por minuto/día y cooldowns |
| `POST /llm/v1/chat/completions` · `GET /llm/v1/models` | Proxy compatible con OpenAI hacia `NVIDIA_BASE_URL` con tiempo máximo (desde 0.10.0, §4.1) |

### 4.1 Proxy del modelo con tiempo máximo (desde 0.10.0)

El nodo `lmChatOpenAi` de n8n no respeta su opción `timeout`: cuando NVIDIA está cargado, la llamada queda colgada minutos y WF-0R nunca pasa al modelo siguiente. Por eso la credencial "OpenAI account" de n8n apunta a `http://mcp-tools:8000/llm/v1` y mcp-tools reenvía cada pedido a NVIDIA:

- **Corta si NVIDIA no manda nada durante `AGENT_LLM_TIMEOUT_SECONDS`** (60 por defecto), ni el primer fragmento ni ninguno de los siguientes, **o si la respuesta no termina en `AGENT_LLM_MAX_SECONDS`** (120): un modelo puede mandar fragmentos sin parar y tardar minutos. Para medirlo, el proxy siempre pide la respuesta en streaming a NVIDIA y la junta entera antes de devolverla: armada (contenido, razonamiento, `tool_calls` y `usage`) si n8n la pidió entera, o como los mismos eventos SSE, todos al final, si la pidió en streaming. Así siempre puede responder un error limpio. Al cortar responde `504` con un error con forma de OpenAI: `{"error": {"code": "LLM_TIMEOUT", "message": "timeout: el modelo <id> no respondió en 60 s"}}`. El agente de n8n falla, WF-0R lo reporta a `/router/failure` (que lo clasifica como transitorio y le da cooldown) y pide otro modelo a `/router/reserve`.
- **Sin razonamiento por defecto:** agrega `chat_template_kwargs: {"enable_thinking": false, "thinking": false}` (respeta lo que mande el pedido). Los modelos de NVIDIA "piensan" miles de tokens antes de contestar: medido, nemotron-3.5-lightning gastó 81 s y 27.700 caracteres sólo razonando ante un pedido largo; sin razonamiento, la importación de un CV bajó a 15–24 s. `AGENT_LLM_THINKING=true` lo vuelve a activar.
- Los logs de mcp-tools dicen qué modelo respondió y en cuánto (`LLM <modelo>: respondió en streaming en 34.8 s`) o cuál se cortó.
- Error de red con NVIDIA → `502 LLM_UPSTREAM_ERROR`. Las demás respuestas de NVIDIA (incluidos `429` y `4xx`) pasan tal cual.
- **No agrega credenciales:** reenvía sólo `Authorization` (la clave de NVIDIA que manda n8n), `Content-Type` y `Accept`. Por eso queda fuera del `SERVICE_TOKEN`. No se publica en el host ni pasa por el gateway.
- **Gemini (Google AI Studio) como primera opción**, opcional: con `GEMINI_ENABLED=true` y `GEMINI_API_KEY`, `GEMINI_MODEL` (default `gemini-2.5-flash`) va primero en `models.default`, `models.cv` y `models.verifier`. El proxy manda los pedidos de ese modelo a `GEMINI_BASE_URL` (endpoint compatible con OpenAI) con `GEMINI_API_KEY`, sin `chat_template_kwargs` y con `reasoning_effort: GEMINI_REASONING_EFFORT` (`none` apaga el razonamiento; vacío no lo manda). La clave sólo está en el entorno de mcp-tools. Si Gemini falla, se pasa del cupo gratuito (`429`) o no contesta a tiempo, el router le da cooldown y sigue con NVIDIA.
- Orden de modelos por defecto, de los rápidos a los grandes: `minimax-m3.1-flash`, `nemotron-3.5-lightning-30b-a3b`, `deepseek-v4.1-flash`, `nemotron-3-ultra-550b-a55b` (el verificador empieza por `nemotron-3.5-lightning`).

## 5. Configuración (`get_agent_settings`)

Devuelve `{ "ok": true, ... }` con:

| Bloque | Campos | Variables |
|---|---|---|
| Modelos | `models.default`, `models.cv`, `models.verifier`, `nvidia_base_url` | `AGENT_MODELS`, `AGENT_MODELS_CV`, `AGENT_MODELS_VERIFIER`, `NVIDIA_BASE_URL` |
| Límites | `rpm_limit`, `llm_timeout_seconds`, `temperature`, `max_verify_retries`, `verify_strict` | `NVIDIA_RPM_LIMIT`, `AGENT_LLM_TIMEOUT_SECONDS`, `AGENT_TEMPERATURE`, `AGENT_MAX_VERIFY_RETRIES`, `AGENT_VERIFY_STRICT` (desde 0.10.0, default `false`: WF-0V toma las competencias no respaldadas como advertencia, sin reintento) |
| `recommendations` | `max_jobs_per_student`, `max_profiles_per_job`, `max_items_per_job`, `min_score` | `RECO_*` |
| `cv` | `max_size_mb`, `allowed_extensions`, `max_text_chars` | `CV_MAX_SIZE_MB`, `CV_ALLOWED_EXTENSIONS`, `CV_MAX_TEXT_CHARS` |
| `notifications` | `enabled`, `min_score`, `max_per_event`, `admin_email`, `frontend_url` | `NOTIFY_ENABLED`, `NOTIFY_MIN_SCORE`, `NOTIFY_MAX_PER_EVENT`, `NOTIFY_ADMIN_EMAIL`, `FRONTEND_URL` |

Fuente: `AGENT_SETTINGS_SOURCE=env` (hoy) o `panel` (un panel HTTP, con respaldo en env). Las cantidades de recomendaciones que ve el usuario las define un admin en matching-service (`/api/v1/matches/settings`).

## 6. Datos reales o mocks

- `MCP_USE_MOCKS=false` (default): `HttpProfileGateway`, `HttpJobsGateway`, `HttpMatchingGateway` y `HttpRecommendationStore` llaman a los servicios reales. Tiene que coincidir con `MATCHING_USE_MOCKS`: WF-06 rankea por MCP los IDs que manda matching-service.
- `MCP_USE_MOCKS=true`: datos ficticios detrás de los mismos puertos, para probar mcp-tools aislado. Los contratos de los mocks están en [`historico/mock_endpoints.yaml`](historico/mock_endpoints.yaml).

## 7. Errores

Cada herramienta devuelve `{ "ok": false, "error": { "code", "message" } }` con un mensaje legible (`not_found`, `invalid_input`, `upstream_error`, …). Los endpoints HTTP responden `401` sin token válido.
