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
| P-018 | 2026-11-06 | Andres | Claude Code (`auth-agent`) | `feature/auth/v0.1.0-admin-cuentas` | Panel de admin: listar usuarios y empresas, editarlos, resetear la clave, cambiar el correo y soft delete (el borrado desaparece de los listados y permite re-alta con el mismo email/CUIT). Back transversal en un core-service nuevo, postulaciones para después, por fases con un PR por servicio. Después: quitar la suspensión y dejar sólo el soft delete | Fase 1 en auth-service v0.1.0: migración `SoftDelete` (`deleted_at` e índices únicos parciales de email y CUIT), `/admin/users` con `RolesGuard` (listar con filtros y paginado, editar, forzar reset, borrar), eventos de cuenta a `ACCOUNT_EVENT_WEBHOOKS`; contratos `auth_frontend.md` §7 y `account_events.md`; 23 tests y prueba E2E | pendiente de revisión |
| P-019 | 2026-11-06 | Andres | Claude Code (`profile-agent` + `jobs-agent`) | `feature/profile/v0.3.0-eventos-cuenta` y `feature/jobs/v0.2.0-eventos-cuenta` | Seguir con la fase 1 del panel de admin: que profile-service y jobs-service reciban los eventos de cuenta de auth-service y dejen de mostrar las cuentas borradas | Receptores `POST /internal/account-events` (sólo `X-Service-Token`, idempotentes) en los dos servicios: `account.deleted` archiva perfiles y ofertas en tablas `*_deleted` y registra la baja (el JWT vigente recibe `401 ACCOUNT_DELETED`; el seed no los resucita); `account.updated` refresca los datos legales de la empresa en profile. auth avisa a los dos por defecto. 101 + 116 tests y E2E | pendiente de revisión |
| P-020 | 2026-11-07 | Andres | Claude Code (`frontend-agent` + `devops-agent` + `matching-agent`) | `fix/infra/v0.1.1-integracion-busquedas` y `feature/frontend/v0.3.0-busquedas` | Revisar `contracts/jobs_busquedas.md` y hacer las integraciones que falten con matching y el front | Gateway con `location = /api/v1/jobs` (listado y alta daban 301); compose cablea `JOBS_SEED_DEMO`, `AUTH_SERVICE_URL` y `JOBS_DB_SCHEMA`; matching usa datos reales por defecto (`MATCHING_USE_MOCKS=false`, sin cambios de código). Front 0.3.0: búsquedas de la empresa (pestañas, alta/edición, cerrar/reabrir, 409/422, candidatos por reglas + IA) y "Todas las ofertas" para el estudiante. 34 tests Vitest y E2E en navegador | pendiente de revisión |
| P-021 | 2026-11-07 | Andres | Claude Code (`devops-agent` + `mcp-agent`) | `fix/infra/v0.1.1-integracion-busquedas` | Corregir el gateway (redirecciones de `/api/v1/jobs/` sin puerto) y atender la revisión del PR: WF-06 consultaba MCP con mocks mientras matching usa datos reales | Gateway: `Host $http_host` (las 307 de FastAPI salían a `http://localhost/...` sin `:8080`). `MCP_USE_MOCKS=false` por defecto en compose y `.env.example`, alineado con `MATCHING_USE_MOCKS` (mcp-tools ya tenía los adaptadores HTTP, sin cambios de código). E2E con IDs reales: ranking MCP = REST y matching → WF-06 → MCP → `/recommendations/batch` completo en modo `student` y `company` | pendiente de revisión |
| P-022 | 2026-11-07 | Andres | Claude Code (`auth-agent`) | `feature/auth/v0.1.0-admin-cuentas` | Atender la revisión del PR de admin: [P1] el evento de borrado se puede perder (best effort después del commit) y [P2] reset o borrado no revocan un access JWT ya emitido; completar la plantilla y coordinar con #18 | Outbox transaccional `auth.account_event_deliveries` (una fila por suscriptor, `event_id`, misma transacción que el cambio) y `AccountEventDispatcher` con reintentos sin límite, backoff 5 s–10 min, orden por cuenta, `SKIP LOCKED` + lease. `token_version` + claim `tv` comparado en cada request (`401 TOKEN_REVOKED`). 41 tests Jest; E2E con profile-service caído que se recupera y tokens de admin revocados |  |
| P-023 | 2026-11-06 | Dario | Gemini (`frontend-agent`) | `feature/frontend/v0.2.2-correcciones-frontend` | Corregir fallos de integración y errores 422 en el envío de formularios de perfil mediante la limpieza de propiedades calculadas por el backend, estabilizar la visualización de componentes en Bootstrap y asegurar la compatibilidad de flujos | Sanitización del objeto de envío en ProfileWizard.tsx excluyendo atributos de solo lectura o calculados (normalized, months, etc.) para evitar conflictos de validación estricta con Pydantic/FastAPI en el backend; verificación y soporte de la estructura SPA basada en Bootstrap 5 manteniendo la separación visual estricta entre reglas (origin: "RULES", badges verdes) y sugerencias de IA (origin: "AI", badges ámbar con disclaimer) | aceptado |
| P-024 | 2026-11-06 | Dario | Gemini (`frontend-agent`) | `feature/frontend/v0.2.2-correcciones-frontend` | Corregir la persistencia del cartel de sugerencias de IA en el dashboard y perfil que requería F5, y solucionar el error visual provocado por la respuesta 404 del backend al descartar sugerencias | Actualización inmutable del estado profile en StudentArea.tsx mediante setProfile((prev) => ({ ...prev, has_cv_suggestions: false })) para forzar re-render inmediato; ajuste en ProfileWizard.tsx para mutar explícitamente updated.has_cv_suggestions = false al guardar paso CV; captura de excepción ApiError (404) para evitar alertas visuales residuales | aceptado |
| P-025 | 2026-11-07 | Dario | Gemini (`frontend-agent`) | `feature/frontend/v0.3.0-auth-flujos` | Crear modal y formulario de recuperación de clave (solicitud y confirmación por mail) interceptando tokens desde la URL | Implementación de ForgotPasswordModal.tsx y ResetPasswordConfirmPage.tsx conectados a authService y App.tsx respetando la UI de Bootstrap e interceptando tokens de recuperación | aceptado |
| P-026 | 2026-11-07 | Dario | Gemini (`frontend-agent`) | `feature/frontend/v0.3.0-auth-flujos` | Crear pantalla receptora de confirmación de cambio de correo electrónico con rotación de sesión | Implementación de ConfirmEmailPage.tsx con captura de ?token=..., limpieza de sesión activa y maquetado institucional | aceptado |
| P-027 | 2026-11-07 | Dario | Gemini (`frontend-agent`) | `feature/frontend/v0.3.0-auth-flujos` | Desarrollar modal "Mi cuenta" para estudiantes y empresas con cambio de clave y solicitud de cambio de correo | Componente AccountSettingsModal.tsx integrado en SiteHeader.tsx con pestañas para solicitar cambio de contraseña y nuevo email | aceptado |
| P-028 | 2026-11-07 | Andres | Claude Code (`frontend-agent`) | `feature/frontend/v0.4.0-panel-admin` | Revisar por qué no se ven las opciones de admin en el front, borrar las cuentas e2e de prueba y crear el panel | El front no tenía panel (sólo el aviso "todavía no está disponible"); además auth-service en dev había quedado con el watcher trabado tras los cambios de rama. `AdminArea` con Panel (cuentas activas por rol + config de matching), Cuentas (buscar, filtrar por rol, incluir borradas, detalle, editar email/empresa con CUIT validado, forzar cambio de clave y borrar con confirmación; sin borrar la propia) y Matching (`GET/PATCH /matches/settings`). 46 tests Vitest y E2E en Chromium 9/9 | pendiente de revisión |
| P-029 | 2026-11-08 | Dario | Gemini (`frontend-agent`) | `feature/v0.5.0-frontend/auth-flujos-panel-admin` | Fusionar localmente el PR del Panel Admin (v0.4.0) con la rama de flujos Auth (v0.3.0), resolviendo conflictos en App.tsx, SiteHeader.tsx y PROMPTS.md, consolidando todo el frontend en la versión v0.5.0 | Fusión completa de AdminArea.tsx con los 3 flujos de autenticación (HU-04, HU-05, HU-06, HU-10), enrutamiento por roles (student, company, admin), resolución manual de marcas de conflicto y sanitización integral del frontend (Prettier, typecheck y tests unitarios en verde) | aceptado |
| P-030 | 2026-11-08 | Andres | Claude Code (`n8n-agent` + `mcp-agent` + `profile-agent`) | `feature/n8n/v0.4.0-notificaciones`, `feature/mcp/v0.4.0-config-notificaciones` y `feature/profile/v0.4.0-consentimiento-contacto` | Bloque 1 del plan: hacer WF-02 a WF-05 (notificaciones por mail y errores) | WF-02 oferta nueva → candidatos por reglas; WF-03 único que manda mails a estudiantes (resumen al quedar buscable + oferta nueva); WF-04 aviso a empresas sin datos personales; WF-05 error workflow → admin. Responden 202 enseguida, respetan `contact_by_email` (nuevo en la vista de servicio de profile), parámetros en `get_agent_settings.notifications` y reserva atómica de `notification_key` en `bolsa.notifications_sent` (staticData se pisaba con ejecuciones simultáneas). n8n-init crea credenciales SMTP/Postgres y la tabla. E2E 12/12 con Mailpit | pendiente de revisión |
| P-031 | 2026-11-08 | Andres | Claude Code (`devops-agent` + `auth-agent` + `frontend-agent`) | `feature/infra/v0.2.0-swagger-redoc` | En el panel de admin, links a Swagger UI y ReDoc de cada servicio | FastAPI (profile, jobs, matching) publican `/docs`, `/redoc` y `/openapi.json` bajo `/api/v1/<recurso>/` (pasan por el gateway sin tocar Nginx). auth-service suma `@nestjs/swagger` (plugin que lee los DTOs) y una página de ReDoc. Panel de admin: sección "Documentación de las APIs" con Swagger UI, ReDoc y OpenAPI por servicio. Tests en los 4 servicios y el front; E2E en Chromium: las 8 páginas cargan | pendiente de revisión |
| P-032 | 2026-11-08 | Andres | Claude Code (`devops-agent`) | `docs/contracts/v1.0.0-contratos-por-servicio` | Antes del PR, mover los contratos a una subcarpeta y dejar en la carpeta principal sólo los finales, uno por servicio | Seis contratos finales en `contracts/` (`auth.md`, `profile.md`, `jobs.md`, `matching.md`, `mcp_tools.md`, `n8n.md`), armados por partes desde los documentos vigentes (sin checklists ni pasos ya hechos) y con el OpenAPI vivo como fuente de verdad. Los anteriores pasan a `contracts/historico/` (con README de equivalencias) y el backlog del front a `docs/frontend/pendientes.md`. 45 archivos con referencias actualizadas; el test de contrato de jobs verifica el OpenAPI vivo | pendiente de revisión |
| P-033 | 2026-11-08 | Andres | Claude Code (`matching-agent` + `n8n-agent`) | `feature/matching/v0.2.0-pedido-formacion` | Etapa 2 del plan: recomendaciones de formación (`mode=training`) de punta a punta en el back | matching 0.2.0: modo `training` con `profile_id` + `job_id` (pedido, guardado por batch y vista `GET /recommendations/students/{id}/training/{job_id}` con el match por reglas y la formación de IA, separada de las recomendaciones de ofertas). WF-06: el resultado de `training` se guarda por `/recommendations/batch` con el `request_id` (antes iba por `save_recommendation` como `student` y pisaba la recomendación de la oferta), ítems saneados (≤ 5, sin score). Tests UT-MATCH-11; E2E con IA real | pendiente de revisión |
| P-034 | 2026-11-08 | Andres | Claude Code (`frontend-agent`) | `feature/frontend/v0.7.0-formacion` | Etapa 2 del plan (front): que el estudiante pida "¿Cómo mejorar para esta oferta?" y vea la formación con el badge ámbar | `TrainingAdvice` en cada oferta de "Ofertas para vos" y en el detalle de "Todas las ofertas": muestra las faltantes por reglas, pide la formación (`mode=training`) y sigue el pedido con `useAiAnalysis`; panel "Sugerido por IA" separado del de reglas, hasta 5 ítems priorizados y disclaimer. Front 0.7.0; 50 tests Vitest (UT-FE-TRAIN-01); E2E en Chromium con IA real: 5 ítems sobre las faltantes Docker y Testing | pendiente de revisión |
| P-035 | 2026-11-08 | Andres | Claude Code (`matching-agent`) | `fix/matching/v0.2.1-company-id-en-snapshot` | Aplicar el fix: el resumen de ofertas de matching no incluye `company_id`, así que "Ofertas para vos" no puede abrir el perfil público de la empresa | matching 0.2.1: `job_snapshot` suma `company_id` (el mismo que jobs-service ya publica en el detalle); contrato `matching.md` (ejemplo y `JobSnapshot`). Test nuevo; 107 tests; verificado en vivo con el perfil público de la empresa | pendiente de revisión |
| P-036 | 2026-11-09 | Dario | Gemini (`frontend-agent`) | `feature/frontend/v0.8.0-modales-empresa-puntaje` | Diseñar e integrar modal de desglose explícito de puntuación de matching ("¿Por qué este puntaje?") | Creación del componente RuleScoreModal.tsx en Bootstrap 5 conectado al desglose por reglas (score_breakdown, missing_skills, conditions_fit y advertencia por regla excluyente) | aceptado |
| P-037 | 2026-11-09 | Dario | Gemini (`frontend-agent`) | `feature/frontend/v0.8.0-modales-empresa-puntaje` | Implementar servicio y modal de Perfil Público de la Empresa accesible desde ofertas de trabajo | Creación del método getPublicProfile en companyService.ts y maquetado de CompanyPublicProfileModal.tsx para mostrar marca empleadora, rubro, beneficios y sedes sin exponer datos administrativos | aceptado |
| P-038 | 2026-11-09 | Dario | Gemini (`frontend-agent`) | `feature/frontend/v0.8.1-optimizacion-cv` | Optimizar flujo de armado de CV, corregir parpadeo de pantalla al sincronizar estados y agregar manejo de excepciones 404 (`ACCOUNT_DELETED` / recursos ausentes) | Eliminación de flickering al navegar entre pasos de perfil, debounce/memoización en guardado automático de borrador, captura limpia de excepciones ApiError 404 en el cliente HTTP sin cierres inesperados ni alertas flotantes residuales | aceptado |
| P-039 | 2026-11-09 | Dario | Gemini (`frontend-agent`) | `feature/frontend/v0.8.1-deuda-tecnica` | Atender deuda técnica del frontend según AGENTS.md §4.7 (etiquetado de tests unitarios) y sanitización final de tipos en TypeScript | Mapeo y re-etiquetado explícito de la suite de tests en Vitest con los identificadores normativos `UT-FE-01` a `UT-FE-04`, eliminación de `any` residuales y verificación limpia de `npm run typecheck`, `npm run format:check` y `npm run test` | aceptado |
| P-040 | 2026-11-10 | Andres | Claude Code (`mcp-agent`, `n8n-agent`, `profile-agent`, `frontend-agent`) | `feature/mcp/v0.5.0-skill-diseno-cv`, `feature/n8n/v0.5.0-wf07-diseno-cv`, `feature/profile/v0.5.0-diseno-cv`, `feature/frontend/v0.9.0-diseno-cv` | Buscar skills de diseño de CV legibles por IA (ATS) y armar un agente que elija el mejor diseño según el contenido | Híbrido IA + reglas: catálogo de 3 diseños de una columna en profile-service, selector por reglas, agente `cv_designer` en WF-07 con la skill `diseno-cv` y el schema `cv_design`, y pantalla para elegir | aceptado (pendiente revisión del equipo) |
| P-041 | 2026-11-10 | Andres | Claude Code (`profile-agent`) | `feature/profile/v0.5.0-diseno-cv` | Mejorar cómo se muestran las competencias y los colores del CV, buscando plantillas IA friendly | Estilo clásico tipo Harvard / "Jake's Resume": competencias en una línea por categoría separadas por comas (nivel sólo si es avanzado o experto), texto casi negro y un acento azul marino, sin fondos | aceptado (pendiente revisión del equipo) |
| P-042 | 2026-11-10 | Andres | Claude Code (`matching-agent`, `mcp-agent`, `n8n-agent`, `frontend-agent`) | `feature/matching/v0.3.0-ponderacion-y-formacion-general`, `feature/mcp/v0.6.0-formacion-general`, `feature/n8n/v0.6.0-formacion-general`, `feature/frontend/v0.10.0-formacion-general` | Ponderar menos las condiciones no técnicas, más la experiencia, no pedir portfolios, formación general según el perfil y las búsquedas más parecidas, y barra de progreso en el front | Pesos 2.0.0 (técnico 60, experiencia 25 con relevancia, condiciones 7 y sólo lo legal excluye), `skill_gaps` por reglas sobre las ofertas más parecidas, `training_advisor` 2.0.0 sin proyectos y barra de progreso estimada | aceptado (pendiente revisión del equipo) |
| P-043 | 2026-11-10 | Andres | Claude Code (`matching-agent`, `mcp-agent`, `n8n-agent`, `frontend-agent`) | `feature/matching/v0.4.0-diccionario-skills`, `feature/mcp/v0.7.0-resolver-skills`, `feature/n8n/v0.7.0-diccionario-skills`, `feature/frontend/v0.11.0-skills-similares` | Diccionario de skills con nombres distintos (MySQL/MariaDB, Postgres/PostgreSQL) y lista de herramientas similares que facilitan el aprendizaje (GitHub/GitLab), para las reglas y como herramienta del agente | `skill_dictionary.json` (148 skills: alias, implies, equivalentes y similares) en matching-service, `resolver_skills` en mcp-tools, prompts que usan `via` y `similar_to`, y la UI con "SQL (por PostgreSQL)" | aceptado (pendiente revisión del equipo) |
| P-044 | 2026-11-11 | Dario | Gemini (`frontend-agent`) | `fix/frontend/v0.11.1-correccion-todas-las-ofertas` | Reseteo de scroll al tope de la pantalla (`window.scrollTo(0,0)`) al navegar entre ofertas o cambiar de sección | Implementación de `useEffect` en `JobDetail.tsx` y `App.tsx` para restablecer la posición vertical del viewport al tope en cada cambio de vista o navegación de ofertas | aceptado |
| P-045 | 2026-11-11 | Dario | Gemini (`frontend-agent`) | `fix/frontend/v0.11.1-correccion-todas-las-ofertas` | Sincronización del Header con la sección de ofertas (`'jobs'`) y mantenimiento del modal de contraseña | Mapeo exacto de la ruta `'jobs'` en `STUDENT_NAV` dentro de `SiteHeader.tsx` manteniendo la invocación de `AccountSettingsModal` al pulsar sobre el correo del usuario | aceptado |

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

### P-018 — Panel de admin, fase 1: cuentas y empresas en auth-service
- **Fecha:** 2026-11-06 · **Autor:** Andres · **Agente:** Claude Code (`auth-agent`) · **Rama:** `feature/auth/v0.1.0-admin-cuentas` · **HU:** administración de cuentas
- **Prompt (resumido):**
  > Quiero armar el admin panel; no sé bien dónde tiene que vivir el back. Debería poder listar usuarios, editarlos, resetear la clave, cambiar el correo, hacer soft delete y suspender una cuenta (el soft delete desaparece de los listados y permite una nueva alta con el mismo email; el suspendido se ve en los listados pero no puede acceder ni matchear). Lo mismo con las empresas, ver sus búsquedas activas, configurar los resultados del match, ver la salud de los servicios y un panel de eventos con alertas por eventos críticos o suma de fallos. Decisiones: core-service nuevo en FastAPI para lo transversal (y eventualmente lógica de negocio), postulaciones para después, unicidad por email/CUIT (sin DNI), por fases con un PR por servicio.
  > Corrección posterior: quitar el estado de cuenta suspendida y dejar sólo el soft delete.
- **Resumen de la respuesta:**
  - Reparto: cuentas y empresas en auth-service (dueño); ocultar al borrado en profile y jobs por eventos; búsquedas por empresa en jobs; configuración del match en matching; salud, eventos y alertas en core-service. Postulaciones no existen todavía.
  - auth-service v0.1.0: migración `SoftDelete` (`deleted_at`; email y CUIT únicos sólo entre no borrados). `@DeleteDateColumn` hace que login, refresh, `/me` y registro ignoren las cuentas borradas.
  - `AdminUsersController` (`/api/v1/auth/admin/users`) con `JwtAuthGuard` + `RolesGuard`: listar (rol, búsqueda, `include_deleted`, paginado), ver, editar email/empresa, forzar reset (invalida la clave, cierra sesiones y manda el link) y borrar. Un admin no puede borrarse a sí mismo.
  - Puerto `AccountEventPublisher` con implementación HTTP best effort a `ACCOUNT_EVENT_WEBHOOKS` (`X-Service-Token`): eventos `account.updated` y `account.deleted`.
  - La primera versión tenía además suspensión (`status`, `403 ACCOUNT_SUSPENDED`, suspender/reactivar); se quitó a pedido antes del merge.
  - Contratos: `auth_frontend.md` §7 y nuevo `account_events.md`. 23 tests Jest (10 nuevos) y E2E contra el stack: cambio de email, reset con mail en Mailpit, soft delete y re-alta con el mismo email y CUIT.
- **Archivos afectados:** `services/auth-service/` (migración, entidades, `admin/`, `roles.guard.ts`, `auth.service.ts`, tests, versión 0.1.0), `contracts/auth_frontend.md`, `contracts/account_events.md`, `docker-compose.yml`, `.env.example`, `AGENTS.md`, `PROMPTS.md`.
- **Decisión:** pendiente de revisión (Integrante 1). Siguen en la fase 1 los receptores de eventos en profile-service y jobs-service.

### P-019 — Panel de admin, fase 1: receptores de eventos de cuenta en profile y jobs
- **Fecha:** 2026-11-06 · **Autor:** Andres · **Agente:** Claude Code (`profile-agent` + `jobs-agent`) · **Rama:** `feature/profile/v0.3.0-eventos-cuenta` y `feature/jobs/v0.2.0-eventos-cuenta` (un PR por servicio) · **HU:** administración de cuentas
- **Prompt (resumido):**
  > Continuá entonces (lo que falta de la fase 1: que profile-service y jobs-service reciban los eventos de cuenta y oculten a las cuentas borradas).
- **Resumen de la respuesta:**
  - Antes de seguir se integró `dev` en las ramas de auth y se quitó la suspensión (ver P-018).
  - **profile-service v0.3.0:** `POST /api/v1/profiles/internal/account-events` (sólo `X-Service-Token`, idempotente). `account.deleted` registra la baja en `profile.deleted_accounts` (aunque no tuviera perfil) y mueve el perfil a `profiles_deleted` / `company_profiles_deleted` (auditoría, sin migraciones: tablas nuevas con `create_all`); borra el logo. `account.updated` actualiza la copia de los datos legales de la empresa; el email del estudiante no se toca.
  - **jobs-service v0.2.0:** `POST /api/v1/jobs/internal/account-events`. `account.deleted` registra la baja y mueve todas las ofertas de la empresa a `jobs.jobs_deleted`; `account.updated` se ignora (el `company_snapshot` se arma al crear o editar).
  - En los dos: el JWT que todavía no venció de una cuenta borrada recibe `401 ACCOUNT_DELETED` (también al intentar crear el perfil) y el seed de demo no vuelve a cargar lo archivado.
  - **auth-service:** `ACCOUNT_EVENT_WEBHOOKS` apunta por defecto a los dos receptores en `docker-compose.yml`; `account_events.md` describe lo que hace cada uno.
  - Contratos: `profiles_matching.md` §8, `jobs_matching.md` §11, OpenAPI de jobs 0.2.0 y el error `ACCOUNT_DELETED` en los contratos para el front. AGENTS §4.2 y §4.3.
  - Tests: UT-PROF-09 (101 tests en profile) y UT-JOBS-03 (116 en jobs); ruff, black y mypy limpios. E2E contra el stack: alta, perfil u oferta, evento, repetido ignorado, `404` en el detalle y `401 ACCOUNT_DELETED` con el JWT vigente.
- **Archivos afectados:** `services/profile-service/` (dominio, `AccountEventsService`, repositorios, `deleted_accounts.py`, seed, `routes_internal.py`, tests), `services/jobs-service/` (ídem), `contracts/profiles_matching.md`, `contracts/profile_frontend.md`, `contracts/company_profile_frontend.md`, `contracts/jobs_matching.md`, `contracts/jobs_frontend.md`, `contracts/jobs_busquedas.md`, `contracts/jobs_service.openapi.json`, `contracts/account_events.md`, `docker-compose.yml`, `.env.example`, `AGENTS.md`, `PROMPTS.md`.
- **Decisión:** pendiente de revisión (Integrante 2 por profile, Integrante 3 por jobs). Pendiente aparte: el gateway no enruta `POST/GET /api/v1/jobs` sin barra final (ya reportado en `jobs_busquedas.md` §11).

### P-020 — Integración de búsquedas (jobs-service) con matching y el front
- **Fecha:** 2026-11-07 · **Autor:** Andres · **Agente:** Claude Code (`frontend-agent` + `devops-agent` + `matching-agent`) · **Rama:** `fix/infra/v0.1.1-integracion-busquedas` y `feature/frontend/v0.3.0-busquedas` (un PR cada una) · **HU:** HU-11, HU-12
- **Prompt (resumido):**
  > Primero revisá este contrato y hacé las integraciones que falten con matching y el front: `contracts/jobs_busquedas.md`.
- **Resumen de la respuesta:**
  - **Diagnóstico:** matching ya tenía `HttpJobSource`/`HttpProfileSource`, pero corría con mocks (`MATCHING_USE_MOCKS=true` por defecto). Probado con datos reales: rankea las 12 ofertas de jobs-service y los perfiles buscables de profile-service con los mismos ids que los mocks. El gateway respondía `301` en `GET/POST /api/v1/jobs` y el front sólo listaba las búsquedas de la empresa.
  - **Infra:** `location = /api/v1/jobs` en Nginx; jobs-service recibe `JOBS_DB_SCHEMA`, `JOBS_SEED_DEMO` y `AUTH_SERVICE_URL`; `MATCHING_USE_MOCKS=false` por defecto. Contratos: `jobs_busquedas.md` §11 (limitaciones 1 y 4 resueltas), `jobs_frontend.md`, `jobs_matching.md`, `profiles_matching.md`, `matching_frontend.md`.
  - **Front 0.3.0:** tipos de `jobs_frontend.md` §9, `jobsService`; "Búsquedas" de la empresa con pestañas activas/cerradas/todas, paginación, detalle, alta y edición (el PATCH manda el formulario completo y conserva lo que no muestra), cerrar (`DELETE`) y reabrir (`PATCH {"status":"active"}`), `409` → recargar y `422` → errores por campo; candidatos por reglas de cada búsqueda (`/matches/recommendations/jobs/{id}`, anonimizados) y análisis con IA (`mode=company`); "Todas las ofertas" para el estudiante con "Sueldo no publicado" si `salary` es `null`. `RuleMatch` y `useAiAnalysis` compartidos con las recomendaciones del estudiante.
  - **Verificación:** 34 tests Vitest (22 nuevos de formulario y formato), `tsc` y prettier limpios. E2E por el gateway (API y navegador con Playwright): alta con validación, detalle, candidatos, edición, cerrar/reabrir, listado del estudiante con sueldo `on_match` oculto, 404 en candidatos de una búsqueda ajena.
- **Archivos afectados:** `gateway/nginx.conf`, `docker-compose.yml`, `.env.example`, `contracts/jobs_busquedas.md`, `contracts/jobs_frontend.md`, `contracts/jobs_matching.md`, `contracts/profiles_matching.md`, `contracts/matching_frontend.md`, `frontend/src/` (`types/jobs.ts`, `types/matching.ts`, `services/jobsService.ts`, `services/matchingService.ts`, `jobs/`, `components/jobs/`, `components/matching/`, páginas y navegación), `frontend/package.json`, `PROMPTS.md`.
- **Decisión:** pendiente de revisión (Integrante 4 por el front, Integrante 1 por gateway/compose). Pendiente aparte: `mcp-tools` sigue con `MCP_USE_MOCKS` del `.env` (resuelto en P-021); postulaciones fuera de alcance.

### P-021 — Gateway con puerto en redirecciones y MCP con datos reales
- **Fecha:** 2026-11-07 · **Autor:** Andres · **Agente:** Claude Code (`devops-agent` + `mcp-agent`) · **Rama:** `fix/infra/v0.1.1-integracion-busquedas` · **HU:** HU-11, HU-12
- **Prompt (resumido):**
  > Corregí el gateway. Después, la revisión del PR: no aprobar hasta alinear MCP con el modo de datos reales (WF-06 rankea por MCP con mocks y los IDs reales no existen ahí) y verificar ese flujo; documentar el cambio de `.env`; completar la plantilla del PR con evidencia.
- **Resumen de la respuesta:**
  - **Gateway:** `proxy_set_header Host $http_host` a nivel `server`. Antes, `/api/v1/jobs/` (y cualquier 307 de FastAPI) redirigía a `http://localhost/api/v1/jobs` y el navegador perdía el puerto.
  - **MCP:** `MCP_USE_MOCKS: ${MCP_USE_MOCKS:-false}` en compose y `MCP_USE_MOCKS=false` en `.env.example`, con la nota de que tiene que coincidir con `MATCHING_USE_MOCKS` y cómo actualizar un `.env` viejo. `build_container` ya elegía `HttpProfileGateway`/`HttpJobsGateway`/`HttpMatchingGateway`/`HttpRecommendationStore`; sus rutas coinciden con las de los servicios.
  - **Verificación (Docker, datos reales):** `rank_jobs_for_student(prof-43166ce0ab7b)` y `rank_candidates_for_job(c8ef87c1-…)` por MCP (streamable-http, `X-Service-Token`) devuelven el mismo orden y score que matching por REST, con ofertas UUID de jobs-service; `get_job`, `get_profile` y `compute_match` también. `POST /api/v1/matches/recommendations/requests` → WF-06 → MCP → `/recommendations/batch`: `completed` en 50 s (`student`, 5 ofertas) y 25 s (`company`, 2 candidatos), `rule_based.origin=RULES` y `ai_recommendations.origin=AI` (sin score en los ítems de IA).
- **Archivos afectados:** `gateway/nginx.conf`, `docker-compose.yml`, `.env.example`, `contracts/jobs_matching.md`, `PROMPTS.md`.
- **Decisión:** pendiente de revisión (Integrante 1 por gateway/compose, Integrante 3 por n8n/MCP).

### P-022 — Eventos de cuenta confiables y revocación inmediata de access tokens
- **Fecha:** 2026-11-07 · **Autor:** Andres · **Agente:** Claude Code (`auth-agent`) · **Rama:** `feature/auth/v0.1.0-admin-cuentas` · **HU:** HU-ADM-01 (panel de admin, fase 1)
- **Prompt (resumido):**
  > Revisión del PR: no aprobar todavía. [P1] El evento de borrado se puede perder: el publicador sólo loguea los errores y el soft delete ya se confirmó; hace falta outbox/reintento durable con una prueba donde el receptor no está y después se recupera. [P2] Reset o borrado no revocan un access JWT ya emitido para un admin: agregar verificación de cuenta/token-version y tests. Completar la plantilla del PR y coordinar con #18 (`auth_frontend.md`, `package.json` 0.0.2).
- **Resumen de la respuesta:**
  - **P1 · outbox:** migración `AccountEventOutbox` (`auth.account_event_deliveries`, identidad creciente, índices parciales de pendientes). `AdminUsersService` encola el evento con el mismo `EntityManager` de la transacción del borrado/edición (si falla, no se confirma) y llama a `afterCommit()`. `AccountEventDispatcher` entrega después de cada commit y cada 5 s: reintenta sin límite con backoff exponencial (5 s → 10 min), sólo la entrega más vieja pendiente por (suscriptor, cuenta), `FOR UPDATE SKIP LOCKED` y lease de 60 s (réplicas y reinicios). `HttpAccountEventSender` trata cualquier respuesta que no sea 2xx como error. El evento suma `event_id` (los receptores ignoran campos extra).
  - **P2 · token_version:** migración `TokenVersion` (`auth.users.token_version`), claim `tv` en el JWT. Suben la versión: reset forzado y borrado del admin, cambio de clave y recuperación de clave. `JwtStrategy` delega en `AccessTokenValidator`, que compara cuenta activa, rol y `tv` contra la base en cada request → `401 TOKEN_REVOKED`. Tokens sin `tv` valen como versión 0.
  - **Verificación:** 41 tests Jest (UT-AUTH-09 a 12, UT-AUTH-ADM-09 a 13: receptor caído que se recupera, orden por cuenta, un suscriptor caído no frena a otro, backoff con tope, transacción), `tsc` y prettier limpios. E2E en Docker: con profile-service apagado, `DELETE /admin/users/{id}` → 204 en 0,02 s, jobs recibe enseguida y profile queda pendiente; se reinicia auth-service (la entrega sigue pendiente) y al levantar profile-service el perfil pasa a `profiles_deleted` a los 63 s, sin intervención. Token de admin vigente → `401 TOKEN_REVOKED` después del reset y del borrado; un login nuevo entra.
  - **#18:** esta rama ya contiene `docs/auth/v0.0.2-contrato-auth` (merge de su cabeza actual): conviene mergear #18 primero y después esta, o cerrar #18. `package.json` queda en 0.1.0.
- **Archivos afectados:** `services/auth-service/src/` (`admin/account-events.ts`, `admin/account-event-dispatcher.ts`, `admin/typeorm-account-event-outbox.ts`, `admin/http-account-event-sender.ts`, `admin/admin-users.service.ts`, `admin/admin.module.ts`, `auth/access-token-validator.ts`, `auth/jwt.strategy.ts`, `auth/auth.service.ts`, `auth/auth.module.ts`, `auth/current-user.decorator.ts`, `users/user.entity.ts`, 2 migraciones, specs), `contracts/account_events.md`, `contracts/auth_frontend.md`, `AGENTS.md`, `docker-compose.yml`, `.env.example`, `PROMPTS.md`.
- **Decisión:** pendiente de revisión (Integrante 2).

### P-023 — Arreglos y estabilización del Frontend (Bootstrap y sanitización)
* **Fecha:** 2026-11-06 · **Autor:** Dario · **Agente:** Copilot / Gemini (`frontend-agent`) · **Rama:** `feature/frontend/v0.2.1-estilo-bootstrap` · **HU:** Correcciones transversales de UI, flujos de sesión y sanitización de payloads (PATCH)
* **Prompt (resumido):**
  > Corrige fallos de integración y errores 422 en el envío de formularios de perfil mediante la limpieza de propiedades calculadas por el backend (como `normalized` o `months`), estabilizar la visualización de componentes en Bootstrap y asegurar la compatibilidad de los flujos de estudiante y empresa con la arquitectura actual.
* **Resumen de la respuesta:**
  - Sanitización del objeto de envío en `ProfileWizard.tsx` excluyendo atributos de solo lectura o calculados (`normalized`, `months`, etc.) para evitar conflictos de validación estricta con Pydantic/FastAPI en el backend.
  - Verificación y soporte de la estructura SPA basada en Bootstrap 5, manteniendo la separación visual estricta entre reglas (`origin: "RULES"`, badges verdes) y sugerencias de IA (`origin: "AI"`, badges ámbar con disclaimer).
  - Ajustes en la navegación y control de vistas privadas según los roles de usuario (`student`, `company`, `admin`).
* **Archivos afectados:** `frontend/src/components/profile/ProfileWizard.tsx`, `frontend/src/components/profile/StepCvData.tsx`, `PROMPTS.md`.
* **Decisión:** aceptado.

### P-024 — Sincronización de estado y manejo de excepciones 404 en sugerencias de CV
* **Fecha:** 2026-11-06 · **Autor:** Dario · **Agente:** Gemini (`frontend-agent`) · **Rama:** `feature/frontend/v0.2.2-estilo-bootstrap` · **HU:** Correcciones de sincronización de UI y flujos de perfil de estudiante
* **Prompt (resumido):**
  > Corregir la persistencia del cartel de sugerencias de IA en el dashboard y perfil que requería recargar con F5, y solucionar el error visual provocado por la respuesta 404 del backend al descartar sugerencias.
* **Resumen de la respuesta:**
  - Actualización inmutable del estado `profile` en `StudentArea.tsx` mediante `setProfile((prev) => ({ ...prev, has_cv_suggestions: false }))` para forzar un re-render inmediato en la UI sin requerir recarga manual (`F5`).
  - Ajuste en `ProfileWizard.tsx` para mutar explícitamente `updated.has_cv_suggestions = false` al guardar el paso del CV y conectar el evento de descarte con la API.
  - Incorporación de un bloque de control para atrapar la excepción `ApiError` con estado `404` (`CV_SUGGESTIONS_NOT_FOUND`), evitando que se renderice una alerta de error global en la interfaz cuando las sugerencias ya habían sido borradas previamente.
* **Archivos afectados:** `frontend/src/pages/StudentArea.tsx`, `frontend/src/components/profile/ProfileWizard.tsx`, `PROMPTS.md`.
* **Decisión:** aceptado.

### P-025 — Recuperación de contraseña (solicitud y confirmación con token)
* **Fecha:** 2026-11-07 · **Autor:** Dario · **Agente:** Gemini (`frontend-agent`) · **Rama:** `feature/frontend/v0.3.0-auth-flujos` · **HU:** HU-06 (Recuperar contraseña por mail)
* **Prompt (resumido):**
  > Crear modal y formulario de recuperación de clave (solicitud y confirmación por mail) interceptando tokens desde la URL.
* **Resumen de la respuesta:**
  - Métodos `requestPasswordReset` y `confirmPasswordReset` en `authService.ts`.
  - Componentes `ForgotPasswordModal.tsx` (modal para solicitar link) y `ResetPasswordConfirmPage.tsx` (formulario para establecer clave de min 12 caracteres).
  - Intercepción de ruta `/auth/password/reset/confirm?token=...` en `App.tsx` enmarcada dentro del layout institucional (`SiteHeader` / `SiteFooter`).
* **Archivos afectados:** `frontend/src/services/authService.ts`, `frontend/src/components/auth/ForgotPasswordModal.tsx`, `frontend/src/pages/ResetPasswordConfirmPage.tsx`, `frontend/src/components/auth/AuthForm.tsx`, `frontend/src/App.tsx`, `PROMPTS.md`.
* **Decisión:** aceptado.

### P-026 — Confirmación de cambio de correo electrónico
* **Fecha:** 2026-11-07 · **Autor:** Dario · **Agente:** Gemini (`frontend-agent`) · **Rama:** `feature/frontend/v0.3.0-auth-flujos` · **HU:** HU-05 (Cambiar email con confirmación)
* **Prompt (resumido):**
  > Crear pantalla receptora de confirmación de cambio de correo electrónico con rotación de sesión.
* **Resumen de la respuesta:**
  - Método `confirmEmail` en `authService.ts` (`POST /api/v1/auth/email/confirm`).
  - Creación de `ConfirmEmailPage.tsx` que procesa el token de la URL, invalida la sesión previa (`session.clear()`) y muestra la pantalla verde para re-iniciar sesión.
* **Archivos afectados:** `frontend/src/services/authService.ts`, `frontend/src/pages/ConfirmEmailPage.tsx`, `frontend/src/App.tsx`, `PROMPTS.md`.
* **Decisión:** aceptado.

### P-027 — Sección "Mi cuenta" en cabecera de usuario
* **Fecha:** 2026-11-07 · **Autor:** Dario · **Agente:** Gemini (`frontend-agent`) · **Rama:** `feature/frontend/v0.3.0-auth-flujos` · **HU:** HU-04 (Cambiar clave conociendo la actual) / HU-05
* **Prompt (resumido):**
  > Desarrollar modal "Mi cuenta" para estudiantes y empresas con cambio de clave y solicitud de cambio de correo.
* **Resumen de la respuesta:**
  - Métodos `me`, `changePassword` y `requestEmailChange` en `authService.ts`.
  - Formulario con pestañas `AccountSettingsModal.tsx` (Bootstrap 5) y su integración en `SiteHeader.tsx` (tanto en la barra superior como en el menú hamburguesa mobile).
* **Archivos afectados:** `frontend/src/services/authService.ts`, `frontend/src/components/auth/AccountSettingsModal.tsx`, `frontend/src/components/layout/SiteHeader.tsx`, `PROMPTS.md`.
* **Decisión:** aceptado.

### P-028 — Panel de administración en el front
- **Fecha:** 2026-11-07 · **Autor:** Andres · **Agente:** Claude Code (`frontend-agent`) · **Rama:** `feature/frontend/v0.4.0-panel-admin` · **HU:** HU-ADM-01 (panel de admin, fase 2: front)
- **Prompt (resumido):**
  > Revisá por qué sigo sin ver las opciones de admin en el front. Después: borrá las cuentas de prueba y creá el panel.
- **Resumen de la respuesta:**
  - **Diagnóstico:** el front no tenía panel: para `admin` `CompanyArea` mostraba "La consola de administración todavía no está disponible" (pendiente 4 de `contracts/pendientes_frontend.md`). Aparte, auth-service en dev había quedado con el watcher de Nest trabado (13 errores por archivos que desaparecieron durante un checkout) y respondía `404` en `/admin/users`: se resolvió con `docker compose restart auth-service`.
  - **Limpieza:** se borraron las 8 cuentas `e2e-…@example.test` de las pruebas de P-022 y sus restos en profile, jobs y el outbox. Queda sólo `admin@bolsa.local`.
  - **Front 0.4.0:** `pages/AdminArea.tsx` con tres secciones en el menú (Panel · Cuentas · Matching) y en el footer. Panel: cuentas activas por rol (cada tarjeta abre el listado filtrado) y la configuración vigente. Cuentas (`auth_frontend.md` §7): búsqueda por email/razón social/CUIT, filtro por rol, "Incluir cuentas borradas", paginación, detalle con datos frescos, edición (PATCH sólo con lo que cambió; CUIT con dígito verificador en el cliente; `409` legible), forzar cambio de clave y borrar con confirmación que explica qué se archiva; el admin no ve "Borrar" en su propia cuenta. Matching (`matching_frontend.md` §4.5): dos campos 1–20, PATCH parcial, "Última modificación" y aviso de que se guarda en memoria. Lógica pura en `src/admin/` (`users.ts`, `settings.ts`) y servicios `adminService` + `matchingService.getSettings/updateSettings`.
  - **Verificación:** 46 tests Vitest (12 nuevos UT-FE-ADM-01 a 05), `tsc` y prettier limpios, `vite build` OK. E2E en Chromium con Playwright (9/9): menú de admin, resumen, búsqueda, edición con CUIT inválido rechazado, reset (la clave vieja deja de funcionar), borrado con confirmación y visible con "Incluir borradas", sin "Borrar" en la propia cuenta, configuración de matching (25 rechazado, 6 guardado y restaurado) y menú mobile. Cuentas e2e borradas al terminar.
- **Archivos afectados:** `frontend/src/` (`pages/AdminArea.tsx`, `components/admin/*`, `admin/*`, `services/adminService.ts`, `services/matchingService.ts`, `types/admin.ts`, `types/matching.ts`, `navigation.ts`, `App.tsx`, `components/layout/SiteHeader.tsx`, `components/layout/SiteFooter.tsx`, `pages/CompanyArea.tsx`, `pages/StudentArea.tsx`), `frontend/package.json` y `package-lock.json` (0.4.0), `contracts/pendientes_frontend.md`, `AGENTS.md`, `PROMPTS.md`.
- **Decisión:** pendiente de revisión (Integrante 3).

### P-029 — Consolidación local de Panel Admin y Flujos Auth (v0.5.0)
* **Fecha:** 2026-11-08 · **Autor:** Dario · **Agente:** Gemini (`frontend-agent`) · **Rama:** `feature/v0.5.0-frontend/auth-flujos-panel-admin` · **HU:** HU-04, HU-05, HU-06, HU-10
* **Prompt (resumido):**
  > Fusionar localmente la rama del panel de administración (v0.4.0) con los flujos de autenticación (v0.3.0), resolviendo conflictos en App.tsx, SiteHeader.tsx y PROMPTS.md para generar una entrega unificada v0.5.0.
* **Resumen de la respuesta:**
  - Fusión de la rama `feature/frontend/v0.4.0-panel-admin` con la rama local de Auth, integrando el componente `AdminArea.tsx` y su enrutamiento de rol `admin` dentro de `App.tsx`.
  - Resolución manual de conflictos de Git en `App.tsx`, `SiteHeader.tsx` y `PROMPTS.md` sin perder interceptores de tokens ni botones del menú superior.
  - Sanitización completa del código frontend (`npx prettier`, `npm run typecheck` y `npm run test` en verde) y actualización de la rama a `feature/v0.5.0-frontend/auth-flujos-panel-admin`.
* **Archivos afectados:** `frontend/src/App.tsx`, `frontend/src/components/layout/SiteHeader.tsx`, `PROMPTS.md`.
* **Decisión:** aceptado.

### P-030 — Notificaciones por mail en n8n (WF-02 a WF-05)
- **Fecha:** 2026-11-08 · **Autor:** Andres · **Agente:** Claude Code (`n8n-agent` + `mcp-agent` + `profile-agent`) · **Ramas:** `feature/n8n/v0.4.0-notificaciones`, `feature/mcp/v0.4.0-config-notificaciones`, `feature/profile/v0.4.0-consentimiento-contacto` · **HU:** automatización con n8n (Plan MVP)
- **Prompt (resumido):**
  > Armá un plan para completar lo que falta del plan original. Arrancá por el bloque 1: WF-02 a WF-05 (notificaciones y errores).
- **Resumen de la respuesta:**
  - **Workflows** (generados en `n8n/generate_workflows.py`):
    - WF-02 `job.created` → candidatos por reglas (`score ≥ min_score`), se los pasa a WF-03 por `/webhook/student-offer`.
    - WF-03 es el único que manda mails a estudiantes: resumen al quedar buscable (`profile.updated`) y oferta nueva (desde WF-02); recalcula el puntaje con `POST /matches`. Reenvía el evento a WF-04.
    - WF-04 avisa al contacto de RR. HH. de cada empresa con el snapshot de matching, sin nombre ni contacto del candidato.
    - WF-05 es el `errorWorkflow` de todos los demás y avisa a `notifications.admin_email`.
    - Todos responden `202` enseguida (los servicios esperan 3 s), validan `X-Service-Token` y respetan `contact_by_email`.
  - **Idempotencia:** primero con `staticData`; el E2E mostró mails repetidos porque las ejecuciones simultáneas se pisan (la última sobrescribe). Se pasó a una reserva atómica: un nodo Postgres inserta la clave en `bolsa.notifications_sent` con `ON CONFLICT DO NOTHING` y sólo sale el mail reservado.
  - **mcp-tools 0.4.0:** `get_agent_settings` suma `notifications` (`NOTIFY_ENABLED`, `NOTIFY_MIN_SCORE`, `NOTIFY_MAX_PER_EVENT`, `NOTIFY_ADMIN_EMAIL`, `FRONTEND_URL`). UT-MCP-03.
  - **profile-service 0.4.0:** la vista de servicio incluye `contact_by_email` (sólo ese consentimiento; la vista de empresa no). Tests UT-PROF-05.
  - **Infra:** `n8n-init` crea las credenciales SMTP (Mailpit; `SMTP_USER`/`SMTP_PASSWORD`/`SMTP_SECURE` opcionales) y Postgres, y la tabla `bolsa.notifications_sent`. Compose suma `N8N_INTERNAL_WEBHOOK_URL`.
  - **Verificación:** mcp-tools 20 tests (90 % cobertura) y profile-service 103 tests (97 %), ruff/black/mypy limpios. E2E en Docker con Mailpit, 12/12:
    - resumen al estudiante y aviso a la empresa sin datos personales;
    - oferta nueva;
    - repetir el evento o editar el perfil no reenvía;
    - 6 avisos simultáneos → 1 mail;
    - sin consentimiento no hay mail;
    - 401/400;
    - WF-05 avisa cuando WF-02 falla con matching caído.
- **Archivos afectados:** `n8n/generate_workflows.py`, `n8n/workflows/*.json`, `n8n/init/bootstrap.sh`, `mcp-tools/app/domain/settings.py`, `mcp-tools/app/infrastructure/settings_env.py`, `mcp-tools/app/tools/registry.py`, `services/profile-service/app/application/views.py`, tests, `docker-compose.yml`, `.env.example`, `contracts/notificaciones_n8n.md` (nuevo), `contracts/profiles_matching.md`, `contracts/jobs_busquedas.md`, `AGENTS.md`, `README.md`, `PROMPTS.md`.
- **Decisión:** pendiente de revisión (Integrante 1 por n8n/mcp-tools, Integrante 3 por profile).

### P-031 — Swagger UI y ReDoc de cada servicio en el panel de admin
- **Fecha:** 2026-11-08 · **Autor:** Andres · **Agente:** Claude Code (`devops-agent` + `auth-agent` + `frontend-agent`) · **Rama:** `feature/infra/v0.2.0-swagger-redoc` · **HU:** HU-ADM-01 (panel de admin)
- **Prompt (resumido):**
  > En el panel de admin armá links a Swagger UI y ReDoc de cada servicio. (Decisión: sumar `@nestjs/swagger` en auth.)
- **Resumen de la respuesta:**
  - **FastAPI** (profile 0.4.1, jobs 0.2.1, matching 0.1.1): `docs_url`, `redoc_url` y `openapi_url` bajo `/api/v1/<recurso>/`, así pasan por el gateway sin rutas nuevas. `/docs` y `/openapi.json` en la raíz dejan de existir. Tests UT-JOBS-04, UT-MATCH-10 y UT-PROF-10.
  - **auth-service 0.2.0:** dependencia nueva `@nestjs/swagger` 11 (avisar en la daily, AGENTS §2.4) con el plugin del CLI (`classValidatorShim`), que arma los schemas desde los DTOs. Swagger UI en `/api/v1/auth/docs`, ReDoc (página propia, JS del CDN) en `/redoc` y OpenAPI en `/openapi.json`. `@ApiTags` y `@ApiBearerAuth` en los controllers. Test UT-AUTH-13.
  - **Front 0.6.0:** sección "Documentación de las APIs" en el resumen del panel de admin, con Swagger UI, ReDoc y OpenAPI de auth, profile, jobs y matching (se abren en otra pestaña). mcp-tools y n8n no tienen API REST pública. Test UT-FE-ADM-06.
  - **Verificación:** auth 44 tests, profile 104, jobs 117, matching 103, front 47; tsc, prettier, ruff y black limpios. Por el gateway, las 12 URLs responden `200`. E2E en Chromium: los 8 links del panel abren Swagger UI/ReDoc con el nombre y la versión de cada servicio. El OpenAPI de auth trae las 15 rutas, con candado en las protegidas.
- **Archivos afectados:** `services/auth-service/` (`src/docs/`, `main.ts`, controllers, `nest-cli.json`, `package.json`, `package-lock.json`), `services/{profile,jobs,matching}-service/app/main.py`, `pyproject.toml` y `tests/test_api_docs.py`, `frontend/src/admin/apiDocs.ts`, `frontend/src/components/admin/ApiDocsLinks.tsx`, `AdminDashboard.tsx`, `frontend/package*.json`, `README.md`, `AGENTS.md`, `PROMPTS.md`.
- **Decisión:** pendiente de revisión (Integrante 1 por auth/gateway, Integrante 4 por el front).

### P-032 — Contratos: uno por servicio y los anteriores al histórico
- **Fecha:** 2026-11-08 · **Autor:** Andres · **Agente:** Claude Code (`devops-agent`) · **Rama:** `docs/contracts/v1.0.0-contratos-por-servicio` · **HU:** — (documentación)
- **Prompt (resumido):**
  > En los contratos, antes de hacer un PR, mové lo que hay a una subcarpeta y dejá en la carpeta principal sólo los contratos finales, uno por servicio. (Decisión: seis contratos: auth, profile, jobs, matching, mcp-tools y n8n; lo transversal repartido.)
- **Resumen de la respuesta:**
  - **Contratos finales:** cada uno tiene un encabezado con a quién va dirigido, la versión del servicio, los links a Swagger UI, ReDoc y OpenAPI vivos, y sus partes. Se armaron con un script a partir de las secciones vigentes de cada fuente, sin las que no son contrato (checklists de PR, "cambios necesarios en el front", preguntas para la daily, el prompt del agente de CV).
    - `auth.md`: API (A), eventos de cuenta (B) y documentación (C).
    - `profile.md`: estudiante (A), empresa (B), servicios (C), CV con n8n (D), snapshot de empresa como propuesta (E) y anexo con la estructura común.
    - `jobs.md`: búsquedas (A), guía del front (B) y servicios (C).
    - `matching.md`: front (A) y endpoints internos + flujo con WF-06 (B).
    - `mcp_tools.md` y `n8n.md`: nuevos. Herramientas, perfiles y endpoints sacados de mcp-tools en ejecución; workflows, webhooks, payloads, salidas de IA y notificaciones.
  - **Histórico:** todos los documentos anteriores (md, OpenAPI estáticos, schemas JSON, yaml y pdf) en `contracts/historico/` con `git mv`, más un README de equivalencias. El backlog del front pasa a `docs/frontend/pendientes.md`.
  - **Referencias:** 45 archivos (código, comentarios, AGENTS, README, compose, plantilla de PR) apuntan al contrato y la parte nuevos. Las secciones de `jobs_frontend.md`, con otra numeración, se mapearon a mano. AGENTS §2.1 regla 6 explica la estructura. PROMPTS no se reescribe (es historial).
  - **Tests:** el test de jobs que leía `jobs_service.openapi.json` ahora verifica el OpenAPI vivo. Resumen de `GET /profiles/companies/me` corregido (ya no menciona búsquedas).
  - **Verificación:** 0 links rotos en los contratos nuevos; jobs 116, matching 103, profile 104, auth 44 y front 47 tests; ruff, black, prettier y tsc limpios; los workflows regenerados no cambian.
- **Archivos afectados:** `contracts/*.md` (nuevos), `contracts/historico/**` (movidos), `docs/frontend/pendientes.md`, `AGENTS.md`, `README.md`, `.github/pull_request_template.md`, `docker-compose.yml`, comentarios en `frontend/src`, `services/*`, `n8n/generate_workflows.py`, `services/jobs-service/tests/test_seed_and_contract.py`, `services/profile-service/app/api/routes_companies.py`, `PROMPTS.md`.
- **Decisión:** pendiente de revisión (todo el equipo: cada dueño revisa el contrato de su servicio).

### P-033 — Recomendaciones de formación (`mode=training`) en el back
- **Fecha:** 2026-11-08 · **Autor:** Andres · **Agente:** Claude Code (`matching-agent` + `n8n-agent`) · **Rama:** `feature/matching/v0.2.0-pedido-formacion` · **HU:** recomendaciones de IA para el estudiante (Plan MVP)
- **Prompt (resumido):**
  > Integrá todo localmente en `dev-tmp` y avanzá con la etapa 2 del plan (recomendaciones de formación).
- **Resumen de la respuesta:**
  - **Diagnóstico:** WF-06 ya tenía la rama `training`, pero:
    - matching no la podía pedir;
    - guardaba con `save_recommendation` sin `mode`, como `student`, y pisaba la recomendación de Jean Grey para la misma oferta;
    - no guardaba el `request_id`.
  - **matching-service 0.2.0:**
    - `RecommendationMode.TRAINING` y `RecommendationRequest.job_id`;
    - `POST /recommendations/requests` con `{mode: "training", profile_id, job_id}`: sólo el dueño, admin o servicio (empresa → `403`, ajeno → `404`, sin oferta → `422`);
    - el disparador a n8n manda `profile_id` + `job_id` y `limit: 1`; `save_batch` acepta `training`;
    - vista `GET /recommendations/students/{profile_id}/training/{job_id}` con el match por reglas (score y faltantes) y el bloque de IA (`status`, `items`, `model`, `disclaimer`);
    - los repositorios ya separaban por modo, así que la formación no aparece en "Ofertas para vos".
  - **WF-06:** el contexto de `training` lleva `request_id` y `subject_id`; el resultado se guarda por `/recommendations/batch` (`mode=training`) con ítems saneados (≤ 5, `type`/`skill`/`text`/`priority`, sin score).
  - **Verificación:** 106 tests en matching (UT-MATCH-11 nuevo, 97,6 % de cobertura), ruff, black y mypy limpios. E2E en Docker con IA real (stu-001 / job-002): pedido `completed` en 15 s; reglas 51,67 con faltantes React, TypeScript y Node.js; la IA devolvió 5 ítems priorizados sobre esas faltantes.
- **Archivos afectados:** `services/matching-service/app/` (`domain/recommendations.py`, `domain/ports.py`, `application/recommendation_service.py`, `application/access_policy.py`, `api/routes.py`, `infrastructure/n8n_trigger.py`, `infrastructure/repositories_memory.py`, `main.py`), `pyproject.toml`, tests, `n8n/generate_workflows.py`, `n8n/workflows/WF-06-recomendador.json`, `contracts/matching.md`, `contracts/n8n.md`, `AGENTS.md`, `PROMPTS.md`.
- **Decisión:** pendiente de revisión (Integrante 3).

### P-034 — "¿Cómo mejorar para esta oferta?" en el front
- **Fecha:** 2026-11-08 · **Autor:** Andres · **Agente:** Claude Code (`frontend-agent`) · **Rama:** `feature/frontend/v0.7.0-formacion` · **HU:** recomendaciones de IA para el estudiante (Plan MVP)
- **Prompt (resumido):**
  > Avanzá con la etapa 2 (formación): que el estudiante la pida desde una oferta y vea los ítems con el badge "Sugerido por IA".
- **Resumen de la respuesta:**
  - **Tipos y servicio:** `TrainingItem` y `TrainingView`; `matchingService.getTraining` y `requestTraining`; `RecommendationRequest.mode` suma `training`.
  - **Componente `TrainingAdvice`:**
    - se despliega con "¿Cómo mejorar para esta oferta?" y muestra las competencias que faltan según el motor de reglas;
    - pide la formación y sigue el pedido con `useAiAnalysis`;
    - lista hasta 5 ítems de prioridad alta a baja (Curso, Proyecto, Consejo para tu perfil) en un panel ámbar "Sugerido por IA" con el disclaimer, separado del panel de reglas (AGENTS §2.2).
  - **Dónde:** en cada oferta de "Ofertas para vos" y en el detalle de "Todas las ofertas" (`JobBoard` recibe el `profileId`; `JobDetail` acepta contenido al pie). Lógica de presentación en `src/matching/training.ts`.
  - **Verificación:** 50 tests Vitest (UT-FE-TRAIN-01 nuevo), tsc y prettier limpios. E2E en Chromium con un estudiante ficticio e IA real: el panel muestra las faltantes (Docker, Testing), el pedido devuelve 5 ítems y el detalle de "Todas las ofertas" también ofrece la formación. Nota: en `dev`, "Todas las ofertas" sólo se abre desde el footer (el menú del estudiante no la tiene desde la 0.5.0).
- **Archivos afectados:** `frontend/src/components/matching/TrainingAdvice.tsx`, `JobRecommendations.tsx`, `frontend/src/components/jobs/JobBoard.tsx`, `JobDetail.tsx`, `frontend/src/pages/StudentArea.tsx`, `frontend/src/matching/training.ts` (+ test), `frontend/src/services/matchingService.ts`, `frontend/src/types/matching.ts`, `frontend/package*.json`, `docs/frontend/pendientes.md`, `PROMPTS.md`.
- **Decisión:** pendiente de revisión (Integrante 4).

### P-035 — `company_id` en el resumen de ofertas de matching
- **Fecha:** 2026-11-08 · **Autor:** Andres · **Agente:** Claude Code (`matching-agent`) · **Rama:** `fix/matching/v0.2.1-company-id-en-snapshot` · **HU:** perfil público de la empresa desde una oferta (etapa 3, ítem 2)
- **Prompt (resumido):**
  > Aplicá este fix y subilo como un PR individual: el resumen de ofertas de matching no incluye `company_id`, así que "Ofertas para vos" necesita sumarlo en matching o pedir el detalle a jobs.
- **Resumen de la respuesta:**
  - Se suma en matching (más simple que un pedido extra a jobs por oferta): `job_snapshot` incluye `company_id`. Llega en "Ofertas para vos" y en la vista de candidatos.
  - No expone nada nuevo: jobs-service ya publica `company_id` en el detalle de cada oferta.
  - matching-service 0.2.1; `contracts/matching.md` actualizado (ejemplo y `JobSnapshot`).
  - **Verificación:** test nuevo (`company_id` de cada ítem = el de la oferta); 107 tests, ruff, black y mypy limpios. En vivo, `stu-001` → `job-004` trae `company_id` y con él `GET /profiles/companies/{company_id}` devuelve el perfil público de la empresa.
  - **PR individual** sobre la rama de #34 (matching 0.2.0) para que el diff muestre sólo este cambio; cuando #34 se mergee, se cambia la base a `dev`.
- **Archivos afectados:** `services/matching-service/app/application/serializers.py`, `app/main.py`, `pyproject.toml`, `tests/test_services.py`, `contracts/matching.md`, `PROMPTS.md`.
- **Decisión:** pendiente de revisión (Integrante 3).

### P-036 — Modal de desglose de puntuación por reglas ("¿Por qué este puntaje?")
* **Fecha:** 2026-11-09 · **Autor:** Dario · **Agente:** Gemini (`frontend-agent`) · **Rama:** `feature/frontend/v0.8.0` · **HU:** HU-08 / HU-12 (Desglose explícito de scoring por reglas)
* **Prompt (resumido):**
  > Diseña e integra modal de desglose explícito de puntuación de matching ("¿Por me este puntaje?") en Bootstrap 5 que detalle la puntuación de 0 a 100 basada en los 6 criterios determinísticos, alertas de tope por reglas excluyentes, competencias faltantes y grado de compatibilidad de condiciones laborales.
* **Resumen de la respuesta:**
  - Creación del componente `RuleScoreModal.tsx` estructurado con la estética institucional en Bootstrap 5.
  - Visualización del desglose ponderado por criterios (`required_skills`, `desired_skills`, `levels`, `experience`, `education`, `languages`).
  - Renderizado de alerta de tope por regla excluyente (`excluding_cap_applied`), tarjetas de competencias faltantes categorizadas por prioridad (`high`, `medium`, `low`) y panel de ajuste de condiciones laborales (`conditions_fit`).
* **Archivos afectados:** `frontend/src/components/matching/RuleScoreModal.tsx`, `frontend/src/components/matching/RuleMatch.tsx`, `PROMPTS.md`.
* **Decisión:** aceptado.

### P-037 — Perfil público de la empresa desde una oferta
* **Fecha:** 2026-11-09 · **Autor:** Dario · **Agente:** Gemini (`frontend-agent`) · **Rama:** `feature/frontend/v0.8.0` · **HU:** HU-14 / HU-15 (Consulta pública de marca empleadora)
* **Prompt (resumido):**
  > Implementa servicio y modal de Perfil Público de la Empresa accesible desde cualquier oferta de trabajo o listado de búsquedas.
* **Resumen de la respuesta:**
  - Incorporación del método `getPublicProfile(companyId)` en `companyService.ts` consumiendo el endpoint `GET /api/v1/profiles/companies/{company_id}`.
  - Creación del componente modal `CompanyPublicProfileModal.tsx` en Bootstrap 5 para visualizar nombre comercial, rubro, tamaño, descripción, modalidades de trabajo, sedes y beneficios sin requerir permisos administrativos ni exponer datos privados de RRHH.
  - Vinculación del modal desde las tarjetas de empleo (`JobCard` / `JobDetail`).
* **Archivos afectados:** `frontend/src/services/companyService.ts`, `frontend/src/components/company/CompanyPublicProfileModal.tsx`, `PROMPTS.md`.
* **Decisión:** aceptado.

### P-038 — Optimización del asistente de CV, corrección de parpadeo y manejo de 404
* **Fecha:** 2026-11-09 · **Autor:** Dario · **Agente:** Gemini (`frontend-agent`) · **Rama:** `feature/frontend/v0.8.1-optimizacion-cv` · **HU:** HU-04 / HU-05 (Carga y edición de perfil de estudiante)
* **Prompt (resumido):**
  > Optimiza la velocidad y renderizado del asistente de armado de CV (ProfileWizard) evitando el parpadeo de pantalla (flickering) al transicionar estados o guardar borradores, e intercepta errores 404 en la API sin romper la experiencia del usuario.
* **Resumen de la respuesta:**
  - Estabilización del renderizado reactivo en `ProfileWizard.tsx` y `StudentArea.tsx` previniendo destrucciones innecesarias del DOM durante el polling o actualización del perfil.
  - Sanitización en cliente para interceptar excepciones `ApiError` con estado `404` (recursos no encontrados o sugerencias ya descartadas), evitando alertas de error globales o cierres de sesión abruptos.
* **Archivos afectados:** `frontend/src/components/profile/ProfileWizard.tsx`, `frontend/src/pages/StudentArea.tsx`, `frontend/src/services/api.ts`, `PROMPTS.md`.
* **Decisión:** aceptado.

### P-039 — Cobertura de deuda técnica (AGENTS.md §4.7) y estandarización de tests Vitest
* **Fecha:** 2026-11-09 · **Autor:** Dario · **Agente:** Gemini (`frontend-agent`) · **Rama:** `feature/frontend/v0.8.1-deuda-tecnica` · **HU:** Deuda Técnica / RNF de Calidad del Frontend
* **Prompt (resumido):**
  > Resuelve los ítems de deuda técnica estipulados en AGENTS.md §4.7, etiquetando los tests unitarios con sus IDs formales (UT-FE-01 a UT-FE-04) y asegurando que las herramientas de CI queden en verde.
* **Resumen de la respuesta:**
  - Estandarización y etiquetado normativo de la suite de pruebas unitarias Vitest (`UT-FE-01` a `UT-FE-04`) para la capa de servicios, cliente HTTP y renderizado de scoring.
  - Depuración de tipos TypeScript y verificación integral en consola previa a PR (`npm run typecheck`, `npm run format:check` y `npm run test` con 0 errores).
* **Archivos afectados:** `frontend/src/__tests__/*`, `frontend/package.json`, `PROMPTS.md`.
* **Decisión:** aceptado.


### P-040 — Diseño del CV elegido por un agente de IA (con reglas de respaldo)
- **Fecha:** 2026-11-10 · **Autor:** Andres · **Agente:** Claude Code (`mcp-agent`, `n8n-agent`, `profile-agent`, `frontend-agent`) · **Ramas:** `feature/mcp/v0.5.0-skill-diseno-cv`, `feature/n8n/v0.5.0-wf07-diseno-cv`, `feature/profile/v0.5.0-diseno-cv`, `feature/frontend/v0.9.0-diseno-cv` · **HU:** generación del CV "IA friendly"
- **Prompt (textual):**
  > Creo que busques skills de diseño de cv que sean IA friendly y armes un agente que elija el mejor diseño en función al contenido.
  - Decisión del usuario: **híbrido IA + reglas** (la IA elige y, si no responde, eligen las reglas).
- **Resumen de la respuesta:**
  - **Búsqueda:** se revisaron skills públicas de CV para agentes (p. ej. `ResumeSkills`, `cv-creator`, `resume-optimization`) y guías de formato ATS 2025-2026. No se copió ninguna: la skill `diseno-cv` es propia y resume el consenso (una columna, texto real, títulos estándar, sin tablas ni gráficos; cronológico o híbrido; nunca funcional puro).
  - **mcp-tools 0.5.0:** skill `diseno-cv` y schema `cv_design` (`layout` del catálogo, `section_order` sin repetir, `rationale`). UT-MCP-04.
  - **n8n:** agente `cv_designer` (Tony Stark, `perfil=cv`), plantilla `n8n/prompts/cv_designer.md` 1.0.0 y `WF-07` (`POST /webhook/cv-design`) sobre `WF-00` + `WF-0V`, que descarta diseños fuera del catálogo y sanea la salida.
  - **profile-service 0.5.0:**
    - catálogo `cronologico` / `primer_empleo` / `competencias` (sólo cambia el orden de las secciones);
    - `CvLayoutSelector` por reglas (`origin: "RULES"`);
    - pedido a la IA en segundo plano con un resumen **sin datos personales** y `consents.ai_processing`;
    - la sugerencia queda vieja si el perfil cambia;
    - endpoints `GET`/`PUT /me/cv-design` y `POST /me/cv-design/requests`; `?layout=` y `X-Cv-Layout` en las descargas;
    - la plantilla HTML y el DOCX dibujan las secciones en el orden del diseño. UT-PROF-10 y UT-PROF-11.
  - **front 0.9.0:** tarjeta "Diseño de tu CV" con los tres diseños, panel verde de reglas y panel ámbar de IA separados, y seguimiento del pedido. UT-FE-CVD-01.
  - **Docs:** `contracts/profile.md` (parte A §8.1), `contracts/n8n.md` §8, `contracts/mcp_tools.md`, AGENTS §4.2, §4.6 y §5.
- **Archivos afectados:** `mcp-tools/app/data/skills/diseno-cv/`, `mcp-tools/app/data/schemas/cv_design.schema.json`, `n8n/agentes/cv_designer.json`, `n8n/prompts/cv_designer.md`, `n8n/generate_workflows.py`, `n8n/workflows/WF-07-diseno-cv.json`, `services/profile-service/app/domain/cv_design*.py`, `services/profile-service/app/application/cv_design_service.py`, `services/profile-service/app/infrastructure/n8n_cv_design.py`, `services/profile-service/app/templates/cv.html`, `frontend/src/components/profile/CvDesignPicker.tsx`, `frontend/src/profile/cvDesign.ts`, contratos, `AGENTS.md`, `PROMPTS.md`.
- **Decisión:** aceptado (pendiente revisión del equipo).

### P-041 — Estilo del CV: competencias en texto y colores sobrios
- **Fecha:** 2026-11-10 · **Autor:** Andres · **Agente:** Claude Code (`profile-agent`) · **Rama:** `feature/profile/v0.5.0-diseno-cv` · **HU:** generación del CV "IA friendly"
- **Prompt (textual):**
  > no me gusta como muestra los skills ni los colores, mejora ese aspecto del diseño buscando plantillas que se adapten al modelo ia friendly
- **Resumen de la respuesta:**
  - **Búsqueda:** las guías de ATS 2026 coinciden en listar las competencias como texto separado por comas, agrupado por categoría. Las barras, estrellas y chips no se leen bien o rompen el orden. Para los colores, recomiendan un solo acento suave sobre una columna. Se tomó como referencia el estilo clásico de las plantillas Harvard y "Jake's Resume".
  - **Competencias:** `SkillGroup.line` arma una línea por categoría ("Técnicas: Python (avanzado), PostgreSQL, React"). El nivel sólo se aclara si es avanzado o experto: "(Inicial)" o "(Básico)" no suman en un CV. Se aplica igual en el PDF, el HTML y el DOCX.
  - **Colores:** texto casi negro (`#111827` / `#1f2937`), gris `#4b5563` para fechas (contraste AA) y un solo acento azul marino (`#1f3a5f`) en la línea del encabezado y los títulos. Se sacaron los chips, el fondo del bloque de disponibilidad y el azul del titular.
  - Plantilla 1.2.0; tests de UT-PROF-06 actualizados.
- **Archivos afectados:** `services/profile-service/app/templates/cv.html`, `app/domain/cv_document.py`, `app/infrastructure/renderers/html.py`, `app/infrastructure/renderers/docx.py`, `tests/test_cv_generation.py`, `contracts/profile.md`, `PROMPTS.md`.
- **Decisión:** aceptado (pendiente revisión del equipo).

### P-042 — Ponderación de las recomendaciones y formación general
- **Fecha:** 2026-11-10 · **Autor:** Andres · **Agente:** Claude Code (`matching-agent`, `mcp-agent`, `n8n-agent`, `frontend-agent`) · **Ramas:** `feature/matching/v0.3.0-ponderacion-y-formacion-general`, `feature/mcp/v0.6.0-formacion-general`, `feature/n8n/v0.6.0-formacion-general`, `feature/frontend/v0.10.0-formacion-general` · **HU:** recomendaciones de empleo
- **Prompt (textual):**
  > necesito unos cambios en las recomendaciones de empleo. No se puede valuar de igual forma la disponibilidad o modelaidas que los skills, a las cuestiones no tecnicas dales menos ponderacion. Podera mas la experiencia. No pidas porfolios ni nada similar. Las recomenrtdaciones de areas o skills a agregar / mejorar son en general y no en funcion de cada puesto. Se calucula en base al perfil y a las busquedas mas similares.
  >
  > ademas pone una barra de progreso en el front mientras busca recomendaciones
- **Resumen de la respuesta:**
  - **matching-service 0.3.0 (reglas 2.0.0):**
    - pesos: obligatorias 40, deseables 10, niveles 10, experiencia 25, formación 5, idiomas 3 y el nuevo criterio `conditions` 7;
    - experiencia: años frente al mínimo (o a 1 año si la oferta no pide) y relevancia según `skills_used`;
    - modalidad, ubicación, horario y tipo de vínculo dejan de excluir: sólo siguen siendo duros la licencia y la autorización para trabajar;
    - `SkillGapAggregator` junta las competencias que faltan en las 10 ofertas más parecidas al perfil (`GET /students/{id}/skill-gaps`) y la formación pasa a ser general (`GET /recommendations/students/{id}/training`).
  - **mcp-tools 0.6.0:** `student_recommendations` sin `project` (`course | skill | profile_tip`); `next_steps` por oferta sólo `apply | profile_tip`; skill `orientacion-postulante` reescrita.
  - **n8n:** WF-06 `mode=training` usa las brechas generales; `training_advisor` 2.0.0 y `match_advisor` 1.1.0 no piden portfolios ni proyectos y ponen las condiciones laborales como avisos breves.
  - **Front 0.10.0:** tarjeta "Qué sumar o mejorar" (reglas e IA separados) en "Ofertas para vos" y barra de progreso estimada mientras la IA genera recomendaciones de ofertas, candidatos y formación.
- **Archivos afectados:** `services/matching-service/**`, `mcp-tools/app/data/**`, `n8n/generate_workflows.py`, `n8n/prompts/*`, `n8n/agentes/*`, `n8n/workflows/WF-06-recomendador.json`, `frontend/src/**`, `contracts/matching.md`, `contracts/mcp_tools.md`, `contracts/n8n.md`, `AGENTS.md`, `PROMPTS.md`.
- **Decisión:** aceptado (pendiente revisión del equipo).

### P-043 — Diccionario de competencias y herramientas similares
- **Fecha:** 2026-11-10 · **Autor:** Andres · **Agente:** Claude Code (`matching-agent`, `mcp-agent`, `n8n-agent`, `frontend-agent`) · **Ramas:** `feature/matching/v0.4.0-diccionario-skills`, `feature/mcp/v0.7.0-resolver-skills`, `feature/n8n/v0.7.0-diccionario-skills`, `feature/frontend/v0.11.0-skills-similares` · **HU:** recomendaciones de empleo
- **Prompt (textual):**
  > arma un diccionario de skills que oueden figurar con distinto nombre ejmplo Mysql y MariaDB o Posgres y PosgresSQL, arma la lista de terminos similares tanto para las recomnendaciones por reglas como para darle de herramienta al agente
  >
  > despues arma una lista de herramientas similares que pueden facilitar el aprendizaje de una solicitada en las busquedas tambien para las reglas y los agentes ejemplo github y gitlab
- **Resumen de la respuesta:**
  - **matching-service 0.4.0:** `app/data/skill_dictionary.json` (148 skills) reemplaza a `skill_synonyms.json`, con cuatro relaciones:
    - alias con errores comunes (`Posgres` → PostgreSQL);
    - `implies` transitivo (PostgreSQL ⇒ SQL);
    - equivalentes que cuentan completas (MySQL ↔ MariaDB);
    - herramientas similares que facilitan el aprendizaje (GitHub ~ GitLab, 27 grupos con `credit` 0,5 o 0,75), que suman una parte y quedan como brecha con `similar_to`.

    El motor lo usa en todos los criterios de skills, en la excluyente, en la experiencia relevante y en las brechas generales. Nuevos `GET /skills/dictionary` y `POST /skills/resolve`.
  - **mcp-tools 0.7.0:** herramienta `resolver_skills` (perfiles `cv`, `postulante`, `empresa` y `verificador`).
  - **n8n:** `training_advisor` 2.1.0 y `match_advisor` 1.2.0 usan `via`, `similar_to` y `resolver_skills`.
  - **Front 0.11.0:** "SQL (por PostgreSQL)", "GitLab (… · similar a GitHub)" y "Ya sabés GitHub: GitLab te va a resultar más fácil".
- **Archivos afectados:** `services/matching-service/**`, `mcp-tools/**`, `n8n/**`, `frontend/src/**`, `contracts/matching.md`, `contracts/mcp_tools.md`, `contracts/n8n.md`, `AGENTS.md`, `PROMPTS.md`.
- **Decisión:** aceptado (pendiente revisión del equipo).

### P-044 — Reseteo automático de scroll en navegación de ofertas
* **Fecha:** 2026-11-11 · **Autor:** Dario · **Agente:** Gemini (`frontend-agent`) · **Rama:** `fix/frontend/v0.11.1-correccion-todas-las-ofertas` · **HU:** Correcciones de UI y Navegación SPA
* **Prompt (resumido):**
  > Corrige un fallo en UX, la posición de la pantalla al scrolear hacia abajo en "Todas las ofertas" y seleccionar una empresa, se mantiene y la vista de detalle de la empresa queda situada respetando scroll en pantalla anterior, se debe resetear arriba (scroll to top) y no mantener la posición desplazada de la vista anterior.
* **Resumen de la respuesta:**
  - Importación e inclusión de `useEffect` en `JobDetail.tsx` ejecutando `window.scrollTo(0, 0)` al montarse el componente.
  - Sincronización en `App.tsx` para forzar el reseteo del scroll vertical de la ventana ante cada cambio de vista (`activeView`) o sección activa (`section`).
* **Archivos afectados:** `frontend/src/components/jobs/JobDetail.tsx`, `frontend/src/App.tsx`, `PROMPTS.md`.
* **Decisión:** aceptado.

### P-045 — Sincronización de rutas Header/Footer y modal de configuración de cuenta
* **Fecha:** 2026-11-11 · **Autor:** Dario · **Agente:** Gemini (`frontend-agent`) · **Rama:** `fix/frontend/v0.11.1-correccion-todas-las-ofertas` · **HU:** HU-04 (Seguridad de cuenta) / Navegación Consistente
* **Prompt (resumido):**
  > Agrega en el Header la opción "Todas las ofertas", ya que solo esta visible en el Footer y hace que la funcionalidad solo sea accesible desde alli, cuida de que  ambas apunten a la sección correcta ('jobs') y asegura que las funcionalidades previa del Header no sean afectadas, ni se pierda el estado ni el renderizado de `AccountSettingsModal`.
* **Resumen de la respuesta:**
  - Corrección de la propiedad `section` en `STUDENT_NAV` dentro de `SiteHeader.tsx` asignando `'jobs'` para evitar desalineaciones con la ruta manejada en `SiteFooter.tsx`.
  - Preservación del estado local `showAccountModal` y su renderizado flotante sobre el `header` al interactuar con el email del usuario.
* **Archivos afectados:** `frontend/src/components/layout/SiteHeader.tsx`, `frontend/src/components/layout/SiteFooter.tsx`, `PROMPTS.md`.
* **Decisión:** aceptado.

### P-046 — Recomendaciones de IA más rápidas y herramientas por agente
- **Fecha:** 2026-11-11 · **Autor:** Andres · **Agente:** Claude Code (`mcp-agent`, `n8n-agent`) · **Ramas:** `feature/mcp/v0.8.0-herramientas-por-agente`, `feature/n8n/v0.8.0-recomendaciones-rapidas` · **HU:** recomendaciones de empleo
- **Prompt (textual):**
  > cuando uso los agentes de IA sobre todo en las recomendaciones demora bastante, quisiera que analises si no hay algun cuello de botella o alguna tarea que pueda agilizarse para responder mas rapido sin perder calidad
  >
  > revisa las ejecuciones con mi usuario
  >
  > empesa a aplicar los cambios y las reglas van por agente, si estos agentes no las usan dejalas en los que si.
  >
  > revisa que tambien los agentes para leer y armar el cv no tengan reglas que no les corresponden
- **Resumen de la respuesta:**
  - **Diagnóstico** (ejecuciones de n8n): el 99 % del tiempo es la generación del LLM en WF-0R; el verificador tarda 0,1 s y el contexto por reglas < 0,5 s. Dos recomendaciones hicieron un reintento completo (30–50 s) sólo porque el modelo devolvió 4 `watch_outs` donde el schema acepta 3.
  - **mcp-tools 0.8.0:** `&herramientas=a,b` en la conexión MCP achica el perfil a las herramientas del agente (nunca lo amplía; vacío = ninguna).
  - **n8n:**
    - cada agente declara `herramientas`; el system prompt lleva sólo esas filas de `reglas.md` con sus skills y schemas, y la regla del puntaje sólo va a los agentes de matching;
    - `match_advisor`, `training_advisor` y `cv_structurer` no usan herramientas (los datos llegan en el pedido) y corren por `Agente sin herramientas`, sin conexión MCP;
    - `cv_designer` y `company_advisor` dejan la skill `verificacion-grounding` (es del verificador);
    - WF-00 recorta la salida a los topes del schema antes de verificar, en vez de reintentar;
    - WF-06 manda el contexto como JSON compacto y pide configuración, ranking, brechas y perfil en paralelo;
    - prompts `match_advisor` 1.3.0 y `training_advisor` 2.2.0.
  - **Resultado medido** con el mismo perfil: entrada de `match_advisor` 11.617 → 5.944 tokens y de `training_advisor` 8.052 → 3.313; sin reintentos por topes. La salida no cambia: el próximo paso es una llamada por oferta en paralelo.
- **Archivos afectados:** `mcp-tools/**`, `n8n/generate_workflows.py`, `n8n/agentes/*`, `n8n/prompts/match_advisor.md`, `n8n/prompts/training_advisor.md`, `n8n/workflows/*`, `contracts/mcp_tools.md`, `contracts/n8n.md`, `AGENTS.md`, `PROMPTS.md`.
- **Decisión:** aceptado (pendiente revisión del equipo).

### P-047 — Análisis de IA por oferta o candidato en paralelo
- **Fecha:** 2026-11-11 · **Autor:** Andres · **Agente:** Claude Code (`n8n-agent`) · **Rama:** `feature/n8n/v0.8.0-recomendaciones-rapidas` (probado primero en una rama local de prueba; mismo PR que P-046) · **HU:** recomendaciones de empleo
- **Prompt (textual):**
  > crea una rama de test sumando las llamadas en paralelo pero no la suubas que quiero probar primero
  >
  > iintegralo en el mismo PR con las modificaciones anteriores ya que todas tienen el mismo objetivo
- **Resumen de la respuesta:**
  - WF-06 (`mode=student|company`) pide a WF-00 un análisis por ítem del ranking y uno para el resumen, todos a la vez con el nodo HTTP Request. Un Code node con `Promise.all` quedaba limitado a 6 pedidos simultáneos.
  - Salen de a 10 con 10 s entre lotes, porque con 11 simultáneos NVIDIA devolvió 429. Cada pedido tiene 100 s y el que se cuelga se reintenta una vez (NVIDIA a veces deja una respuesta abierta que el timeout del LLM no corta).
  - `match_advisor` 1.4.0 (un ítem por pedido).
  - **Medido** con el mismo perfil: student 23,8–37,7 s (antes 46–96 s) y company 32,7 s con 10 candidatos; 111 s cuando hubo que reintentar un candidato colgado.
- **Archivos afectados:** `n8n/generate_workflows.py`, `n8n/workflows/WF-06-recomendador.json`, `n8n/prompts/match_advisor.md`, `contracts/n8n.md`, `PROMPTS.md`.
- **Decisión:** aceptado (pendiente revisión del equipo).

### P-048 — (plantilla)
- **Fecha:** · **Autor:** · **Agente:** · **Rama:** · **HU:**
- **Prompt (textual o resumido):**
  > …
- **Resumen de la respuesta:**
  - …
- **Archivos afectados:** …