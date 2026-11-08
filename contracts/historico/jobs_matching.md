# Contrato matching-service / mcp-tools ↔ jobs-service

> **Para:** quien mantiene `matching-service` y `mcp-tools` (Integrante 3 / Integrante 1) y los agentes de n8n.
> **Servicio:** `jobs-service` v0.1.0.
> **Fuente de verdad:** [`jobs_service.openapi.json`](jobs_service.openapi.json) y [`estructura_comun_perfil_oferta_match.md`](estructura_comun_perfil_oferta_match.md).
> **Objetivo:** que `HttpJobSource`, `HttpJobsGateway` y `JobMapper` sigan funcionando sin cambios cuando se apague el modo mock.

---

## 1. Endpoints que consume matching/mcp

| Consumidor | Llamada | Auth |
|---|---|---|
| `matching-service` (`HttpJobSource`) | `GET /api/v1/jobs?status=active&limit=200` | `X-Service-Token` |
| `matching-service` (`HttpJobSource`) | `GET /api/v1/jobs/{job_id}` | `X-Service-Token` |
| `mcp-tools` (`HttpJobsGateway`) | `GET /api/v1/jobs?status=active&limit=N` | `X-Service-Token` |
| `mcp-tools` (`HttpJobsGateway`) | `GET /api/v1/jobs/{job_id}` | `X-Service-Token` |
| n8n / matching | `GET /api/v1/jobs?status=active&limit=200` | `X-Service-Token` |

- **No** se usa Bearer para servicios.
- El gateway borra `X-Service-Token` en peticiones externas; las llamadas internas van directo a `http://jobs-service:8000`.
- No hace falta cambiar `HttpJobSource` ni `HttpJobsGateway`: ya esperan estas rutas y el formato `{"items": [...]}`.

---

## 2. Listado

`GET /api/v1/jobs?status=active&limit=200`

- `status=active` es el único estado que debe usar matching para recomendar.
- `limit` es un alias de `size`; máximo 200 (matching usa `max_pool: 200`).
- También se acepta `page`/`size` para el front. matching puede seguir mandando `limit`.
- Respuesta:

```json
{
  "items": [ { "...": "JobOpportunity completa" } ],
  "total": 12,
  "page": 1,
  "size": 200,
  "pages": 1
}
```

- `items` trae **objetos completos**, no summaries. `HttpJobSource.list_active_jobs` filtra por `status` y corta a `limit`; no necesita más.
- Orden: `published_at DESC`, `id ASC`.
- Las ofertas `closed` no se devuelven con `status=active`.
- Las ofertas de **empresas dadas de baja** no aparecen nunca (ni con `status=all`) y su detalle da `404`: ver §11.
- El service token puede pedir `status=closed` o `status=all` si necesita auditar; matching no lo hace.

---

## 3. Detalle

`GET /api/v1/jobs/{job_id}`

- Devuelve `JobOpportunity` completa.
- Oferta inexistente → `404` con `{"error": {...}}`.
- Oferta cerrada → visible para el service token (matching puede recalcular un match viejo).
- El `job_id` es el `id` de la oferta (ej. `job-001`). Es el mismo que usa `Match.job_id`.

---

## 4. Campos que espera `JobMapper`

`services/matching-service/app/application/mappers.py` lee:

| Campo en jobs-service | Uso en matching |
|---|---|
| `id` | `JobOpportunity.id` |
| `company_id` | `JobOpportunity.company_id` |
| `company_snapshot.name` | `JobOpportunity.company_name` |
| `status` | `JobOpportunity.status` |
| `seniority` | `JobOpportunity.seniority` |
| `location.country/province/city` | `JobOpportunity.location` |
| `work_conditions.work_schedule` | `WorkConditions.work_schedule` |
| `work_conditions.work_modality` | `WorkConditions.work_modality` |
| `work_conditions.hybrid_onsite_days` | `WorkConditions.hybrid_onsite_days` |
| `work_conditions.employment_type` | `WorkConditions.employment_type` |
| `work_conditions.contract_duration` | `WorkConditions.contract_duration` |
| `work_conditions.weekly_hours.min/max` | `WorkConditions.weekly_hours` |
| `work_conditions.shifts` | `WorkConditions.shifts` |
| `work_conditions.availability_start` | `WorkConditions.availability_start` |
| `work_conditions.salary` | `WorkConditions.salary` |
| `work_conditions.relocation_support` | `WorkConditions.relocation_support` |
| `work_conditions.travel_availability` | `WorkConditions.travel_availability` |
| `work_conditions.driver_license` | `WorkConditions.driver_license` |
| `work_conditions.own_vehicle` | `WorkConditions.own_vehicle` |
| `work_conditions.work_authorization` | `WorkConditions.work_authorization` |
| `requirements.skills[].name` | `JobOpportunity.skills` |
| `requirements.skills[].normalized` | Normalización (si falta, matching normaliza `name`) |
| `requirements.skills[].level` | Nivel pedido |
| `requirements.skills[].kind` | `required / desired / excluding` |
| `requirements.languages[].name/normalized/level/kind` | `JobOpportunity.languages` |
| `requirements.education[].level/status/degree/field/kind` | `JobOpportunity.education` |
| `requirements.experience.min_years/area/kind` | `JobOpportunity.experience` |
| `requirements.academic.min_progress_percent/careers/min_current_year` | `JobOpportunity.academic` |

### Garantías del contrato

1. `company_snapshot.name` siempre está presente y no vacío (jobs-service lo valida al crear y al cargar el seed).
2. `requirements.skills` tiene al menos una `required`.
3. `level` de skill siempre está entre 1 y 5.
4. `kind` siempre es `required`, `desired` o `excluding`.
5. Los enums respetan `estructura_comun_perfil_oferta_match.md` §3.
6. `requirements.experience` está presente como campo (objeto o `null`; matching lo trata como un mínimo de 0 años).
7. `requirements.languages` y `requirements.education` existen (pueden ser `[]`).
8. `version` se incrementa en cada edición, cierre o reapertura.
9. `salary` viaja completo con service token, incluso si `visibility` es `on_match` o `hidden`.
10. `company_id` es el `sub` de la empresa en auth-service; para el seed son IDs ficticios.

---

## 5. Sueldo y visibilidad

- Para **service token**, jobs-service **no enmascara** el sueldo. matching recibe `salary` completo y aplica su propia regla de `visibility` en `SalaryComparator`.
- Para usuarios (`student`/`company`), jobs-service devuelve `salary: null` si `visibility` es `on_match` o `hidden` y el usuario no es la empresa dueña.
- Si `salary.to_agree = true`, `min`/`max` pueden venir `null`; matching ya lo trata como `unknown`.
- `salary.currency` y `salary.period` vienen cuando hay monto.

---

## 6. Ejemplo de oferta (job-004 del seed)

```json
{
  "id": "job-004",
  "company_id": "22222222-2222-4222-8222-000000000004",
  "company_snapshot": {
    "name": "Nube Austral S.A.",
    "industry": "software",
    "size": "51-200",
    "logo_url": null
  },
  "status": "active",
  "title": "Desarrollador/a Python Trainee (remoto)",
  "description": "Primer empleo en desarrollo Python: scripts, APIs internas y tests, con mentoría.",
  "responsibilities": [],
  "area": "software",
  "seniority": "trainee",
  "vacancies": 1,
  "location": {
    "country": "AR",
    "province": "CABA",
    "city": "Buenos Aires",
    "postal_code": null,
    "zone": null
  },
  "work_conditions": {
    "work_schedule": ["part_time", "full_time"],
    "work_modality": ["remote"],
    "hybrid_onsite_days": null,
    "employment_type": ["employee", "internship"],
    "contract_duration": ["permanent"],
    "weekly_hours": { "min": 20, "max": 40 },
    "shifts": ["morning", "afternoon"],
    "availability_start": "within_15_days",
    "salary": {
      "min": 600000,
      "max": 800000,
      "currency": "ARS",
      "period": "month",
      "gross": true,
      "payment_mode": null,
      "negotiable": false,
      "adjustment": null,
      "variable_compensation": [],
      "visibility": "public",
      "to_agree": false,
      "notes": null
    },
    "relocation_support": false,
    "travel_availability": "none",
    "driver_license": [],
    "own_vehicle": null,
    "own_equipment": null,
    "invoicing_status": null,
    "work_authorization": [],
    "timezone": null,
    "timezone_overlap_hours": null
  },
  "requirements": {
    "skills": [
      { "name": "Python", "normalized": "python", "level": 2, "kind": "required", "years": null, "category": null },
      { "name": "Git", "normalized": "git", "level": 2, "kind": "required", "years": null, "category": null },
      { "name": "SQL", "normalized": "sql", "level": 2, "kind": "desired", "years": null, "category": null },
      { "name": "Testing", "normalized": "testing", "level": 1, "kind": "desired", "years": null, "category": null },
      { "name": "Docker", "normalized": "docker", "level": 1, "kind": "desired", "years": null, "category": null }
    ],
    "languages": [
      { "name": "Inglés", "normalized": "ingles", "level": "A2", "kind": "desired", "certification": null }
    ],
    "education": [
      {
        "institution": null,
        "degree": null,
        "field": null,
        "level": "university",
        "status": "in_progress",
        "progress_percent": null,
        "gpa": null,
        "kind": "required"
      }
    ],
    "experience": { "min_years": 0, "area": "desarrollo", "kind": "required" },
    "certifications": [],
    "academic": { "min_progress_percent": 30, "careers": [], "min_current_year": null }
  },
  "benefits": ["mentoría", "días de estudio", "equipo provisto"],
  "created_at": "2026-11-01T12:03:00Z",
  "updated_at": "2026-11-01T12:03:00Z",
  "published_at": "2026-11-01T12:03:00Z",
  "expires_at": null,
  "version": 1
}
```

---

## 7. Seed de demo

- `job-001` a `job-012`, copiados de `services/matching-service/app/data/mock/jobs.json` y normalizados al contrato común.
- Conservan `id` y `company_id` ficticios para que matching pueda seguir usando sus matches de demo.
- Se cargan al arrancar jobs-service si `JOBS_SEED_DEMO=true` y la tabla `jobs` está vacía.
- Si el seed no cumple las reglas, el servicio falla al arrancar (para detectar inconsistencias antes de la demo).

---

## 8. Integración con matching

`matching-service` usa jobs-service real por defecto (`docker-compose.yml`):

```env
MATCHING_USE_MOCKS=false   # true = pool ficticio de app/data/mock
MCP_USE_MOCKS=false        # mcp-tools: tiene que coincidir (WF-06 rankea por MCP)
JOBS_SERVICE_URL=http://jobs-service:8000
SERVICE_TOKEN=...
```

`HttpJobSource` ya hace:

```python
GET /api/v1/jobs?status=active&limit={limit}
GET /api/v1/jobs/{job_id}
```

con `X-Service-Token` y `items_of(data)`. No hace falta tocar código de matching; sólo verificar que el listado traiga los 12 jobs y que `JobMapper` los mapee.

### Prueba manual sugerida

```bash
curl -H "X-Service-Token: $SERVICE_TOKEN" \
  "http://localhost:8000/api/v1/jobs?status=active&limit=200" | jq '.total'

curl -H "X-Service-Token: $SERVICE_TOKEN" \
  "http://localhost:8000/api/v1/jobs/job-004" | jq '.requirements.skills'
```

Luego, desde la red interna:

```bash
curl -H "X-Service-Token: $SERVICE_TOKEN" \
  "http://localhost:8000/api/v1/matches/students/stu-001/jobs?limit=5"
```

---

## 9. Qué **no** cambia

- matching sigue siendo el único que calcula el score (`origin=RULES`).
- matching sigue aplicando `SalaryComparator` y `conditions_fit`.
- jobs-service no llama a matching ni a n8n para calcular nada; sólo emite `job.created`.
- mcp-tools sigue usando `get_job` y `list_active_jobs` como hasta ahora.
- El modo mock sigue disponible para tests y para la demo si jobs-service no está levantado.

---

## 10. Checklist de integración

- [ ] `GET /api/v1/jobs?status=active&limit=200` con `X-Service-Token` devuelve `total: 12`.
- [ ] Cada item trae `company_snapshot.name` y `requirements.skills`; `requirements.experience` va como objeto o `null`.
- [ ] `JobMapper.to_domain` mapea los 12 jobs sin excepciones.
- [ ] `GET /api/v1/jobs/job-004` devuelve el detalle completo.
- [ ] Una oferta cerrada no aparece en `status=active`.
- [x] Con `MATCHING_USE_MOCKS=false` (default), el ranking de matching usa los jobs reales.
- [x] `mcp-tools` con `MCP_USE_MOCKS=false` (default) obtiene los mismos jobs: `rank_jobs_for_student` y `rank_candidates_for_job` devuelven el mismo ranking que matching por REST, con ofertas y perfiles reales (UUID / `prof-…`).
- [ ] El sueldo llega completo al service token, aunque `visibility` sea `on_match`.

---

## 11. Eventos de cuenta (auth-service → jobs-service)

`POST http://jobs-service:8000/api/v1/jobs/internal/account-events` · sólo `X-Service-Token` (un usuario recibe `403`; por el gateway no llega porque se borra el header). Cuerpo y entrega en [`account_events.md`](account_events.md). Responde `200` con `{ "event", "user_id", "result", "archived_jobs" }`.

| Evento | Qué hace jobs-service | `result` |
|---|---|---|
| `account.deleted` | Anota la baja en `jobs.deleted_accounts` y mueve **todas** las ofertas de la empresa (activas y cerradas) a `jobs.jobs_deleted` (auditoría). Desde ahí no salen en `GET /jobs`, en el detalle, en `/companies/me/searches` ni en el matching, y el JWT que todavía no venció recibe `401 ACCOUNT_DELETED`. El seed de demo no las vuelve a cargar | `archived` (o `registered` si no tenía ofertas, p. ej. un estudiante) |
| `account.updated` | Nada: el `company_snapshot` se arma al crear o editar una oferta | `ignored` |
| Repetido o de un tipo desconocido | Nada (idempotente) | `ignored` |

