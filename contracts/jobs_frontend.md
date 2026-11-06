# Contrato frontend ↔ jobs-service · Búsquedas de empresas

> **Para:** quien desarrolla el `frontend` (Integrante 4, Dario) y su asistente (`frontend-agent`, AGENTS.md §4.7).
> **Servicio:** `jobs-service` v0.1.0 · implementa RF-11, RF-12, HU-11 y HU-12 del Plan MVP.
> **Fuente de verdad:** [`jobs_service.openapi.json`](jobs_service.openapi.json) (contrato completo) y [`estructura_comun_perfil_oferta_match.md`](estructura_comun_perfil_oferta_match.md) (estructura de datos).
> **Alcance de esta entrega:** crear, editar, cerrar/reabrir y listar búsquedas de la empresa. No incluye postulaciones, pasantías ni analíticas.

---

## 1. Pantallas y endpoints

| Pantalla / acción | Método y ruta | Respuesta |
|---|---|---|
| "Mis búsquedas" (activas) | `GET /api/v1/companies/me/searches` | `JobList` |
| "Mis búsquedas" filtradas por estado | `GET /api/v1/companies/me/searches?status=active\|closed\|all` | `JobList` |
| "Ver todas las ofertas" (estudiante o empresa) | `GET /api/v1/jobs?status=active&page=1&size=10` | `JobList` |
| Detalle de una oferta | `GET /api/v1/jobs/{job_id}` | `JobOpportunity` |
| "Nueva búsqueda" | `POST /api/v1/jobs` | `201` + `JobOpportunity` |
| "Editar búsqueda" | `PATCH /api/v1/jobs/{job_id}` | `200` + `JobOpportunity` |
| "Cerrar búsqueda" | `DELETE /api/v1/jobs/{job_id}` | `204` sin body |
| "Reabrir búsqueda" | `PATCH /api/v1/jobs/{job_id}` con `{"status":"active"}` | `200` + `JobOpportunity` |

- **Base:** same-origin detrás del gateway: `/api/v1/...`.
- **Auth:** `Authorization: Bearer <access_token>` en todas las llamadas, con el cliente único `src/api/client.ts` y su refresh automático.
- **No hay endpoint público anónimo** en `v0.1.0`: todo requiere sesión.

> **Dependencia del gateway (Integrante 1):** `gateway/nginx.conf` hoy tiene `location /api/v1/jobs/` (con barra final). Eso no matchea `/api/v1/jobs` ni `/api/v1/jobs` sin barra, que es el listado y el POST. Hace falta un `location = /api/v1/jobs` o cambiar el prefijo. Mientras tanto, el front puede probar contra `http://localhost:8000/api/v1/jobs` en desarrollo.

---

## 2. Reglas que el front debe respetar

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

## 3. Crear una búsqueda

### Request

`POST /api/v1/jobs`

```json
{
  "title": "Desarrollador/a Backend Python Jr.",
  "description": "Desarrollo de microservicios REST con Python, FastAPI y PostgreSQL.",
  "responsibilities": [
    "Implementar endpoints REST",
    "Escribir tests unitarios"
  ],
  "area": "software",
  "seniority": "junior",
  "vacancies": 1,
  "location": {
    "country": "AR",
    "province": "CABA",
    "city": "Buenos Aires",
    "postal_code": null,
    "zone": null
  },
  "work_conditions": {
    "work_schedule": ["full_time"],
    "work_modality": ["hybrid"],
    "hybrid_onsite_days": 2,
    "employment_type": ["employee"],
    "contract_duration": ["permanent"],
    "weekly_hours": { "min": 30, "max": 40 },
    "shifts": ["morning", "afternoon"],
    "availability_start": "within_15_days",
    "salary": {
      "min": 800000,
      "max": 1000000,
      "currency": "ARS",
      "period": "month",
      "gross": true,
      "payment_mode": "local",
      "negotiable": false,
      "adjustment": "quarterly",
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
      { "name": "Python", "level": 3, "kind": "required" },
      { "name": "FastAPI", "level": 3, "kind": "required" },
      { "name": "SQL", "level": 3, "kind": "required" },
      { "name": "Docker", "level": 3, "kind": "desired" }
    ],
    "languages": [
      { "name": "Inglés", "level": "B1", "kind": "required" }
    ],
    "education": [
      {
        "level": "university",
        "status": "in_progress",
        "field": "sistemas",
        "kind": "required"
      }
    ],
    "experience": {
      "min_years": 1,
      "area": "desarrollo backend",
      "kind": "required"
    },
    "certifications": [],
    "academic": {
      "min_progress_percent": 50,
      "careers": [],
      "min_current_year": null
    }
  },
  "benefits": ["capacitación", "días de estudio"],
  "expires_at": "2026-12-31T23:59:59Z"
}
```

### Reglas de validación

- `title` y `description` no vacíos.
- `seniority`, `location` y `requirements` obligatorios.
- `requirements.skills` debe tener **al menos una** con `kind: "required"`. Si no, `422` (UT-JOBS-01).
- `level` de skill entre 1 y 5.
- `vacancies >= 1`.
- `salary.min <= salary.max`; si hay monto, `currency` y `period` son obligatorios.
- `weekly_hours.min <= weekly_hours.max`.
- `hybrid_onsite_days` entre 0 y 5.
- `expires_at` si viene debe ser futuro.

### Response `201`

Devuelve el `JobOpportunity` completo. Ejemplo abreviado:

```json
{
  "id": "job-013",
  "company_id": "8f14e45f-ea3b-4c1a-9f0e-2b7a6d1c3a10",
  "company_snapshot": {
    "name": "Mi Empresa S.A.",
    "industry": "software",
    "size": null,
    "logo_url": null
  },
  "status": "active",
  "title": "Desarrollador/a Backend Python Jr.",
  "description": "Desarrollo de microservicios REST con Python, FastAPI y PostgreSQL.",
  "responsibilities": ["Implementar endpoints REST", "Escribir tests unitarios"],
  "area": "software",
  "seniority": "junior",
  "vacancies": 1,
  "location": {
    "country": "AR",
    "province": "CABA",
    "city": "Buenos Aires",
    "postal_code": null,
    "zone": null
  },
  "work_conditions": { "...": "..." },
  "requirements": {
    "skills": [
      { "name": "Python", "normalized": "python", "level": 3, "kind": "required", "years": null, "category": null }
    ],
    "languages": [],
    "education": [],
    "experience": { "min_years": 1, "area": "desarrollo backend", "kind": "required" },
    "certifications": [],
    "academic": null
  },
  "benefits": ["capacitación", "días de estudio"],
  "created_at": "2026-11-05T14:00:00Z",
  "updated_at": "2026-11-05T14:00:00Z",
  "published_at": "2026-11-05T14:00:00Z",
  "expires_at": "2026-12-31T23:59:59Z",
  "version": 1
}
```

> `company_snapshot.name` y `industry` salen de auth-service (`legal_name` y `activity`). `size` y `logo_url` son `null` porque auth-service todavía no los expone.

---

## 4. Editar una búsqueda

`PATCH /api/v1/jobs/{job_id}`

- Mandar sólo los campos/bloques que cambian.
- **Los bloques son completos:** si mandás `requirements`, reemplaza todo el bloque; si omitís `languages`, se vacía.
- Cada edición incrementa `version` y actualiza `updated_at`.
- No se puede cambiar `company_id`, `status` (salvo reapertura), `version` ni timestamps.

Ejemplo: cambiar título y sueldo.

```json
{
  "title": "Desarrollador/a Backend Python Semi-Senior",
  "work_conditions": {
    "work_schedule": ["full_time"],
    "work_modality": ["remote"],
    "employment_type": ["employee"],
    "salary": {
      "min": 1200000,
      "max": 1500000,
      "currency": "ARS",
      "period": "month",
      "gross": true,
      "visibility": "public",
      "to_agree": false
    }
  }
}
```

> Ojo: el ejemplo de `work_conditions` reemplaza el bloque completo. Si querés conservar `weekly_hours`, `shifts`, etc., mandalos también. La UI puede hacer un `PATCH` con el objeto completo del formulario.

---

## 5. Cerrar y reabrir

### Cerrar

`DELETE /api/v1/jobs/{job_id}` → `204 No Content`.

- Sólo la empresa dueña.
- Si ya estaba cerrada, también `204` (idempotente).
- La oferta no se borra: queda `status: "closed"`.
- En "Mis búsquedas" se puede ver con `?status=closed` o `?status=all`.

### Reabrir

`PATCH /api/v1/jobs/{job_id}` con:

```json
{ "status": "active" }
```

- Sólo desde `closed`.
- Actualiza `published_at` a la fecha de reapertura.
- Si ya estaba `active`, responde `200` sin cambios.
- No se puede mandar `status: "closed"` por PATCH; para cerrar va `DELETE`.

---

## 6. Listados y paginación

### `GET /api/v1/jobs`

Parámetros:

| Parámetro | Tipo | Default | Notas |
|---|---|---|---|
| `status` | `active \| closed \| all` | `active` | Estudiante/empresa sólo `active`; admin/service pueden el resto |
| `page` | int ≥ 1 | 1 | 1-based |
| `size` | int 1–200 | 5 | Tamaño de página |
| `limit` | int 1–200 | — | Alias de `size` para matching/mcp; el front usa `size` |

### `GET /api/v1/companies/me/searches`

Mismos parámetros. `status` default `active`; `closed` y `all` permiten gestionar el historial (HU-12).

### Response `JobList`

```json
{
  "items": [ { "...": "JobOpportunity" } ],
  "total": 12,
  "page": 1,
  "size": 5,
  "pages": 3
}
```

- `pages = ceil(total / size)`.
- Si `page` supera `pages`, `items` viene vacío y `total` sigue siendo el total real.

---

## 7. Sueldo y privacidad

| `salary.visibility` | Empresa dueña / admin / service | Estudiante / otra empresa |
|---|---|---|
| `public` | Completo | Completo |
| `on_match` | Completo | `salary: null` |
| `hidden` | Completo | `salary: null` |

- `salary` puede ser `null` también si la oferta no publica monto (`to_agree: true`).
- La UI debe mostrar:
  - `salary === null` → "Sueldo no publicado" o "A convenir".
  - `salary.to_agree === true` → "A convenir".
  - `salary.min`/`max` → formatear con `Intl.NumberFormat("es-AR", { style: "currency", currency: salary.currency })`.
- `on_match` se trata como oculto para terceros hasta que exista integración de postulaciones. Queda documentado como limitación de `v0.1.0`.

---

## 8. Errores

Formato:

```json
{
  "error": {
    "code": "FORBIDDEN",
    "message": "La oferta pertenece a otra empresa",
    "details": { "job_id": "job-001" }
  }
}
```

| HTTP | `code` | Cuándo | Qué muestra la UI |
|---|---|---|---|
| 400 | `INVALID_INPUT` | Regla de negocio violada | Mensaje del error |
| 401 | `UNAUTHORIZED` | Sin token / token vencido | Redirigir a login o refrescar |
| 403 | `FORBIDDEN` | Estudiante creando, otra empresa editando/cerrando | "No tenés permiso para esta acción" |
| 404 | `NOT_FOUND` | Oferta inexistente o cerrada de otra empresa | "No encontramos esta búsqueda" |
| 422 | `INVALID_INPUT` | Body/query inválido (incluye UT-JOBS-01) | Errores por campo |
| 502 | `UPSTREAM_ERROR` | auth-service o n8n no respondieron | "Probá de nuevo en unos minutos" |

Para 422, `details` puede traer una lista de errores de Pydantic. La UI debe mapear `details[].loc` a los campos del formulario.

---

## 9. Tipos TypeScript sugeridos

Crear `src/api/types/jobs.ts` (o ampliar el existente). No depender de `any`.

```ts
export type JobStatus = 'active' | 'closed';
export type JobStatusFilter = JobStatus | 'all';
export type RequirementKind = 'required' | 'desired' | 'excluding';

export type Seniority =
  | 'no_experience'
  | 'trainee'
  | 'junior'
  | 'semi_senior'
  | 'senior';

export type WorkSchedule = 'full_time' | 'part_time' | 'hourly' | 'flexible';
export type WorkModality = 'onsite' | 'remote' | 'hybrid';
export type EmploymentType = 'employee' | 'freelance' | 'internship' | 'trainee';
export type ContractDuration = 'permanent' | 'fixed_term' | 'project' | 'seasonal';
export type AvailabilityStart = 'immediate' | 'within_15_days' | 'within_30_days' | 'to_agree';
export type Shift = 'morning' | 'afternoon' | 'evening' | 'night' | 'weekend' | 'rotating';
export type LanguageLevel = 'A1' | 'A2' | 'B1' | 'B2' | 'C1' | 'C2' | 'native';
export type EducationLevel = 'secondary' | 'tertiary' | 'university' | 'postgraduate' | 'course';
export type EducationStatus = 'in_progress' | 'completed' | 'incomplete';
export type Currency = 'ARS' | 'USD';
export type SalaryPeriod = 'hour' | 'day' | 'month' | 'year' | 'project';
export type SalaryVisibility = 'public' | 'on_match' | 'hidden';

export interface Location {
  country: string;
  province: string;
  city: string;
  postal_code?: string | null;
  zone?: string | null;
}

export interface VariableCompensation {
  type: 'bonus' | 'commission' | 'profit_sharing';
  description?: string | null;
  max_percent?: number | null;
}

export interface SalaryRange {
  min?: number | null;
  max?: number | null;
  currency?: Currency | null;
  period?: SalaryPeriod | null;
  gross?: boolean;
  payment_mode?: 'local' | 'usd' | 'usd_paid_in_local' | null;
  negotiable?: boolean;
  adjustment?: 'none' | 'monthly' | 'quarterly' | 'semiannual' | 'by_agreement' | null;
  variable_compensation?: VariableCompensation[];
  visibility?: SalaryVisibility | null;
  to_agree?: boolean;
  notes?: string | null;
}

export interface WorkConditions {
  work_schedule: WorkSchedule[];
  work_modality: WorkModality[];
  hybrid_onsite_days?: number | null;
  employment_type: EmploymentType[];
  contract_duration: ContractDuration[];
  weekly_hours?: { min: number; max: number } | null;
  shifts: Shift[];
  availability_start?: AvailabilityStart | null;
  salary?: SalaryRange | null;
  relocation_support?: boolean;
  travel_availability?: 'none' | 'occasional' | 'frequent' | null;
  driver_license: string[];
  own_vehicle?: boolean | null;
  own_equipment?: boolean | null;
  invoicing_status?: 'monotributo' | 'responsable_inscripto' | 'none' | 'to_register' | null;
  work_authorization: string[];
  timezone?: string | null;
  timezone_overlap_hours?: number | null;
}

export interface SkillRequirement {
  name: string;
  normalized?: string;
  level: number; // 1–5
  kind: RequirementKind;
  years?: number | null;
  category?: 'hard' | 'soft' | 'tool' | 'methodology' | null;
}

export interface LanguageRequirement {
  name: string;
  normalized?: string;
  level: LanguageLevel;
  kind: RequirementKind;
  certification?: string | null;
}

export interface EducationRequirement {
  institution?: string | null;
  degree?: string | null;
  field?: string | null;
  level: EducationLevel;
  status: EducationStatus;
  progress_percent?: number | null;
  gpa?: number | null;
  kind: RequirementKind;
}

export interface ExperienceRequirement {
  min_years: number;
  area?: string | null;
  kind: RequirementKind;
}

export interface CertificationRequirement {
  name: string;
  kind: RequirementKind;
}

export interface AcademicRequirement {
  min_progress_percent?: number | null;
  careers: string[];
  min_current_year?: number | null;
}

export interface Requirements {
  skills: SkillRequirement[];
  languages: LanguageRequirement[];
  education: EducationRequirement[];
  experience?: ExperienceRequirement | null;
  certifications: CertificationRequirement[];
  academic?: AcademicRequirement | null;
}

export interface CompanySnapshot {
  name: string;
  industry?: string | null;
  size?: '1-10' | '11-50' | '51-200' | '201-1000' | '1000+' | null;
  logo_url?: string | null;
}

export interface JobOpportunity {
  id: string;
  company_id: string;
  company_snapshot: CompanySnapshot;
  status: JobStatus;
  title: string;
  description: string;
  responsibilities: string[];
  area: string;
  seniority: Seniority;
  vacancies: number;
  location: Location;
  work_conditions: WorkConditions;
  requirements: Requirements;
  benefits: string[];
  created_at: string;
  updated_at: string;
  published_at: string | null;
  expires_at: string | null;
  version: number;
}

export interface JobList {
  items: JobOpportunity[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

// Requests: sin company_id, company_snapshot, status, version ni timestamps.

export interface SkillRequirementInput {
  name: string;
  level: number;
  kind: RequirementKind;
  years?: number | null;
  category?: 'hard' | 'soft' | 'tool' | 'methodology' | null;
}

export interface RequirementsInput {
  skills: SkillRequirementInput[];
  languages?: Omit<LanguageRequirement, 'normalized'>[];
  education?: EducationRequirement[];
  experience?: ExperienceRequirement | null;
  certifications?: CertificationRequirement[];
  academic?: AcademicRequirement | null;
}

export interface JobCreateInput {
  title: string;
  description: string;
  responsibilities?: string[];
  area?: string;
  seniority: Seniority;
  vacancies?: number;
  location: Location;
  work_conditions?: WorkConditions | null;
  requirements: RequirementsInput;
  benefits?: string[];
  expires_at?: string | null;
}

export type JobUpdateInput = Partial<Omit<JobCreateInput, 'status'>> & {
  status?: 'active';
};
```

### Cambios respecto del `jobs.ts` actual del front

- `status` pasa de `'draft' | 'active' | 'paused' | 'closed' | 'expired'` a `'active' | 'closed'`.
- `JobOpportunity` suma `company_snapshot`, `responsibilities`, `area`, `created_at`, `updated_at`, `published_at`, `expires_at` y `version`.
- `requirements.languages` y `requirements.education` usan `kind`.
- `JobCreateInput` no incluye `company_id` ni `status`.

---

## 10. Textos en español para enums

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

## 11. Flujo sugerido de UI

### "Mis búsquedas"

1. `GET /api/v1/companies/me/searches?status=active&page=1&size=10`.
2. Mostrar cards con título, estado, ubicación, seniority, cantidad de postulantes (cuando matching lo exponga) y acciones "Ver", "Editar", "Cerrar".
3. Tabs "Activas" / "Cerradas" / "Todas" → cambiar `status`.
4. "Cerrar" → `DELETE`, invalidar la query y refrescar.
5. "Reabrir" (en cerradas) → `PATCH {"status":"active"}`, invalidar.

### "Nueva búsqueda"

1. Formulario en pasos o secciones:
   - Datos generales: título, descripción, área, seniority, vacantes, ubicación.
   - Condiciones: modalidad, horario, horas, sueldo, beneficios.
   - Requisitos: skills con nivel y tipo, idiomas, educación, experiencia.
2. Validación en cliente con Zod (mismas reglas que §3).
3. `POST /api/v1/jobs`.
4. En `201`, redirigir al detalle o a "Mis búsquedas" y mostrar toast "Búsqueda creada".
5. En `422`, mapear errores a los campos.

### "Editar búsqueda"

1. Cargar el detalle con `GET /api/v1/jobs/{id}`.
2. Precargar el formulario.
3. `PATCH` con los bloques modificados. Para simplificar, mandar el formulario completo (todos los bloques) y dejar que el servicio reemplace.
4. En `200`, actualizar la caché/query y mostrar toast "Búsqueda actualizada".

---

## 12. Checklist para el PR del front

- [ ] Tipos `JobOpportunity`/`JobCreateInput`/`JobUpdateInput` alineados con §9.
- [ ] `status` sólo `active | closed`.
- [ ] No se envía `company_id` ni `status` al crear.
- [ ] "Cerrar" usa `DELETE`; "Reabrir" usa `PATCH {"status":"active"}`.
- [ ] `salary: null` se muestra como "No publicado / A convenir".
- [ ] Listado de "Mis búsquedas" usa `/api/v1/companies/me/searches`.
- [ ] Errores 401/403/404/422/502 manejados con el formato común.
- [ ] Paginación con `page`/`size` y controles de página.
- [ ] Sin `any` en los tipos de jobs.
