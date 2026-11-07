# PROMPTS.md — Registro de prompts y resumen de respuestas · MVP Bolsa de Trabajo

> Archivo dedicado exclusivamente al historial de prompts relevantes utilizados con asistentes de IA de código durante el desarrollo del MVP (según [AGENTS.md §2.4 y §7](AGENTS.md)).

## Reglas del registro

- Una fila/entrada por prompt relevante (que generó código, diseño o decisiones arquitectónicas). Los triviales no hace falta registrarlos.
- ID correlativo `P-NNN`. Se referencia en la descripción de cada Pull Request hacia `dev`.
- El resumen de respuesta es de 1–3 líneas, escrito por la persona (no copiar la respuesta entera).
- Columna **Decisión**: `aceptado`, `aceptado con cambios`, `descartado` (+ motivo).
- Agregar entradas al final; no editar las anteriores (salvo corregir errores de tipeo).

---

## 1. Tabla resumen

| ID | Fecha | Autor | Agente / herramienta | Rama | Prompt (resumen) | Resumen de la respuesta | Decisión |
|---|---|---|---|---|---|---|---|
| P-001 | 2026-10-30 | Andres | Claude (planificación) | `docs/plan/v0.0.1-plan-inicial` | Generar plan de trabajo para MVP de bolsa de trabajo con SOLID, REST, microservicios, Docker, Django, FastAPI, n8n, MCP Python y React; 4 personas, 2 semanas; PDF con arquitectura, capas, tecnologías, roles, plan, RF/RNF, HU y tests; MD con reglas de agentes y registro de prompts | Se generó `Plan_MVP_Bolsa_de_Trabajo.pdf` (11 secciones: 7 servicios, 21 RF, 14 RNF, 18 HU ≈ 67 pts, 34 casos de test, plan día a día en 2 sprints, flujo Git) y este AGENTS.md con 10 agentes de desarrollo y 3 de runtime | aceptado (pendiente revisión del equipo) |
| P-002 | 2026-10-31 | Andres | Claude Code (`devops-agent`) | `chore/infra/v0.0.1-contenedores-base` | Crear sólo los contenedores y archivos de configuración comunes; auth-service pasa a NestJS | Compose (dev/prod), gateway Nginx, Postgres con rol+schema por servicio, Dockerfiles multi-stage no root con healthcheck, esqueletos `/health` por servicio, CI por carpeta, config común de lint y plantilla de PR | pendiente de revisión |
| P-003 | 2026-10-31 | Andres | Antigravity (`mcp-agent` + `n8n-agent`) | `feature/mcp-n8n/v0.1.0-agentes-nvidia` | Armar flujos de n8n y agentes (orquestador, verificador, extractor de CV PDF/DOC/DOCX/MD y recomendador postulantes/empresas) usando modelos remotos de NVIDIA, reutilizando router/lectura de `agentes`, migrando Postgres a 17 y dejando toda la configuración en `.env` vía `mcp-tools` (con soporte futuro para panel y mocks de endpoints pendientes) | Migración a PostgreSQL 17, `mcp-tools` v0.1.0 con arquitectura limpia (`domain`/`application`/`infrastructure`/`tools`), router NVIDIA, `parse_cv_file` (con `antiword`), validación JSON Schema + grounding, mocks configurables (`MCP_USE_MOCKS`), cobertura 90 % y workflows `WF-0R`, `WF-0V`, `WF-00`, `WF-01` y `WF-06` | aceptado |
| P-004 | 2026-11-01 | Andres | Antigravity (`mcp-agent` + `n8n-agent` + `devops-agent`) | `feature/mcp-n8n/v0.2.0-nodos-agente-y-skills` | Crear repo `Grupo-1-EPIALC/bolsa-de-trabajo` con reglas de publicación (PR + ramas por feature) y alinear la arquitectura de agentes con `C:\Users\Andres\proyectos\agentes` usando los nodos de Agente de n8n (`@n8n/n8n-nodes-langchain.agent`, `mcpClientTool`, `mcpClient`, `memoryBufferWindow`), perfiles MCP y skills (`leer_skill`), sin modelos locales Ollama | Repo creado y protegido en GitHub (`dev` y `main`), `mcp-tools` v0.2.0 con `ProfiledFastMCP` (`?perfil=`), `leer_skill` (con anti-bucle), `reglas.md`, skills de reclutamiento + ingeniería, catálogo `n8n/agentes/*.json` y workflows regenerados con nodos nativos de Agente de n8n conectados a NVIDIA NIM | aceptado |
| P-005 | 2026-11-01 | Andres | Antigravity (`profile-agent` + `n8n-agent`) | `feature/profile/v0.1.0-cv-webhook-async` | Armar formulario de prueba en `profile-service` para enviar un CV al webhook de n8n (`WF-01`) con espera asíncrona e indicador de progreso, tarjetas verticales en columnas de ancho fijo con Bootstrap 5 y salto de línea en el JSON, optimizando la verificación y reemplazando campos ausentes por `COMPLETAR_MANUALMENTE` / `[]` (sin `null`) | Endpoints `/api/v1/profiles/cv-test`, `/cv-extract/async` y `/cv-extract/jobs/{job_id}` por capas en `profile-service` con UI Bootstrap 5 vertical y wrap de JSON, normalizador de campos análogos (`COMPLETAR_MANUALMENTE` + `pending_manual_fields`), `maxTokens: 8192` + reparador de JSON en `WF-00`/`WF-0R` y verificación instantánea determinística en `WF-0V` | aceptado |
| P-006 | 2026-11-01 | Andres | Antigravity (`devops-agent` + `n8n-agent` + `mcp-agent`) | `refactor/infra/v0.2.0-sin-ai-service-y-prompts-md` | Simplificar arquitectura eliminando `ai-service` (ya que toda la IA corre en `n8n`), asegurar que `mcp-tools` se comunique directo con `n8n` sin pasar por Nginx (`gateway`), y separar el historial de prompts en un archivo independiente (`PROMPTS.md`) fuera de `README.md` y `AGENTS.md` | Eliminación de `services/ai-service` (plantillas movidas a `n8n/prompts/`), red interna `mcp_internal` directa entre `n8n` y `mcp-tools` sin exposición en `gateway/nginx.conf`, actualización de `docker-compose*.yml`, `.env.example`, `01-schemas.sh`, `ci.yml`, `README.md`, `AGENTS.md` y extracción del historial a `PROMPTS.md` | aceptado |
| P-007 | 2026-11-04 | Andres | Claude Code (`matching-agent`) | `feature/matching/v0.1.0-motor-reglas-y-recomendador` | En base a `estructura_comun_perfil_oferta_match.md`, armar el servicio de match (n8n analiza y el servicio devuelve las recomendaciones); pool de datos de prueba; contrato para el front con el cálculo del score; integrar el JWT de auth-service; límites de ofertas/candidatos configurables por admin | `matching-service` v0.1.0 por capas (6 criterios, regla excluyente, `MissingSkillsAnalyzer`, 12 `ConditionCheck`, `SalaryComparator`, rankings, pedidos a WF-06, guardado y vistas reglas+IA), JWT RS256 vía JWKS con acceso por rol y dueño, `/settings` para admin, pool de 15 perfiles y 12 ofertas, `contracts/matching_frontend.md`; 102 tests, 97 % | pendiente de revisión |
| P-008 | 2026-11-05 | Andres | Claude Code (`mcp-agent` + `n8n-agent`) | `feature/mcp-n8n/v0.3.0-match-advisor-ranking` | Agente de n8n que hace los match para recomendar a empresas y estudiantes; herramientas MCP de ranking (`rank_jobs_for_student`, `rank_candidates_for_job`) usadas por WF-06; cantidades configurables por admin | `mcp-tools` v0.3.0 con las 2 herramientas (HTTP a matching-service + mocks, perfiles `postulante`/`empresa`), agente `match_advisor` (Jean Grey) con prompt y 2 schemas sin score (`maxItems` 20), WF-06 reescrito (`student`/`company` por MCP, `training` conservado) que descarta score/rank/ids inventados y guarda en matching-service | pendiente de revisión |
| P-009 | 2026-11-05 | Dario | Gemini (`frontend-agent`) | `feature/frontend/v0.1.0-vistas-iniciales` | Maquetación SPA responsive del Frontend en React + Vite + Tailwind v4, cliente HTTP `apiFetch` desacoplado, manejo de respuestas 304/404, validación de CV ≤5MB (RNF-04), AuthForm con CUIT/Registro y redirección automática con Toast centrado | Layout SPA desacoplado (`VITE_USE_MOCKS`), componentes `RuleScoreCard` (badge verde `RULES`), `AISuggestionCard` (badge ámbar `AI` con disclaimer), `StudentProfile` (CV PDF/DOCX), `AuthForm` con soporte CUIT/Razón Social y Toast flotante de bienvenida | aceptado |
| P-010 | 2026-11-05 | Elian | OpenCode (DeepSeek V4.1 Flash Free) | `docs/jobs/v0.1.0-plan-y-contratos` → `feature/jobs/v0.1.0-ofertas-empresa` | Elaborar, según AGENTS.md §2 y §4.3, README y contratos, el plan de implementación de jobs-service (búsquedas/vacantes de empresas), sin inventar alcance fuera de los MD; incluir contratos para frontend y matching, arquitectura, endpoints, persistencia, auth, validación, tests y fases. Luego implementar el plan aprobado en `services/jobs-service` | Plan ajustado a los MD: Job/Requirement, active/closed, 403 para recurso ajeno, ≥1 required, `GET /companies/me/searches`, `job.created`, tests UT-JOBS-01/02; contratos OpenAPI + front + matching; PostgreSQL schema `jobs`; JWT/service token. Implementación v0.1.0 por capas (dominio, aplicación, infraestructura SQLAlchemy/in-memory, API FastAPI), seed con las 12 ofertas demo de matching y **99 tests / 94.79 % de cobertura**; `ruff`, `black` y `mypy` limpios | aceptado (pendiente review de Dario y del compañero de matching) |
| P-011 | 2026-11-06 | Andres | Claude Code (`profile-agent`) | `feature/profile/v0.2.0-perfil-completo-y-cv-ia` | Con la estructura común y AGENTS.md, armar profile-service: alta con auth, carga del CV que devuelve lo reconocido y pide completar el resto, luego disponibilidad/modalidad/etc.; sin login pide loguear y sin perfil ofrece CV o carga manual; con el perfil cargado, generar un CV nuevo IA friendly, moderno y profesional en PDF o DOCX; contratos para matching y front | `profile-service` v0.2.0 por capas: perfil completo (§5) en PostgreSQL (`profile`), JWT RS256 vía JWKS, subida multipart → WF-01 → `profile_draft` + `review_fields`, `PATCH` por secciones sin `COMPLETAR_MANUALMENTE`, completitud por reglas en 3 pasos, `SkillExtractor` con catálogo, vistas por rol, pool para matching (seed = mocks de matching), CV PDF (WeasyPrint, PDF/UA) / DOCX / HTML; `profile_frontend.md`, `profiles_matching.md`, OpenAPI; perfil de empresa (logo, rubro, ubicación, marca empleadora; búsquedas quedan en jobs-service) con `company_profile_frontend.md` y `company_profiles_jobs.md`; 92 tests, 97 % | pendiente de revisión |
| P-012 | 2026-11-06 | Andres | Claude Code (`frontend-agent`) | `feature/frontend/v0.2.0-estilo-bootstrap` | Adaptar el diseño del front (Bootstrap + Bootstrap Icons) al estilo de udelaciudad.edu.ar —magenta dominante, violeta en detalles, fondos blancos— y usar la foto adjunta como portada cuando el usuario no se autenticó | Tailwind/lucide → Bootstrap 5.3 + Bootstrap Icons con tema propio (Montserrat, magenta `#BA3995`, violeta `#682CAD`), portada pública con hero de foto y rótulo magenta, página de acceso con la foto de fondo, cabecera/footer institucionales, `resolveView` (sin sesión no se ven vistas privadas) con tests; paneles RULES/IA conservados | pendiente de revisión |
| P-013 | 2026-11-06 | Andres | Claude Code (`frontend-agent`) | `feature/frontend/v0.2.0-estilo-bootstrap` | Implementar en el front `profile_frontend.md` y `company_profile_frontend.md`: sin login ve el home; estudiante sin perfil → importar CV o carga manual; con perfil → recomendaciones de ofertas, modificar perfil y descargar CV PDF/Word; empresa → alta y perfil | Cliente API con refresh y error común, login/registro reales (tokens `access_token`, empresa anidada), alta de perfil (CV con polling y precarga `profile_draft`/`COMPLETAR_MANUALMENTE`, o manual) en 3 pasos, panel con ofertas (reglas + IA separadas, pedido a WF-06), edición y descarga/vista previa del CV; área de empresa (alta precargada, 2 pasos, logo, búsquedas activas); 12 tests; E2E con Playwright | pendiente de revisión |
| P-014 | 2026-11-06 | Andres | Claude Code (`devops-agent` + `n8n-agent`) | `feature/frontend/v0.2.0-estilo-bootstrap` | Revisar por qué desaparecieron los workflows de n8n, asegurar que persistan y que bases, configuración y media queden fuera de los contenedores | Causa: volúmenes recreados el 2026-11-03 (README sugería `down -v`) y la importación de workflows era manual. Volúmenes `bolsa_pg_data`/`bolsa_n8n_data`/`bolsa_cv_storage` pasan a externos (sobreviven a `down -v`) + `infra/scripts/create-volumes.sh`; servicio `n8n-init` que importa credencial NVIDIA (opcional, `NVIDIA_API_KEY`) y workflows y los publica en cada arranque; README actualizado | pendiente de revisión |
| P-015 | 2026-11-06 | Andres | Claude Code (`auth-agent`) | `docs/auth/v0.0.2-contrato-auth` | Buscar el contrato de auth y ponerlo en `contracts/` | `services/auth-service/AUTH-RESPONSES.md` (sólo register/login) se mueve a `contracts/auth_frontend.md` y se completa con los 10 endpoints, pedidos, sesión/refresh de un solo uso, JWT/JWKS, flujos por mail y errores reales, verificados contra el servicio en Docker; AGENTS §4.1 enlaza el contrato | pendiente de revisión |
| P-016 | 2026-11-06 | Elian | OpenCode (GLM 5.3 Flash Free) | `fix/jobs/v0.1.0-revision-y-contrato` | Revisión exhaustiva de la implementación de jobs-service (bugs, concurrencia/deadlocks, seguridad XSS/SQLi/auth, checks de la PR y contraste plan/contratos), aplicando los fixes detectados | Lock optimista por `version` con `409 CONFLICT` (antes: lost-update), seed idempotente ante réplicas, validación previa a auth-service, límites de ítems/listas y `page` ≤ 1.000.000 (DoS de entrada), `company_snapshot.name` obligatorio; docs corregidos (no hay `400`, `to_agree` no anula `salary`, `experience` puede ser `null`); confirmados gateway/JWKS/`/me` y errores report-only fuera de alcance | aceptado |
| P-017 | 2026-11-06 | Elian | OpenCode (GLM 5.3 Flash Free) | `fix/jobs/v0.1.0-revision-y-contrato` | Generar el contrato de búsquedas en un MD para compartir con los compañeros (como con el de matching), cubriendo sólo el trabajo propio y lo que cada quien necesita integrar al final | `contracts/jobs_busquedas.md` v0.1.0: tabla de endpoints, roles/service token, paginación, ejemplo de creación con reglas de `422`, `JobOpportunity` y garantías, visibilidad de sueldo, errores y seed; notas de integración por compañero (front, matching, auth, n8n; profile sin dependencias) sin especificar internos de otros servicios | aceptado |
| P-018 | | | | | | | |

---

## 2. Detalle de entradas

### P-001 — Plan inicial del MVP
- **Fecha:** 2026-10-30 · **Autor:** Andres · **Agente:** Claude · **Rama:** `docs/plan/v0.0.1-plan-inicial`
- **Prompt (textual):**
  > quiero generar un plan de trabajo para armar un mvp de una bolsa de trabajo. Quiero que se utilicen los principios solid y la arquitectura rest. usa los principios solid, arquitectura de microservicios, docker, python, django para la configuracion y autenticacion, fastapi, n8n como orquestador de agentes, un mcp local en python para las herramientas, y react para el frontend. […] somos 4 personas y tenemos 2 semanas. Funcionalidades: cargar empleos; recomendar candidatos; cargar CV en doc o pdf y que lo reconozca e integre al sistema, permitir editar o agregar información al perfil; login con mail y clave, cambiar clave/email, recuperar contraseña por mail; descargar CV generado en PDF; empresas con CUIT, actividad y búsquedas activas. Además: perfiles de estudiantes con competencias, ofertas con requisitos, comparación, scoring con criterios explícitos, competencias faltantes, recomendaciones de IA, automatización con n8n, distinguir resultados por reglas de recomendaciones IA. […] Armá en un PDF la arquitectura, capas, tecnologías, roles del equipo, plan de trabajo, requisitos funcionales y no funcionales, historias de usuario y test unitarios. Armá un md con las instrucciones y reglas para cada agente que incluya un registro de los prompts y un resumen de las respuestas. Versionado en GitHub con ramas separadas y versionadas por cada cambio, mergeando a dev.
- **Resumen de la respuesta:**
  - Arquitectura inicial de microservicios + gateway + n8n + mcp-tools en Python, JWT emitido por el servicio de autenticación y validado localmente por FastAPI.
  - Scoring por reglas con 6 criterios y pesos explícitos (50/15/15/10/5/5) + regla excluyente; contrato JSON con bloques `rule_based` (`origin=RULES`) y `ai_recommendations` (`origin=AI`).
  - Roles: TL/DevOps, QA Lead, Integraciones/n8n, SM/PO/Front; plan de 10 días con releases `v0.1.0`, `v0.9.0`, `v1.0.0`.
  - Ramas `<tipo>/<servicio>/v<semver>-<desc>` → PR a `dev` → release a `main`.
- **Decisión:** aceptado; el equipo valida la asignación de roles y el proveedor de LLM.

### P-002 — Contenedores y configuración común
- **Fecha:** 2026-10-31 · **Autor:** Andres · **Agente:** Claude Code (`devops-agent`) · **Rama:** `chore/infra/v0.0.1-contenedores-base` · **HU:** —
- **Prompt (textual):**
  > De estas instrucciones quiero solo crear los contenedores y archivos de configuracion comunes para todo el proyecto. El auth service se va a hacer finalmente con nesjs
- **Resumen de la respuesta:**
  - `docker-compose.yml` + `docker-compose.override.yml` (dev con hot reload), gateway Nginx con rutas por recurso, rate limit en login/reset y errores JSON; Postgres con rol + schema por servicio (n8n en base propia).
  - Dockerfiles multi-stage, usuario no root y healthcheck; esqueleto mínimo con `/health` y un test por servicio (auth en NestJS 11).
  - Cambios respecto del plan: auth en NestJS; Mailpit en lugar de MailHog; volumen Docker en lugar de MinIO para CVs.
  - CI con detección de carpetas modificadas; `ruff.toml`, `.prettierrc.json`, `.editorconfig`, `.gitattributes`, plantilla de PR.
- **Archivos afectados:** raíz, `gateway/`, `infra/`, `.github/`, `services/*`, `mcp-tools/`, `frontend/`, `AGENTS.md`.
- **Decisión:** pendiente de revisión del equipo.

### P-003 — Herramientas MCP, Router NVIDIA y Workflows n8n (Orquestador, Verificador, CV y Recomendador)
- **Fecha:** 2026-10-31 · **Autor:** Andres · **Agente:** Antigravity (`mcp-agent` + `n8n-agent`) · **Rama:** `feature/mcp-n8n/v0.1.0-agentes-nvidia` · **HU:** transversal (IA / MCP / n8n)
- **Prompt (resumido):**
  > Armar los flujos de n8n y los agentes (orquestador, verificador, extractor de CV en PDF/MD/DOC/DOCX por webhook que devuelva JSON estandarizado, y recomendador por webhook para postulantes y empresas) usando modelos remotos de NVIDIA y reutilizando componentes de `C:\Users\Andres\proyectos\agentes`. Migrar Postgres a 17 sin dejar deuda técnica. No hardcodear cantidades ni modelos: tomarlos de `.env` a través de `mcp-tools` para que más adelante puedan venir de un panel de configuración, y mockear los endpoints que aún no existen.
- **Resumen de la respuesta:**
  - Migración de PostgreSQL 16 → 17 con dump/restore e importación de la credencial `OpenAI account` (NVIDIA) en `bolsa-n8n-1`.
  - Implementación completa de `mcp-tools` v0.1.0 por capas SOLID (`domain`, `application`, `infrastructure`, `tools`), con `SettingsProvider` (`env` hoy, `panel` mañana), `ModelRouter` NVIDIA, `CvParserService` (PDF/DOCX/DOC con `antiword`/MD), `VerificationService` (JSON Schema + grounding + integridad de score), adaptadores HTTP y Mock (`MCP_USE_MOCKS=true`), middleware `X-Service-Token` y 90 % de cobertura en `pytest`.
  - Generador `n8n/generate_workflows.py` y workflows `WF-0R`, `WF-0V`, `WF-00`, `WF-01` y `WF-06` en `n8n/workflows/`, más plantillas de prompts y schemas en `contracts/`.
- **Archivos afectados:** `.env.example`, `docker-compose.yml`, `mcp-tools/`, `n8n/`, `contracts/`, `README.md`, `AGENTS.md`.
- **Decisión:** aceptado.

### P-004 — Nodos de Agente de n8n, Perfiles MCP, Skills (`leer_skill`) y Reglas de Repositorio GitHub
- **Fecha:** 2026-11-01 · **Autor:** Andres · **Agente:** Antigravity (`mcp-agent` + `n8n-agent` + `devops-agent`) · **Rama:** `feature/mcp-n8n/v0.2.0-nodos-agente-y-skills` · **HU:** transversal (IA / MCP / n8n / DevOps)
- **Prompt (resumido):**
  > Crear el repositorio en `https://github.com/Grupo-1-EPIALC/bolsa-de-trabajo`, revisar `.gitignore`, armar el versionado, publicar en `dev` con reglas de publicación por ramas de feature y PR. Además, revisar cómo funcionan las herramientas, workflows y skills de `C:\Users\Andres\proyectos\agentes` para que acá funcionen de forma similar con los nodos de agente de n8n, pero sin los modelos locales.
- **Resumen de la respuesta:**
  - Creación y protección del repositorio `Grupo-1-EPIALC/bolsa-de-trabajo` (PR obligatorio + 1 aprobación + `CI Gate` + `Flujo Git y Versionado de Rama` en `dev` y `main`).
  - Evolución de `mcp-tools` a `v0.2.0`: `ProfiledFastMCP` con filtrado de herramientas por `?perfil=` (`planificador`, `cv`, `postulante`, `empresa`, `verificador`, `adjuntos`), soporte de autenticación por `?key=` + `MaskKeyLogFilter`, `reglas.md` (`/reglas`), `FileSystemSkillRepository` con `leer_skill` (protección anti-bucle por sesión) y skills en `mcp-tools/app/data/skills/`.
  - Catálogo de agentes en `n8n/agentes/{_sistema,cv_structurer,training_advisor,company_advisor}.json` y workflows `WF-0R`, `WF-0V`, `WF-00`, `WF-01` y `WF-06` regenerados usando `@n8n/n8n-nodes-langchain.agent`, `@n8n/n8n-nodes-langchain.lmChatOpenAi` (solo NVIDIA NIM, sin Ollama local), `@n8n/n8n-nodes-langchain.memoryBufferWindow`, `@n8n/n8n-nodes-langchain.mcpClientTool` y `@n8n/n8n-nodes-langchain.mcpClient`.
- **Archivos afectados:** `.gitignore`, `.github/workflows/ci.yml`, `VERSION`, `mcp-tools/`, `n8n/agentes/`, `n8n/generate_workflows.py`, `n8n/workflows/`, `AGENTS.md`.
- **Decisión:** aceptado.

### P-005 — Formulario de prueba asíncrono en `profile-service` (Bootstrap 5) y normalización de CV sin `null`
- **Fecha:** 2026-11-01 · **Autor:** Andres · **Agente:** Antigravity (`profile-agent` + `n8n-agent`) · **Rama:** `feature/profile/v0.1.0-cv-webhook-async` · **HU:** HU-04 / HU-05 (Carga y estructuración de CV)
- **Prompt (resumido):**
  > Armar una interfaz de prueba en `profile-service` para enviar un CV al webhook de n8n y devolver el JSON con el perfil. Corregir la demora agregando un indicador de progreso y espera asíncrona del resultado, reconocer campos presentes o análogos devolviendo vacíos los faltantes sin usar `null` (con un indicador para completar manualmente), reparar la extracción en CVs PDF extensos y organizar las tarjetas de forma vertical con ancho fijo en columnas Bootstrap y salto de línea en las respuestas (incluido el JSON).
- **Resumen de la respuesta:**
  - Implementación por capas en `services/profile-service` (`domain/`, `application/`, `infrastructure/`, `api/`): almacenamiento en `CV_STORAGE_PATH`, cola en memoria `CvExtractionJobStore`, endpoints `POST /api/v1/profiles/cv-extract/async`, `GET /api/v1/profiles/cv-extract/jobs/{job_id}` y formulario `GET /api/v1/profiles/cv-test` maquetado con Bootstrap 5.3.3 (`cv-fixed-col` vertical + `json-pre` con `pre-wrap`/`overflow-wrap: anywhere`).
  - Normalización tolerante (`normalize_cv_suggestions` y `normalizeCvCandidate`): mapea claves análogas en español/inglés, reemplaza escalares ausentes por `"COMPLETAR_MANUALMENTE"` y listas vacías por `[]` (cero `null`), y genera `pending_manual_fields`.
  - Optimización de `WF-0R`, `WF-00` y `WF-0V`: `maxTokens: 8192` en NVIDIA NIM para evitar truncamiento tras `<think>`, reparador `extractJsonObject`/`repairJsonString` y fast-path determinístico en `WF-0V`.
- **Archivos afectados:** `services/profile-service/`, `n8n/agentes/cv_structurer.json`, `n8n/generate_workflows.py`, `n8n/workflows/`, `mcp-tools/app/data/schemas/cv_standard.schema.json`, `contracts/cv_standard.schema.json`, `gateway/nginx.conf`, `.env.example`, `AGENTS.md`.
- **Decisión:** aceptado.

### P-006 — Simplificación arquitectónica: eliminación de `ai-service`, red directa `n8n ↔ mcp-tools` y separación de `PROMPTS.md`
- **Fecha:** 2026-11-01 · **Autor:** Andres · **Agente:** Antigravity (`devops-agent` + `n8n-agent` + `mcp-agent`) · **Rama:** `refactor/infra/v0.2.0-sin-ai-service-y-prompts-md` · **HU:** transversal (Arquitectura / DevOps / Documentación)
- **Prompt (resumido):**
  > Vamos a hacer un cambio en la arquitectura: el servicio de IA (`ai-service`) no tiene sentido porque en realidad todo lo hace `n8n`, ni tampoco tiene sentido que `mcp-tools` pase por Nginx para comunicarse con `n8n` que es el único que lo va a consumir. Además, que el historial de prompts se registre en un archivo por separado y no esté en el `README.md`. Hacer esos cambios en la arquitectura y en `AGENTS.md`.
- **Resumen de la respuesta:**
  - Eliminación del contenedor y carpeta `services/ai-service` (trasladando las plantillas de prompts a `n8n/prompts/*.md` y el guardado de recomendaciones a `matching-service`), quitando `ai_svc` de Postgres, `location /api/v1/ai/` de Nginx y `ai-service` del matrix de CI.
  - Comunicación directa y exclusiva `n8n ↔ mcp-tools` (`http://mcp-tools:8000/mcp`) mediante la red interna `mcp_internal` en `docker-compose.yml`, sin pasar por el API Gateway Nginx.
  - Extracción del registro de prompts a `PROMPTS.md` y actualización de `AGENTS.md`, `README.md` y `.github/PULL_REQUEST_TEMPLATE.md`.
- **Archivos afectados:** `PROMPTS.md`, `AGENTS.md`, `README.md`, `docker-compose.yml`, `docker-compose.override.yml`, `gateway/nginx.conf`, `infra/postgres/init/01-schemas.sh`, `.env.example`, `.github/workflows/ci.yml`, `.github/PULL_REQUEST_TEMPLATE.md`, `n8n/generate_workflows.py`, `n8n/prompts/`, `mcp-tools/`, `contracts/mock_endpoints.yaml`.
- **Decisión:** aceptado.

### P-007 — `matching-service` v0.1.0: motor de reglas, recomendaciones, JWT y configuración por admin
- **Fecha:** 2026-11-04 · **Autor:** Andres · **Agente:** Claude Code (`matching-agent`) · **Rama:** `feature/matching/v0.1.0-motor-reglas-y-recomendador` · **HU:** Matching y recomendaciones (estudiantes y empresas)
- **Prompt (resumido):**
  > En función a `contracts/estructura_comun_perfil_oferta_match.md` armá el servicio de match y el agente que va a hacer los match en n8n para recomendar a empresas y estudiantes: n8n hace el análisis y el servicio devuelve las recomendaciones. Después: armar un pool de datos de prueba, un contrato md para el front que explique el cálculo del score, revisar la integración con auth-service, verificar arquitectura y estándares, separar en 2 ramas y que la cantidad de ofertas y candidatos se pueda ajustar en configuración por un admin.
- **Resumen de la respuesta:**
  - Capas `domain/` (6 `ScoringCriterion` con pesos en `scoring_rules.yaml`, tope 40 por excluyente, `MissingSkillsAnalyzer`, 12 `ConditionCheck` duros/blandos, `SalaryComparator` §7.2), `application/` (mappers del contrato + legacy de mocks MCP, rankings, recomendaciones, `AccessPolicy`, `SettingsService`), `infrastructure/` (REST a profile/jobs, trigger a WF-06, mocks, repositorios en memoria, JWT) y `api/`.
  - Endpoints para el front (vistas reglas + IA, pedidos asíncronos, match puntual, `/settings`) e internos para n8n/mcp-tools (rankings, missing-skills, guardado). Contratos `matching_service.openapi.json` y `matching_frontend.md`.
  - Seguridad: JWT RS256 de auth-service validado contra el JWKS (`pyjwt[crypto]`), acceso por rol y dueño (404 en recursos ajenos, 403 en internos) y token de servicio sólo por `X-Service-Token`. Errores 404/405 con el formato común.
  - Pool de datos ficticios (15 perfiles y 12 ofertas con dueños UUID); los tests usan fixtures propios. 102 tests, 97 % de cobertura, ruff/black/mypy estricto limpios.
- **Archivos afectados:** `services/matching-service/`, `contracts/matching_service.openapi.json`, `contracts/matching_frontend.md`, `contracts/mock_endpoints.yaml`, `docker-compose.yml`, `.env.example`, `AGENTS.md`.
- **Decisión:** pendiente de revisión (librerías nuevas `pyyaml` y `pyjwt[crypto]` a discutir en la daily).

### P-008 — Agente `match_advisor` en WF-06 y herramientas MCP de ranking (`mcp-tools` v0.3.0)
- **Fecha:** 2026-11-05 · **Autor:** Andres · **Agente:** Claude Code (`mcp-agent` + `n8n-agent`) · **Rama:** `feature/mcp-n8n/v0.3.0-match-advisor-ranking` (sale de `feature/matching/v0.1.0-motor-reglas-y-recomendador`) · **HU:** Matching y recomendaciones (estudiantes y empresas)
- **Prompt (resumido):**
  > Armá el agente que va a hacer los match en n8n para recomendar a las empresas y a los estudiantes (n8n hace el análisis y el servicio devuelve las recomendaciones). Separá en 2 ramas, agregá en mcp-tools herramientas de ranking (`rank_jobs_for_student`, `rank_candidates_for_job`) y que WF-06 las use; los números de ofertas y candidatos ajustables por un admin.
- **Resumen de la respuesta:**
  - `mcp-tools` v0.3.0: `rank_jobs_for_student` y `rank_candidates_for_job` (sólo lectura) detrás de `MatchingGateway`, con adaptador HTTP a matching-service (sin `limit` usa la cantidad del admin) y mock con la misma forma, sin datos personales; agregadas a los perfiles `postulante` y `empresa`. Schemas `match_*_recommendations` registrados.
  - n8n: agente `match_advisor` (Jean Grey), prompt `match_advisor.md` v1.0.0, tareas `match_student`/`match_company` en WF-00, términos de grounding nuevos en WF-0V y WF-06 reescrito: ranking por MCP, contexto sin nombres ni montos, agente, filtro de integridad (sin score/rank del LLM, sólo ids del ranking, orden por reglas) y guardado por REST en matching-service. El flujo de cursos queda como `mode=training`. Generador con salida LF.
- **Archivos afectados:** `mcp-tools/`, `n8n/agentes/match_advisor.json`, `n8n/prompts/match_advisor.md`, `n8n/generate_workflows.py`, `n8n/workflows/`, `contracts/match_student_recommendations.schema.json`, `contracts/match_company_recommendations.schema.json`, `contracts/mock_endpoints.yaml`, `AGENTS.md`.
- **Decisión:** pendiente de revisión (requiere review de Integrante 1 por `mcp-tools`).

### P-009 — Maquetación SPA del Frontend, Cliente API y UX de Navegación (v0.1.0)
- **Fecha:** 2026-11-05 · **Autor:** Dario · **Agente:** Gemini (`frontend-agent`) · **Rama:** `feature/frontend/v0.1.0-vistas-iniciales` · **HU / RNF:** HU-01, HU-02, HU-03, HU-07, HU-08, HU-14, HU-15 / RNF-04, RNF-12, RF-19
- **Prompt (resumido):**
  > Desarrollar e integrar la interfaz SPA del Frontend en React 18 + Vite + Tailwind CSS v4, estableciendo la capa de infraestructura HTTP desacoplada (`VITE_USE_MOCKS`) para alternar entre datos locales de prueba y el API Gateway Nginx (`http://localhost:8080/api/v1`), implementando la separación visual de Scoring (RULES vs AI), Perfil de Estudiante con validación de CV y Auth con CUIT/Registro y Toast de bienvenida.
- **Resumen de la respuesta:**
  - Implementación de cliente HTTP resiliente `src/services/api.ts` (`apiFetch`) sanitizado para respuestas 304, 404, 500 y parseo seguro de JSON.
  - Componentes `RuleScoreCard.tsx` (badge verde `origin="RULES"`, fondo tenue `bg-emerald-100/60`) y `AISuggestionCard.tsx` (badge ámbar `origin="AI"`, fondo tenue `bg-amber-100/60` con disclaimer).
  - Formulario `AuthForm.tsx` con soporte para CUIT/Razón Social y notificación callback `onLoginSuccess` para redirección automática y Toast centrado de bienvenida (3 seg).
  - Componente `StudentProfile.tsx` con encabezado destacado (`text-2xl sm:text-3xl font-black`) y validación en cliente para CVs PDF/DOCX max 5 MB (RNF-04).
  - Menú hamburguesa responsive (`md:hidden`) y layout Full-width en `App.tsx`.
- **Archivos afectados:** `frontend/src/App.tsx`, `frontend/src/components/*`, `frontend/src/services/*`, `frontend/src/types/*`, `AGENTS.md`, `PROMPTS.md`.
- **Decisión:** aceptado (comprobado localmente en Vite y validado en vivo contra el stack Docker de microservicios).

### P-010 — Plan e implementación de jobs-service (búsquedas/vacantes)
- **Fecha:** 2026-11-05 · **Autor:** Elian · **Agente:** OpenCode (DeepSeek V4.1 Flash Free) · **Rama:** `docs/jobs/v0.1.0-plan-y-contratos` (plan y contratos) → `feature/jobs/v0.1.0-ofertas-empresa` (implementación) · **HU:** Cargar empleos y búsquedas activas de empresas (AGENTS.md §4.3)
- **Prompt (resumido y estructurado):**
  > Actuá como `jobs-agent` (AGENTS.md §4.3). Antes de escribir código, elaborá un plan de implementación para las búsquedas/vacantes de empresas en `services/jobs-service`. Usá como fuente de verdad AGENTS.md §1–§3 y §4.3, README.md, `contracts/estructura_comun_perfil_oferta_match.md`, `contracts/matching_frontend.md`, `contracts/mock_endpoints.yaml` y los consumidores `matching-service`/`mcp-tools`. No inventes funcionalidades ni cambies el alcance: cada requisito del plan debe estar justificado por un MD del proyecto. Incluí contratos para el frontend y para matching, endpoints, modelo de datos, persistencia, auth, validación, tests UT-JOBS-01/02, riesgos y fases. No toques código de otros servicios. Después implementá el plan en `services/jobs-service`.
- **Resumen de la respuesta:**
  - Se separó lo obligatorio por MD (Job/Requirement, active/closed, 403 para recurso ajeno, ≥1 required, `GET /companies/me/searches`, `job.created`, tests) de lo que no corresponde al MVP.
  - Se definieron los contratos OpenAPI + front + matching, la arquitectura por capas, el schema PostgreSQL `jobs`, JWT RS256/`X-Service-Token` y las fases hasta el 20.
  - Implementación v0.1.0 completa por capas: dominio puro (modelos, reglas, visibilidad de sueldo, normalización), aplicación (`JobService` con creación/edición/cierre/reapertura, paginación, propiedad y evento `job.created` best-effort), infraestructura (JWT RS256 vía JWKS, auth-service, n8n, repositorios SQLAlchemy 2.0 e in-memory, seed de 12 ofertas) y API FastAPI (`/api/v1/jobs`, `/api/v1/companies/me/searches`).
  - Seed determinístico con los mismos `id`/`company_id` del pool de matching; 99 tests (UT-JOBS-01/02 incluidos) con 94.79 % de cobertura; `ruff`, `black` y `mypy app` sin errores.
- **Archivos afectados:** `PROMPTS.md`, `contracts/jobs_service.openapi.json`, `contracts/jobs_frontend.md`, `contracts/jobs_matching.md`, `docs/jobs/v0.1.0-plan.md` y `services/jobs-service/` (app por capas, `scripts/generate_seed.py`, `app/infrastructure/data/jobs_seed.json`, `tests/`).
- **Decisión:** aceptado (pendiente review de Dario y del compañero de matching).

### P-011 — `profile-service` v0.2.0: perfil completo, CV con IA y CV IA friendly en PDF/DOCX
- **Fecha:** 2026-11-06 · **Autor:** Andres · **Agente:** Claude Code (`profile-agent`) · **Rama:** `feature/profile/v0.2.0-perfil-completo-y-cv-ia` · **HU:** Perfil del estudiante y carga de CV
- **Prompt (resumido):**
  > Teniendo en cuenta `contracts/estructura_comun_perfil_oferta_match.md` y AGENTS.md, armar el servicio de profile (Python + FastAPI, en Docker). El usuario da el alta con auth y carga el CV; el servicio devuelve lo reconocido y pide completar el resto; después completa disponibilidad, modalidad, etc. Sin login pide loguear; sin perfil ofrece cargar el CV o el perfil a mano; con el perfil cargado permite generar un CV nuevo "IA friendly", moderno y profesional, descargable en DOCX o PDF. Entregar el contrato para matching (si no coincide con lo actual) y para el front.
- **Resumen de la respuesta:**
  - Dominio puro: `StudentProfile` y bloques §4–§5, enums §3, `ProfileCompletenessPolicy` (reglas por paso `cv`/`preferences`/`privacy`, `origin: "RULES"`), `SkillExtractor` con `skills_catalog.json` (claves de matching), `CvDocumentBuilder` y serialización genérica dataclass ↔ JSON.
  - Aplicación: `ProfileService` (alta, `PATCH` por secciones, rechazo de `COMPLETAR_MANUALMENTE`, invariantes, normalización, meses de experiencia, `profile.updated` best-effort), `CvSuggestionMapper` (sugerencias de WF-01 → `profile_draft` + `review_fields`, sin `null`, sin inventar) y vistas por rol (dueño, admin, servicio, empresa) con minimización de datos.
  - Infraestructura: PostgreSQL (SQLAlchemy, schema `profile`) o memoria, JWT RS256 vía JWKS, email desde `/auth/me`, evento a n8n, seed con los 15 perfiles del pool de matching y renderers HTML (Jinja2), PDF (WeasyPrint, PDF/UA, fuente Inter) y DOCX (python-docx, estilos nativos).
  - API: `/profiles/me` (GET/POST/PATCH), `/me/cv` (multipart) + polling, `/me/cv-suggestions`, `/me/cv.pdf|docx|html`, y para servicios/admin `GET /profiles` y `/profiles/{id}`. Los endpoints `cv-extract` quedan por compatibilidad y ahora piden autenticación.
  - Pedido posterior: "también hay que crear el perfil de empresa, que lleva menos datos: logo, rubro, ubicación, búsquedas activas, etc." + "recordá que las búsquedas tienen su servicio propio y no van en profile". Se agregó `CompanyProfile` en `/api/v1/profiles/companies/...` (razón social, CUIT y actividad como copia de sólo lectura de auth-service; nombre comercial, logo validado por firma y servido público, rubro, tamaño, sede, descripción, links, beneficios, contacto, qué perfiles contrata), completitud por reglas (`company`/`branding`), vistas por rol y `snapshot` para jobs-service. Las búsquedas no se guardan ni se consultan desde profile-service. Seed de 10 empresas con los mismos `company_id` que jobs-service.
  - Verificado: 92 tests (UT-PROF-01 a 08), 97 % de cobertura, ruff/black/mypy limpios dentro de Docker. Prueba punta a punta por el gateway con auth y Postgres reales. matching-service con `MATCHING_USE_MOCKS=false` da el mismo ranking que con mocks.
- **Archivos afectados:** `services/profile-service/`, `contracts/profile_frontend.md`, `contracts/profiles_matching.md`, `contracts/company_profile_frontend.md`, `contracts/company_profiles_jobs.md`, `contracts/profile_service.openapi.json`, `contracts/mock_endpoints.yaml`, `contracts/cv_recognition_profile_service.md`, `docker-compose.yml`, `.env.example`, `AGENTS.md`, `PROMPTS.md`.
- **Decisión:** pendiente de revisión (librerías nuevas a discutir en la daily: `jinja2`, `weasyprint`, `python-docx`; `sqlalchemy`, `psycopg` y `pyjwt` ya las usa jobs-service).

### P-012 — Frontend v0.2.0: estilo institucional con Bootstrap y portada pública
- **Fecha:** 2026-11-06 · **Autor:** Andres · **Agente:** Claude Code (`frontend-agent`) · **Rama:** `feature/frontend/v0.2.0-estilo-bootstrap` · **HU:** HU-01, HU-02, HU-03 (acceso) / RNF de accesibilidad
- **Prompt (resumido):**
  > Adaptar el diseño del front (usando Bootstrap y Bootstrap Icons) al diseño y estilo de https://www.udelaciudad.edu.ar/ y usar la foto adjunta como imagen de portada cuando el usuario no se autenticó / dio de alta. Aclaración: predomina el magenta, el violeta está para algunos detalles y el blanco para los fondos.
- **Resumen de la respuesta:**
  - Paleta y tipografía tomadas de las variables globales de Elementor del sitio (`#BA3995`, `#682CAD`, `#FFD200`, `#E3B0D5`, Montserrat); sólo estilo, sin logos ni textos de la universidad.
  - Dependencias: se quitan `tailwindcss`, `@tailwindcss/vite`, `postcss`, `autoprefixer` y `lucide-react`; se agregan `bootstrap` y `bootstrap-icons` (a confirmar en la daily). Tema en `src/styles/theme.css` sobre variables CSS de Bootstrap (sin Sass).
  - Layout: barra superior magenta, navbar blanca con links violeta y botón magenta "Registrate", footer magenta (`components/layout/`).
  - Sin sesión: `pages/LandingPage.tsx` (hero con la foto `src/assets/portada.jpg` optimizada a 1920 px / 245 KB y rótulo magenta redondeado, secciones de beneficios y pasos, banda para empresas) y `pages/AuthPage.tsx` (foto de fondo + formulario). Con sesión: encabezado magenta + vistas existentes.
  - `navigation.ts` con `resolveView` (vistas privadas inaccesibles sin sesión) y `navigation.test.ts`. Componentes reescritos en Bootstrap manteniendo la lógica y la separación RULES (verde) / IA (ámbar + disclaimer).
  - Verificado en Docker: `tsc --noEmit` + `vite build` OK, 5 tests Vitest OK, prettier OK; capturas con Playwright en escritorio y móvil.
- **Archivos afectados:** `frontend/package.json`, `frontend/package-lock.json`, `frontend/vite.config.ts`, `frontend/index.html`, `frontend/src/` (`main.tsx`, `App.tsx`, `navigation*.ts`, `styles/theme.css`, `assets/portada.jpg`, `pages/`, `components/`), `PROMPTS.md`.
- **Decisión:** pendiente de revisión (Integrante 3).

### P-013 — Frontend: flujos de estudiante y empresa según los contratos de profile-service
- **Fecha:** 2026-11-06 · **Autor:** Andres · **Agente:** Claude Code (`frontend-agent`) · **Rama:** `feature/frontend/v0.2.0-estilo-bootstrap` · **HU:** HU-01, HU-02, HU-03, HU-07, HU-08 y perfil de empresa
- **Prompt (resumido):**
  > Fijate el contrato `contracts/profile_frontend.md`. El usuario sin loguearse ve el home; si ya tiene perfil ve sus opciones: traer recomendaciones de ofertas, modificar perfil y descargar su CV en PDF o Word. Si no tiene usuario, alta de usuario y luego alta de perfil; si no tiene perfil, ofrecer importar datos desde el CV o cargarlos a mano. Revisá también `contracts/company_profile_frontend.md`.
- **Resumen de la respuesta:**
  - `services/api.ts` como cliente único: JWT, refresh automático ante 401, error común `{error: {code, message, details}}` → `ApiError`, mensajes de validación 422. `session.ts` con tokens y usuario.
  - Se corrigen login/registro contra auth-service real (respuesta `access_token`/`refresh_token`/`user`, empresa en `company.{legal_name,cuit,activity}`, contraseña ≥ 12); se quitan el "éxito mock" y `mockData.ts`.
  - Estudiante (`pages/StudentArea.tsx`): sin perfil → `ProfileStart` (importar CV o manual); `CvImport` con polling cada 1,5 s y progreso; `ProfileWizard` en 3 pasos (datos del CV / preferencias / privacidad) con `PATCH` por sección, precarga de `profile_draft`, campos `COMPLETAR_MANUALMENTE` resaltados, badge IA + disclaimer; `ProfileDashboard` con ofertas, edición, descarga PDF/Word y vista previa (iframe sandbox); completitud con badge "Calculado por reglas".
  - `JobRecommendations`: vista de matching-service con bloque por reglas (score, desglose, skills, condiciones) separado del bloque IA (sin score), pedido a WF-06 y polling cada 3 s; 404 → "tu perfil todavía no entró al matching".
  - Empresa (`pages/CompanyArea.tsx`): alta precargada, formulario en 2 pasos (datos / marca empleadora con logo), panel con perfil, completitud y búsquedas activas de jobs-service.
  - Lógica pura en `profile/draft.ts` (placeholders, compactado del payload, paso pendiente) con tests. Verificado: `tsc` + build + 12 tests Vitest; E2E Playwright contra el stack: registro → alta manual → panel → descargas `CV_Julian_Ficticio.pdf/.docx` → ofertas; empresa → perfil → logo → panel.
- **Archivos afectados:** `frontend/src/` (`services/`, `types/`, `profile/`, `components/form|profile|matching|company|layout/`, `pages/`, `App.tsx`, `navigation*.ts`), `PROMPTS.md`.
- **Decisión:** pendiente de revisión. React Hook Form/Zod/TanStack Query (AGENTS §4.7) no se agregaron: formularios con estado propio hasta acordarlo en la daily.

### P-014 — n8n: workflows persistentes y datos en volúmenes externos
- **Fecha:** 2026-11-06 · **Autor:** Andres · **Agente:** Claude Code (`devops-agent` + `n8n-agent`) · **Rama:** `feature/frontend/v0.2.0-estilo-bootstrap` · **HU:** infraestructura
- **Prompt (resumido):**
  > Revisá qué pasó que desaparecieron los workflows de n8n y asegurate que persistan. Que las bases, las configuraciones y los archivos de media se creen por fuera de la imagen de Docker, así persisten si recreo los contenedores.
- **Resumen de la respuesta:**
  - Diagnóstico: la base `n8n` tenía 0 workflows, 0 credenciales y 0 ejecuciones; los volúmenes `bolsa_pg_data`/`bolsa_n8n_data` se crearon el 2026-11-03 (el README indicaba `docker compose down -v`) y la importación de workflows era un paso manual.
  - Volúmenes `pg_data`, `n8n_data` y `cv_storage` declarados `external` (`bolsa_*`): compose no los crea ni los borra, ni con `down -v`. Se crean una vez con `infra/scripts/create-volumes.sh`. Los logos de empresas están en Postgres.
  - Servicio `n8n-init` (`n8n/init/bootstrap.sh`) que corre antes de n8n: credencial NVIDIA desde `NVIDIA_API_KEY` (opcional; vacía no toca la de la UI), `import:workflow` (ids fijos) y `publish:workflow`. Verificado con `--force-recreate`: 5 workflows activos y webhooks `cv-extract`/`recommendations` en 200.
- **Archivos afectados:** `docker-compose.yml`, `n8n/init/bootstrap.sh`, `infra/scripts/create-volumes.sh`, `.env.example`, `README.md`, `.github/pull_request_template.md`, `PROMPTS.md`.
- **Decisión:** pendiente de revisión (Integrante 4 por compose). Falta cargar la credencial de NVIDIA (UI o `NVIDIA_API_KEY`).

### P-015 — Contrato de auth-service en `contracts/`
- **Fecha:** 2026-11-06 · **Autor:** Andres · **Agente:** Claude Code (`auth-agent`) · **Rama:** `docs/auth/v0.0.2-contrato-auth` · **HU:** HU-01, HU-02, HU-03 (contrato)
- **Prompt (resumido):**
  > Revisá si encontrás el contrato del auth y ponelo en `contracts`.
- **Resumen de la respuesta:**
  - El único documento era `services/auth-service/AUTH-RESPONSES.md` (PR #9), que cubría sólo `register` y `login`. Se movió a `contracts/auth_frontend.md`, siguiendo el nombre de los otros contratos para el front.
  - Se completó con lo que hace el código: los 10 endpoints (incluidos `token/refresh`, `me`, cambio/recuperación de clave, cambio de email y JWKS), reglas de los pedidos, refresh de un solo uso, revocación al cambiar la clave, claims del JWT, links de los mails al front y la tabla de errores.
  - Todo verificado contra el servicio en Docker. Detalles que no estaban: en validación `message` es una lista (también en `details.validation_errors`); sin Bearer el código es `HTTP_401`.
  - AGENTS §4.1 enlaza el contrato. auth-service pasa a 0.0.2.
- **Archivos afectados:** `contracts/auth_frontend.md` (antes `services/auth-service/AUTH-RESPONSES.md`), `services/auth-service/package.json`, `services/auth-service/package-lock.json`, `AGENTS.md`, `PROMPTS.md`.
- **Decisión:** pendiente de revisión (Integrante 1, dueño de auth-service). Pendiente en el front: pantallas para los links `/auth/password/reset/confirm` y `/auth/email/confirm`.

### P-016 — Revisión exhaustiva de jobs-service y fixes de concurrencia/seguridad/docs
- **Fecha:** 2026-11-06 · **Autor:** Elian · **Agente:** OpenCode (GLM 5.3 Flash Free) · **Rama:** `fix/jobs/v0.1.0-revision-y-contrato` (PR #15 a `dev`; revisión hecha sobre la rama de la PR #10 ya mergeada) · **HU:** transversal de jobs-service
- **Prompt (resumido):**
  > Hacé una revisión exhaustiva de los cambios del jobs-service en la PR: bugs y edge cases, problemas de concurrencia y deadlocks, seguridad (XSS, SQL injection, tokens/JWT), el estado de los checks de la PR, y el contraste contra la documentación (plan, AGENTS §4.3, `estructura_comun` y los contratos de matching/front/openapi). Cargá el prompt en `PROMPTS.md`. Después: subir los cambios con el "por qué" y cargar también el prompt del contrato de búsquedas.
- **Resumen de la respuesta (hallazgos → fix):**
  - **Lost-update** en create/update/close (read-modify-write sin guard): se agrega lock optimista — `update(job, expected_version)` en la interfaz `JobRepository` con `UPDATE ... WHERE id=… AND version=…` (memoria y SQLAlchemy) y nuevo `409 CONFLICT` (`ConflictError`). El cierre sigue idempotente si otro escritor ya cerró.
  - **Seed con carrera entre réplicas** (count-then-add): inserts duplicados por carrera se saltan (idempotente) y cualquier otro error de arranque se propaga.
  - **Orden de dependencias en `create`**: se valida el payload antes de consultar auth-service (un body inválido responde `422` sin upstream) y se agrega regla `ensure_company_snapshot` (garantía 1 de `jobs_matching.md`).
  - **DoS de entrada**: límites por ítem y por lista en todos los arrays del body (`skills ≤50`, `languages/education/certifications ≤20`, `responsibilities/benefits ≤50 con ítems ≤500`, etc.) y `page` acotado a 1.000.000 en deps + OpenAPI.
  - **Docs desalineados**: no existen respuestas `400` (tabla de `jobs_frontend.md` y plan corregidas; OpenAPI `400→422` y componente `Conflict`); `to_agree` no produce `salary: null` (min/max en `null`); garantía 6 ajustada (`experience` puede ser `null`, matching lo tolera).
  - **Confirmado sin cambios**: gateway borra `X-Service-Token`; refresh opaco (no JWT) → sin confusión Bearer; auth `/me` coincide con `HttpCompanyDirectory`; matching tolera `experience: null` y coordenadas faltantes.
  - **Report-only (fuera de alcance de la rama)**: falta ruta exacta `/api/v1/jobs` en el gateway, `JOBS_SEED_DEMO`/`AUTH_SERVICE_URL` sin pipeline en compose, WF-02 aún no consume `job.created`, flood de `kid` sobre el JWKS mitigado por caché (600 s) y, tras la actualización de AGENTS.md, evaluar el `snapshot` de empresa de profile-service como fuente de `company_snapshot`.
- **Archivos afectados:** `services/jobs-service/app/**` (errors, ports, rules, job_service, deps, schemas, repositories, seed), `services/jobs-service/tests/**` + `tests/fakes.py`, `contracts/jobs_service.openapi.json`, `contracts/jobs_frontend.md`, `contracts/jobs_matching.md`, `docs/jobs/v0.1.0-plan.md`, `PROMPTS.md`.
- **Decisión:** aceptado.

### P-017 — Contrato de búsquedas consolidado para el equipo (v0.1.0)
- **Fecha:** 2026-11-06 · **Autor:** Elian · **Agente:** OpenCode (GLM 5.3 Flash Free) · **Rama:** `fix/jobs/v0.1.0-revision-y-contrato` · **HU:** Cargar empleos y búsquedas activas de empresas
- **Prompt (textual):**
  > ok, mis compañeros pidieron que les pase el contrato de busquedas, así como pasé con el contrato de matching, pero de mi trabajo que hicimos. pasame eso en un md, nosotros solo tocamos lo que es busquedas, no tocamos otras cosas de otros servicios o de otros compañeros, por las dudas
- **Resumen de la respuesta:**
  - Nuevo `contracts/jobs_busquedas.md` (v0.1.0): alcance declarado "sólo búsquedas", tabla de los 6 endpoints + `/health`, roles (student/company/admin/service-token), paginación (`page ≤ 1.000.000`, `size 1–200`, alias `limit`), ejemplo de creación con la tabla de reglas `422`, PATCH (reabrir)/DELETE (cierre idempotente), modelo `JobOpportunity` con garantías, matriz de visibilidad de sueldo (`to_agree` viaja con `min`/`max` en `null`), tabla de errores (sin `400`, con `409`) y seed demo.
  - **Lo que necesita integrar cada compañero al final:** front (Integrante 4) — flujos con Bearer, manejo 401 (refresh) / 409 (recargar y reaplicar) / 422 (mapear `details[].loc`), sueldo con `salary === null` → "Sueldo no publicado"; matching (Integrante 3, review I1) — consumir `GET /api/v1/jobs` con `X-Service-Token` y `limit`, sueldo completo y `experience` tolerante a `null`; auth (Integrante 1) — exponer JWKS y `GET /me` con `company.{legal_name, cuit, activity}`; n8n (Integrante 3) — recibir `POST {N8N_WEBHOOK_BASE_URL}/job-created` con `X-Service-Token` (WF-02 pendiente); profile (Integrante 2) — sin dependencias de búsquedas en `v0.1.0`, con el `snapshot` de empresa como alternativa futura a `/auth/me`.
  - El MD lista lo que búsquedas consume de otros servicios pero **no especifica internos** de auth/profile/matching/n8n/gateway (alcance pedido).
- **Archivos afectados:** `contracts/jobs_busquedas.md`, `PROMPTS.md`.
- **Decisión:** aceptado.

- ### P-018 — (plantilla)
- **Fecha:** · **Autor:** · **Agente:** · **Rama:** · **HU:**
- **Prompt (textual o resumido):**
  > …
- **Resumen de la respuesta:**
  - …
- **Archivos afectados:** …
