# Bolsa de Trabajo · MVP

Matching estudiante–oferta con microservicios REST, scoring por reglas y agentes de IA orquestados en `n8n`.
- Reglas de arquitectura y agentes: [AGENTS.md](AGENTS.md).
- Historial de prompts de desarrollo: [PROMPTS.md](PROMPTS.md).

## Requisitos

- Docker Desktop (Compose v2)
- Para trabajar fuera de Docker: Python 3.12 y Node 22

## Levantar el entorno

```bash
cp .env.example .env            # completar valores (en dev los de ejemplo sirven)
mkdir -p secrets                # claves JWT de auth-service (ver .env.example)
docker compose up -d --build    # modo desarrollo (hot reload)
docker compose ps               # todos deben quedar "healthy"
```

Modo tipo producción (sin `docker-compose.override.yml`):

```bash
docker compose -f docker-compose.yml up -d --build
```

Apagar: `docker compose down` · Borrar también datos (base, n8n, CVs): `docker compose down -v`.

## URLs

| Qué | URL |
|---|---|
| App + API (gateway) | http://localhost:8080 · API en `/api/v1/*` |
| Formulario de prueba CV (`profile-service → n8n`) | http://localhost:8080/api/v1/profiles/cv-test |
| n8n | http://localhost:5678 (o el `N8N_PORT` definido en `.env`) |
| Mailpit (correos de prueba) | http://localhost:8025 |
| PostgreSQL (solo dev) | `localhost:5432` · base `bolsa` |

Si algún puerto está ocupado en tu máquina, cambialo en `.env` (`GATEWAY_PORT`, `N8N_PORT`, `MAIL_UI_PORT`, `POSTGRES_HOST_PORT`).

## Servicios y Arquitectura

| Servicio | Stack | Puerto interno | Ruta en el gateway Nginx | Red / Acceso | Schema DB |
|---|---|---|---|---|---|
| `auth-service` | NestJS (Node 22) | 3000 | `/api/v1/auth/` | `backend` (vía `gateway`) | `auth` |
| `profile-service` | FastAPI | 8000 | `/api/v1/profiles/` | `backend` (vía `gateway`) | `profile` |
| `jobs-service` | FastAPI | 8000 | `/api/v1/jobs/`, `/api/v1/companies/` | `backend` (vía `gateway`) | `jobs` |
| `matching-service` | FastAPI | 8000 | `/api/v1/matches/` | `backend` (vía `gateway`) | `matching` |
| `frontend` | React 18 + Vite | 8080 | `/` | `edge` (vía `gateway`) | — |
| `n8n` | n8n + Agentes IA | 5678 | — (webhooks internos) | `backend`, `mcp_internal` | base propia `n8n` |
| `mcp-tools` | FastMCP (`streamable-http`) | 8000 (`/mcp`, `/router/*`) | **No pasa por Nginx** | `mcp_internal` (**directo con `n8n`**) + `backend` | — |

### Decisiones clave de arquitectura (IA y MCP)
1. **Sin `ai-service` intermedio**: toda la orquestación y ejecución de agentes de IA (estructuración de CVs, recomendaciones para estudiantes y empresas, selección de modelos en NVIDIA NIM y verificación anti-alucinación) se ejecuta directamente en **`n8n`**.
2. **Comunicación directa `n8n ↔ mcp-tools` sin pasar por Nginx**: `n8n` es el único consumidor de `mcp-tools` y se conecta directamente a `http://mcp-tools:8000/mcp` a través de la red interna `mcp_internal`, sin exponer ni enrutar `mcp-tools` en el API Gateway (`gateway/nginx.conf`).

### Agentes IA (`n8n`) y Servidor MCP (`mcp-tools`)

- **`mcp-tools` (`v0.2.0`)**: expone herramientas MCP filtradas por perfil (`?perfil=planificador|cv|postulante|empresa|verificador|adjuntos`) y endpoints HTTP internos protegidos por `X-Service-Token`:
  - Configuración dinámica (`get_agent_settings`), lectura de skills (`list_skills`, `leer_skill` con protección anti-bucle), extracción de CV en PDF/DOCX/DOC/MD (`parse_cv_file`), consulta de perfiles y ofertas (`get_profile`, `list_candidate_profiles`, `get_job`, `list_active_jobs`), scoring determinístico por reglas (`compute_match`, `missing_skills`), catálogo de cursos (`search_courses`), persistencia (`save_recommendation`) y verificación (`validate_json_schema`, `check_grounding`).
  - **Router NVIDIA**: selección inteligente de modelos con circuit-breaker, cuota por minuto y telemetría en `/router/status`.
- **Workflows n8n (`n8n/workflows/`, generados desde `n8n/agentes/` y `n8n/prompts/`)**:
  - `WF-0R-router-nvidia.json`: sub-workflow especialista y router de modelos NVIDIA NIM.
  - `WF-0V-verificador.json`: sub-workflow verificador (validación determinística JSON Schema + grounding + agente verificador).
  - `WF-00-orquestador.json`: sub-workflow orquestador con lectura de adjunto vía MCP y reintento guiado.
  - `WF-01-procesar-cv.json`: webhook `POST /webhook/cv-extract` (`CV Structurer`).
  - `WF-06-recomendador.json`: webhook `POST /webhook/recommendations` (`Training Advisor` para postulantes y `Company Advisor` para empresas).

Para regenerar e importar los workflows en el contenedor `n8n`:

```bash
python n8n/generate_workflows.py
docker exec bolsa-n8n-1 n8n import:workflow --separate --input=/workflows
```

### Base de datos

Una instancia PostgreSQL 17 con un **rol y un schema por microservicio REST** (`infra/postgres/init/01-schemas.sh`: `auth`, `profile`, `jobs`, `matching`).
Cada rol sólo puede usar su schema, así ningún servicio lee los datos de otro. `n8n` usa una base aparte porque gestiona su propio esquema.
El script corre solo al crear el volumen; si lo cambiás: `docker compose down -v && docker compose up -d`.

### Almacenamiento y correo

- CVs: volumen Docker `cv_storage` montado en `profile-service` (`/data/cvs`).
- Correo: Mailpit (puertos SMTP 1025 / UI 8025).

## Estructura

```
.
├── docker-compose.yml            # stack completo
├── docker-compose.override.yml   # dev: hot reload, Postgres expuesto
├── .env.example                  # todas las variables (copiar a .env)
├── AGENTS.md                     # reglas de arquitectura y de agentes
├── PROMPTS.md                    # historial de prompts y decisiones (separado)
├── gateway/nginx.conf            # API Gateway (solo frontend + microservicios REST)
├── infra/postgres/init/          # roles + schemas por microservicio
├── services/
│   ├── auth-service/             # NestJS
│   ├── profile-service/          # FastAPI por capas (api, application, domain, infrastructure)
│   ├── jobs-service/             # FastAPI por capas
│   └── matching-service/         # FastAPI por capas
├── mcp-tools/                    # servidor MCP (consumido directo por n8n)
├── n8n/
│   ├── agentes/                  # catálogo declarativo de agentes
│   ├── prompts/                  # plantillas versionadas de prompts IA
│   ├── workflows/                # WF-0X-<nombre>.json (sin credenciales)
│   └── generate_workflows.py     # generador determinístico de workflows
├── frontend/                     # React + Vite
├── contracts/                    # esquemas JSON y contratos OpenAPI
├── ruff.toml · .prettierrc.json · .editorconfig   # estilo común
└── .github/                      # CI + plantilla de PR
```

## Calidad (lo mismo que corre el CI)

Python (desde la carpeta del servicio):

```bash
pip install -e ".[dev]"
ruff check . && black --check . && mypy app && pytest
```

Node (`auth-service` / `frontend`):

```bash
npm ci && npm run format:check && npm run typecheck && npm test
```

El CI (`.github/workflows/ci.yml`) corre sólo los servicios cuyas carpetas cambiaron.

## Flujo Git

Ramas `<tipo>/<servicio>/v<semver>-<desc>` → PR a `dev` → release a `main`. Ver [AGENTS.md §3](AGENTS.md) y registrar los prompts en [PROMPTS.md](PROMPTS.md).
