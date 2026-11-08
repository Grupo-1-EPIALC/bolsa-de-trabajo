# Contrato de eventos de cuenta · auth-service → servicios

> **Para:** quienes mantienen profile-service, jobs-service y core-service.
> **Emisor:** `auth-service` (dueño de las cuentas). **Origen:** acciones del panel de administración (`contracts/auth_frontend.md` §7).

Cuando un admin edita o borra una cuenta, auth-service avisa a cada servicio para que actualice u oculte los datos de esa cuenta. Cada servicio sólo cambia sus propios datos (AGENTS §2.1).

---

## 1. Entrega

- `POST` a cada URL de `ACCOUNT_EVENT_WEBHOOKS` (separadas por coma). Por defecto, en `docker-compose.yml`:
  - `http://profile-service:8000/api/v1/profiles/internal/account-events`
  - `http://jobs-service:8000/api/v1/jobs/internal/account-events`
- Header `X-Service-Token: <SERVICE_TOKEN>`. El receptor rechaza cualquier otro pedido con `401`/`403`.
- `Content-Type: application/json`. Timeout de 5 s por suscriptor.
- **Outbox con reintentos (al menos una vez):** el evento se guarda en `auth.account_event_deliveries` **en la misma transacción** que el cambio de la cuenta (una fila por suscriptor). Si no se puede guardar, el cambio no se confirma. Después del commit se intenta entregar enseguida; si falla (servicio caído, timeout o respuesta que no es `2xx`), se reintenta **sin límite** con backoff exponencial: 5 s, 10 s, 20 s… hasta 10 min entre intentos. Sobrevive a reinicios de auth-service: una entrega cortada a mitad de camino vuelve a la cola al minuto (lease).
- **Orden:** los eventos de una misma cuenta llegan a cada suscriptor en el orden en que ocurrieron (un `account.updated` viejo nunca llega después del `account.deleted`). Un suscriptor caído no frena a los demás.
- El receptor responde `2xx` rápido y **tiene que ser idempotente**: el mismo evento puede llegar más de una vez (mismo `event_id`). Un `4xx` también se reintenta: hay que corregir el receptor o la configuración.
- Configuración opcional de auth-service: `ACCOUNT_EVENT_RETRY_INTERVAL_MS` (cada cuánto revisa la cola, 5000), `ACCOUNT_EVENT_RETRY_BASE_MS` (primer reintento, 5000) y `ACCOUNT_EVENT_RETRY_MAX_MS` (tope, 600000).
- **Auditoría:** `SELECT event_type, subscriber, attempts, delivered_at, last_error FROM auth.account_event_deliveries WHERE delivered_at IS NULL` lista lo pendiente y el último error.
- Ruta de cada receptor: `POST /api/v1/<recurso>/internal/account-events` (interna, nunca para usuarios; el gateway borra `X-Service-Token`).
- Respuesta del receptor: `200` con `{ "event", "user_id", "result" }`, donde `result` es `archived`, `updated`, `registered` o `ignored`.

---

## 2. Cuerpo

```json
{
  "event_id": "6b3c5343-5fcd-4b3c-a579-7c80dbd34a67",
  "event": "account.deleted",
  "user_id": "64e3d052-54f4-458e-af3f-82f81cadaed7",
  "role": "student",
  "deleted": true,
  "email": "persona@example.test",
  "actor_id": "55cfadff-0abd-4c44-8232-0a2eb5498d41",
  "occurred_at": "2026-11-06T21:44:40.123Z"
}
```

Para empresas se agrega `company`:

```json
"company": { "legal_name": "Empresa Ficticia S.A.", "cuit": "30712345671", "activity": "Software" }
```

| Campo | Descripción |
|---|---|
| `event_id` | UUID del evento. Es el mismo en cada reintento y para todos los suscriptores: sirve para deduplicar y rastrear (opcional para el receptor) |
| `event` | `account.deleted` · `account.updated` |
| `user_id` | `sub` del JWT. Para empresas es el `company_id` de jobs-service y de `/profiles/companies` |
| `role` | `student`, `company` o `admin` |
| `deleted` | `true` si la cuenta quedó borrada (soft delete) |
| `email`, `company` | Datos actuales de la cuenta (copias de sólo lectura) |
| `actor_id` | Admin que hizo el cambio |
| `occurred_at` | ISO-8601 UTC |

---

## 3. Qué hace cada receptor

| Evento | profile-service | jobs-service |
|---|---|---|
| `account.deleted` | Registra la baja y mueve el perfil de estudiante o de empresa al archivo (`profiles_deleted` / `company_profiles_deleted`); borra el logo. Sale del pool de matching, de los listados y de `/me`. Si la persona se registra de nuevo, es **otro `user_id`** y otro perfil | Registra la baja y mueve todas las ofertas de la empresa a `jobs_deleted`. Salen de `GET /jobs`, del detalle, de `/companies/me/searches` y del matching |
| `account.updated` | Empresa: actualiza la copia de razón social, CUIT y actividad. Estudiante: nada (`personal.email` es un dato de contacto que edita él) | Nada: el `company_snapshot` se arma al crear o editar una oferta |

Detalle de cada receptor: [`profiles_matching.md`](profiles_matching.md) §8 y [`jobs_matching.md`](jobs_matching.md) §11.

En los listados del admin, un borrado sólo se ve con `include_deleted=true`.

---

## 4. Seguridad y límites

- Al borrar, auth-service revoca los refresh tokens y sube la `token_version` de la cuenta: en auth-service el access token deja de valer al instante (`401 TOKEN_REVOKED`, [`auth_frontend.md`](auth_frontend.md) §4). profile-service y jobs-service validan el JWT localmente, así que lo rechazan con `401 ACCOUNT_DELETED` cuando reciben `account.deleted`: normalmente en milisegundos y, si estaban caídos, apenas vuelven (outbox, §1).
- Un evento no se pierde aunque el receptor esté caído: queda pendiente en el outbox hasta que responde `2xx`. Alertas sobre entregas que llevan mucho tiempo pendientes: core-service (fase 3 del panel de admin).
