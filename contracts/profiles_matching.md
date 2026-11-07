# Contrato matching-service / mcp-tools / n8n ↔ profile-service

> **Para:** quien mantiene `matching-service` y `mcp-tools` (Integrante 3 / Integrante 1) y los workflows de n8n.
> **Servicio:** `profile-service` v0.2.0. Fuente de verdad: [`profile_service.openapi.json`](profile_service.openapi.json) y [`estructura_comun_perfil_oferta_match.md`](estructura_comun_perfil_oferta_match.md) §5.
> **Resultado:** **no hace falta cambiar código** en matching-service ni en mcp-tools. `HttpProfileSource`, `HttpProfileGateway` y `ProfileMapper` funcionan tal como están. Se probó con `MATCHING_USE_MOCKS=false` contra profile-service y jobs-service reales: el ranking de `stu-001` es el mismo que con mocks (`job-004, job-001, job-006, job-005, job-002`).

---

## 1. Endpoints que consumen

| Consumidor | Llamada | Auth |
|---|---|---|
| matching-service (`HttpProfileSource.get_profile`) | `GET /api/v1/profiles/{profile_id}` | `X-Service-Token` |
| matching-service (`HttpProfileSource.list_profiles`) | `GET /api/v1/profiles?limit=N` | `X-Service-Token` |
| mcp-tools (`HttpProfileGateway.get_profile`) | `GET /api/v1/profiles/{profile_id}` | `X-Service-Token` |
| mcp-tools (`HttpProfileGateway.list_profiles`) | `GET /api/v1/profiles?limit=N&skills=python,sql` | `X-Service-Token` |

- Llamar directo a `http://profile-service:8000` por la red interna. El gateway borra `X-Service-Token` y no enruta `/api/v1/profiles` sin barra final, así que el listado **no es accesible desde afuera**.
- **Nunca Bearer** para servicios. Un `admin` con su JWT también puede usar estos endpoints (ve la completitud de cada perfil).
- Un estudiante con JWT puede leer **su** perfil por id (`GET /profiles/{id}`), lo que coincide con la regla de matching `profile.user_id == sub`.

---

## 2. Listado (pool de candidatos)

`GET /api/v1/profiles?limit=200[&skills=python,sql][&page=1][&include_all=false]`

```json
{ "items": [ { "...": "perfil completo, vista de servicio (§4)" } ], "total": 15, "page": 1, "size": 200, "pages": 1 }
```

- `limit` (alias de `size`) entre 1 y 200; `page` desde 1. Orden estable por `id`.
- **Filtro por defecto (cambio respecto del mock):** sólo perfiles **buscables**: `status = "complete"`, `visibility != "hidden"` y `job_search_status != "not_looking"`. Los borradores no entran al ranking. `include_all=true` los incluye (auditoría).
- `skills`: se queda con los perfiles que tengan **alguna** de esas skills. Se normalizan con el mismo catálogo y sinónimos (`python3` → `python`).
- `items` trae objetos completos, igual que jobs-service.
- Los perfiles de **cuentas dadas de baja** no aparecen nunca (ni con `include_all=true`) y `GET /profiles/{id}` da `404`: ver §8.

---

## 3. Detalle

`GET /api/v1/profiles/{profile_id}`

- `200` con la vista de servicio (§4), sin importar `status` ni `visibility`: matching puede recalcular un match viejo.
- `404 PROFILE_NOT_FOUND` con el formato común si no existe.
- `profile_id` es el `id` del perfil (ej. `stu-001` en el seed, `prof-<12 hex>` en los nuevos) y es el que usa `Match.profile_id`.

---

## 4. Campos que lee `ProfileMapper` (vista de servicio)

| Campo en profile-service | Uso en matching |
|---|---|
| `id` | `StudentProfile.id` |
| `user_id` | `StudentProfile.user_id` (= `sub` del JWT de auth-service) |
| `personal.name` | `display_name` (matching lo saca de los snapshots) |
| `headline` | `headline` (si falta, matching usa `summary`) |
| `personal.location.country/province/city/postal_code/zone` | `location` (objeto; ya no texto libre) |
| `work_conditions.*` | `WorkConditions` (mismos enums §3) |
| `work_conditions.salary` | Sueldo pretendido **completo** (min, max, currency, period, gross, negotiable, to_agree, visibility). matching aplica `visibility` en `SalaryComparator` |
| `skills[].name / normalized / level` | Skills (nivel entero 1–5; `normalized` ya viene resuelto) |
| `languages[].name / normalized / level` | Idiomas (`A1`…`C2`, `native`) |
| `education[].level / status / degree / field` | Educación |
| `experience[]` (`start`, `end`, `months`) | Años de experiencia si no viene `years_experience` |
| **`years_experience`** | **Nuevo, calculado por reglas**: suma de `experience[].months` / 12. matching lo usa directo (campo `explicit_years` del mapper) |
| `academic_status.career / current_year / progress_percent / student_shift` | `AcademicStatus` |
| `target.roles` | `target_roles` |

### Garantías

1. Sin `"COMPLETAR_MANUALMENTE"` en ningún campo: lo confirmado se valida al guardar.
2. `skills[].level` siempre entero entre 1 y 5; `skills[].normalized` siempre presente y sin repetidos.
3. Enums según la estructura común §3.
4. `personal.location` es un objeto `{country, province, city}` (país ISO alfa-2).
5. Los opcionales vacíos **no vienen** en el JSON (no hay `null`). Las listas vienen siempre (pueden ser `[]`).
6. `version` aumenta con cada `PATCH` del estudiante.
7. `salary` viaja completo con service token, aunque `visibility` sea `on_match` o `hidden`.

### Lo que la vista de servicio **no** incluye (minimización de datos)

`personal.phone`, `personal.birth_year`, `inclusion` (datos de discapacidad: nunca a IA), `consents`, `cv_files` y `cv_suggestions`. `personal.email` **sí** viaja, para las notificaciones de WF-02/WF-03.

> **mcp-tools / n8n:** `get_profile` devuelve esta vista. Antes de mandarla a un prompt, quitar `personal.name`, `personal.email` y los montos de `salary` si `visibility = "hidden"`, como ya hace WF-06 en el contexto de `match_advisor`.

---

## 5. Pool de prueba (seed)

- Con `PROFILE_SEED_DEMO=true` (por defecto en dev), profile-service carga los **15 perfiles ficticios de `matching-service/app/data/mock/profiles.json`**, con los mismos `id` (`stu-001`…`stu-015`) y `user_id`.
- A cada perfil se le agregan `summary`, `consents` y una experiencia ficticia equivalente a su `years_experience`. Todos quedan `complete` y buscables.
- Es idempotente (no pisa perfiles existentes). En producción: `PROFILE_SEED_DEMO=false`.

### Datos reales o mocks en matching

matching-service usa por defecto los datos reales (`MATCHING_USE_MOCKS=false` en `docker-compose.yml`): con profile-service y jobs-service levantados (los dos con seed), rankea contra el pool real y los estudiantes que se registran y completan el perfil entran solos. Para probar matching aislado con el pool ficticio:

```bash
MATCHING_USE_MOCKS=true docker compose up -d matching-service
```

---

## 6. Evento `profile.updated` (pendiente en n8n)

Después de cada alta o `PATCH`, profile-service hace un **POST best-effort** a n8n:

`POST {N8N_WEBHOOK_BASE_URL}/profile-updated` · header `X-Service-Token`

```json
{
  "event": "profile.updated",
  "occurred_at": "2026-11-06T03:35:10+00:00",
  "profile_id": "prof-ef0b380e927d",
  "user_id": "f110bd46-96c8-4ad1-8bea-9ee3660f0b7a",
  "status": "complete",
  "version": 3,
  "searchable": true
}
```

- **Hoy no existe ese webhook en n8n**: profile-service registra un warning y sigue. Falta crear el disparador en WF-03 (Match Notifier) para recalcular o notificar cuando `searchable = true`.
- Para idempotencia, usar `profile_id + version` como `notification_key`.

---

## 7. Extracción de CV (sin cambios para n8n)

- profile-service sigue llamando a `POST http://n8n:5678/webhook/cv-extract` (WF-01) con el mismo body, documentado en [`cv_recognition_profile_service.md`](cv_recognition_profile_service.md) §2.2.
- La respuesta de WF-01 (`cv_suggestions` con forma `cv_standard`) **no cambia**. profile-service le agrega `profile_draft` y `review_fields` para el front.
- **Para probarlo de punta a punta, WF-01 tiene que estar importado y activo en n8n.** Si no, el job termina en `failed` con `CV_WEBHOOK_ERROR` ("webhook not registered").

---

## 8. Eventos de cuenta (auth-service → profile-service)

`POST http://profile-service:8000/api/v1/profiles/internal/account-events` · sólo `X-Service-Token` (un usuario recibe `403`; por el gateway no llega porque se borra el header). Cuerpo y entrega en [`account_events.md`](account_events.md). Responde `200` con `{ "event", "user_id", "result" }`.

| Evento | Qué hace profile-service | `result` |
|---|---|---|
| `account.deleted` | Anota la baja en `profile.deleted_accounts` (aunque no tuviera perfil) y mueve el perfil del estudiante a `profile.profiles_deleted` o el de la empresa a `profile.company_profiles_deleted` (auditoría). Borra el logo. Desde ahí sale del pool de matching, de los listados y de `/me`, y el JWT que todavía no venció recibe `401 ACCOUNT_DELETED` | `archived` (o `updated` si no tenía perfil) |
| `account.updated` (empresa) | Actualiza la copia de sólo lectura de razón social, CUIT y actividad (`legal` y el `snapshot` para jobs-service) | `updated` |
| `account.updated` (estudiante) | Nada: `personal.email` es un dato de contacto que edita el estudiante | `ignored` |
| Repetido o de un tipo desconocido | Nada (idempotente) | `ignored` |

Una re-alta con el mismo email o CUIT es otra cuenta (otro `user_id`), con un perfil nuevo.

