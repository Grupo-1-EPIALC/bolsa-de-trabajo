# Contrato · matching-service

> **Para:** el frontend (recomendaciones y score), n8n (WF-06), mcp-tools y el panel de admin.
> **Servicio:** `matching-service` 0.2.1 (FastAPI) · base `/api/v1/matches` · motor `engine_version` 1.0.0.
> **Fuente de verdad viva:** [Swagger UI](/api/v1/matches/docs) · [ReDoc](/api/v1/matches/redoc) · [OpenAPI](/api/v1/matches/openapi.json) (por el gateway, en dev `http://localhost:8080`).
> **Partes:** A. Recomendaciones y score (front) · B. Endpoints internos y flujo con n8n. Los `§` de cada parte se refieren a esa parte.
> Los documentos de los que sale este contrato están en [`historico/`](historico/). Todos los ejemplos usan datos ficticios.

---

## A. Recomendaciones y score (frontend)

> Fuente: [`historico/matching_frontend.md`](historico/matching_frontend.md).

### 1. Qué muestra el front

Cada pantalla de recomendaciones recibe **dos bloques que nunca se mezclan** (AGENTS.md §2.2):

| Bloque | Origen | Qué trae | Cómo se muestra |
|---|---|---|---|
| `rule_based` | `origin: "RULES"` — motor de reglas | Ranking, **score 0–100**, desglose, skills que coinciden y faltan, condiciones laborales, sueldo | Componente `ScoreCard` con badge verde **"Calculado por reglas"** |
| `ai_recommendations` | `origin: "AI"` — agente `match_advisor` en n8n | Textos: por qué conviene, advertencias, próximos pasos, preguntas de entrevista | Componente `AIRecommendations` con badge ámbar **"Sugerido por IA"** + `disclaimer` |

Reglas para la UI:
- **El score y el orden salen siempre de `rule_based`.** El bloque de IA no trae score; si alguna vez aparece uno, ignoralo.
- Los dos bloques se unen por id: `job_id` (vista del estudiante) o `profile_id` (vista de la empresa).
- La IA puede no estar disponible (todavía no se pidió, está procesando o falló). La pantalla tiene que funcionar sólo con `rule_based`.

---

### 2. Acceso, autenticación y errores

- **Base:** same-origin detrás del gateway: `/api/v1/matches/...` (Nginx ya enruta `/api/v1/matches/`).
- **Autenticación:** el mismo `access_token` que devuelve auth-service (`POST /api/v1/auth/token`), en `Authorization: Bearer <access_token>`. Usá el cliente único `src/api/client.ts`, con su interceptor y el refresh automático (el access token dura 15 minutos).
  - matching-service valida el JWT por su cuenta: firma RS256 con la clave pública del JWKS de auth-service (`/api/v1/auth/.well-known/jwks.json`), `iss = bolsa-auth`, `aud = bolsa-api`, `exp`, y `role` ∈ `student | company | admin`.
  - El token interno de servicio (`X-Service-Token`) es sólo para n8n y mcp-tools. El gateway lo borra en las peticiones que vienen de afuera y **no se acepta como Bearer**.
- **Qué puede ver cada rol** (el dueño se compara con el `sub` del JWT):

| Rol | Puede ver | Si pide algo ajeno |
|---|---|---|
| `student` | Sus recomendaciones (`profile.user_id == sub`), sus pedidos de IA y el match de su perfil con cualquier oferta | Perfil de otro estudiante → **404**. Vista de candidatos de una oferta → **403** |
| `company` | Los candidatos de sus ofertas (`job.company_id == sub`; es el `user_id` de la empresa en auth-service), sus pedidos de IA y el match de sus ofertas con cualquier candidato | Oferta de otra empresa → **404**. Vista de un estudiante → **403** |
| `admin` | Todo | — |

  Ante recursos de otro usuario se responde 404 y no 403, para no revelar qué ids existen.
- **Errores** (formato común):

```json
{ "error": { "code": "NOT_FOUND", "message": "Perfil 'stu-999' no encontrado", "details": { "profile_id": "stu-999" } } }
```

| HTTP | `code` | Cuándo | Qué hace el front |
|---|---|---|---|
| 401 | `UNAUTHORIZED` | Falta el token o es inválido | Renovar sesión / redirigir a login |
| 403 | `FORBIDDEN` | El rol no corresponde a la pantalla (ej. un estudiante pidiendo candidatos) o es un endpoint interno | Mensaje "No tenés acceso a esta sección" |
| 404 | `NOT_FOUND` | No existe el perfil, la oferta o el pedido, o es de otro usuario | Mensaje "No encontramos…" |
| 422 | `INVALID_INPUT` | Parámetros inválidos (`limit` fuera de 1–100, `mode` inválido) | Error de formulario |
| 502 | `UPSTREAM_ERROR` | profile-service, jobs-service o n8n no respondieron | "Probá de nuevo en unos minutos" |

---

### 3. Endpoints para el front

| Pantalla / acción | Método y ruta | Respuesta |
|---|---|---|
| Estudiante: "Ofertas para vos" | `GET /api/v1/matches/recommendations/students/{profile_id}?limit=5` | `StudentRecommendationsView` (§4.1) |
| Empresa: "Candidatos para tu búsqueda" | `GET /api/v1/matches/recommendations/jobs/{job_id}?limit=10` | `CompanyRecommendationsView` (§4.2) |
| Botón "Generar recomendaciones con IA" | `POST /api/v1/matches/recommendations/requests` | `202` + `RecommendationRequest` (§4.3) |
| Polling del pedido | `GET /api/v1/matches/recommendations/requests/{request_id}` | `RecommendationRequest` |
| Estudiante: "Qué sumar o mejorar" (pedir a la IA) | `POST /api/v1/matches/recommendations/requests` con `{ "mode": "training", "profile_id" }` | `202` + `RecommendationRequest` |
| Estudiante: ver qué sumar o mejorar (general, no por oferta) | `GET /api/v1/matches/recommendations/students/{profile_id}/training` | `TrainingView` (parte B §B.2) |
| Detalle de un match puntual (modal "¿Por qué este puntaje?") | `POST /api/v1/matches` con `{ "profile_id", "job_id" }` | `Match` (§4.4) |
| Diccionario de competencias (alias, equivalentes, implicaciones y similares) | `GET /api/v1/matches/skills/dictionary` | `SkillDictionary` (§5.1) |
| Normalizar competencias y saber si el perfil ya las cubre | `POST /api/v1/matches/skills/resolve` con `{ "skills": [...], "profile_skills": [...] }` | `{ items: SkillInfo[] }` (§5.1) |
| Admin: ver la configuración | `GET /api/v1/matches/settings` | `RecommendationSettings` (§4.5) |
| Admin: cambiar cuántas ofertas y candidatos se recomiendan | `PATCH /api/v1/matches/settings` | `RecommendationSettings` (§4.5) |

- **Cuántos ítems vienen lo decide el admin** (§4.5): `student_jobs_limit` ofertas por estudiante (por defecto 5) y `company_candidates_limit` candidatos por oferta (por defecto 10). El `limit` del query es opcional (1–20) y sólo sirve para **pedir menos**: nunca supera lo configurado.
- Las vistas **recalculan el bloque por reglas en cada GET** (siempre está al día con el perfil y la oferta). La parte de IA es la última que se guardó.
- **Internos, responden 403 con JWT** (sólo n8n y mcp-tools): `POST /recommendations`, `POST /recommendations/batch`, `POST /missing-skills` y los rankings sin IA `GET /students/{id}/jobs` y `GET /jobs/{id}/candidates`.
- **El front necesita el `profile_id` o el `job_id`**, no el `sub`. El estudiante obtiene su `profile_id` de profile-service; la empresa, los `job_id` de sus búsquedas en `GET /api/v1/companies/me/searches` (jobs-service).

#### 3.1 Flujo para generar las recomendaciones de IA

```
1. GET vista ──► ai_recommendations.status
      ├─ "ready"          → mostrar los textos
      ├─ "pending" / "processing" → mostrar spinner y hacer polling (paso 3)
      ├─ "not_requested"  → mostrar botón "Generar recomendaciones con IA"
      ├─ "completed" sin items → "La IA no encontró recomendaciones para agregar"
      └─ "failed"         → mostrar ai_recommendations.error.message + botón "Reintentar"
2. Click en el botón ──► POST /recommendations/requests
      body estudiante: { "mode": "student", "profile_id": "stu-001", "limit": 5 }
      body empresa:    { "mode": "company", "job_id": "job-004", "limit": 10 }
      ◄── 202 { "request_id": "req-…", "status": "pending", … }
3. Polling cada 3 s (máx. ~5 min) ──► GET /recommendations/requests/{request_id}
      hasta status "completed" o "failed"
4. Volver a pedir la vista (paso 1). Con TanStack Query: invalidar la query de la vista.
```

`limit` en el pedido es opcional (1–20). Sin `limit`, la IA analiza la cantidad configurada por el admin; con `limit`, el menor de los dos. La respuesta `202` trae el `limit` efectivo.

---

### 4. Respuestas

#### 4.1 `StudentRecommendationsView` — ofertas para un estudiante

```json
{
  "profile_id": "stu-001",
  "rule_based": {
    "origin": "RULES",
    "profile_id": "stu-001",
    "profile": { "profile_id": "stu-001", "headline": "…", "skills": [ … ], "…": "…" },
    "engine_version": "1.0.0",
    "rules_version": "1.0.0",
    "evaluated": 12,
    "excluded_incompatible": 3,
    "items": [
      {
        "rank": 1,
        "job": {
          "job_id": "job-004",
          "title": "Desarrollador/a Python Trainee (remoto)",
          "company_id": "22222222-2222-4222-8222-000000000004",
          "company_name": "Nube Austral S.A.",
          "seniority": "trainee",
          "location": { "city": "Buenos Aires", "province": "CABA", "country": "AR" },
          "requirements": { "skills": [ { "name": "Python", "level": 2, "kind": "required" } ], "…": "…" },
          "work_conditions": { "work_modality": ["remote"], "work_schedule": ["full_time", "part_time"], "…": "…" }
        },
        "match": { "score": 90.0, "…": "ver §4.4" }
      }
    ]
  },
  "ai_recommendations": {
    "origin": "AI",
    "status": "ready",
    "request_id": "req-3f2a9c1d7b20",
    "error": null,
    "summary": "Tus mejores opciones son las de Python remoto…",
    "model": "nvidia/nemotron-3-ultra-550b-a55b",
    "prompt_version": "1.0.0",
    "generated_at": "2026-11-04T12:00:00Z",
    "disclaimer": "Recomendación orientativa generada por IA. El puntaje y el ranking provienen exclusivamente del motor de reglas.",
    "verified": true,
    "items": [
      {
        "job_id": "job-004",
        "content": {
          "priority": "alta",
          "fit_reasons": ["Cubrís Python y Git por encima del nivel pedido."],
          "watch_outs": [],
          "next_steps": [
            { "type": "apply", "skill": "Python", "text": "Postulate esta semana.", "priority": "alta" },
            { "type": "course", "skill": "Docker", "text": "Hacé un curso introductorio de Docker.", "priority": "media" }
          ]
        }
      }
    ]
  }
}
```

#### 4.2 `CompanyRecommendationsView` — candidatos para una oferta

Igual que §4.1, pero:
- `rule_based.job` trae el snapshot de la oferta.
- Cada ítem trae `candidate` en lugar de `job`.
- `ai_recommendations.items[]` se une por `profile_id` y su `content` tiene otra forma.

```json
{
  "job_id": "job-004",
  "rule_based": {
    "origin": "RULES",
    "job_id": "job-004",
    "job": { "job_id": "job-004", "title": "Desarrollador/a Python Trainee (remoto)", "…": "…" },
    "evaluated": 15,
    "excluded_incompatible": 3,
    "items": [
      {
        "rank": 2,
        "candidate": {
          "profile_id": "stu-014",
          "headline": "Estudiante de Sistemas con Python, Django y PostgreSQL",
          "location": { "city": "Salta", "province": "Salta", "country": "AR" },
          "years_experience": 1.5,
          "skills": [ { "name": "Python", "level": 3 }, { "name": "Git", "level": 3 } ],
          "languages": [ { "name": "Inglés", "level": "B1" } ],
          "education": [ { "level": "university", "status": "in_progress", "degree": "Licenciatura en Análisis de Sistemas", "field": "sistemas" } ],
          "academic_status": { "career": "Licenciatura en Análisis de Sistemas", "current_year": 4, "progress_percent": 75.0 },
          "target_roles": ["Desarrolladora backend"],
          "work_conditions": { "work_modality": ["remote"], "availability_start": "within_30_days", "…": "…" }
        },
        "match": { "score": 95.0, "…": "ver §4.4" }
      }
    ]
  },
  "ai_recommendations": {
    "origin": "AI",
    "status": "ready",
    "items": [
      {
        "profile_id": "stu-014",
        "content": {
          "priority": "alta",
          "justification": "Cubre Python y Git con nivel superior al pedido.",
          "strengths": ["Python", "Git"],
          "gaps": [],
          "conditions_alerts": ["Puede empezar en 30 días; la oferta lo necesita en 15."],
          "interview_questions": ["¿Qué consultas SQL escribiste con PostgreSQL?"]
        }
      }
    ],
    "…": "mismos metadatos que §4.1"
  }
}
```

> **Privacidad:** `candidate` **no trae nombre, email, teléfono ni dirección**, a propósito: así el ranking y la IA no se sesgan. Para mostrar el nombre, el front lo pide a profile-service con el `profile_id`, y sólo si la empresa tiene permiso.

#### 4.3 `RecommendationRequest`

```json
{
  "request_id": "req-3f2a9c1d7b20",
  "mode": "company",
  "subject_id": "job-004",
  "status": "pending",
  "created_at": "2026-11-04T12:00:00Z",
  "updated_at": "2026-11-04T12:00:00Z",
  "error": null
}
```

`status`: `pending` → `processing` → `completed` | `failed`. Si es `failed`, `error` tiene `{ code, message, details }`.

#### 4.4 `Match` — resultado por reglas (lo que va dentro de cada `match`)

```json
{
  "origin": "RULES",
  "engine_version": "2.0.0",
  "rules_version": "2.0.0",
  "computed_at": "2026-11-10T01:16:22Z",
  "profile_id": "stu-014",
  "job_id": "job-004",
  "score": 94.42,
  "excluding_cap_applied": false,
  "breakdown": [
    { "criterion": "required_skills", "weight": 40, "earned": 40,   "details": { "required": 2, "matched": 2, "similar": 0 } },
    { "criterion": "desired_skills",  "weight": 10, "earned": 10,   "details": { "desired": 3, "matched": 3, "similar": 0 } },
    { "criterion": "levels",          "weight": 10, "earned": 10,   "details": { "compared": 5 } },
    { "criterion": "experience",      "weight": 25, "earned": 20,   "details": { "min_years": 0, "profile_years": 1.5, "years_fit": 1.0, "relevance": 0.5, "relevant_skills": [] } },
    { "criterion": "education",       "weight": 5,  "earned": 5,    "details": { "required": true } },
    { "criterion": "languages",       "weight": 3,  "earned": 3,    "details": { "required": 1 } },
    { "criterion": "conditions",      "weight": 7,  "earned": 6.42, "details": { "compared": 12, "matched": 10, "partial": 2, "mismatched": 0 } }
  ],
  "matched_skills": [
    { "skill": "Python", "kind": "required", "profile_level": 3, "required_level": 2, "via": null, "relation": "exact" },
    { "skill": "SQL", "kind": "desired", "profile_level": 3, "required_level": 2, "via": "PostgreSQL", "relation": "implied" }
  ],
  "missing_skills": [
    { "skill": "GitLab", "kind": "desired", "required_level": 2, "current_level": 0, "gap": 2, "priority": "media", "similar_to": "GitHub", "credit": 0.75 }
  ],
  "conditions_fit": {
    "compatible": true,
    "distance_km": null,
    "checks": [
      { "condition": "availability_start", "result": "partial", "hard": false,
        "profile_value": "within_30_days", "job_value": "within_15_days", "details": {} }
    ],
    "salary_fit": {
      "result": "partial",
      "expected_monthly": { "min": 850000, "max": 850000 },
      "offered_monthly": { "min": 600000, "max": 800000 },
      "gap_percent": 5.88,
      "currency": "ARS"
    }
  }
}
```

- `checks` trae **las 12 condiciones**; el ejemplo muestra una sola.
- `matched_skills[].via`: la skill del perfil que cubre la pedida cuando no es la misma (`"SQL"` por `"PostgreSQL"`); `relation` es `exact`, `implied` o `equivalent` (§5.1).
- `missing_skills[].similar_to`: una herramienta similar que el candidato ya sabe y le facilita aprender la que falta (`"GitLab"` → `"GitHub"`); `credit` es la parte que ya suma. El ejemplo de `GitLab` es ilustrativo.
- `salary_fit.expected_monthly` llega en `null` cuando el estudiante ocultó su pretensión (`visibility: "hidden"`) y quien mira es la empresa. Lo mismo pasa con `offered_monthly` cuando la empresa lo ocultó y quien mira es el estudiante. Mostrá entonces sólo el resultado ("Dentro de lo esperado", "Por debajo de lo esperado").

#### 4.5 `RecommendationSettings` — configuración (pantalla de administración)

```json
{
  "student_jobs_limit": 5,
  "company_candidates_limit": 10,
  "limits": { "min": 1, "max": 20 },
  "updated_at": "2026-11-05T14:20:00Z",
  "updated_by": "33333333-3333-4333-8333-000000000001"
}
```

- `GET`: lo puede hacer un `admin` (y los servicios internos). Cualquier otro rol recibe **403**.
- `PATCH`: **sólo `admin`**. Body con uno o los dos campos, enteros entre `limits.min` y `limits.max`:

```json
{ "student_jobs_limit": 8 }
```

- Campos desconocidos, body vacío o valores fuera de rango → **422 `INVALID_INPUT`**.
- El cambio rige enseguida: para las vistas, para los rankings que usa n8n y para los pedidos de IA nuevos. Los pedidos que ya estaban en curso siguen con el número que tenían.
- `updated_by` es el `sub` del admin que hizo el cambio.
- Se guarda en PostgreSQL (schema `matching`, tabla `recommendation_settings`) y sobrevive a los reinicios. Los valores de `scoring_rules.yaml` sólo se cargan la primera vez, cuando todavía no hay configuración guardada. Sin `DATABASE_URL` (modo mock) queda en memoria.

Sugerencia de UI: un formulario con dos campos numéricos (`min`/`max` tomados de `limits`) y la leyenda "Última modificación: {updated_at}". Mostralo sólo si `role === 'admin'`.

---

### 5. Cómo se calcula el score de cada candidato respecto de la búsqueda

El score (0–100) lo calcula **sólo el motor de reglas** del matching-service, siempre de la misma forma, para cada par candidato–oferta. No interviene ningún LLM. Los pesos están en `services/matching-service/app/data/scoring_rules.yaml` (versión `rules_version`).

#### 5.1 Paso 0 — Diccionario de competencias

Antes de comparar, cada skill se pasa a minúsculas, sin acentos y a su clave del **diccionario de competencias** (`services/matching-service/app/data/skill_dictionary.json`, unas 150 skills). El diccionario tiene cuatro relaciones, de más fuerte a más débil:

| Relación | Qué significa | Ejemplos | Cuenta en el score |
|---|---|---|---|
| **Alias** (`exact`) | El mismo nombre escrito distinto, con errores comunes | `Postgres`, `Posgres`, `psql` → PostgreSQL · `ReactJS` → React · `Spring Boot` → Spring · `Metodologías ágiles` → agile | Completa |
| **Implica** (`implied`) | Saber una supone saber otra más general. Es transitiva y vale con el nivel de la que implica | PostgreSQL, MySQL, SQL Server ⇒ SQL · Next.js ⇒ React ⇒ JavaScript · Django ⇒ Python · GitHub ⇒ Git · Scrum ⇒ agile | Completa |
| **Equivalente** (`equivalent`) | Se usan una por otra | MySQL ↔ MariaDB · Docker ↔ Podman | Completa |
| **Similar** (`similar`) | Herramientas parecidas: saber una **facilita aprender** la otra | GitHub ~ GitLab ~ Bitbucket · PostgreSQL ~ MySQL ~ SQL Server · React ~ Vue ~ Angular · AWS ~ Azure ~ GCP · Power BI ~ Tableau · Jira ~ Trello · Excel ~ Google Sheets | Sólo `credit` (0,5 o 0,75 según el grupo). Sigue como faltante, con `similar_to` |

Reglas:
- **Obligatorias y deseables** suman 1 por cada skill cubierta (alias, implicada o equivalente) y el `credit` del grupo si sólo sabe una similar. `details.similar` cuenta estas últimas.
- **Niveles** compara sólo las cubiertas del todo, con el nivel de la skill del perfil que la cubre.
- **Excluyente**: una similar no la cubre (se aplica el tope).
- **Experiencia relevante**: una skill de `skills_used` también cubre las que implica o sus equivalentes.
- `implies` no es simétrica: saber SQL no implica PostgreSQL.

`GET /api/v1/matches/skills/dictionary` (cualquier usuario autenticado o servicio) devuelve el diccionario completo:
- `skills`: `{ key, name, category, aliases }`;
- `groups`: `{ kind: "equivalent" | "similar", label, credit, skills }`;
- `implies`: `{ "PostgreSQL": ["SQL"], … }`.

`POST /api/v1/matches/skills/resolve` normaliza hasta 50 nombres y, si se manda `profile_skills`, dice si el perfil ya cubre cada uno. Lo usa la herramienta MCP `resolver_skills` del agente.

```json
{
  "origin": "RULES",
  "dictionary_version": "1.0.0",
  "items": [
    {
      "input": "GitLab", "key": "gitlab", "name": "GitLab", "known": true, "category": "devops",
      "aliases": ["git lab"], "implies": ["Git"], "implied_by": [], "equivalents": [],
      "similar": [{ "skill": "GitHub", "credit": 0.75, "group": "Plataformas de Git" }, { "skill": "Bitbucket", "credit": 0.75, "group": "Plataformas de Git" }],
      "covered_by": { "relation": "similar", "credit": 0.75, "via": "GitHub", "full": false }
    }
  ]
}
```

Una skill que no está en el diccionario se compara por su texto normalizado (`known: false`). Para sumar skills, alias o grupos se edita el JSON, se sube su `version` y se corren los tests (UT-MATCH-13 valida que no haya alias repetidos ni claves desconocidas).

Cada requisito de la oferta tiene un **nivel mínimo (1–5)** y un **tipo**:
- `required` (obligatoria)
- `desired` (deseable)
- `excluding` (excluyente: obligatoria y además pone un tope al score; §5.3)

#### 5.2 Paso 1 — Siete criterios que suman 100

Lo técnico (60) y la experiencia (25) son lo que más pesa. Las condiciones laborales (modalidad, horario, ubicación, disponibilidad, etc.) suman poco (7): son negociables y no dicen nada de la capacidad del candidato.

| Criterio | Peso | Fórmula | Si la oferta no pide nada de esto |
|---|---|---|---|
| **Skills obligatorias** (`required_skills`) | 40 | `40 × (obligatorias + excluyentes que tiene ÷ total de obligatorias + excluyentes)`. Sólo importa si la tiene, no el nivel. | 40 |
| **Skills deseables** (`desired_skills`) | 10 | `10 × (deseables que tiene ÷ total de deseables)` | 10 |
| **Niveles** (`levels`) | 10 | Para cada skill pedida (de cualquier tipo) que el candidato **tiene**: `min(1, nivel del candidato ÷ nivel pedido)`. Se promedian y se multiplica por 10. Si no tiene ninguna, 0. | 10 |
| **Experiencia** (`experience`) | 25 | `25 × (0,6 × años + 0,4 × relevancia)`. **Años:** `min(1, años ÷ mínimo pedido)`; si la oferta no pide mínimo, `0,5 + 0,5 × min(1, años ÷ 1)` (no tener experiencia resta la mitad, no todo). **Relevancia:** competencias de la oferta que figuran en `skills_used` de la experiencia (con 3 ya es completa); experiencia sin competencias cargadas → 0,5; sin experiencia → 0. Los valores `1` año y `0,4` están en `experience` del YAML. | Ver "Años" |
| **Formación** (`education`) | 5 | Nivel superior al pedido → 5 · mismo nivel con estado igual o mejor → 5 · mismo nivel con estado peor (ej. "en curso" cuando piden "completo") → 2,5 · nivel inferior → 0. Niveles: secundario < terciario < universitario < posgrado. Estados: incompleto < en curso < completo. | 5 |
| **Idiomas** (`languages`) | 3 | Por cada idioma pedido: lo tiene con nivel igual o mayor → 1 · lo tiene con nivel menor → 0,5 · no lo tiene → 0. Se promedia y se multiplica por 3. Niveles: A1 < A2 < B1 < B2 < C1 < C2 < nativo. | 3 |
| **Condiciones** (`conditions`) | 7 | Promedio de las condiciones de `conditions_fit` con dato en los dos lados: coincide → 1 · parcial → 0,5 · no coincide → 0. Las `unknown` no cuentan. | 7 |

Cada criterio se redondea a 2 decimales; el score es la suma.

#### 5.3 Paso 2 — Regla excluyente

Si al candidato le falta **una skill `excluding`**, el score queda **topeado en 40** (`excluding_cap` en el YAML) y `excluding_cap_applied` viene en `true`.

> `excluding_cap_applied: true` quiere decir "le falta un excluyente", aunque la suma ya diera menos de 40. En la UI conviene mostrarlo siempre como alerta roja: **"No cumple un requisito excluyente"**.

#### 5.4 Ejemplos reales del pool de demo

**Búsqueda `job-004` — "Desarrollador/a Python Trainee (remoto)", Nube Austral S.A.**
- Skills: Python 2 (obligatoria) · Git 2 (obligatoria) · SQL 2 (deseable) · Testing 1 (deseable) · Docker 1 (deseable)
- Experiencia mínima 0 años · universitario en curso · inglés A2

En el pool de demo las experiencias no traen `skills_used`, así que la relevancia queda en 0,5 y la experiencia suma como mucho 20 de 25. Con `skills_used` cargado, quien usó en el trabajo las competencias de la oferta llega a 25.

**Ejemplo A — Carla Medina (`stu-014`) → 94,42**
Python 3 · Django 3 · PostgreSQL 3 · Docker 2 · Git 3 · Linux 3 · Testing 2 · inglés B1 · universitaria en curso · 1,5 años.

| Criterio | Cálculo | Puntos |
|---|---|---|
| Obligatorias | Python ✔ · Git ✔ → 2/2 × 40 | 40 |
| Deseables | SQL ✔ (por PostgreSQL, que implica SQL) · Testing ✔ · Docker ✔ → 3/3 × 10 | 10 |
| Niveles | Python 3/2→1 · Git 3/2→1 · SQL (PostgreSQL 3)/2→1 · Testing 2/1→1 · Docker 2/1→1 → promedio 1 × 10 | 10 |
| Experiencia | sin mínimo, 1,5 años → años 1 · sin `skills_used` → relevancia 0,5 → 25 × (0,6 + 0,2) | 20 |
| Formación | universitaria en curso = la pedida | 5 |
| Idiomas | B1 ≥ A2 | 3 |
| Condiciones | 10 coinciden y 2 parciales de 12 → 11/12 × 7 | 6,42 |
| **Total** | | **94,42** |

**Ejemplo B — Ignacio Castro (`stu-013`) → 86,66**
Java 4 · Spring 3 · SQL 3 · Git 3 · **Python 1** · inglés B2 · universitario en curso · 1 año.

| Criterio | Cálculo | Puntos |
|---|---|---|
| Obligatorias | Python ✔ (aunque con nivel bajo) · Git ✔ → 2/2 × 40 | 40 |
| Deseables | SQL ✔ · Testing ✘ · Docker ✘ → 1/3 × 10 | 3,33 |
| Niveles | Python 1/2→0,5 · Git 3/2→1 · SQL 3/2→1 → promedio 0,833 × 10 | 8,33 |
| Experiencia | como en A | 20 |
| Formación · Idiomas · Condiciones | completos | 5 + 3 + 7 |
| **Total** | | **86,66** |

> El nivel bajo de Python **no lo deja afuera**. Le resta en "Niveles" y aparece en `missing_skills` como brecha de nivel: `{ "skill": "Python", "kind": "required", "current_level": 1, "required_level": 2, "gap": 1, "priority": "media" }`.

**Ejemplo C — regla excluyente: Mateo Fernández (`stu-002`) en `job-003` "Ingeniero/a de Datos" → 40**
La oferta pide Python 4 (**excluyente**), SQL 4 y Docker 3 (obligatorias), Linux 3 (deseable), 2 años, terciario completo e inglés B2. Mateo tiene Docker 2, inglés C1, 2 años y universitario en curso; no tiene Python.

| Criterio | Cálculo | Puntos |
|---|---|---|
| Obligatorias | Python ✘ · SQL ✘ · Docker ✔ → 1/3 × 40 | 13,33 |
| Deseables | Linux ✘ → 0/1 | 0 |
| Niveles | Docker 2/3 → 0,667 × 10 | 6,67 |
| Experiencia | 2 / 2 años · relevancia 0,5 | 20 |
| Formación | universitario > terciario pedido | 5 |
| Idiomas | C1 ≥ B2 | 3 |
| Condiciones | 5 coinciden y 6 no, de 11 → 5/11 × 7 | 3,18 |
| Suma | | 51,18 |
| **Tope por excluyente** (falta Python) | | **40** |

#### 5.5 Condiciones laborales: poco peso y detalle aparte

Las **condiciones laborales** y el **sueldo** se detallan en `conditions_fit` y al score sólo aportan con el criterio `conditions` (7 de 100). Además sirven para:

1. **Filtrar sólo lo legal.** Si una condición dura (`hard: true`) da `mismatch`, el match es **incompatible** (`compatible: false`) y se excluye del ranking (`excluded_incompatible` cuenta cuántos quedaron afuera). Hoy son duras sólo la licencia/vehículo y la autorización para trabajar.
2. **Avisar.** El resto se muestra como alerta y el candidato sigue en el ranking: presencialidad, ubicación/traslado, modalidad horaria y horas, tipo de vínculo, turnos (incluido el choque con el horario de cursada), duración del contrato, disponibilidad de inicio, sueldo, viajes y requisitos académicos.

| `result` | Significado | Sugerencia de UI |
|---|---|---|
| `match` | Coincide | ✓ gris o verde suave |
| `partial` | Coincide en parte (ej. empieza más tarde, sueldo apenas por debajo, ciudad distinta en la misma provincia) | ⚠ ámbar |
| `mismatch` | No coincide | ✕ rojo (si `hard`, el ítem no aparece en la vista) |
| `unknown` | Falta el dato en algún lado; no penaliza | "Sin dato" + invitar a completar el perfil |

**Sueldo** (`salary_fit`): se pasan los dos sueldos a **mensual bruto**:
- Por hora → × horas semanales × 4,33.
- Por día → × 21.
- Anual → ÷ 13 (12 sueldos + aguinaldo).
- Neto → bruto: × 1,21.

Resultados posibles:
- `match`: el máximo ofrecido llega al mínimo pretendido.
- `partial`: no llega, pero la brecha es ≤ 10 % o alguno marcó que es negociable.
- `below_expectation`: la brecha supera ese margen.
- `unknown`: falta un dato, el sueldo es "a convenir" o las monedas son distintas y no hay tipo de cambio configurado.

`gap_percent` es cuánto le falta al ofrecido para llegar al pretendido.

#### 5.6 Orden del ranking

1. Compatibles primero (sólo importa si se piden incompatibles; las vistas del front ya los excluyen).
2. Score de mayor a menor.
3. Empate → por id, ascendente. Ejemplo: en `job-004` hay cuatro candidatos con 90 (`stu-001`, `stu-005`, `stu-007`, `stu-008`).

`missing_skills` viene ordenado por prioridad:
- `alta`: excluyente u obligatoria que no tiene.
- `media`: deseable que no tiene, o tiene una obligatoria con nivel menor al pedido.
- `baja`: tiene una deseable con nivel menor al pedido.

Dentro de la misma prioridad va primero la brecha más grande.

---

### 6. Textos sugeridos para la UI (valores de los enums)

| Campo | Valor → texto |
|---|---|
| `criterion` | `required_skills` Skills obligatorias · `desired_skills` Skills deseables · `levels` Nivel en las skills · `experience` Experiencia · `education` Formación · `languages` Idiomas · `conditions` Condiciones laborales |
| `kind` | `required` Obligatoria · `desired` Deseable · `excluding` Excluyente |
| `priority` | `alta` · `media` · `baja` (ya en español) |
| `condition` | `work_modality` Presencialidad · `location` Ubicación · `work_schedule` Horario · `shifts` Turnos · `employment_type` Tipo de contratación · `contract_duration` Duración · `availability_start` Disponibilidad · `salary` Sueldo · `travel` Viajes · `driver_license` Licencia de conducir · `work_authorization` Autorización para trabajar · `academic` Requisitos académicos |
| `work_modality` | `onsite` Presencial · `remote` Remoto · `hybrid` Híbrido |
| `work_schedule` | `full_time` Full time · `part_time` Part time · `hourly` Por horas · `flexible` Flexible |
| `employment_type` | `employee` Relación de dependencia · `freelance` Freelance · `internship` Pasantía · `trainee` Trainee |
| `availability_start` | `immediate` Inmediata · `within_15_days` En 15 días · `within_30_days` En 30 días · `to_agree` A convenir |
| `salary_fit.result` | `match` Dentro de lo esperado · `partial` Cerca de lo esperado · `below_expectation` Por debajo de lo esperado · `unknown` Sin dato para comparar |
| `next_steps[].type` (IA) | `apply` Postularte · `course` Curso · `project` Proyecto práctico · `profile_tip` Mejorá tu perfil |

Sugerencia para el `ScoreCard`: el score grande, una barra por criterio (`earned / weight`), las skills que coinciden en verde, las que faltan con su `priority`, y las alertas de condiciones debajo.

---

### 7. Tipos TypeScript sugeridos (`src/api/types/matching.ts`)

```ts
export type Priority = 'alta' | 'media' | 'baja';
export type RequirementKind = 'required' | 'desired' | 'excluding';
export type CheckResult = 'match' | 'partial' | 'mismatch' | 'unknown';
export type AiStatus = 'not_requested' | 'pending' | 'processing' | 'ready' | 'completed' | 'failed';

export interface ApiError { error: { code: string; message: string; details: Record<string, unknown> } }

export interface CriterionResult {
  criterion: 'required_skills' | 'desired_skills' | 'levels' | 'experience' | 'education' | 'languages' | 'conditions';
  weight: number;
  earned: number;
  details: Record<string, unknown>;
}

export interface MissingSkill { skill: string; kind: RequirementKind; required_level: number; current_level: number; gap: number; priority: Priority; similar_to: string | null; credit: number }
export interface MatchedSkill { skill: string; kind: RequirementKind; profile_level: number; required_level: number; via: string | null; relation: 'exact' | 'implied' | 'equivalent' }

export interface ConditionCheck {
  condition: string;
  result: CheckResult;
  hard: boolean;
  profile_value: unknown;
  job_value: unknown;
  details: Record<string, unknown>;
}

export interface SalaryFit {
  result: 'match' | 'partial' | 'below_expectation' | 'unknown';
  expected_monthly: { min: number; max: number } | null;
  offered_monthly: { min: number; max: number } | null;
  gap_percent: number | null;
  currency: string;
}

export interface Match {
  origin: 'RULES';
  engine_version: string;
  rules_version: string;
  computed_at: string;
  profile_id: string;
  job_id: string;
  score: number;
  excluding_cap_applied: boolean;
  breakdown: CriterionResult[];
  matched_skills: MatchedSkill[];
  missing_skills: MissingSkill[];
  conditions_fit: { compatible: boolean; distance_km: number | null; checks: ConditionCheck[]; salary_fit: SalaryFit | null };
}

export interface JobSnapshot {
  job_id: string; title: string; company_name: string; seniority: string;
  /** Desde matching 0.2.1: abre el perfil público con GET /api/v1/profiles/companies/{company_id}. */
  company_id: string;
  location: { city: string; province: string; country: string };
  requirements: Record<string, unknown>;
  work_conditions: Record<string, unknown>;
}

export interface CandidateSnapshot {
  profile_id: string; headline: string;
  location: { city: string; province: string; country: string };
  years_experience: number;
  skills: { name: string; level: number }[];
  languages: { name: string; level: string }[];
  education: { level: string; status: string; degree: string; field: string }[];
  academic_status: { career: string; current_year: number | null; progress_percent: number | null };
  target_roles: string[];
  work_conditions: Record<string, unknown>;
}

interface AiBlockBase {
  origin: 'AI';
  status: AiStatus;
  request_id: string;
  error: ApiError['error'] | null;
  summary: string;
  model: string;
  prompt_version: string;
  generated_at: string;
  disclaimer: string;
  verified: boolean;
}

export interface StudentAiContent {
  priority: Priority;
  fit_reasons: string[];
  watch_outs: string[];
  next_steps: { type: 'apply' | 'course' | 'project' | 'profile_tip'; skill: string; text: string; priority: Priority }[];
}

export interface CompanyAiContent {
  priority: Priority;
  justification: string;
  strengths: string[];
  gaps: string[];
  conditions_alerts: string[];
  interview_questions: string[];
}

export interface StudentRecommendationsView {
  profile_id: string;
  rule_based: { origin: 'RULES'; profile_id: string; engine_version: string; rules_version: string;
                evaluated: number; excluded_incompatible: number;
                items: { rank: number; job: JobSnapshot; match: Match }[] };
  ai_recommendations: AiBlockBase & { items: { job_id: string; content: StudentAiContent }[] };
}

export interface CompanyRecommendationsView {
  job_id: string;
  rule_based: { origin: 'RULES'; job_id: string; job: JobSnapshot; engine_version: string; rules_version: string;
                evaluated: number; excluded_incompatible: number;
                items: { rank: number; candidate: CandidateSnapshot; match: Match }[] };
  ai_recommendations: AiBlockBase & { items: { profile_id: string; content: CompanyAiContent }[] };
}

export interface RecommendationRequest {
  request_id: string; mode: 'student' | 'company'; subject_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  created_at: string; updated_at: string; error: ApiError['error'] | null;
  limit?: number; // sólo en la respuesta 202 del POST
}

export interface RecommendationSettings {
  student_jobs_limit: number;
  company_candidates_limit: number;
  limits: { min: number; max: number };
  updated_at: string;
  updated_by: string;
}
```

Los ítems de `ai_recommendations.items` traen además metadatos (`id`, `model`, `generated_at`, `items`, etc.). El front puede ignorarlos y usar sólo `job_id` / `profile_id` y `content`.

---

### 8. Limitaciones actuales (v0.1.0)

| Tema | Estado | Impacto en el front |
|---|---|---|
| Persistencia | Las recomendaciones de IA, los pedidos y la configuración del admin se guardan en PostgreSQL (schema `matching`); sólo en modo mock (sin `DATABASE_URL`) quedan en memoria | Sobreviven a los reinicios del contenedor |
| Datos | Perfiles y ofertas reales de profile-service y jobs-service (`MATCHING_USE_MOCKS=false`, default). El seed de demo suma `stu-001`…`stu-015` y `job-001`…`job-012`, con dueños ficticios | Un estudiante con perfil **completo** y buscable entra al ranking; una empresa ve los candidatos de sus búsquedas por `job_id`. Los perfiles en borrador no aparecen como candidatos de las empresas |
| Dueño del perfil | Los perfiles tienen que traer `user_id` y las ofertas, `company_id` (ver [`historico/estructura_comun_perfil_oferta_match.md`](historico/estructura_comun_perfil_oferta_match.md) §5 y §6) | Si un perfil no trae `user_id`, sólo lo ven `admin` y los servicios |
| Idiomas deseables | El criterio de idiomas cuenta un idioma `desired` igual que uno obligatorio | Un candidato sin un idioma deseable pierde puntos en "Idiomas" |
| Skills relacionadas | Diccionario curado a mano (§5.1); una skill que no está se compara por texto | Puede mostrar como faltante una skill con un nombre muy distinto que no esté en el diccionario |

## B. Endpoints internos y flujo con n8n

Sólo con `X-Service-Token` (por la red interna; el gateway lo borra). Un usuario recibe `403`.

| Método y ruta | Quién lo usa | Para qué |
|---|---|---|
| `POST /api/v1/matches` | mcp-tools (`compute_match`), n8n WF-03 | Calcula el match por reglas de un perfil y una oferta (`origin: "RULES"`) |
| `POST /api/v1/matches/missing-skills` | mcp-tools (`missing_skills`) | Competencias faltantes y brecha de nivel |
| `GET /api/v1/matches/students/{profile_id}/jobs` | mcp-tools (`rank_jobs_for_student`), n8n WF-03/WF-04 | Ofertas rankeadas por reglas para un estudiante |
| `POST /api/v1/matches/skills/resolve` | mcp-tools (`resolver_skills`) | Normaliza competencias y dice si el perfil las cubre (§5.1) |
| `GET /api/v1/matches/students/{profile_id}/skill-gaps` | n8n WF-06 (`mode=training`) | Qué competencias sumar o mejorar según las ofertas más parecidas (`SkillGaps`, §B.2) |
| `GET /api/v1/matches/jobs/{job_id}/candidates` | mcp-tools (`rank_candidates_for_job`), n8n WF-02 | Candidatos rankeados por reglas para una oferta (snapshots sin datos personales) |
| `POST /api/v1/matches/recommendations` | mcp-tools (`save_recommendation`) | Guarda una recomendación de IA (`origin: "AI"`) |
| `POST /api/v1/matches/recommendations/batch` | n8n WF-06 | Guarda el resultado completo de un pedido de análisis (`request_id`) |

### B.2 Qué sumar o mejorar, en general (`mode=training`)

La formación **no es por oferta**. Se calcula sobre el perfil y las ofertas activas **más parecidas** a él:

1. **Reglas (`SkillGaps`, `origin: "RULES"`).** matching-service toma las `training.similar_jobs` ofertas (10 por defecto) con mejor score para el estudiante, sin las incompatibles por requisitos legales. Junta las competencias que faltan o quedan cortas de nivel y las ordena:
   - `alta`: obligatoria o excluyente en al menos la mitad de esas ofertas;
   - `media`: obligatoria en alguna, o deseable en al menos la mitad;
   - `baja`: el resto.

   Devuelve como mucho `training.max_gaps` (8).
2. **IA (`training_advisor`).** Propone cursos del catálogo y consejos para sumar o mejorar esas competencias. Nunca toca el puntaje y **no pide portfolios, proyectos personales ni nada similar**.

- **Pedido:** `POST /api/v1/matches/recommendations/requests` con `{ "mode": "training", "profile_id": "..." }`. Si llega un `job_id`, se ignora.
  - Sólo el estudiante dueño del perfil, un admin o un servicio. Una empresa recibe `403`; un perfil ajeno, `404`.
  - Se sigue con el mismo polling de `GET /recommendations/requests/{request_id}`.
- **Vista:** `GET /api/v1/matches/recommendations/students/{profile_id}/training` (mismos permisos). Reemplaza a la ruta anterior por oferta (`/training/{job_id}`), que ya no existe.
- **Interno:** `GET /api/v1/matches/students/{profile_id}/skill-gaps` (sólo `X-Service-Token`) devuelve el bloque `rule_based` solo; lo usa WF-06.

```json
{
  "profile_id": "stu-001",
  "rule_based": {
    "origin": "RULES",
    "profile_id": "stu-001",
    "engine_version": "2.0.0",
    "rules_version": "2.0.0",
    "computed_at": "2026-11-10T21:00:00Z",
    "evaluated": 12,
    "similar_jobs": [
      { "job_id": "job-001", "title": "Desarrollador/a Backend Python Jr.", "score": 85.0 },
      { "job_id": "job-002", "title": "Desarrollador/a Frontend React + TypeScript", "score": 58.33 }
    ],
    "skill_gaps": [
      { "skill": "React", "status": "missing", "jobs_count": 1, "share": 0.5, "required_in": 1, "current_level": 0, "required_level": 3, "priority": "alta" },
      { "skill": "Docker", "status": "improve", "jobs_count": 1, "share": 0.5, "required_in": 0, "current_level": 1, "required_level": 3, "priority": "media", "similar_to": null },
      { "skill": "GitLab", "status": "missing", "jobs_count": 1, "share": 0.5, "required_in": 1, "current_level": 0, "required_level": 2, "priority": "alta", "similar_to": "GitHub" }
    ]
  },
  "ai_recommendations": {
    "origin": "AI",
    "status": "ready",
    "request_id": "req-…",
    "model": "nvidia/…",
    "prompt_version": "2.0.0",
    "generated_at": "2026-11-10T21:00:00Z",
    "disclaimer": "Recomendación orientativa generada por IA. El puntaje y el ranking provienen exclusivamente del motor de reglas.",
    "summary": "Las ofertas más parecidas a tu perfil piden React y Docker…",
    "items": [
      { "type": "course", "skill": "React", "text": "Hacé el curso …", "priority": "alta" },
      { "type": "skill", "skill": "Docker", "text": "Practicá … para pasar de nivel 1 a 3", "priority": "media" },
      { "type": "profile_tip", "skill": "Git", "text": "Si ya lo usás, cargalo en tu experiencia …", "priority": "baja" }
    ]
  }
}
```

- `status` (`skill_gaps`): `missing` si no la tiene; `improve` si la tiene con nivel menor al pedido.
- `share`: parte de las ofertas parecidas en las que falta (0–1). `required_in`: en cuántas es obligatoria o excluyente.
- `similar_to`: herramienta similar que ya sabe y le facilita aprenderla (§5.1); la IA la usa para decir "como ya usás GitHub, GitLab te va a resultar fácil". Las skills se agrupan por su clave del diccionario (`Postgres` y `PostgreSQL` cuentan como una).
- `status` (IA): `not_requested` · `pending` · `processing` · `ready` · `failed`, igual que en las otras vistas (parte A §4.1).
- `items`: hasta 5, ordenados por prioridad. `type` es `course` (curso del catálogo), `skill` (competencia para sumar o mejorar, con cómo practicarla) o `profile_tip` (cómo mostrar mejor algo que ya tiene). Nunca traen `score`. Las recomendaciones viejas pueden traer `type: "project"`; el front las muestra como `skill`.
- La formación se guarda aparte (`mode=training`, una sola por estudiante): no aparece en "Ofertas para vos".

### B.1 Pedido de análisis con IA (WF-06)

1. El front llama a `POST /api/v1/matches/recommendations/requests` (parte A §3.1). matching-service crea el pedido (`pending`) y llama al webhook de n8n:
   `POST {N8N_WEBHOOK_BASE_URL}/recommendations` · `X-Service-Token` · cuerpo `{ "mode": "student" | "company" | "training", "request_id": "...", "limit": N, "profile_id" | "job_id": "..." }` (`training` lleva sólo `profile_id`; `limit` es la cantidad máxima de ítems, 5). `limit` es la cantidad que configuró el admin (`/settings`), o menos si el pedido trae un `limit` menor.
2. WF-06 arma el ranking por reglas con mcp-tools (en `training`, pide `GET /students/{profile_id}/skill-gaps`), ejecuta al agente y guarda el resultado con `POST /recommendations/batch`.
3. El front consulta `GET /recommendations/requests/{request_id}` hasta `completed` o `failed` y lee la vista combinada (`GET /recommendations/{students|jobs}/{id}`).
4. matching-service descarta cualquier `score` o `rank` que venga en el contenido de IA: el valor mostrado sale siempre del motor.

Detalle del lado de n8n en [`n8n.md`](n8n.md).
