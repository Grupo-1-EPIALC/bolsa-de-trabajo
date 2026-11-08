# Contrato · jobs-service

> **Para:** el frontend (búsquedas de empresas y ofertas), matching-service, mcp-tools, n8n y auth-service.
> **Servicio:** `jobs-service` 0.2.1 (FastAPI) · base `/api/v1/jobs` y `/api/v1/companies/me/searches`.
> **Fuente de verdad viva:** [Swagger UI](/api/v1/jobs/docs) · [ReDoc](/api/v1/jobs/redoc) · [OpenAPI](/api/v1/jobs/openapi.json) (por el gateway, en dev `http://localhost:8080`).
> **Partes:** A. Búsquedas: API y consumidores · B. Guía para el frontend · C. Servicios: matching-service, mcp-tools y eventos de cuenta. Los `§` de cada parte se refieren a esa parte.
> Los documentos de los que sale este contrato están en [`historico/`](historico/). Todos los ejemplos usan datos ficticios.

---

## A. Búsquedas: API y consumidores

> Fuente: [`historico/jobs_busquedas.md`](historico/jobs_busquedas.md).

### 1. Qué expone jobs-service

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

### 2. Acceso, autenticación y roles

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

### 3. Listado y paginación

#### `GET /api/v1/jobs`

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

#### `GET /api/v1/companies/me/searches`

- Devuelve **sólo las búsquedas de la empresa autenticada**, con el sueldo completo.
- Mismo esquema de paginación que el listado público. Default `status=active`; `closed` y `all` muestran el historial.

---

### 4. Crear una búsqueda

#### Request

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

#### Reglas de validación

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

#### Response `201`

`201 Created` con el `JobOpportunity` completo (§6): la oferta nace `active`, `version = 1`,
`published_at = now` y `company_snapshot` tomado de auth-service.

---

### 5. Editar, cerrar y reabrir

#### Editar — `PATCH /api/v1/jobs/{job_id}`

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

#### Cerrar — `DELETE /api/v1/jobs/{job_id}`

- Cierra la oferta: `204 No Content` (sin body). **No se borra físicamente**: queda
  `status="closed"`, invisible para terceros (detalle → `404`) y visible para la dueña en
  `/companies/me/searches?status=closed`.
- Cerrar una oferta ya cerrada es idempotente (`204`).

#### Reabrir — `PATCH /api/v1/jobs/{job_id}` con `{"status":"active"}`

- Sólo funciona si estaba `closed`: la pasa a `active`, actualiza `published_at = now` y suma
  `version`. Reabrir una que ya estaba activa es idempotente (`200` sin cambios).
- `{"status":"closed"}` por PATCH → `422`: para cerrar se usa `DELETE`.

---

### 6. `JobOpportunity`

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
5. Los enums respetan [`historico/estructura_comun_perfil_oferta_match.md`](historico/estructura_comun_perfil_oferta_match.md) §3.
6. `requirements.experience` está presente como campo: objeto o `null` (matching lo trata como un mínimo de 0 años).
7. `requirements.languages` y `requirements.education` existen (pueden ser `[]`).
8. Las listas (`responsibilities`, `benefits`, `skills`, …) **siempre van como array**, aunque estén vacías; los escalares ausentes viajan `null`.
9. `salary` viaja completo con service-token, incluso si `visibility` es `on_match` o `hidden` (§7).

---

### 7. Sueldo y privacidad

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

### 8. Integración por consumidor

#### 8.1 Auth-service (Integrante 1)

Es la única dependencia externa de búsquedas. jobs-service espera:

| Dependencia | Cuándo | Qué espera |
|---|---|---|
| `GET /api/v1/auth/.well-known/jwks.json` | al validar cualquier JWT (caché 600 s) | claves públicas RS256 con `kid` |
| `GET /api/v1/auth/me` con el Bearer del usuario | al **crear** una oferta | `{ "id": …, "company": { "legal_name", "cuit", "activity" } }` |

- `legal_name` → `company_snapshot.name` (obligatorio; si falta o viene vacío, sale `422`).
- `activity` → `company_snapshot.industry`. `size` y `logo_url` quedan `null` (auth-service todavía no los expone).
- Si auth-service no responde al crear → `502 UPSTREAM_ERROR`; listar, detallar, editar y cerrar siguen funcionando.

#### 8.2 n8n (Integrante 3)

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
  WF-03 les manda el mail a los que aceptaron contacto por email. Ver [`n8n.md`](n8n.md).

#### 8.3 Matching-service y mcp-tools

- Consumen `GET /api/v1/jobs` con `X-Service-Token`: reciben el `JobOpportunity` completo, con el
  sueldo **sin enmascarar** y sin datos personales.
- El alias `limit` (1–200) existe para que paginen sin cambiar de contrato. Detalle completo en
  [`jobs.md`](jobs.md).

#### 8.4 Frontend (Integrante 4)

- Contrato detallado de pantallas y componentes en [`jobs.md`](jobs.md).
- Lo mínimo para integrar: manejar `401` (refresh), `403` (ocultar acción), `404` (oferta cerrada
  de otra empresa), `409` (recargar y reaplicar) y `422` (mapear `details` a los campos del formulario).

#### 8.5 Profile-service (Integrante 2)

- Sin dependencias directas de búsquedas en `v0.1.0`: las búsquedas no se guardan ni se consultan
  desde profile-service.
- Tras la actualización de `AGENTS.md`, profile-service expone un `snapshot` con la forma de
  `company_snapshot` (`contracts/profile.md`). jobs-service **todavía no lo consume**:
  en `v0.1.0` el snapshot se arma desde `GET /api/v1/auth/me`. Adoptarlo queda como mejora posterior
  (§11) y no cambia el contrato de búsquedas.

---

### 9. Errores

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

### 10. Datos de demo (seed)

- 12 ofertas ficticias: `job-001` … `job-012`, todas `active`, todas con `requirements.skills`
  (con al menos una `required`), `company_snapshot.name` completo y `experience` presente.
- Empresas ficticias del pool: `22222222-2222-4222-8222-0000000000NN` (NN = 1…12). Los ids y
  `company_id` están alineados con el mock `services/matching-service/app/data/mock/jobs.json`.
- Se cargan sólo si la base está vacía, al arrancar el contenedor. Se activa/desactiva con
  `JOBS_SEED_DEMO` (default `true`).
- Para probar flujos "como dueño" hacen falta usuarios `company` reales en auth-service y recargar
  esos UUIDs en `company_id` (o probar con service-token).

---

### 11. Limitaciones actuales (v0.1.0)

1. ~~**Gateway:** `GET/POST /api/v1/jobs` sin barra final respondía `301`.~~ Resuelto: `gateway/nginx.conf`
   tiene `location = /api/v1/jobs` (rama `fix/infra/v0.1.1-integracion-busquedas`).
2. ~~**n8n:** `WF-02` (consumidor de `job.created`) todavía no existía.~~ Resuelto: WF-02 a WF-05
   ([`n8n.md`](n8n.md)). El evento sigue siendo best-effort.
3. **`on_match`:** se trata como sueldo oculto para terceros hasta que exista la integración de
   postulaciones.
4. ~~**Compose:** `JOBS_SEED_DEMO` y `AUTH_SERVICE_URL` sin cablear.~~ Resuelto: `docker-compose.yml`
   pasa `JOBS_DB_SCHEMA`, `JOBS_SEED_DEMO` (default `true`) y `AUTH_SERVICE_URL`; `.env.example` documenta
   `JOBS_SEED_DEMO`. matching-service usa los datos reales por defecto (`MATCHING_USE_MOCKS=false`).
5. **`company_snapshot`:** se arma desde `GET /api/v1/auth/me`. El `snapshot` de empresa que expone
   profile-service todavía no se consume; evaluarlo cuando se cierre la integración de perfiles.
6. No hay borradores, postulaciones, pasantías ni analíticas en esta entrega.

## B. Guía para el frontend

> Fuente: [`historico/jobs_frontend.md`](historico/jobs_frontend.md). El resto del contrato del front (endpoints, validaciones, errores) está en la parte A.

### 2. Reglas que el front debe respetar

1. **El front nunca manda** `company_id`, `company_snapshot`, `status` (salvo la reapertura), `version`, `created_at`, `updated_at` ni `published_at`. Los pone el servicio.
2. `job.id` es el `job_id` que después usa matching-service (`/api/v1/matches/...`). No usar el título como clave.
3. **Crear** una oferta la deja `active` automáticamente. No hay botón "guardar borrador" en `v0.1.0`.
4. **Cerrar** es `DELETE`, no `PATCH`. No se borra físicamente: la oferta queda `closed`.
5. **Reabrir** es `PATCH` con `{"status":"active"}` y sólo funciona si estaba `closed`.
6. **PATCH reemplaza bloques completos.** Si mandás `requirements`, mandá todas sus listas (`skills`, `languages`, `education`, etc.). No hay merge profundo.
7. El listado público (`GET /api/v1/jobs`) sólo devuelve `active` para estudiantes y empresas. Las cerradas se ven en "Mis búsquedas" con `status=closed|all`.
8. Una oferta cerrada de otra empresa responde `404`; no se muestra.
9. El sueldo puede venir `null` si `visibility` es `on_match` o `hidden` y el usuario no es la empresa dueña. La UI debe mostrar "Sueldo a convenir / no publicado", no `$ 0`.
10. Los errores siempre tienen la forma `{"error": {"code", "message", "details"}}`.

---

### 10. Textos en español para enums

| Enum | Valores y etiquetas |
|---|---|
| `status` | `active` → "Activa"; `closed` → "Cerrada" |
| `seniority` | `no_experience` → "Sin experiencia"; `trainee` → "Trainee"; `junior` → "Junior"; `semi_senior` → "Semi-Senior"; `senior` → "Senior" |
| `work_schedule` | `full_time` → "Tiempo completo"; `part_time` → "Medio tiempo"; `hourly` → "Por horas"; `flexible` → "Flexible" |
| `work_modality` | `onsite` → "Presencial"; `remote` → "Remoto"; `hybrid` → "Híbrido" |
| `employment_type` | `employee` → "Relación de dependencia"; `freelance` → "Freelance"; `internship` → "Pasantía"; `trainee` → "Trainee" |
| `contract_duration` | `permanent` → "Indefinido"; `fixed_term` → "Plazo fijo"; `project` → "Por proyecto"; `seasonal` → "Temporada" |
| `availability_start` | `immediate` → "Inmediata"; `within_15_days` → "En 15 días"; `within_30_days` → "En 30 días"; `to_agree` → "A convenir" |
| `shift` | `morning` → "Mañana"; `afternoon` → "Tarde"; `evening` → "Noche"; `night` → "Nocturno"; `weekend` → "Fin de semana"; `rotating` → "Rotativo" |
| `requirement_kind` | `required` → "Obligatorio"; `desired` → "Deseable"; `excluding` → "Excluyente" |
| `language_level` | `A1`–`C2` → "A1"–"C2"; `native` → "Nativo" |
| `education_level` | `secondary` → "Secundario"; `tertiary` → "Terciario"; `university` → "Universitario"; `postgraduate` → "Posgrado"; `course` → "Curso" |
| `education_status` | `in_progress` → "En curso"; `completed` → "Completo"; `incomplete` → "Incompleto" |
| `salary_visibility` | `public` → "Público"; `on_match` → "Visible con match"; `hidden` → "Oculto" |

---

### 11. Flujo sugerido de UI

#### "Mis búsquedas"

1. `GET /api/v1/companies/me/searches?status=active&page=1&size=10`.
2. Mostrar cards con título, estado, ubicación, seniority, cantidad de postulantes (cuando matching lo exponga) y acciones "Ver", "Editar", "Cerrar".
3. Tabs "Activas" / "Cerradas" / "Todas" → cambiar `status`.
4. "Cerrar" → `DELETE`, invalidar la query y refrescar.
5. "Reabrir" (en cerradas) → `PATCH {"status":"active"}`, invalidar.

#### "Nueva búsqueda"

1. Formulario en pasos o secciones:
   - Datos generales: título, descripción, área, seniority, vacantes, ubicación.
   - Condiciones: modalidad, horario, horas, sueldo, beneficios.
   - Requisitos: skills con nivel y tipo, idiomas, educación, experiencia.
2. Validación en cliente con Zod (mismas reglas que §3).
3. `POST /api/v1/jobs`.
4. En `201`, redirigir al detalle o a "Mis búsquedas" y mostrar toast "Búsqueda creada".
5. En `422`, mapear errores a los campos.

#### "Editar búsqueda"

1. Cargar el detalle con `GET /api/v1/jobs/{id}`.
2. Precargar el formulario.
3. `PATCH` con los bloques modificados. Para simplificar, mandar el formulario completo (todos los bloques) y dejar que el servicio reemplace.
4. En `200`, actualizar la caché/query y mostrar toast "Búsqueda actualizada".

---

## C. Servicios: matching-service, mcp-tools y eventos de cuenta

> Fuente: [`historico/jobs_matching.md`](historico/jobs_matching.md).

### 1. Endpoints que consume matching/mcp

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

### 2. Listado

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

### 3. Detalle

`GET /api/v1/jobs/{job_id}`

- Devuelve `JobOpportunity` completa.
- Oferta inexistente → `404` con `{"error": {...}}`.
- Oferta cerrada → visible para el service token (matching puede recalcular un match viejo).
- El `job_id` es el `id` de la oferta (ej. `job-001`). Es el mismo que usa `Match.job_id`.

---

### 4. Campos que espera `JobMapper`

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

#### Garantías del contrato

1. `company_snapshot.name` siempre está presente y no vacío (jobs-service lo valida al crear y al cargar el seed).
2. `requirements.skills` tiene al menos una `required`.
3. `level` de skill siempre está entre 1 y 5.
4. `kind` siempre es `required`, `desired` o `excluding`.
5. Los enums respetan [`historico/estructura_comun_perfil_oferta_match.md`](historico/estructura_comun_perfil_oferta_match.md) §3.
6. `requirements.experience` está presente como campo (objeto o `null`; matching lo trata como un mínimo de 0 años).
7. `requirements.languages` y `requirements.education` existen (pueden ser `[]`).
8. `version` se incrementa en cada edición, cierre o reapertura.
9. `salary` viaja completo con service token, incluso si `visibility` es `on_match` o `hidden`.
10. `company_id` es el `sub` de la empresa en auth-service; para el seed son IDs ficticios.

---

### 5. Sueldo y visibilidad

- Para **service token**, jobs-service **no enmascara** el sueldo. matching recibe `salary` completo y aplica su propia regla de `visibility` en `SalaryComparator`.
- Para usuarios (`student`/`company`), jobs-service devuelve `salary: null` si `visibility` es `on_match` o `hidden` y el usuario no es la empresa dueña.
- Si `salary.to_agree = true`, `min`/`max` pueden venir `null`; matching ya lo trata como `unknown`.
- `salary.currency` y `salary.period` vienen cuando hay monto.

---

### 6. Ejemplo de oferta (job-004 del seed)

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

### 7. Seed de demo

- `job-001` a `job-012`, copiados de `services/matching-service/app/data/mock/jobs.json` y normalizados al contrato común.
- Conservan `id` y `company_id` ficticios para que matching pueda seguir usando sus matches de demo.
- Se cargan al arrancar jobs-service si `JOBS_SEED_DEMO=true` y la tabla `jobs` está vacía.
- Si el seed no cumple las reglas, el servicio falla al arrancar (para detectar inconsistencias antes de la demo).

---

### 11. Eventos de cuenta (auth-service → jobs-service)

`POST http://jobs-service:8000/api/v1/jobs/internal/account-events` · sólo `X-Service-Token` (un usuario recibe `403`; por el gateway no llega porque se borra el header). Cuerpo y entrega en [`auth.md`](auth.md). Responde `200` con `{ "event", "user_id", "result", "archived_jobs" }`.

| Evento | Qué hace jobs-service | `result` |
|---|---|---|
| `account.deleted` | Anota la baja en `jobs.deleted_accounts` y mueve **todas** las ofertas de la empresa (activas y cerradas) a `jobs.jobs_deleted` (auditoría). Desde ahí no salen en `GET /jobs`, en el detalle, en `/companies/me/searches` ni en el matching, y el JWT que todavía no venció recibe `401 ACCOUNT_DELETED`. El seed de demo no las vuelve a cargar | `archived` (o `registered` si no tenía ofertas, p. ej. un estudiante) |
| `account.updated` | Nada: el `company_snapshot` se arma al crear o editar una oferta | `ignored` |
| Repetido o de un tipo desconocido | Nada (idempotente) | `ignored` |
