# Bolsa de Trabajo · MVP

**TP2 · Elementos de Programación IA y LowCode · 2.º cuatrimestre 2026 · Grupo 1**
Proyecto A: Plataforma de vinculación y desarrollo profesional.

Matching estudiante–oferta con microservicios REST, scoring por reglas y agentes de IA orquestados en `n8n`.

## Objetivo

Vincular estudiantes y graduados con las ofertas laborales de empresas. El sistema:

1. Registra perfiles de estudiantes, a mano o **importando el CV en PDF/DOCX, que la IA interpreta** y el estudiante revisa antes de guardar.
2. Registra empresas y sus búsquedas con requisitos (competencias obligatorias, deseables y excluyentes, experiencia, idiomas, condiciones).
3. Compara perfil ↔ oferta y calcula un **puntaje de compatibilidad por reglas explícitas** (`origin: "RULES"`), con el desglose por criterio y las **competencias faltantes**.
4. Permite que el estudiante **se postule** a una oferta: la empresa ve a todos los postulados con su contacto y, entre los recomendados por reglas, cuáles se postularon.
5. Pide a **agentes de IA en n8n** recomendaciones de formación, de mejora del perfil y de candidatos (`origin: "AI"`), verificadas antes de mostrarse.
6. Automatiza con n8n la lectura de CVs, las recomendaciones y los avisos por mail (oferta nueva, candidato nuevo, errores).

El front **siempre muestra separados** el resultado por reglas (badge verde) y la sugerencia de la IA (badge ámbar, con aviso de que es orientativa). La IA nunca calcula ni cambia el puntaje.

## Documentación

| Documento | Contenido |
|---|---|
| [docs/manuales/](docs/manuales/) | Manuales de instalación y de uso (estudiante, empresa y admin) |
| [docs/manuales/arquitectura.pdf](docs/manuales/arquitectura.pdf) | Arquitectura en PDF: vista general, capas, flujo de trabajo y tecnologías con el porqué de cada una |
| [docs/ARQUITECTURA.md](docs/ARQUITECTURA.md) | Diagrama de arquitectura, redes, puertos y recorrido de los datos |
| [docs/BITACORA_IA.md](docs/BITACORA_IA.md) | Bitácora de uso de IA: herramientas, decisiones, modelo elegido y sus límites, dificultades y correcciones |
| [docs/RESPONSABILIDADES.md](docs/RESPONSABILIDADES.md) | Responsabilidades de cada integrante |
| [docs/ENTREGA.md](docs/ENTREGA.md) | Correspondencia entre la consigna y el repositorio |
| [PROMPTS.md](PROMPTS.md) | Historial de prompts de desarrollo y decisiones |
| [AGENTS.md](AGENTS.md) | Reglas de arquitectura y de agentes |
| [contracts/](contracts/) | Un contrato por servicio (endpoints, JSON, errores) |
| [n8n/workflows/](n8n/workflows/) | Workflows de n8n exportados en JSON |

## Requisitos

- Docker Desktop (Compose v2). Es lo único obligatorio.
- `openssl` para generar las claves JWT (viene con Git Bash en Windows, macOS y Linux).
- **API key gratuita de NVIDIA NIM** para los agentes de IA: crear una cuenta en <https://build.nvidia.com>, entrar a *API Keys* y generar una. Sin la key funciona todo lo demás (cuentas, perfiles, búsquedas, puntaje por reglas, avisos), pero la lectura de CVs y las recomendaciones de IA no responden.
- Para trabajar fuera de Docker: Python 3.12 y Node 22.

## Levantar el entorno

```bash
cp .env.example .env            # completar NVIDIA_API_KEY (el resto de los valores de ejemplo sirven en dev)

# Claves RSA con las que auth-service firma los JWT (no se suben al repo)
mkdir -p secrets
openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:2048 -out secrets/jwt_private.pem
openssl rsa -in secrets/jwt_private.pem -pubout -out secrets/jwt_public.pem

sh infra/scripts/create-volumes.sh   # una sola vez: volúmenes externos con los datos
docker compose up -d --build    # modo desarrollo (hot reload)
docker compose ps               # todos deben quedar "healthy"
```

Sin `sh` (PowerShell): `docker volume create bolsa_pg_data; docker volume create bolsa_n8n_data; docker volume create bolsa_cv_storage`.

Modo tipo producción (sin `docker-compose.override.yml`):

```bash
docker compose -f docker-compose.yml up -d --build
```

### Iniciar, detener y reiniciar

| Acción | Comando |
|---|---|
| Levantar todo | `docker compose up -d --build` |
| Ver el estado | `docker compose ps` |
| Ver los logs de un servicio | `docker compose logs -f matching-service` |
| Detener sin borrar contenedores | `docker compose stop` |
| Volver a arrancar lo detenido | `docker compose start` |
| Reiniciar un servicio | `docker compose restart profile-service` |
| Reiniciar n8n y volver a cargar los workflows | `docker compose up -d --force-recreate n8n` |
| Reconstruir un servicio después de cambiar dependencias | `docker compose up -d --build jobs-service` |
| Apagar y borrar contenedores (los datos quedan) | `docker compose down` |

### Datos persistentes

Los datos viven en **volúmenes externos**, fuera de los contenedores y de compose: sobreviven a recrear contenedores o imágenes y también a `docker compose down -v`.

| Volumen | Qué guarda |
|---|---|
| `bolsa_pg_data` | PostgreSQL: bases de todos los servicios, la base de n8n (workflows, credenciales, ejecuciones) y los logos de empresas |
| `bolsa_n8n_data` | Configuración de n8n (`/home/node/.n8n`) |
| `bolsa_cv_storage` | CVs subidos por los estudiantes |

Para empezar de cero hay que borrarlos a mano (**se pierde todo**): `docker compose down && docker volume rm bolsa_pg_data bolsa_n8n_data bolsa_cv_storage && sh infra/scripts/create-volumes.sh`.

### Datos de configuración y de prueba

En [`infra/datos-prueba/`](infra/datos-prueba/) hay un juego de datos ficticio listo para importar:

| Archivo | Qué tiene |
|---|---|
| `bolsa_datos_prueba.sql` | Dump (sólo datos) de los schemas `auth`, `profile`, `jobs` y `matching`: 2 cuentas `admin`, 10 empresas con perfil, logo y 5 búsquedas cada una, 50 estudiantes con el perfil completo (Administración, IT, Educación y Administración pública) y la configuración de matching |
| `usuarios_prueba.xlsx` | Las cuentas con su clave (todas las de prueba usan la misma), los perfiles, las empresas y las búsquedas |

La configuración de n8n (credenciales y workflows) no va en el dump: la crea `n8n/init/bootstrap.sh` en cada arranque desde `.env` y `n8n/workflows/`. Para que los agentes de IA respondan, cargá `NVIDIA_API_KEY` en `.env`.

Para importarlos:

1. En `.env`, apagá los datos de demo para que no se mezclen con los de prueba:
   ```bash
   PROFILE_SEED_DEMO=false
   JOBS_SEED_DEMO=false
   ```
2. Levantá el entorno y esperá a que todo quede `healthy`. Los servicios crean las tablas al arrancar:
   ```bash
   docker compose up -d --build
   docker compose ps
   ```
3. Importá el dump. **Reemplaza** todas las cuentas, perfiles, búsquedas y recomendaciones que haya:
   ```bash
   docker compose exec -T postgres sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 -q' < infra/datos-prueba/bolsa_datos_prueba.sql
   ```
   En PowerShell: `Get-Content infra/datos-prueba/bolsa_datos_prueba.sql -Raw | docker compose exec -T postgres sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 -q'`.
4. Entrá en http://localhost:8080 con cualquier cuenta de `usuarios_prueba.xlsx`.

Los mails de prueba (`@example.test`) no salen a internet: llegan a Mailpit. Los manuales de instalación y de uso están en [`docs/manuales/`](docs/manuales/).

Si no se importa el dump, los servicios cargan solos un juego de demo (15 perfiles y 12 ofertas) mientras `PROFILE_SEED_DEMO` y `JOBS_SEED_DEMO` estén en `true`, pero no hay cuentas de administrador. Para tener una, registrarse como estudiante y cambiarle el rol (con los valores de `POSTGRES_USER` y `POSTGRES_DB` de `.env`):

```bash
docker compose exec postgres psql -U postgres -d bolsa \
  -c "UPDATE auth.users SET role='admin' WHERE email='admin@bolsa.local';"
```

y volver a iniciar sesión.

Todos los datos del repositorio son **ficticios**.

## Funcionalidades principales

**Estudiante:** registro e inicio de sesión · alta del perfil importando el CV (la IA propone los datos y el estudiante los revisa y confirma) o a mano · "Ofertas para vos" con el puntaje por reglas, el desglose "¿Por qué este puntaje?" y las competencias faltantes · recomendaciones de formación y de mejora del perfil generadas por IA · descarga del CV en PDF o Word con el diseño sugerido por la IA o elegido por el estudiante · postularse a una oferta (la empresa ve su nombre, email, teléfono y título) y ver o retirar sus postulaciones en "Mis postulaciones" · contacto de selección de la empresa, si la empresa lo hace público · cambio y recuperación de clave y de correo.

**Empresa:** registro con razón social y CUIT validado · perfil público (logo, rubro, sedes, beneficios) · alta, edición, cierre y reapertura de búsquedas · postulados de cada búsqueda con sus datos de contacto · candidatos ordenados por reglas con el análisis de la IA, marcando los que se postularon.

**Administrador:** cuentas de estudiantes y empresas (buscar, editar, forzar cambio de clave, borrar) · cantidad de ofertas y candidatos que se recomiendan · enlaces a la documentación de las APIs.

**Automatizaciones (n8n):** lectura y estructuración del CV · recomendaciones para estudiantes y empresas · diseño del CV · mail a estudiantes compatibles cuando se publica una oferta · aviso a empresas cuando aparece un candidato compatible · aviso al admin cuando falla un workflow.

### Recorrido sugerido para la demo

1. **Empresa:** publicar una búsqueda con competencias obligatorias y ver en Mailpit el aviso a los estudiantes compatibles.
2. **Estudiante:** crear el perfil subiendo un CV en PDF; la IA completa los campos y marca los que hay que revisar.
3. En "Ofertas para vos", abrir una oferta: puntaje por reglas, "¿Por qué este puntaje?", faltantes y luego las recomendaciones de la IA. Tocar **Postularme** y verla en "Mis postulaciones".
4. **Empresa:** ver los candidatos de la búsqueda: el estudiante aparece en "Postulados" con su contacto y, en el ranking, marcado con "Se postuló"; después, el análisis de la IA y el aviso de candidato nuevo en Mailpit.
5. **Errores:** subir un archivo que no es un CV o pesa más de 5 MB, crear una búsqueda sin competencias obligatorias (422), detener un servicio con `docker compose stop matching-service` y mostrar el mensaje del front y el mail de error al admin.
6. Mostrar las ejecuciones en n8n y los endpoints en Swagger.

## URLs

| Qué | URL |
|---|---|
| App + API (gateway) | http://localhost:8080 · API en `/api/v1/*` |
| Formulario de prueba CV (`profile-service → n8n`) | http://localhost:8080/api/v1/profiles/cv-test |
| n8n | http://localhost:5678 (o el `N8N_PORT` definido en `.env`) |
| Mailpit (correos de prueba) | http://localhost:8025 |
| Documentación de las APIs (Swagger UI / ReDoc / OpenAPI) | `http://localhost:8080/api/v1/<recurso>/docs` · `/redoc` · `/openapi.json`, con `<recurso>` = `auth`, `profiles`, `jobs` o `matches`. También desde el panel de admin |
| PostgreSQL (solo dev) | `localhost:5432` · base `bolsa` |

Si algún puerto está ocupado en tu máquina, cambialo en `.env` (`GATEWAY_PORT`, `N8N_PORT`, `MAIL_UI_PORT`, `POSTGRES_HOST_PORT`).

## Servicios y Arquitectura

El diagrama de componentes y los recorridos de datos están en [docs/ARQUITECTURA.md](docs/ARQUITECTURA.md).

| Servicio | Stack | Puerto interno | Ruta en el gateway Nginx | Red / Acceso | Schema DB |
|---|---|---|---|---|---|
| `auth-service` | NestJS (Node 22) | 3000 | `/api/v1/auth/` | `backend` (vía `gateway`) | `auth` |
| `profile-service` | FastAPI | 8000 | `/api/v1/profiles/` | `backend` (vía `gateway`) | `profile` |
| `jobs-service` | FastAPI | 8000 | `/api/v1/jobs/`, `/api/v1/companies/` | `backend` (vía `gateway`) | `jobs` |
| `matching-service` | FastAPI | 8000 | `/api/v1/matches/` | `backend` (vía `gateway`) | `matching` |
| `frontend` | React 18 + Vite | 8080 | `/` | `edge` (vía `gateway`) | — |
| `n8n` | n8n + Agentes IA | 5678 | — (webhooks internos) | `backend`, `mcp_internal` | base propia `n8n` |
| `mcp-tools` | FastMCP (`streamable-http`) | 8000 (`/mcp`, `/router/*`) | **No pasa por Nginx** | `mcp_internal` (**directo con `n8n`**) + `backend` | — |
| `postgres` | PostgreSQL 17 | 5432 | — | `backend` | un schema por servicio + base `n8n` |
| `mail` | Mailpit | 1025 (SMTP) · 8025 (UI) | — | `backend` | — |
| IA externa | NVIDIA NIM (API gratuita) | HTTPS | — | Sale desde `n8n` | — |

### Decisiones clave de arquitectura (IA y MCP)
1. **Sin `ai-service` intermedio**: toda la orquestación y ejecución de agentes de IA (estructuración de CVs, recomendaciones para estudiantes y empresas, selección de modelos en NVIDIA NIM y verificación anti-alucinación) se ejecuta directamente en **`n8n`**.
2. **Comunicación directa `n8n ↔ mcp-tools` sin pasar por Nginx**: `n8n` es el único consumidor de `mcp-tools` y se conecta directamente a `http://mcp-tools:8000/mcp` a través de la red interna `mcp_internal`, sin exponer ni enrutar `mcp-tools` en el API Gateway (`gateway/nginx.conf`).

### Auth API

`auth-service` mantiene las cuentas (`student`, `company`, `admin`) en el schema PostgreSQL `auth`. Los datos profesionales de estudiantes y las vacantes permanecen en sus respectivos servicios.

- `POST /api/v1/auth/register`: alta de `student` o `company`; las empresas envían razón social, CUIT y actividad.
- `POST /api/v1/auth/login` (alias compatible: `/token`) y `POST /api/v1/auth/token/refresh`: login y rotación de refresh token.
- `GET /api/v1/auth/me`, `POST /api/v1/auth/password/change`, `POST /api/v1/auth/email/change`: requieren `Authorization: Bearer <access_token>`.
- `POST /api/v1/auth/password/reset`, `/password/reset/confirm`, `/email/confirm`: recuperación y confirmación de credenciales por email.
- `GET /api/v1/auth/.well-known/jwks.json`: publica la clave RSA pública para validar access tokens RS256.

El access token dura 15 minutos; el refresh token dura 7 días y se almacena como hash, se rota al usarlo y se revoca al cambiar o restablecer la contraseña. TypeORM aplica las migraciones de auth al iniciar el servicio. En desarrollo, los correos salen por SMTP hacia Mailpit.

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
  - `WF-02-oferta-nueva.json` a `WF-05-errores.json`: notificaciones por mail (oferta nueva, resumen al estudiante, candidato nuevo a la empresa) y aviso de errores al admin. Se ven en Mailpit; ver [`contracts/n8n.md`](contracts/n8n.md) (§7).

**Los workflows se cargan solos.** El contenedor de n8n corre [`n8n/init/bootstrap.sh`](n8n/init/bootstrap.sh) antes de arrancar, en cada `docker compose up` y cada reinicio:

1. crea o actualiza la credencial **"OpenAI account"** (NVIDIA NIM) si `NVIDIA_API_KEY` está en `.env`; si está vacía, deja la que se haya creado en la UI;
2. importa `n8n/workflows/*.json` (ids fijos: actualiza, no duplica);
3. publica (activa) cada workflow para que respondan los webhooks.

El repo es la fuente de verdad: lo que se cambie **sólo en la UI** de n8n se pisa en el próximo arranque. Para cambiar un workflow, editá el generador o el JSON y reiniciá:

```bash
python n8n/generate_workflows.py
docker compose up -d --force-recreate n8n   # vuelve a correr bootstrap.sh
```

Si n8n se reinicia en bucle con `You do not have permission to deactivate this workflow`, la base quedó con workflows activados por otra versión de n8n (por ejemplo 1.x). Se arregla una vez:

```bash
docker compose stop n8n
docker compose run --rm --no-deps --entrypoint n8n n8n unpublish:workflow --all
docker compose up -d n8n
```

### Base de datos

Una instancia PostgreSQL 17 con un **rol y un schema por microservicio REST** (`infra/postgres/init/01-schemas.sh`: `auth`, `profile`, `jobs`, `matching`).
Cada rol sólo puede usar su schema, así ningún servicio lee los datos de otro. `n8n` usa una base aparte porque gestiona su propio esquema.
El script corre sólo cuando el volumen `bolsa_pg_data` está vacío. Si lo cambiás, aplicá el cambio con SQL sobre la base existente; recrear el volumen borra **todos** los datos, incluidos los workflows y credenciales de n8n (ver "Datos persistentes").

### Almacenamiento y correo

- CVs: volumen externo `bolsa_cv_storage` montado en `profile-service` (`/data/cvs`).
- Logos de empresas: en PostgreSQL (schema `profile`), dentro de `bolsa_pg_data`.
- Correo: Mailpit (puertos SMTP 1025 / UI 8025).

## Estructura

```
.
├── docker-compose.yml            # stack completo
├── docker-compose.override.yml   # dev: hot reload, Postgres expuesto
├── .env.example                  # todas las variables (copiar a .env)
├── requirements.txt              # dependencias Python de todos los servicios
├── AGENTS.md                     # reglas de arquitectura y de agentes
├── PROMPTS.md                    # historial de prompts y decisiones (separado)
├── docs/                         # arquitectura, bitácora de IA, responsabilidades, entrega, manuales
├── gateway/nginx.conf            # API Gateway (solo frontend + microservicios REST)
├── infra/postgres/init/          # roles + schemas por microservicio
├── infra/datos-prueba/           # dump de datos ficticios + planilla de usuarios
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
├── contracts/                    # un contrato por servicio (auth, profile, jobs, matching, mcp_tools, n8n); historico/ con los anteriores
├── ruff.toml · .prettierrc.json · .editorconfig   # estilo común
└── .github/                      # CI + plantilla de PR
```

## Dependencias

Cada servicio Python declara sus dependencias en `pyproject.toml` (las usan los Dockerfiles) y en un `requirements.txt` equivalente. El `requirements.txt` de la raíz los incluye a todos para trabajar sin Docker:

```bash
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Los servicios Node (`auth-service`, `frontend`) usan `package.json` / `package-lock.json` (`npm ci`).

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

Estado al 13/11/2026: 131 tests en `matching-service`, 125 en `jobs-service`, 124 en `profile-service` y 31 en `mcp-tools`, todos en verde, con cobertura de 91 % a 98 %.

## Seguridad

No se suben contraseñas, tokens ni claves: `.env`, `secrets/` y `*.pem` están en `.gitignore`. Los workflows exportados no llevan credenciales; la de NVIDIA la crea `bootstrap.sh` desde `.env`. Las cuentas de `usuarios_prueba.xlsx` son ficticias y sólo sirven para el entorno local.

## Flujo Git

Ramas `<tipo>/<servicio>/v<semver>-<desc>` → PR a `dev` → release a `main`. Ver [AGENTS.md §3](AGENTS.md) y registrar los prompts en [PROMPTS.md](PROMPTS.md).
