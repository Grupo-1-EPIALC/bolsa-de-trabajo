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
| P-001 | 2026-10-30 | Andres | Claude (planificación) | `docs/plan/v0.0.1-plan-inicial` | Generar plan de trabajo para MVP de bolsa de trabajo con SOLID, REST, microservicios, Docker, Django, FastAPI, n8n, MCP Python y React; 4 personas, 2 semanas; PDF con arquitectura, capas, tecnologías, roles, plan, RF/RNF, HU y tests; MD con reglas de agentes y registro de prompts | Se generó `Plan_MVP_Bolsa_de_Trabajo.pdf` (11 secciones: servicios, 21 RF, 14 RNF, 18 HU ≈ 67 pts, 34 casos de test, plan día a día en 2 sprints, flujo Git) y `AGENTS.md` con agentes de desarrollo y de runtime | aceptado (pendiente revisión del equipo) |
| P-002 | 2026-10-31 | Andres | Claude Code (`devops-agent`) | `chore/infra/v0.0.1-contenedores-base` | Crear sólo los contenedores y archivos de configuración comunes; auth-service pasa a NestJS | Compose (dev/prod), gateway Nginx, Postgres con rol+schema por servicio, Dockerfiles multi-stage no root con healthcheck, esqueletos `/health` por servicio, CI por carpeta, config común de lint y plantilla de PR | pendiente de revisión |
| P-003 | 2026-10-31 | Andres | Antigravity (`mcp-agent` + `n8n-agent`) | `feature/mcp-n8n/v0.1.0-agentes-nvidia` | Armar flujos de n8n y agentes (orquestador, verificador, extractor de CV PDF/DOC/DOCX/MD y recomendador postulantes/empresas) usando modelos remotos de NVIDIA, reutilizando router/lectura de `agentes`, migrando Postgres a 17 y dejando toda la configuración en `.env` vía `mcp-tools` (con soporte futuro para panel y mocks de endpoints pendientes) | Migración a PostgreSQL 17, `mcp-tools` v0.1.0 con arquitectura limpia (`domain`/`application`/`infrastructure`/`tools`), router NVIDIA, `parse_cv_file` (con `antiword`), validación JSON Schema + grounding, mocks configurables (`MCP_USE_MOCKS`), cobertura 90 % y workflows `WF-0R`, `WF-0V`, `WF-00`, `WF-01` y `WF-06` | aceptado |
| P-004 | 2026-11-01 | Andres | Antigravity (`mcp-agent` + `n8n-agent` + `devops-agent`) | `feature/mcp-n8n/v0.2.0-nodos-agente-y-skills` | Crear repo `Grupo-1-EPIALC/bolsa-de-trabajo` con reglas de publicación (PR + ramas por feature) y alinear la arquitectura de agentes con `C:\Users\Andres\proyectos\agentes` usando los nodos de Agente de n8n (`@n8n/n8n-nodes-langchain.agent`, `mcpClientTool`, `mcpClient`, `memoryBufferWindow`), perfiles MCP y skills (`leer_skill`), sin modelos locales Ollama | Repo creado y protegido en GitHub (`dev` y `main`), `mcp-tools` v0.2.0 con `ProfiledFastMCP` (`?perfil=`), `leer_skill` (con anti-bucle), `reglas.md`, skills de reclutamiento + ingeniería, catálogo `n8n/agentes/*.json` y workflows regenerados con nodos nativos de Agente de n8n conectados a NVIDIA NIM | aceptado |
| P-005 | 2026-11-01 | Andres | Antigravity (`profile-agent` + `n8n-agent`) | `feature/profile/v0.1.0-cv-webhook-async` | Armar formulario de prueba en `profile-service` para enviar un CV al webhook de n8n (`WF-01`) con espera asíncrona e indicador de progreso, tarjetas verticales en columnas de ancho fijo con Bootstrap 5 y salto de línea en el JSON, optimizando la verificación y reemplazando campos ausentes por `COMPLETAR_MANUALMENTE` / `[]` (sin `null`) | Endpoints `/api/v1/profiles/cv-test`, `/cv-extract/async` y `/cv-extract/jobs/{job_id}` por capas en `profile-service` con UI Bootstrap 5 vertical y wrap de JSON, normalizador de campos análogos (`COMPLETAR_MANUALMENTE` + `pending_manual_fields`), `maxTokens: 8192` + reparador de JSON en `WF-00`/`WF-0R` y verificación instantánea determinística en `WF-0V` | aceptado |
| P-006 | 2026-11-01 | Andres | Antigravity (`devops-agent` + `n8n-agent` + `mcp-agent`) | `refactor/infra/v0.2.0-sin-ai-service-y-prompts-md` | Simplificar arquitectura eliminando `ai-service` (ya que toda la IA corre en `n8n`), asegurar que `mcp-tools` se comunique directo con `n8n` sin pasar por Nginx (`gateway`), y separar el historial de prompts en un archivo independiente (`PROMPTS.md`) fuera de `README.md` y `AGENTS.md` | Eliminación de `services/ai-service` (plantillas movidas a `n8n/prompts/`), red interna `mcp_internal` directa entre `n8n` y `mcp-tools` sin exposición en `gateway/nginx.conf`, actualización de `docker-compose*.yml`, `.env.example`, `01-schemas.sh`, `ci.yml`, `README.md`, `AGENTS.md` y extracción del historial a `PROMPTS.md` | aceptado |
| P-007 | 2026-11-04 | Andres | Claude Code (`matching-agent`) | `feature/matching/v0.1.0-motor-reglas-y-recomendador` | En base a `estructura_comun_perfil_oferta_match.md`, armar el servicio de match (n8n analiza y el servicio devuelve las recomendaciones); pool de datos de prueba; contrato para el front con el cálculo del score; integrar el JWT de auth-service; límites de ofertas/candidatos configurables por admin | `matching-service` v0.1.0 por capas (6 criterios, regla excluyente, `MissingSkillsAnalyzer`, 12 `ConditionCheck`, `SalaryComparator`, rankings, pedidos a WF-06, guardado y vistas reglas+IA), JWT RS256 vía JWKS con acceso por rol y dueño, `/settings` para admin, pool de 15 perfiles y 12 ofertas, `contracts/matching_frontend.md`; 102 tests, 97 % | pendiente de revisión |
| P-008 | 2026-11-05 | Andres | Claude Code (`mcp-agent` + `n8n-agent`) | `feature/mcp-n8n/v0.3.0-match-advisor-ranking` | Agente de n8n que hace los match para recomendar a empresas y estudiantes; herramientas MCP de ranking (`rank_jobs_for_student`, `rank_candidates_for_job`) usadas por WF-06; cantidades configurables por admin | `mcp-tools` v0.3.0 con las 2 herramientas (HTTP a matching-service + mocks, perfiles `postulante`/`empresa`), agente `match_advisor` (Jean Grey) con prompt y 2 schemas sin score (`maxItems` 20), WF-06 reescrito (`student`/`company` por MCP, `training` conservado) que descarta score/rank/ids inventados y guarda en matching-service | pendiente de revisión |
| P-009 | | | | | | | |

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

### P-009 — (plantilla)
- **Fecha:** · **Autor:** · **Agente:** · **Rama:** · **HU:**
- **Prompt (textual o resumido):**
  > …
- **Resumen de la respuesta:**
  - …
- **Archivos afectados:** …
- **Decisión:** aceptado / aceptado con cambios / descartado — motivo

