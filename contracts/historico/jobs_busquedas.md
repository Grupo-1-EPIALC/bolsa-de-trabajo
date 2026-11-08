# Contrato de búsquedas ↔ consumidores · jobs-service

> **Para:** frontend (Integrante 4), matching-service y n8n (Integrante 3), auth-service (Integrante 1) y sus asistentes (`frontend-agent`, `matching-agent`, `n8n-agent`, `auth-agent`).
> **Servicio:** `jobs-service` v0.1.0 · implementa RF-11, RF-12, HU-11 y HU-12 del Plan MVP.
> **Fuentes de verdad:** [`jobs_service.openapi.json`](jobs_service.openapi.json) (contrato completo), [`estructura_comun_perfil_oferta_match.md`](estructura_comun_perfil_oferta_match.md) (estructura de datos), [`jobs_frontend.md`](jobs_frontend.md) (detalle para el front) y [`jobs_matching.md`](jobs_matching.md) (detalle para matching).
> **Alcance de esta entrega:** alta, edición, cierre/reapertura y consulta de búsquedas de empresas. **No cubre** auth-service, profile-service, matching-service, mcp-tools, n8n ni el gateway: de ellos sólo se documenta lo que búsquedas **consume o emite** (§8). Tampoco incluye postulaciones, pasantías ni analíticas.
> Los ejemplos usan los datos ficticios del seed (`services/jobs-service/app/infrastructure/data/jobs_seed.json`).

---

## 1. Qué expone jobs-service

| Pantalla / acción | Método y ruta | Respuesta |
|---|---|---|
| "Ver todas las ofertas" (estudiante o empresa) | `GET /api/v1/jobs?status=active&page=1&size=10` | `JobList` |
| "Mis búsquedas" (activas) | `GET /api/v1/companies/me/searches` | `JobList` |
| "Mis búsquedas" filtradas por estado | `GET /api/v1/companies/me/searches?status=active\|closed\|all` | `JobList` |
| Detalle de una oferta | `GET /api/v1/jobs/{job_id}` | `JobOpportunity` |
| "Nueva búsqueda" | `POST /api/v1/jobs` | `201` + `JobOpportunity` |
| "Editar búsqueda" | `PATCH /api/v1/jobs/{job_id}` | `200` + `JobOpportunity` |
| "Cerrar búsqueda" | `DELETE /api/v1/jobs/{job_id}` | `204` sin body |
| "Reabrir búsqueda" | `PATCH /api/v1/jobs/{job_id}` con `{"status":"active"}` | `200` + `JobOpportunity` |
| Health (infra) | `GET /health` | `{"status":"ok","service":"jobs-service","version":"0.1.0"}` |

- **Base:** same-origin detrás del gateway: `/api/v1/jobs` y `/api/v1/companies/me/searches`. En desarrollo se puede pegar directo a `http://localhost:8000`.
- **Formato:** JSON UTF-8. Los errores usan el formato común `{"error": {"code", "message", "details"}}` (§9).

Reglas transversales:

1. **El cliente nunca manda** `company_id` ni `company_snapshot` (salen del JWT y de auth-service), ni `status` (salvo la reapertura), `version` ni timestamps. El schema usa `extra="forbid"`: si aparecen, responde `422`.
2. `company_id` **siempre** es el `sub` del JWT de la empresa. Ningún body puede cambiarlo.
3. Sólo la empresa **dueña** edita o cierra; un recurso ajeno responde `403` (UT-JOBS-02).
4. Cada edición, cierre o reapertura incrementa `version`. La escritura se guarda sólo si la `version` leída sigue siendo la guardada; si otra escritura se adelantó, responde `409 CONFLICT` (§5).

---

## 2. Acceso, autenticación y roles

- **Autenticación:** el mismo `access_token` que devuelve auth-service (`POST /api/v1/auth/token`), en `Authorization: Bearer <access_token>`. Usá el cliente único `src/api/client.ts`, con su interceptor y el refresh automático (el access token dura 15 minutos).
  - jobs-service valida el JWT por su cuenta: firma RS256 con la clave pública del JWKS de auth-service (`/api/v1/auth/.well-known/jwks.json`), `iss = bolsa-auth`, `aud = bolsa-api`, `exp`, `sub` y `role` ∈ `student | company | admin`. No llama a auth-service para validar cada request.
  - El token interno de servicio (`X-Service-Token`) es sólo para matching-service, mcp-tools y n8n. El gateway lo borra en las peticiones que vienen de afuera y **no se acepta como Bearer**.
- **Qué puede hacer cada rol** (el dueño se compara con el `sub` del JWT):

| Rol | Puede | Si pide algo ajeno o inválido |
|---|---|---|
| `student` | Listar y ver ofertas `active` (con el sueldo enmascarado según §7) | Oferta `closed` → **404**. Crear/editar/cerrar → **403** |
| `company` | Listar y ver ofertas `active`; crear búsquedas; editar, cerrar y reabrir las propias; ver su historial en `/companies/me/searches` | Oferta de otra empresa → **403** para editar/cerrar y **404** para verla si está `closed` |
| `admin` | Todo, incluido listar `closed` y `all` | — |
| `X-Service-Token` | Listar `active`, `closed` o `all` y ver el sueldo completo | Crear, editar o cerrar → **403** |

---

## 3. Listado y paginación

### `GET /api/v1/jobs`

| Param | Valores | Default | Notas |
|---|---|---|---|
| `status` | `active` \| `closed` \| `all` | `active` | `closed`/`all` sólo para `admin` o service-token; para el resto → `403` |
| `page` | 1–1.000.000 | `1` | si `page > pages`, `items` viene `[]` y `total` conserva el total real |
| `size` | 1–200 | `5` | |
| `limit` | 1–200 | — | alias de `size` para matching-service y mcp-tools; si viene, **gana** sobre `size` |

Respuesta `200`:

```json
{
  "items": [ /* JobOpportunity */ ],
  "total": 12,
  "page": 1,
  "size": 5,
  "pages": 3
}
```

- `pages = ceil(total / size)`.
- Orden: `published_at` descendente, con `id` como desempate. Es estable entre páginas.

### `GET /api/v1/companies/me/searches`

- Devuelve **sólo las búsquedas de la empresa autenticada**, con el sueldo completo.
- Mismo esquema de paginación que el listado público. Default `status=active`; `closed` y `all` muestran el historial.

---

## 4. Crear una búsqueda

### Request

`PATCH` y `POST` comparten los mismos bloques; acá va el ejemplo completo de creación:

```json
{
  "title": "Desarrollador/a Backend Python Jr.",
  "description": "Desarrollo de microservicios REST con Python, FastAPI y PostgreSQL.",
  "seniority": "junior",
  "vacancies": 1,
  "area": "desarrollo backend",
  "responsibilities": ["Implementar endpoints REST"],
  "location": { "country": "AR", "province": "CABA", "city": "Buenos Aires" },
  "work_conditions": {
    "work_schedule": ["full_time"],
    "work_modality": ["hybrid"],
    "hybrid_onsite_days": 2,
    "weekly_hours": { "min": 30, "max": 40 },
    "salary": {
      "min": 800000,
      "max": 1000000,
      "currency": "ARS",
      "period": "month",
      "visibility": "public"
    }
  },
  "requirements": {
    "skills": [
      { "name": "Python", "level": 3, "kind": "required" },
      { "name": "SQL", "level": 2, "kind": "desired" },
      { "name": "Docker", "level": 2, "kind": "excluding" }
    ],
    "languages": [ { "name": "Inglés", "level": "B1", "kind": "desired" } ],
    "education": [ { "level": "university", "status": "in_progress", "kind": "desired" } ],
    "experience": { "min_years": 1, "area": "desarrollo backend", "kind": "required" },
    "certifications": [],
    "academic": null
  },
  "benefits": ["Seguro de salud"],
  "expires_at": "2026-12-31T23:59:59Z"
}
```

### Reglas de validación

Requeridos: `title`, `description`, `seniority`, `location` y `requirements` (con `skills` no vacío).
Todo lo demás es opcional. Si una regla falla, responde `422 INVALID_INPUT` con `details.field`.

| Campo | Regla |
|---|---|
| `title` | obligatorio, 1–200 caracteres |
| `description` | obligatorio, 1–20.000 caracteres |
| `vacancies` | 1–1000 (default `1`) |
| `requirements.skills` | al menos una skill y **al menos una con `kind: "required"`** (UT-JOBS-01) |
| `skills[].level` | 1–5 · `skills[].years` ≥ 0 |
| `languages[].name/level` | nombre ≤ 80 · nivel `A1…C2, native` |
| `education[]` | `level` y `status` del enum común · `progress_percent` 0–100 |
| `experience.min_years` | 0–60 · `kind` del enum común |
| `location.country` | ISO 3166-1 alfa-2 (ej. `AR`) |
| `work_conditions.weekly_hours` | 0–168 y `min ≤ max` |
| `work_conditions.salary` | `min`, `max` ≥ 0 · con monto, `currency` + `period` obligatorios · `min ≤ max` |
| `expires_at` | fecha futura (se valida al crear y al editar) |

### Response `201`

`201 Created` con el `JobOpportunity` completo (§6): la oferta nace `active`, `version = 1`,
`published_at = now` y `company_snapshot` tomado de auth-service.

---

## 5. Editar, cerrar y reabrir

### Editar — `PATCH /api/v1/jobs/{job_id}`

- **PATCH reemplaza bloques completos.** Si mandás `requirements`, mandá todas sus listas
  (`skills`, `languages`, `education`, `certifications`); no hay merge profundo.
- Campos modificables: `title`, `description`, `responsibilities`, `area`, `seniority`,
  `vacancies`, `location`, `work_conditions`, `requirements`, `benefits`, `expires_at`.
  Cualquier otro campo (incluidos los server-side) → `422`.
- Body vacío o sin campos → `422`.
- `work_conditions: null` y `expires_at: null` limpian el bloque / la fecha.
- Responde `200` con el `JobOpportunity` actualizado y `version` incrementada.
- **Lock optimista:** si otra persona editó la oferta entre que la leíste y guardaste,
  la escritura no pisa la nueva versión; responde `409 CONFLICT` y la UI debe releer la
  oferta (`GET`) y volver a aplicar el cambio.

### Cerrar — `DELETE /api/v1/jobs/{job_id}`

- Cierra la oferta: `204 No Content` (sin body). **No se borra físicamente**: queda
  `status="closed"`, invisible para terceros (detalle → `404`) y visible para la dueña en
  `/companies/me/searches?status=closed`.
- Cerrar una oferta ya cerrada es idempotente (`204`).

### Reabrir — `PATCH /api/v1/jobs/{job_id}` con `{"status":"active"}`

- Sólo funciona si estaba `closed`: la pasa a `active`, actualiza `published_at = now` y suma
  `version`. Reabrir una que ya estaba activa es idempotente (`200` sin cambios).
- `{"status":"closed"}` por PATCH → `422`: para cerrar se usa `DELETE`.

---

## 6. `JobOpportunity`

```json
{
  "id": "job-001",
  "company_id": "22222222-2222-4222-8222-000000000001",
  "company_snapshot": {
    "name": "PampaTech S.A.",
    "industry": "software",
    "size": "51-200",
    "logo_url": null
  },
  "status": "active",
  "title": "Desarrollador/a Backend Python Jr.",
  "description": "…",
  "responsibilities": [],
  "area": "desarrollo backend",
  "seniority": "junior",
  "vacancies": 1,
  "location": {
    "country": "AR",
    "province": "CABA",
    "city": "Buenos Aires",
    "postal_code": null,
    "zone": null
  },
  "work_conditions": { "…": "ver §4" },
  "requirements": { "…": "ver §4" },
  "benefits": [],
  "created_at": "2026-11-05T14:00:00Z",
  "updated_at": "2026-11-05T14:00:00Z",
  "published_at": "2026-11-05T14:00:00Z",
  "expires_at": null,
  "version": 1
}
```

Garantías hacia los consumidores (matching, front y n8n):

1. `company_snapshot.name` siempre está presente y no vacío (se valida al crear y en el seed).
2. `requirements.skills` tiene al menos una `required`; `level` siempre está entre 1 y 5.
3. `kind` siempre es `required`, `desired` o `excluding`.
4. `status` es `active` o `closed`; `version` ≥ 1 y se incrementa en cada escritura.
5. Los enums respetan `estructura_comun_perfil_oferta_match.md` §3.
6. `requirements.experience` está presente como campo: objeto o `null` (matching lo trata como un mínimo de 0 años).
7. `requirements.languages` y `requirements.education` existen (pueden ser `[]`).
8. Las listas (`responsibilities`, `benefits`, `skills`, …) **siempre van como array**, aunque estén vacías; los escalares ausentes viajan `null`.
9. `salary` viaja completo con service-token, incluso si `visibility` es `on_match` o `hidden` (§7).

---

## 7. Sueldo y privacidad

jobs-service enmascara el sueldo a terceros según `salary.visibility`; matching-service lo recibe
completo con `X-Service-Token` y aplica su propio chequeo (`salary_fit`).

| `salary.visibility` | Dueña / `admin` / service-token | Estudiante u otra empresa |
|---|---|---|
| `public` | Completo | Completo |
| `on_match` | Completo | `work_conditions.salary = null` |
| `hidden` | Completo | `work_conditions.salary = null` |

- `salary.to_agree = true` **no** anula el objeto: viaja con `min`/`max` en `null`. La UI debe
  distinguir: `salary === null` → "Sueldo no publicado"; `salary.to_agree` → "A convenir".
- En `GET /companies/me/searches` la empresa ve siempre el sueldo completo de sus búsquedas.
- `on_match` se trata como oculto para terceros hasta que exista la integración de postulaciones;
  queda documentado como limitación de `v0.1.0` (§11).

---

## 8. Integración por consumidor

### 8.1 Auth-service (Integrante 1)

Es la única dependencia externa de búsquedas. jobs-service espera:

| Dependencia | Cuándo | Qué espera |
|---|---|---|
| `GET /api/v1/auth/.well-known/jwks.json` | al validar cualquier JWT (caché 600 s) | claves públicas RS256 con `kid` |
| `GET /api/v1/auth/me` con el Bearer del usuario | al **crear** una oferta | `{ "id": …, "company": { "legal_name", "cuit", "activity" } }` |

- `legal_name` → `company_snapshot.name` (obligatorio; si falta o viene vacío, sale `422`).
- `activity` → `company_snapshot.industry`. `size` y `logo_url` quedan `null` (auth-service todavía no los expone).
- Si auth-service no responde al crear → `502 UPSTREAM_ERROR`; listar, detallar, editar y cerrar siguen funcionando.

### 8.2 n8n (Integrante 3)

- jobs-service emite `job.created` al crear una oferta: `POST {N8N_WEBHOOK_BASE_URL}/job-created`
  con `X-Service-Token`, timeout de 3 s y **best-effort**. Si n8n falla, el alta responde `201` igual
  (queda logueado).
- Payload:

```json
{
  "event": "job.created",
  "occurred_at": "2026-11-05T14:00:00Z",
  "job_id": "job-013",
  "company_id": "22222222-2222-4222-8222-000000000004",
  "title": "Desarrollador/a Backend",
  "status": "active"
}
```

- Lo consume **WF-02**: toma los candidatos por reglas de la oferta (`score ≥ notifications.min_score`) y
  WF-03 les manda el mail a los que aceptaron contacto por email. Ver [`notificaciones_n8n.md`](notificaciones_n8n.md).

### 8.3 Matching-service y mcp-tools

- Consumen `GET /api/v1/jobs` con `X-Service-Token`: reciben el `JobOpportunity` completo, con el
  sueldo **sin enmascarar** y sin datos personales.
- El alias `limit` (1–200) existe para que paginen sin cambiar de contrato. Detalle completo en
  [`jobs_matching.md`](jobs_matching.md).

### 8.4 Frontend (Integrante 4)

- Contrato detallado de pantallas y componentes en [`jobs_frontend.md`](jobs_frontend.md).
- Lo mínimo para integrar: manejar `401` (refresh), `403` (ocultar acción), `404` (oferta cerrada
  de otra empresa), `409` (recargar y reaplicar) y `422` (mapear `details` a los campos del formulario).

### 8.5 Profile-service (Integrante 2)

- Sin dependencias directas de búsquedas en `v0.1.0`: las búsquedas no se guardan ni se consultan
  desde profile-service.
- Tras la actualización de `AGENTS.md`, profile-service expone un `snapshot` con la forma de
  `company_snapshot` (`contracts/company_profiles_jobs.md`). jobs-service **todavía no lo consume**:
  en `v0.1.0` el snapshot se arma desde `GET /api/v1/auth/me`. Adoptarlo queda como mejora posterior
  (§11) y no cambia el contrato de búsquedas.

---

## 9. Errores

Formato común:

```json
{ "error": { "code": "NOT_FOUND", "message": "Oferta 'job-999' no encontrada", "details": { "job_id": "job-999" } } }
```

| HTTP | `code` | Cuándo | Qué hace el consumidor |
|---|---|---|---|
| 401 | `UNAUTHORIZED` | Falta el token o es inválido | Renovar sesión / redirigir a login |
| 401 | `ACCOUNT_DELETED` | La cuenta fue dada de baja y el token todavía no venció | Cerrar la sesión |
| 403 | `FORBIDDEN` | Rol incorrecto, recurso de otra empresa o `status=closed` sin permiso | Ocultar la acción y avisar |
| 404 | `NOT_FOUND` | Oferta inexistente, o cerrada y el usuario no es dueño/admin/service | Tratarla como inexistente |
| 405 | `METHOD_NOT_ALLOWED` | Método no soportado en la ruta | — |
| 409 | `CONFLICT` | La oferta cambió mientras la editabas/cerrabas (lock optimista) | Releer la oferta y reintentar |
| 422 | `INVALID_INPUT` | Body/query inválido o regla de negocio violada (incluye UT-JOBS-01) | Mapear `details` a los campos del formulario |
| 502 | `UPSTREAM_ERROR` | auth-service no respondió o el usuario no tiene perfil de empresa | Reintentar más tarde |

- Para `422` de Pydantic, `details.errors` trae `loc`/`msg`/`type` por campo.
- **No existen respuestas `400`**: las reglas de negocio y Pydantic comparten el `422 INVALID_INPUT`.

---

## 10. Datos de demo (seed)

- 12 ofertas ficticias: `job-001` … `job-012`, todas `active`, todas con `requirements.skills`
  (con al menos una `required`), `company_snapshot.name` completo y `experience` presente.
- Empresas ficticias del pool: `22222222-2222-4222-8222-0000000000NN` (NN = 1…12). Los ids y
  `company_id` están alineados con el mock `services/matching-service/app/data/mock/jobs.json`.
- Se cargan sólo si la base está vacía, al arrancar el contenedor. Se activa/desactiva con
  `JOBS_SEED_DEMO` (default `true`).
- Para probar flujos "como dueño" hacen falta usuarios `company` reales en auth-service y recargar
  esos UUIDs en `company_id` (o probar con service-token).

---

## 11. Limitaciones actuales (v0.1.0)

1. ~~**Gateway:** `GET/POST /api/v1/jobs` sin barra final respondía `301`.~~ Resuelto: `gateway/nginx.conf`
   tiene `location = /api/v1/jobs` (rama `fix/infra/v0.1.1-integracion-busquedas`).
2. ~~**n8n:** `WF-02` (consumidor de `job.created`) todavía no existía.~~ Resuelto: WF-02 a WF-05
   ([`notificaciones_n8n.md`](notificaciones_n8n.md)). El evento sigue siendo best-effort.
3. **`on_match`:** se trata como sueldo oculto para terceros hasta que exista la integración de
   postulaciones.
4. ~~**Compose:** `JOBS_SEED_DEMO` y `AUTH_SERVICE_URL` sin cablear.~~ Resuelto: `docker-compose.yml`
   pasa `JOBS_DB_SCHEMA`, `JOBS_SEED_DEMO` (default `true`) y `AUTH_SERVICE_URL`; `.env.example` documenta
   `JOBS_SEED_DEMO`. matching-service usa los datos reales por defecto (`MATCHING_USE_MOCKS=false`).
5. **`company_snapshot`:** se arma desde `GET /api/v1/auth/me`. El `snapshot` de empresa que expone
   profile-service todavía no se consume; evaluarlo cuando se cierre la integración de perfiles.
6. No hay borradores, postulaciones, pasantías ni analíticas en esta entrega.
