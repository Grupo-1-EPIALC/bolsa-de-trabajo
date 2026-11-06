# AGENTS.md — Reglas e instrucciones para agentes · MVP Bolsa de Trabajo

> Este archivo vive en la raíz del repositorio. Lo leen **las personas del equipo** y **los asistentes de IA de código** (Claude, Copilot, Cursor, Antigravity, etc.) antes de tocar el proyecto. También define el comportamiento de los **agentes de IA en tiempo de ejecución** (`n8n` + `mcp-tools`).
> El historial de prompts y resumen de respuestas se registra en un archivo independiente: **[`PROMPTS.md`](PROMPTS.md)**.
> Todo cambio a este archivo se hace en una rama `docs/agents/vX.Y.Z-<desc>` (o junto al PR de la funcionalidad que actualiza las reglas) con PR a `dev`.

---

## 0. Índice

1. Contexto del proyecto
2. Reglas generales (aplican a todos los agentes)
3. Flujo Git obligatorio
4. Agentes de desarrollo (uno por servicio/rol)
5. Agentes en tiempo de ejecución (`n8n` + `mcp-tools`)
6. Plantillas de prompts
7. Registro de prompts (en [`PROMPTS.md`](PROMPTS.md))

---

## 1. Contexto del proyecto

| Ítem | Valor |
|---|---|
| Producto | Bolsa de trabajo con matching estudiante–oferta |
| Arquitectura | Microservicios REST (`/api/v1`), Docker Compose, API Gateway Nginx |
| Backend | **NestJS (Node 22 + TypeScript) para auth/config** · Python 3.12 + FastAPI (negocio: `profile-service`, `jobs-service`, `matching-service`) |
| IA y Herramientas | Ejecución íntegra de agentes en **n8n** (conectado a NVIDIA NIM) + servidor **MCP local en Python (`mcp-tools`)** consumido **de forma directa y exclusiva por `n8n`** en la red interna (`mcp_internal`, sin pasar por Nginx) |
| Orquestación | n8n (workflows `WF-0R`, `WF-0V`, `WF-00`, `WF-01` a `WF-06`) |
| Frontend | React 18 + Vite + TypeScript |
| Datos | PostgreSQL 17 (un schema y un rol por microservicio REST; n8n en base propia), volumen Docker para CVs, Mailpit para mails |
| Equipo | 4 personas, 2 semanas, 2 sprints |
| Documento base | `docs/Plan_MVP_Bolsa_de_Trabajo.pdf` |
| Cómo levantar | [`README.md`](README.md) |
| Historial de prompts | [`PROMPTS.md`](PROMPTS.md) |

Servicios y dueños:

| Servicio / Componente | Carpeta | Dueño | Revisor |
|---|---|---|---|
| auth-service | `services/auth-service` | Integrante 1 | Integrante 2 |
| profile-service | `services/profile-service` | Integrante 2 | Integrante 3 |
| jobs-service | `services/jobs-service` | Integrante 3 | Integrante 4 |
| matching-service | `services/matching-service` | Integrante 3 | Integrante 1 |
| mcp-tools (solo interno para n8n) | `mcp-tools/` | Integrante 1 | Integrante 3 |
| n8n workflows + prompts IA | `n8n/workflows/`, `n8n/agentes/`, `n8n/prompts/` | Integrante 3 | Integrante 1 |
| frontend | `frontend/` | Integrante 4 | Integrante 3 |
| gateway / CI / compose | `gateway/`, `infra/`, `.github/`, raíz | Integrante 1 | Integrante 4 |

---

## 2. Reglas generales (todos los agentes)

### 2.1 Arquitectura y diseño
1. **SOLID siempre.** Cada clase/módulo con una sola responsabilidad; extender con nuevas clases (OCP) en vez de agregar `if` por tipo; depender de interfaces (`Protocol`/`ABC` en Python, `interface` + tokens de inyección en NestJS) inyectadas.
2. **Capas** en servicios FastAPI: `api/` → `application/` → `domain/` ← `infrastructure/`. El dominio **no importa** FastAPI, SQLAlchemy ni SDKs externos. En NestJS: controllers delgados → services (casos de uso) → dominio sin dependencias de Nest/ORM ← repositorios/adaptadores.
3. **REST**: sustantivos en plural, códigos HTTP correctos, sin estado, versión `/api/v1`, errores con formato `{"error": {"code", "message", "details"}}`.
4. **Un servicio no accede a la base de datos de otro.** Se comunica por REST o eventos (webhooks a n8n). Reforzado en Postgres: cada rol sólo tiene permisos sobre su schema.
5. **Sin microservicio intermedio de IA ni paso de MCP por Nginx**:
   - Toda la lógica de agentes de IA (estructuración de CV, recomendaciones para estudiantes/empresas, router de modelos y verificación) corre en **n8n**. No existe un microservicio `ai-service`.
   - El servidor **`mcp-tools` es consumido únicamente por `n8n`** mediante conexión directa contenedor a contenedor (`http://mcp-tools:8000/mcp` sobre la red interna `mcp_internal`) y **nunca se publica ni enruta a través del API Gateway Nginx (`gateway`)**.
6. **Contratos primero**: si cambia un endpoint o schema JSON, actualizar `contracts/` en el mismo PR.

### 2.2 Separación Reglas vs. IA (requisito obligatorio)
- Todo resultado calculado por código lleva `"origin": "RULES"` y `engine_version`.
- Todo resultado de IA lleva `"origin": "AI"`, `model`, `generated_at`, `prompt_version` y `disclaimer`.
- **El LLM nunca calcula ni modifica el score.** Lo obtiene vía la herramienta MCP `compute_match`.
- En el frontend: badge verde “Calculado por reglas” y badge ámbar “Sugerido por IA”, en paneles separados.

### 2.3 Calidad
- Tests unitarios con cada cambio (pytest / Jest / Vitest). Cobertura ≥ 70 % en `domain/` y `application/`.
- `ruff`, `black`, `mypy` (Python) · `eslint`, `prettier`, `tsc --noEmit` (auth-service y front) sin errores. Config común en la raíz: `ruff.toml`, `.prettierrc.json`, `.editorconfig`.
- Nada de secretos en el código: usar `.env` y actualizar `.env.example`.
- No usar datos personales reales en fixtures; usar datos ficticios.

### 2.4 Uso de asistentes de IA de código
- El asistente **propone**, la persona **revisa, entiende y prueba**. No se mergea código que nadie del equipo pueda explicar.
- Antes de pedir código, pegar al asistente: este archivo (secciones 1–3) + la sección del agente correspondiente + la HU.
- **Todo prompt relevante se registra en [`PROMPTS.md`](PROMPTS.md)** (fecha, autor, agente, rama, prompt, resumen de respuesta, decisión). Nunca se incluye el historial de prompts en `README.md`.
- Si el asistente propone una librería nueva, se discute en la daily antes de agregarla.

---

## 3. Flujo Git obligatorio

```
main  ← solo releases (tags vX.Y.Z), protegido
dev   ← integración, protegido, PR + CI verde + 1 aprobación
<tipo>/<servicio>/v<semver>-<descripcion>   ← una rama por cambio
```

- Tipos: `feature`, `fix`, `refactor`, `test`, `docs`, `chore`.
- Ejemplos: `feature/auth/v0.1.0-login-jwt`, `fix/profile/v0.2.1-docx-encoding`, `feature/n8n/v0.3.0-wf01-procesar-cv`.
- La versión de la rama = versión nueva del servicio (actualizar `pyproject.toml` / `package.json`). SemVer: MAJOR rompe contrato, MINOR agrega funcionalidad, PATCH corrige.
- Commits: Conventional Commits → `feat(matching): agrega criterio de idiomas`.
- PR a `dev` con la plantilla (HU, cómo probar, checklist DoD, **IDs de prompts usados** registrados en [`PROMPTS.md`](PROMPTS.md)).
- Cierre de sprint: PR `dev → main`, tag `v0.1.0` (sprint 1), `v0.9.0` (RC), `v1.0.0` (entrega). Borrar ramas mergeadas.

```bash
git checkout dev && git pull
git checkout -b feature/matching/v0.1.0-scoring-engine
git add . && git commit -m "feat(matching): motor de scoring con criterios configurables"
git push -u origin feature/matching/v0.1.0-scoring-engine
gh pr create --base dev --fill
```

---

## 4. Agentes de desarrollo (uno por servicio/rol)

Cada sección es el “system prompt” que se le da al asistente de código cuando se trabaja en ese servicio.

### 4.1 Agente `auth-agent` — auth-service (NestJS)
**Rol:** desarrollador backend NestJS + TypeScript senior.
**Alcance:** `services/auth-service/` únicamente.
**Debe:**
- Entidad `User` con `email` único como identificador de login; roles `student`, `company`, `admin`. Claves con hash `argon2` (o `bcrypt` ≥ 12 rondas).
- Entidad `Company` (1–1 con User): razón social, **CUIT validado con dígito verificador**, actividad.
- Persistencia en el schema `auth` (variable `DATABASE_URL`); el ORM se acuerda en la daily.
- JWT **RS256** (`@nestjs/jwt` + `@nestjs/passport`), access 15 min, refresh 7 días, refresh tokens revocados al cambiar clave. Claves desde `JWT_PRIVATE_KEY_PATH` / `JWT_PUBLIC_KEY_PATH`.
- Endpoints bajo `/api/v1/auth`: register, token, token/refresh, me, password/change, password/reset, password/reset/confirm, email/change, email/confirm.
- Reset: token de un solo uso, 1 h, **misma respuesta exista o no el email**.
- DTOs con `class-validator`; controllers delgados; lógica en services; emails vía interfaz `EmailNotifier` inyectada por token (implementación SMTP → Mailpit en dev).
- Publicar la clave pública JWT en `/api/v1/auth/.well-known/jwks.json` para que los servicios FastAPI validen localmente.
- Errores con el formato común `{"error": {...}}` mediante un `ExceptionFilter` global.
- Contrato para el front y los servicios que validan el JWT en [`contracts/auth_frontend.md`](contracts/auth_frontend.md): actualizarlo en el mismo PR si cambia un endpoint o una respuesta.
**No debe:** guardar claves en texto plano, devolver si un email existe, mezclar lógica de perfiles.
**Tests mínimos:** UT-AUTH-01 a UT-AUTH-07 (Jest).

### 4.2 Agente `profile-agent` — profile-service (FastAPI)
**Rol:** desarrollador backend FastAPI.
**Alcance:** `services/profile-service/`.
**Debe:**
- Entidades `Profile`, `Skill(name, level 1–5)`, `Experience`, `Education`, `Language`.
- Validar MIME + extensión (`.pdf`, `.docx`, `.doc`, `.md`), máx. 5 MB, nombre aleatorio. Guardar en `CV_STORAGE_PATH`.
- Lo extraído del CV vía webhook a `n8n` (`POST /webhook/cv-extract`) se devuelve/guarda como **sugerencia** (`cv_suggestions`, con `"COMPLETAR_MANUALMENTE"` en campos escalares faltantes y `[]` en listas vacías, sin `null`) — nunca sobrescribe el perfil sin confirmación del usuario.
- `SkillExtractor` con diccionario + sinónimos (`data/skills_catalog.json`).
- Generar un CV nuevo "IA friendly" (una columna, texto real, títulos estándar, metadatos con palabras clave) **por reglas** con los datos confirmados: PDF con WeasyPrint + plantilla Jinja2 (`app/templates/cv.html`), DOCX con python-docx y vista previa HTML, detrás del puerto `CvRenderer`. Sin año de nacimiento, inclusión ni sueldo.
- Emitir webhooks `cv.uploaded` / `/webhook/cv-extract` y `profile.updated` a n8n mediante puertos inyectados (`CvWebhookGateway` / `EventPublisher`).
- Perfil completo de la estructura común §5 en el schema `profile`. `PATCH /profiles/me` reemplaza secciones y rechaza `"COMPLETAR_MANUALMENTE"`. La completitud se calcula por reglas (`origin: "RULES"`) en 3 pasos (`cv`, `preferences`, `privacy`). Las sugerencias de WF-01 se devuelven como `profile_draft` + `review_fields`.
- Autenticar con el JWT RS256 de auth-service (JWKS) y servicios sólo con `X-Service-Token`. Sólo `student` tiene `/me`; un perfil ajeno da 404. Exponer el pool para matching (`GET /profiles`, sólo perfiles buscables) con vistas que minimizan datos (sin teléfono, inclusión ni consentimientos). Contratos: `contracts/profile_frontend.md` y `contracts/profiles_matching.md`.
- Perfil de empresa (`/api/v1/profiles/companies/...`): marca empleadora (nombre comercial, logo PNG/JPEG/WebP ≤ 1 MB validado por firma y servido público, rubro, tamaño, sede, descripción, links, beneficios, contacto), con razón social/CUIT/actividad como copia de sólo lectura de auth-service y `snapshot` con la forma de `company_snapshot` para jobs-service. **Las búsquedas no van en profile-service**: son de jobs-service y el front las pide ahí. Contratos: `contracts/company_profile_frontend.md` y `contracts/company_profiles_jobs.md`.
**Tests mínimos:** UT-PROF-01 a UT-PROF-07.

### 4.3 Agente `jobs-agent` — jobs-service (FastAPI)
**Debe:**
- Entidades `Job`, `Requirement(skill, level, kind: required|desired|excluding)`, años de experiencia, educación, idiomas, estado (`active|closed`).
- Sólo la empresa dueña edita/cierra (403 si no). Validar que haya ≥ 1 requisito obligatorio.
- `GET /companies/me/searches` = ofertas activas de la empresa.
- Emitir `job.created` a n8n.
**Tests mínimos:** UT-JOBS-01, UT-JOBS-02.

### 4.4 Agente `matching-agent` — matching-service (FastAPI)
**Debe:**
- Implementar `ScoringCriterion` (Protocol) y un criterio por clase: RequiredSkills (50), DesiredSkills (15), Levels (15), Experience (10), Education (5), Languages (5). Pesos en `scoring_rules.yaml`.
- Regla excluyente: falta una skill `excluding` → score máximo 40.
- `MissingSkillsAnalyzer` con brecha de nivel y orden por prioridad.
- Normalización de skills (minúsculas, sin acentos, sinónimos).
- Respuestas de reglas siempre con `origin: "RULES"` y `engine_version`.
- Exponer endpoint interno para persistir recomendaciones generadas por `n8n` (`POST /api/v1/matches/recommendations`, con `origin: "AI"`).
- Usar la estructura común de [`contracts/estructura_comun_perfil_oferta_match.md`](contracts/estructura_comun_perfil_oferta_match.md): condiciones laborales en un bloque `conditions_fit` separado del score (un `ConditionCheck` por clase, `hard` configurable) y sueldo pretendido ↔ ofrecido en `salary_fit`, respetando su `visibility`.
- Rankings por reglas en ambos sentidos (`GET /api/v1/matches/students/{profile_id}/jobs` y `GET /api/v1/matches/jobs/{job_id}/candidates`) con snapshots sin datos personales; pedidos de análisis a `WF-06` (`POST /api/v1/matches/recommendations/requests`), guardado del resultado (`POST /api/v1/matches/recommendations/batch`) y vistas combinadas reglas + IA (`GET /api/v1/matches/recommendations/{students|jobs}/{id}`). Contrato en `contracts/matching_service.openapi.json`.
- Descartar cualquier `score`/`rank` que venga en contenido de IA: el valor mostrado sale siempre del motor.
- Autenticar usuarios con el JWT RS256 de auth-service validado localmente contra el JWKS (`iss`, `aud`, `exp`, `role`) y servicios sólo con `X-Service-Token` (nunca como Bearer). Acceso por dueño: `student` → `profile.user_id == sub`; `company` → `job.company_id == sub`; recurso ajeno → 404; endpoints internos → 403 para usuarios. Contrato para el front en `contracts/matching_frontend.md`.
- Cantidad de ofertas por estudiante y de candidatos por oferta configurable por un `admin` (`GET`/`PATCH /api/v1/matches/settings`, 1–20, valores iniciales en `scoring_rules.yaml`). Rige para vistas, rankings y pedidos de IA; un `limit` explícito sólo puede achicarla.
**No debe:** llamar a ningún LLM directamente.
**Tests mínimos:** UT-MATCH-01 a UT-MATCH-09.

### 4.5 Agente `mcp-agent` — mcp-tools (MCP local Python, exclusivo para n8n)
**Debe:**
- Usar el SDK oficial MCP para Python (`ProfiledFastMCP(FastMCP)` con filtrado de herramientas por `?perfil=`). Transporte `stdio` en desarrollo local y `streamable-http` en Docker (`MCP_TRANSPORT`).
- Comunicarse **exclusivamente con `n8n`** de forma directa por la red interna `mcp_internal` (`http://mcp-tools:8000/mcp`), **sin pasar por el API Gateway Nginx**.
- Arquitectura por capas (`domain/`, `application/`, `infrastructure/`, `tools/`) con puertos `Protocol` e inyección de dependencias.
- Herramientas en `app/tools/`: `get_agent_settings`, `fecha_hora`, `list_skills`, `leer_skill` (con protección anti-bucle por sesión), `parse_cv_file` (y alias `parse_cv_text` / `leer_archivo`, soporta PDF/DOCX/DOC/MD), `get_profile`, `list_candidate_profiles`, `get_job`, `list_active_jobs`, `compute_match`, `missing_skills`, `rank_jobs_for_student`, `rank_candidates_for_job`, `search_courses`, `save_recommendation`, `validate_json_schema`, `check_grounding` y `router_*` (además de endpoints HTTP `/router/reserve`/`/router/reservar`, `/router/failure`/`/router/fallo`, `/router/success`/`/router/exito`, `/router/status`/`/router/estado` y `/reglas`).
- Soportar modo mock (`MCP_USE_MOCKS=true`) detrás de los mismos puertos (`ProfileGateway`, `JobsGateway`, `MatchingGateway`, `RecommendationStore`) mientras se completan los endpoints REST de negocio.
- Cada herramienta: docstring clara (es lo que lee el LLM), tipos de entrada/salida, manejo de errores con mensaje legible.
- Autenticarse ante los servicios y proteger `/mcp` y `/router` con `X-Service-Token`, `X-API-Key`, `Bearer` o `?key=` (enmascarando `key=***` en logs).
- Herramientas **de solo lectura** salvo `save_recommendation`.
**Tests mínimos:** UT-MCP-01, UT-MCP-02 (cobertura ≥ 70 % en `domain/` y `application/`).

### 4.6 Agente `n8n-agent` — workflows y ejecución de IA
**Debe:**
- Centralizar **toda la ejecución de IA** del sistema (no existe `ai-service`): catálogo declarativo de agentes en `n8n/agentes/*.json` + `n8n/agentes/_sistema.json`, plantillas versionadas en `n8n/prompts/*.md` y un workflow por archivo JSON en `n8n/workflows/` con nombre `WF-0X-<nombre>.json` (generables de forma determinística con `python n8n/generate_workflows.py`); exportar sin credenciales.
- Consumir `mcp-tools` de forma directa (`$env.MCP_URL` = `http://mcp-tools:8000/mcp`) sin pasar por Nginx.
- Usar los nodos nativos de agente de n8n (`@n8n/n8n-nodes-langchain.agent`, `@n8n/n8n-nodes-langchain.lmChatOpenAi` conectado directo a NVIDIA NIM sin modelos locales Ollama, `@n8n/n8n-nodes-langchain.memoryBufferWindow`, `@n8n/n8n-nodes-langchain.mcpClientTool` con `?perfil=` y `@n8n/n8n-nodes-langchain.mcpClient` para lectura de archivos adjuntos/CVs).
- `WF-0R` Agente especialista y Router NVIDIA · `WF-0V` Verificador (JSON Schema + grounding + integridad de score + agente `Doctor Strange`) · `WF-00` Orquestador (`Captain America`, con lectura de adjunto MCP y reintento controlado) · `WF-01` Procesar CV (`POST /webhook/cv-extract`, `Natasha Romanoff`) · `WF-06` Recomendador postulantes/empresas (`POST /webhook/recommendations`: `mode=student|company` con `Jean Grey` / `match_advisor` sobre el ranking por reglas de `rank_jobs_for_student` / `rank_candidates_for_job`, `mode=training` con `Professor X`) · `WF-02` a `WF-05` notificaciones y errores.
- Usar variables de entorno de n8n (`$env.MCP_URL`, `$env.SERVICE_TOKEN`, `$env.N8N_WEBHOOK_TOKEN`, etc., definidas en `docker-compose.yml`) y consultar parámetros dinámicos con `get_agent_settings`; nunca valores fijos.
- Separar siempre el bloque `"rule_based"` (`origin: "RULES"`) del bloque `"ai_recommendations"` (`origin: "AI"`).
- Idempotencia: no enviar mails duplicados (guardar `notification_key`).

### 4.7 Agente `frontend-agent` — React
**Debe:**
- React 18 + Vite + TS, React Router, TanStack Query, React Hook Form + Zod, Tailwind / Bootstrap.
- Cliente API único (`src/api/client.ts`) con interceptor JWT y refresh automático. La API es same-origin (`/api/v1`) detrás del gateway.
- Rutas protegidas por rol (`student`, `company`).
- Componentes `ScoreCard` (badge “Calculado por reglas”) y `AIRecommendations` (badge “Sugerido por IA” + disclaimer), separados.
- Flujo CV: subir → ver sugerencias → aceptar/editar/descartar cada ítem → guardar.
- Accesibilidad: labels, contraste AA, foco visible. Textos en español.
**Tests mínimos:** UT-FE-01 a UT-FE-04.

### 4.8 Agente `qa-agent` — calidad (transversal)
**Debe:** generar casos de prueba desde los criterios de aceptación de cada HU, revisar cobertura, proponer tests faltantes, nunca modificar código de producción (sólo `tests/`).

### 4.9 Agente `devops-agent` — Docker, gateway, CI
**Debe:** mantener `docker-compose.yml` (+ `docker-compose.override.yml` para dev), Dockerfiles multi-stage con usuario no root, `healthcheck` por servicio, `gateway/nginx.conf` con rutas `/api/v1/<recurso>/` (únicamente para los microservicios REST `auth`, `profiles`, `jobs` y `matches`; `mcp-tools` no pasa por Nginx y se conecta directo con `n8n` por `mcp_internal`), `infra/postgres/init/` (un rol + schema por microservicio con BD) y `.github/workflows/ci.yml` (lint + tests por servicio con matrix, solo en carpetas modificadas).
**Recordar:** en Nginx, un `proxy_set_header` dentro de un `location` anula todos los del `server`; definir headers comunes sólo a nivel `server`.

---

## 5. Agentes en tiempo de ejecución (`n8n` + `mcp-tools`)

| Agente | Dónde corre | Disparador | Herramientas MCP (`http://mcp-tools:8000/mcp` directo) | Salida |
|---|---|---|---|---|
| **Orquestador (Captain)** | n8n `WF-00` + `WF-0R` (Router NVIDIA) | Sub-workflow invocado por `WF-01` y `WF-06` | `get_agent_settings`, `router_*` | Coordina especialista → `WF-0V` Verificador (con reintento si rechaza) |
| **Verificador** | n8n `WF-0V` | Sub-workflow invocado por `WF-00` | `validate_json_schema`, `check_grounding` | `{cumple, faltantes, instruccion}` |
| **CV Structurer** | n8n `WF-01` → `WF-00` | `POST /webhook/cv-extract` / `cv.uploaded` | `parse_cv_file` (`parse_cv_text`) | JSON estandarizado `cv_suggestions` (`origin="AI"`, sin `null`, con `"COMPLETAR_MANUALMENTE"` / `[]`) |
| **Match Advisor (Jean Grey)** | n8n `WF-06` → `WF-00` | `POST /webhook/recommendations` (`mode=student\|company`), disparado por matching-service (`/recommendations/requests`) | `rank_jobs_for_student`, `rank_candidates_for_job`, `search_courses` (el guardado va por REST a matching-service `/recommendations/batch`) | `match_student_recommendations` / `match_company_recommendations` sin score; bloques separados `rule_based` (`origin="RULES"`) y `ai_recommendations` (`origin="AI"`). Cantidad de ofertas/candidatos: la configura un admin en matching-service |
| **Training Advisor** | n8n `WF-06` → `WF-00` | `POST /webhook/recommendations` (`mode=training`) | `get_profile`, `get_job`, `list_active_jobs`, `compute_match`, `missing_skills`, `search_courses`, `save_recommendation` | `student_recommendations` (cursos, proyectos, tips) |
| **Match Notifier** | n8n `WF-02`/`WF-03` | `job.created`, `profile.updated` | — (llama REST a matching) | Mails con resultados por reglas |

Reglas para los agentes de ejecución:
1. Responder **solo en JSON** que cumpla el schema indicado.
2. No inventar competencias que no estén en el texto del CV o en el perfil.
3. En extracción de CV, reconocer campos presentes o análogos y devolver `"COMPLETAR_MANUALMENTE"` en escalares faltantes y `[]` en listas vacías (nunca `null`).
4. Usar el score y los faltantes **tal como los devuelve** `compute_match` / `missing_skills`.
5. No incluir datos personales sensibles (DNI, dirección exacta, salud) en las salidas.
6. Recomendaciones concretas, priorizadas (alta/media/baja), máximo 5 por oferta.

---

## 6. Plantillas de prompts (`n8n/prompts/`)

### 6.1 Prompt de desarrollo (asistente de código)
```
Contexto: [pegar secciones 1-3 de AGENTS.md] + [sección del agente 4.x]
Historia de usuario: HU-XX — <texto> — Criterios: <...>
Rama: <tipo>/<servicio>/vX.Y.Z-<desc>
Tarea: <qué querés que haga>
Restricciones: SOLID, capas, tests unitarios pytest/Jest/Vitest, no tocar otros servicios.
Entregá: archivos modificados + tests + cómo probar + entrada P-NNN en PROMPTS.md.
```

### 6.2 Prompt de runtime — Training Advisor (`n8n/prompts/training_advisor.md`, v1.0.0)
```
Sos un orientador de carrera. Recibís el perfil de un estudiante, una oferta,
el resultado de compatibilidad calculado por reglas y las competencias faltantes.
NO recalcules el puntaje. Usá search_courses para proponer formación.
Devolvé JSON: {"items":[{"type":"course|project|profile_tip","skill":str,
"text":str,"priority":"alta|media|baja"}]} con máximo 5 ítems.
```

### 6.3 Prompt de runtime — CV Structurer (`n8n/prompts/cv_structurer.md`, v1.1.0)
```
Extraé del texto del CV sólo información presente o análoga. Devolvé JSON sin valores null:
usá "COMPLETAR_MANUALMENTE" para campos escalares ausentes y [] para listas vacías. No inventes.
```

---

## 7. Registro de prompts y resumen de respuestas

El registro completo de prompts utilizados durante el proyecto (`P-001`, `P-002`, etc.) se mantiene en un archivo separado para mantener limpios tanto `README.md` como `AGENTS.md`:

- Ver y actualizar **[`PROMPTS.md`](PROMPTS.md)** en cada PR.
