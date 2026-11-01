# Bolsa de Trabajo · MVP

Matching estudiante–oferta con microservicios REST, scoring por reglas y recomendaciones de IA separadas.
Reglas del proyecto y de los agentes: [AGENTS.md](AGENTS.md).

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
| n8n | http://localhost:5678 |
| Mailpit (correos de prueba) | http://localhost:8025 |
| PostgreSQL (solo dev) | `localhost:5432` · base `bolsa` |

Si algún puerto está ocupado en tu máquina, cambialo en `.env` (`GATEWAY_PORT`, `N8N_PORT`, `MAIL_UI_PORT`, `POSTGRES_HOST_PORT`).

## Servicios

| Servicio | Stack | Puerto interno | Ruta en el gateway | Schema DB |
|---|---|---|---|---|
| auth-service | NestJS (Node 22) | 3000 | `/api/v1/auth/` | `auth` |
| profile-service | FastAPI | 8000 | `/api/v1/profiles/` | `profile` |
| jobs-service | FastAPI | 8000 | `/api/v1/jobs/`, `/api/v1/companies/` | `jobs` |
| matching-service | FastAPI | 8000 | `/api/v1/matches/` | `matching` |
| ai-service | FastAPI | 8000 | `/api/v1/ai/` | `ai` |
| mcp-tools | FastMCP (streamable-http) | 8000 (`/mcp`, `/router/status`) | interno | — |
| frontend | React 18 + Vite | 8080 | `/` | — |
| n8n | n8n | 5678 | — | base propia `n8n` |

Cada servicio tiene `GET /health` (interno) usado por el healthcheck de Docker.
Los microservicios de negocio hoy son **esqueletos** (sólo exponen `/health`); `mcp-tools` (v0.1.0) y los workflows de IA en `n8n` ya están implementados y operan con pasarelas mock (`MCP_USE_MOCKS=true`) hasta que cada dueño implemente sus endpoints reales (ver `contracts/mock_endpoints.yaml`).

### Agentes IA, MCP Tools y Workflows n8n

- **mcp-tools (`v0.1.0`)**: expone herramientas MCP y endpoints HTTP internos protegidos por `X-Service-Token`:
  - Configuración dinámica (`get_agent_settings`), extracción de CV en PDF/DOCX/DOC/MD (`parse_cv_file`), consulta de perfiles y ofertas (`get_profile`, `get_job`, `list_active_jobs`, `list_candidates_for_job`), scoring determinístico por reglas (`compute_match`, `missing_skills`), catálogo de cursos (`search_courses`), persistencia (`save_cv_suggestions`, `save_recommendation`) y verificación anti-alucinación + JSON Schema (`verify_agent_output`).
  - **Router NVIDIA**: selección inteligente de modelos con circuit-breaker, cuota diaria y telemetría en `GET /router/status` (`select_nvidia_model`, `report_nvidia_outcome`).
- **Workflows n8n (`n8n/workflows/`)**:
  - `WF-0R-router-nvidia.json`: sub-workflow router de modelos NVIDIA.
  - `WF-0V-verificador.json`: sub-workflow verificador (reglas determinísticas + juez LLM).
  - `WF-00-orquestador.json`: webhook `POST /webhook/orchestrator/run` con reintento automático guiado por feedback del verificador.
  - `WF-01-procesar-cv.json`: webhook `POST /webhook/cv-uploaded` (`CV Structurer`).
  - `WF-06-recomendador.json`: webhook `POST /webhook/recommendations` (`Training Advisor` para postulantes y `Company Advisor` para empresas).

Para regenerar e importar los workflows en el contenedor `n8n`:

```bash
python n8n/generate_workflows.py
docker exec bolsa-n8n-1 n8n import:workflow --separate --input=/workflows
```

### Base de datos

Una instancia PostgreSQL 17 con un **rol y un schema por servicio** (`infra/postgres/init/01-schemas.sh`).
Cada rol sólo puede usar su schema, así ningún servicio lee los datos de otro. n8n usa una base aparte porque gestiona su propio esquema.
El script corre solo al crear el volumen; si lo cambiás: `docker compose down -v && docker compose up -d`.

### Almacenamiento y correo

- CVs: volumen Docker `cv_storage` montado en profile-service (`/data/cvs`).
- Correo: Mailpit (reemplazo mantenido de MailHog, mismos puertos SMTP 1025 / UI 8025).

## Estructura

```
.
├── docker-compose.yml            # stack completo
├── docker-compose.override.yml   # dev: hot reload, Postgres expuesto
├── .env.example                  # todas las variables (copiar a .env)
├── gateway/nginx.conf            # API Gateway
├── infra/postgres/init/          # roles + schemas por servicio
├── services/
│   ├── auth-service/             # NestJS
│   └── <x>-service/app/{api,application,domain,infrastructure}/   # FastAPI por capas
├── mcp-tools/                    # servidor MCP
├── frontend/                     # React + Vite
├── n8n/workflows/                # WF-0X-<nombre>.json (sin credenciales)
├── contracts/                    # OpenAPI por servicio
├── ruff.toml · .prettierrc.json · .editorconfig   # estilo común
└── .github/                      # CI + plantilla de PR
```

## Calidad (lo mismo que corre el CI)

Python (desde la carpeta del servicio):

```bash
pip install -e ".[dev]"
ruff check . && black --check . && mypy app && pytest
```

Node (auth-service / frontend):

```bash
npm ci && npm run format:check && npm run typecheck && npm test
```

El CI (`.github/workflows/ci.yml`) corre sólo los servicios cuyas carpetas cambiaron.

## Flujo Git

Ramas `<tipo>/<servicio>/v<semver>-<desc>` → PR a `dev` → release a `main`. Ver [AGENTS.md §3](AGENTS.md).
