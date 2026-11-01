# AGENTS.md — Reglas e instrucciones para agentes · MVP Bolsa de Trabajo

> Este archivo vive en la raíz del repositorio. Lo leen **las personas del equipo** y **los asistentes de IA de código** (Claude, Copilot, Cursor, etc.) antes de tocar el proyecto. También define el comportamiento de los **agentes de IA en tiempo de ejecución** (n8n + ai-service + MCP).
> Todo cambio a este archivo se hace en una rama `docs/agents/vX.Y.Z-<desc>` con PR a `dev`.

---

## 0. Índice

1. Contexto del proyecto
2. Reglas generales (aplican a todos los agentes)
3. Flujo Git obligatorio
4. Agentes de desarrollo (uno por servicio/rol)
5. Agentes en tiempo de ejecución (n8n / ai-service / MCP)
6. Plantillas de prompts
7. Registro de prompts y resumen de respuestas

---

## 1. Contexto del proyecto

| Ítem | Valor |
|---|---|
| Producto | Bolsa de trabajo con matching estudiante–oferta |
| Arquitectura | Microservicios REST (`/api/v1`), Docker Compose, API Gateway Nginx |
| Backend | **NestJS (Node 22 + TypeScript) para auth/config** · Python 3.12 + FastAPI (negocio) |
| IA | ai-service (FastAPI + LLM configurable) · servidor **MCP local en Python** con herramientas |
| Orquestación | n8n (workflows WF-01 a WF-05) |
| Frontend | React 18 + Vite + TypeScript |
| Datos | PostgreSQL 17 (un schema y un rol por servicio; n8n en base propia), volumen Docker para CVs, Mailpit para mails |
| Equipo | 4 personas, 2 semanas, 2 sprints |
| Documento base | `docs/Plan_MVP_Bolsa_de_Trabajo.pdf` |
| Cómo levantar | `README.md` |

Servicios y dueños:

| Servicio | Carpeta | Dueño | Revisor |
|---|---|---|---|
| auth-service | `services/auth-service` | Integrante 1 | Integrante 2 |
| profile-service | `services/profile-service` | Integrante 2 | Integrante 3 |
| jobs-service | `services/jobs-service` | Integrante 3 | Integrante 4 |
| matching-service | `services/matching-service` | Integrante 3 | Integrante 1 |
| ai-service | `services/ai-service` | Integrante 1 | Integrante 2 |
| mcp-tools | `mcp-tools/` | Integrante 1 | Integrante 3 |
| n8n workflows | `n8n/workflows/` | Integrante 3 | Integrante 1 |
| frontend | `frontend/` | Integrante 4 | Integrante 3 |
| gateway / CI / compose | `gateway/`, `infra/`, `.github/`, raíz | Integrante 1 | Integrante 4 |

---

## 2. Reglas generales (todos los agentes)

### 2.1 Arquitectura y diseño
1. **SOLID siempre.** Cada clase/módulo con una sola responsabilidad; extender con nuevas clases (OCP) en vez de agregar `if` por tipo; depender de interfaces (`Protocol`/`ABC` en Python, `interface` + tokens de inyección en NestJS) inyectadas.
2. **Capas** en servicios FastAPI: `api/` → `application/` → `domain/` ← `infrastructure/`. El dominio **no importa** FastAPI, SQLAlchemy ni SDKs externos. En NestJS: controllers delgados → services (casos de uso) → dominio sin dependencias de Nest/ORM ← repositorios/adaptadores.
3. **REST**: sustantivos en plural, códigos HTTP correctos, sin estado, versión `/api/v1`, errores con formato `{"error": {"code", "message", "details"}}`.
4. **Un servicio no accede a la base de datos de otro.** Se comunica por REST o eventos (webhooks a n8n). Reforzado en Postgres: cada rol sólo tiene permisos sobre su schema.
5. **Contratos primero**: si cambia un endpoint, actualizar `contracts/<servicio>.yaml` en el mismo PR.

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
- **Todo prompt relevante se registra** en la sección 7 (fecha, autor, agente, rama, prompt, resumen de respuesta, decisión).
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
- PR a `dev` con la plantilla (HU, cómo probar, checklist DoD, **IDs de prompts usados** de la sección 7).
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
**No debe:** guardar claves en texto plano, devolver si un email existe, mezclar lógica de perfiles.
**Tests mínimos:** UT-AUTH-01 a UT-AUTH-07 (Jest).

### 4.2 Agente `profile-agent` — profile-service (FastAPI)
**Rol:** desarrollador backend FastAPI.
**Alcance:** `services/profile-service/`.
**Debe:**
- Entidades `Profile`, `Skill(name, level 1–5)`, `Experience`, `Education`, `Language`.
- `CVParser` (Protocol) con `PdfCVParser` (pdfplumber) y `DocxCVParser` (python-docx) + `ParserFactory` (OCP/LSP).
- Validar MIME + extensión, máx. 5 MB, nombre aleatorio. Guardar en `CV_STORAGE_PATH`.
- Lo extraído del CV se guarda como **sugerencia** (`cv_suggestions`) — nunca sobrescribe el perfil sin confirmación del usuario.
- `SkillExtractor` con diccionario + sinónimos (`data/skills_catalog.json`).
- Generar CV PDF con WeasyPrint + plantilla Jinja2 (`templates/cv.html`). Las librerías de sistema ya están en el Dockerfile.
- Emitir webhooks `cv.uploaded` y `profile.updated` a n8n mediante `EventPublisher` (interfaz).
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
- Respuestas siempre con `origin: "RULES"` y `engine_version`.
**No debe:** llamar a ningún LLM ni a ai-service.
**Tests mínimos:** UT-MATCH-01 a UT-MATCH-09.

### 4.5 Agente `ai-agent` — ai-service (FastAPI)
**Debe:**
- `LLMClient` (Protocol) con implementación real configurable por `.env` (`LLM_PROVIDER`, `LLM_MODEL`, `LLM_API_KEY`) y `FakeLLMClient` para tests (`LLM_PROVIDER=fake`).
- Consumir herramientas a través del servidor MCP (`mcp-tools`, `MCP_SERVER_URL`), no llamando directo a la base de otros servicios.
- Prompts como plantillas versionadas en `prompts/*.md` con `prompt_version`.
- Respuesta estructurada (JSON validado con Pydantic). Si el LLM devuelve algo inválido: reintentar 1 vez y luego 503 controlado.
- Guardar cada recomendación con `origin: "AI"`, modelo, versión de prompt, fecha.
- Caché por `(profile_id, job_id, profile_version, prompt_version)`.
**Tests mínimos:** UT-AI-01 a UT-AI-03.

### 4.6 Agente `mcp-agent` — mcp-tools (MCP local Python)
**Debe:**
- Usar el SDK oficial MCP para Python (FastMCP). Transporte `stdio` en desarrollo y `streamable-http` en Docker (`MCP_TRANSPORT`).
- Arquitectura por capas (`domain/`, `application/`, `infrastructure/`, `tools/`) con puertos `Protocol` e inyección de dependencias.
- Herramientas en `app/tools/`: `get_agent_settings`, `parse_cv_file` (y alias `parse_cv_text`, soporta PDF/DOCX/DOC/MD), `get_profile`, `list_candidate_profiles`, `get_job`, `list_active_jobs`, `compute_match`, `missing_skills`, `search_courses`, `save_recommendation`, `validate_json_schema`, `check_grounding` y `router_*` (además de endpoints HTTP `/router/reserve`, `/router/failure`, `/router/success`, `/router/status`).
- Soportar modo mock (`MCP_USE_MOCKS=true`) detrás de los mismos puertos (`ProfileGateway`, `JobsGateway`, `MatchingGateway`, `RecommendationStore`) mientras se completan los endpoints REST de negocio.
- Cada herramienta: docstring clara (es lo que lee el LLM), tipos de entrada/salida, manejo de errores con mensaje legible.
- Autenticarse ante los servicios y proteger `/mcp` y `/router` con `X-Service-Token`.
- Herramientas **de solo lectura** salvo `save_recommendation`.
**Tests mínimos:** UT-MCP-01, UT-MCP-02 (cobertura ≥ 70 % en `domain/` y `application/`).

### 4.7 Agente `n8n-agent` — workflows
**Debe:**
- Un workflow por archivo JSON en `n8n/workflows/` con nombre `WF-0X-<nombre>.json` (generables de forma determinística con `python n8n/generate_workflows.py`); exportar sin credenciales.
- `WF-0R` Sub-workflow Router NVIDIA (límite RPM, fallback y cooldown vía `mcp-tools`) · `WF-0V` Verificador (JSON Schema + grounding + integridad de score) · `WF-00` Orquestador (Captain, con reintento controlado) · `WF-01` Procesar CV (`POST /webhook/cv-extract`) · `WF-06` Recomendador postulantes/empresas (`POST /webhook/recommendations`) · `WF-02` a `WF-05` notificaciones y errores.
- Usar variables de entorno de n8n (`$env.MCP_URL`, `$env.SERVICE_TOKEN`, `$env.N8N_WEBHOOK_TOKEN`, etc., definidas en `docker-compose.yml`) y consultar parámetros dinámicos con `get_agent_settings`; nunca valores fijos.
- Separar siempre el bloque `"rule_based"` (`origin: "RULES"`) del bloque `"ai_recommendations"` (`origin: "AI"`).
- Idempotencia: no enviar mails duplicados (guardar `notification_key`).

### 4.8 Agente `frontend-agent` — React
**Debe:**
- React 18 + Vite + TS, React Router, TanStack Query, React Hook Form + Zod, Tailwind.
- Cliente API único (`src/api/client.ts`) con interceptor JWT y refresh automático. La API es same-origin (`/api/v1`) detrás del gateway.
- Rutas protegidas por rol (`student`, `company`).
- Componentes `ScoreCard` (badge “Calculado por reglas”) y `AIRecommendations` (badge “Sugerido por IA” + disclaimer), separados.
- Flujo CV: subir → ver sugerencias → aceptar/editar/descartar cada ítem → guardar.
- Accesibilidad: labels, contraste AA, foco visible. Textos en español.
**Tests mínimos:** UT-FE-01 a UT-FE-04.

### 4.9 Agente `qa-agent` — calidad (transversal)
**Debe:** generar casos de prueba desde los criterios de aceptación de cada HU, revisar cobertura, proponer tests faltantes, nunca modificar código de producción (sólo `tests/`).

### 4.10 Agente `devops-agent` — Docker, gateway, CI
**Debe:** mantener `docker-compose.yml` (+ `docker-compose.override.yml` para dev), Dockerfiles multi-stage con usuario no root, `healthcheck` por servicio, `gateway/nginx.conf` con rutas `/api/v1/<recurso>/`, `infra/postgres/init/` (un rol + schema por servicio) y `.github/workflows/ci.yml` (lint + tests por servicio con matrix, solo en carpetas modificadas).
**Recordar:** en Nginx, un `proxy_set_header` dentro de un `location` anula todos los del `server`; definir headers comunes sólo a nivel `server`.

---

## 5. Agentes en tiempo de ejecución

| Agente | Dónde corre | Disparador | Herramientas MCP | Salida |
|---|---|---|---|---|
| **Orquestador (Captain)** | n8n `WF-00` + `WF-0R` (Router NVIDIA) | Sub-workflow invocado por `WF-01` y `WF-06` | `get_agent_settings`, `router_*` | Coordina especialista → `WF-0V` Verificador (con reintento si rechaza) |
| **Verificador** | n8n `WF-0V` | Sub-workflow invocado por `WF-00` | `validate_json_schema`, `check_grounding` | `{cumple, faltantes, instruccion}` |
| **CV Structurer** | n8n `WF-01` → `WF-00` | `POST /webhook/cv-extract` / `cv.uploaded` | `parse_cv_file` (`parse_cv_text`) | JSON estandarizado `cv_suggestions` (`origin="AI"`) para confirmar |
| **Training / Company Advisor** | n8n `WF-06` → `WF-00` | `POST /webhook/recommendations` (`mode=student\|company`) | `get_profile`, `list_candidate_profiles`, `get_job`, `list_active_jobs`, `compute_match`, `missing_skills`, `search_courses`, `save_recommendation` | Bloques separados `rule_based` (`origin="RULES"`) y `ai_recommendations` (`origin="AI"`) |
| **Match Notifier** | n8n `WF-02`/`WF-03` | `job.created`, `profile.updated` | — (llama REST a matching) | Mails con resultados por reglas |

Reglas para los agentes de ejecución:
1. Responder **solo en JSON** que cumpla el schema indicado.
2. No inventar competencias que no estén en el texto del CV o en el perfil.
3. Usar el score y los faltantes **tal como los devuelve** `compute_match` / `missing_skills`.
4. No incluir datos personales sensibles (DNI, dirección, salud) en las salidas.
5. Recomendaciones concretas, priorizadas (alta/media/baja), máximo 5 por oferta.

---

## 6. Plantillas de prompts

### 6.1 Prompt de desarrollo (asistente de código)
```
Contexto: [pegar secciones 1-3 de AGENTS.md] + [sección del agente 4.x]
Historia de usuario: HU-XX — <texto> — Criterios: <...>
Rama: <tipo>/<servicio>/vX.Y.Z-<desc>
Tarea: <qué querés que haga>
Restricciones: SOLID, capas, tests unitarios pytest/Jest/Vitest, no tocar otros servicios.
Entregá: archivos modificados + tests + cómo probar.
```

### 6.2 Prompt de runtime — Training Advisor (`prompts/training_advisor.md`, v1.0.0)
```
Sos un orientador de carrera. Recibís el perfil de un estudiante, una oferta,
el resultado de compatibilidad calculado por reglas y las competencias faltantes.
NO recalcules el puntaje. Usá search_courses para proponer formación.
Devolvé JSON: {"items":[{"type":"course|project|profile_tip","skill":str,
"text":str,"priority":"alta|media|baja"}]} con máximo 5 ítems.
```

### 6.3 Prompt de runtime — CV Structurer (`prompts/cv_structurer.md`, v1.0.0)
```
Extraé del texto del CV sólo información presente. Devolvé JSON con
skills[{name, level_estimado 1-5|null}], experience[], education[], languages[].
Si un dato no aparece, dejalo vacío. No inventes.
```

---

## 7. Registro de prompts y resumen de respuestas

**Reglas del registro**
- Una fila/entrada por prompt relevante (que generó código, diseño o decisiones). Los triviales no hace falta.
- ID correlativo `P-NNN`. Se referencia en el PR.
- El resumen de respuesta es de 1–3 líneas, escrito por la persona (no copiar la respuesta entera).
- Columna **Decisión**: `aceptado`, `aceptado con cambios`, `descartado` (+ motivo).
- Agregar entradas al final; no editar las anteriores (salvo corregir errores de tipeo).

### 7.1 Tabla resumen

| ID | Fecha | Autor | Agente / herramienta | Rama | Prompt (resumen) | Resumen de la respuesta | Decisión |
|---|---|---|---|---|---|---|---|
| P-001 | 2026-10-30 | Andres | Claude (planificación) | `docs/plan/v0.0.1-plan-inicial` | Generar plan de trabajo para MVP de bolsa de trabajo con SOLID, REST, microservicios, Docker, Django, FastAPI, n8n, MCP Python y React; 4 personas, 2 semanas; PDF con arquitectura, capas, tecnologías, roles, plan, RF/RNF, HU y tests; MD con reglas de agentes y registro de prompts | Se generó `Plan_MVP_Bolsa_de_Trabajo.pdf` (11 secciones: 7 servicios, 21 RF, 14 RNF, 18 HU ≈ 67 pts, 34 casos de test, plan día a día en 2 sprints, flujo Git) y este `AGENTS.md` con 10 agentes de desarrollo y 3 de runtime | aceptado (pendiente revisión del equipo) |
| P-002 | 2026-10-31 | Andres | Claude Code (`devops-agent`) | `chore/infra/v0.0.1-contenedores-base` | Crear sólo los contenedores y archivos de configuración comunes; auth-service pasa a NestJS | Compose (dev/prod), gateway Nginx, Postgres con rol+schema por servicio, Dockerfiles multi-stage no root con healthcheck, esqueletos `/health` por servicio, CI por carpeta, config común de lint y plantilla de PR | pendiente de revisión |
| P-003 | 2026-10-31 | Andres | Antigravity (`mcp-agent` + `n8n-agent`) | `feature/mcp-n8n/v0.1.0-agentes-nvidia` | Armar flujos de n8n y agentes (orquestador, verificador, extractor de CV PDF/DOC/DOCX/MD y recomendador postulantes/empresas) usando modelos remotos de NVIDIA, reutilizando router/lectura de `agentes`, migrando Postgres a 17 y dejando toda la configuración en `.env` vía `mcp-tools` (con soporte futuro para panel y mocks de endpoints pendientes) | Migración a PostgreSQL 17, `mcp-tools` v0.1.0 con arquitectura limpia (`domain`/`application`/`infrastructure`/`tools`), router NVIDIA, `parse_cv_file` (con `antiword`), validación JSON Schema + grounding, mocks configurables (`MCP_USE_MOCKS`), cobertura 90 % y workflows `WF-0R`, `WF-0V`, `WF-00`, `WF-01` y `WF-06` | aceptado |
| P-004 | | | | | | | |

### 7.2 Detalle de entradas

#### P-001 — Plan inicial del MVP
- **Fecha:** 2026-10-30 · **Autor:** Andres · **Agente:** Claude · **Rama:** `docs/plan/v0.0.1-plan-inicial`
- **Prompt (textual):**
  > quiero generar un plan de trabajo para armar un mvp de una bolsa de trabajo. Quiero que se utilicen los principios solid y la arquitectura rest. usa los principios solid, arquitectura de microservicios, docker, python, django para la configuracion y autenticacion, fastapi, n8n como orquestador de agentes, un mcp local en python para las herramientas, y react para el frontend. […] somos 4 personas y tenemos 2 semanas. Funcionalidades: cargar empleos; recomendar candidatos; cargar CV en doc o pdf y que lo reconozca e integre al sistema, permitir editar o agregar información al perfil; login con mail y clave, cambiar clave/email, recuperar contraseña por mail; descargar CV generado en PDF; empresas con CUIT, actividad y búsquedas activas. Además: perfiles de estudiantes con competencias, ofertas con requisitos, comparación, scoring con criterios explícitos, competencias faltantes, recomendaciones de IA, automatización con n8n, distinguir resultados por reglas de recomendaciones IA. […] Armá en un PDF la arquitectura, capas, tecnologías, roles del equipo, plan de trabajo, requisitos funcionales y no funcionales, historias de usuario y test unitarios. Armá un md con las instrucciones y reglas para cada agente que incluya un registro de los prompts y un resumen de las respuestas. Versionado en GitHub con ramas separadas y versionadas por cada cambio, mergeando a dev.
- **Resumen de la respuesta:**
  - Arquitectura de 6 servicios + gateway + n8n (auth en Django; profile, jobs, matching, ai en FastAPI; mcp-tools en Python), JWT emitido por Django y validado localmente por FastAPI.
  - Scoring por reglas con 6 criterios y pesos explícitos (50/15/15/10/5/5) + regla excluyente; contrato JSON con bloques `rule_based` (origin=RULES) y `ai_recommendations` (origin=AI).
  - Roles: TL/DevOps, QA Lead, Integraciones/n8n, SM/PO/Front; plan de 10 días con releases v0.1.0, v0.9.0, v1.0.0.
  - Ramas `<tipo>/<servicio>/v<semver>-<desc>` → PR a `dev` → release a `main`.
- **Decisión:** aceptado; el equipo debe validar la asignación de roles y el proveedor de LLM.

#### P-002 — Contenedores y configuración común
- **Fecha:** 2026-10-31 · **Autor:** Andres · **Agente:** Claude Code (`devops-agent`) · **Rama:** `chore/infra/v0.0.1-contenedores-base` · **HU:** —
- **Prompt (textual):**
  > De estas instrucciones quiero solo crear los contenedores y archivos de configuracion comunes para todo el proyecto. El auth service se va a hacer finalmente con nesjs
- **Resumen de la respuesta:**
  - `docker-compose.yml` + `docker-compose.override.yml` (dev con hot reload), gateway Nginx con rutas por recurso, rate limit en login/reset y errores JSON; Postgres 16 con rol + schema por servicio (n8n en base propia).
  - Dockerfiles multi-stage, usuario no root y healthcheck; esqueleto mínimo con `/health` y un test por servicio (auth en NestJS 11).
  - Cambios respecto del plan: auth en NestJS; Mailpit en lugar de MailHog (sin mantenimiento); volumen Docker en lugar de MinIO para CVs.
  - CI con detección de carpetas modificadas; `ruff.toml`, `.prettierrc.json`, `.editorconfig`, `.gitattributes`, plantilla de PR.
- **Archivos afectados:** raíz, `gateway/`, `infra/`, `.github/`, `services/*`, `mcp-tools/`, `frontend/`, `AGENTS.md` (§1, §2, §4.1, §4.10, §7).
- **Decisión:** pendiente de revisión del equipo.

#### P-003 — Herramientas MCP, Router NVIDIA y Workflows n8n (Orquestador, Verificador, CV y Recomendador)
- **Fecha:** 2026-10-31 · **Autor:** Andres · **Agente:** Antigravity (`mcp-agent` + `n8n-agent`) · **Rama:** `feature/mcp-n8n/v0.1.0-agentes-nvidia` · **HU:** transversal (IA / MCP / n8n)
- **Prompt (resumido):**
  > Armar los flujos de n8n y los agentes (orquestador, verificador, extractor de CV en PDF/MD/DOC/DOCX por webhook que devuelva JSON estandarizado, y recomendador por webhook para postulantes y empresas) usando modelos remotos de NVIDIA y reutilizando componentes de `C:\Users\Andres\proyectos\agentes`. Migrar Postgres a 17 sin dejar deuda técnica. No hardcodear cantidades ni modelos: tomarlos de `.env` a través de `mcp-tools` para que más adelante puedan venir de un panel de configuración, y mockear los endpoints que aún no existen.
- **Resumen de la respuesta:**
  - Migración de PostgreSQL 16 → 17 con dump/restore e importación de la credencial `OpenAI account` (NVIDIA) en `bolsa-n8n-1`.
  - Implementación completa de `mcp-tools` v0.1.0 por capas SOLID (`domain`, `application`, `infrastructure`, `tools`), con `SettingsProvider` (`env` hoy, `panel` mañana), `ModelRouter` NVIDIA, `CvParserService` (PDF/DOCX/DOC con `antiword`/MD), `VerificationService` (JSON Schema + grounding + integridad de score), adaptadores HTTP y Mock (`MCP_USE_MOCKS=true`), middleware `X-Service-Token` y 90 % de cobertura en `pytest`.
  - Generador `n8n/generate_workflows.py` y workflows `WF-0R`, `WF-0V`, `WF-00`, `WF-01` y `WF-06` en `n8n/workflows/`, más plantillas de prompts en `services/ai-service/prompts/*.md` y schemas en `contracts/`.
- **Archivos afectados:** `.env.example`, `docker-compose.yml`, `mcp-tools/`, `n8n/`, `services/ai-service/prompts/`, `contracts/`, `README.md`, `AGENTS.md`.
- **Decisión:** aceptado.

#### P-004 — (plantilla)
- **Fecha:** · **Autor:** · **Agente:** · **Rama:** · **HU:**
- **Prompt (textual o resumido):**
  > …
- **Resumen de la respuesta:**
  - …
- **Archivos afectados:** …
- **Decisión:** aceptado / aceptado con cambios / descartado — motivo
