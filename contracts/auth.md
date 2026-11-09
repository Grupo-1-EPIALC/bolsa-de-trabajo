# Contrato · auth-service

> **Para:** el frontend, los servicios que validan el JWT (profile, jobs, matching) y los que reciben eventos de cuenta.
> **Servicio:** `auth-service` 0.2.0 (NestJS) · base `/api/v1/auth`.
> **Fuente de verdad viva:** [Swagger UI](/api/v1/auth/docs) · [ReDoc](/api/v1/auth/redoc) · [OpenAPI](/api/v1/auth/openapi.json) (por el gateway, en dev `http://localhost:8080`).
> **Partes:** A. API (cuentas, sesión, tokens y administración) · B. Eventos de cuenta (auth → servicios) · C. Documentación de la API. Los `§` de cada parte se refieren a esa parte.
> Los documentos de los que sale este contrato están en [`historico/`](historico/). Todos los ejemplos usan datos ficticios.

---

## A. API: cuentas, sesión, tokens y administración

> Fuente: [`historico/auth_frontend.md`](historico/auth_frontend.md).

### 1. Endpoints

| Método y ruta | Auth | Para qué | OK |
|---|---|---|---|
| `POST /register` | — | Alta de `student` o `company` (devuelve sesión) | `201` `AuthResponse` |
| `POST /login` · alias `POST /token` | — | Iniciar sesión | `200` `AuthResponse` |
| `POST /token/refresh` | — | Renovar el par de tokens (rota el refresh) | `200` `TokenPair` |
| `GET /me` | Bearer | Datos públicos de la cuenta | `200` `PublicUser` |
| `POST /password/change` | Bearer | Cambiar la clave (cierra todas las sesiones y el access token actual deja de valer) | `200` `Message` |
| `POST /password/reset` | — | Pedir el mail de recuperación | `200` `Message` (siempre igual) |
| `POST /password/reset/confirm` | — | Fijar clave nueva con el token del mail | `200` `Message` |
| `POST /email/change` | Bearer | Pedir cambio de email (manda mail al nuevo) | `200` `Message` |
| `POST /email/confirm` | — | Confirmar el email nuevo con el token del mail | `200` `Message` |
| `GET /.well-known/jwks.json` | — | Clave pública para validar el JWT | `200` JWKS |
| `/admin/users/...` | Bearer (admin) | Administración de cuentas y empresas (§7) | ver §7 |

- "Bearer" = header `Authorization: Bearer <access_token>`.
- Las cuentas `admin` no se crean por `/register`: se dan de alta directamente en la base.
- Una cuenta puede estar borrada (soft delete): para login, refresh y `/me` es como si no existiera. Ver §7.

---

### 2. Respuestas

#### `AuthResponse` (register y login)

```json
{
  "user": {
    "id": "746c880a-67b7-4a41-ba2d-1d07687933db",
    "email": "estudiante@example.test",
    "role": "student"
  },
  "access_token": "<access-token>",
  "refresh_token": "<refresh-token>",
  "token_type": "Bearer",
  "expires_in": "15m"
}
```

Para una empresa, `user` incluye además `company`:

```json
{
  "id": "6e80d17c-8fd1-4ba9-9f31-cfb56cde8bea",
  "email": "empresa@example.test",
  "role": "company",
  "company": { "legal_name": "Empresa de ejemplo", "cuit": "30712345678", "activity": "Servicios" }
}
```

#### `TokenPair` (token/refresh)

Igual que `AuthResponse` pero **sin** `user`: `{ access_token, refresh_token, token_type, expires_in }`.

#### `PublicUser` (me)

El objeto `user` de arriba: `{ id, email, role, company? }`.

#### `Message`

```json
{ "message": "Contraseña actualizada. Iniciá sesión nuevamente." }
```

| Campo | Tipo | Descripción |
|---|---|---|
| `user.id` | string (UUID) | Id de la cuenta. Es el `sub` del JWT y el `company_id` de las ofertas en jobs-service. |
| `user.email` | string | Email normalizado (sin espacios, en minúsculas). |
| `user.role` | string | `student`, `company` o `admin`. |
| `user.company` | object | Sólo empresas: `legal_name`, `cuit`, `activity`. |
| `access_token` | string | JWT RS256. Dura `JWT_ACCESS_TTL` (por defecto `15m`). |
| `refresh_token` | string | Opaco, 64 caracteres. Dura `JWT_REFRESH_TTL` (por defecto `7d`). Tratarlo como secreto. |
| `token_type` | string | Siempre `Bearer`. |
| `expires_in` | string | Duración del access token (`15m`). |

Ninguna respuesta expone la contraseña ni su hash.

---

### 3. Pedidos

| Endpoint | Body | Reglas |
|---|---|---|
| `register` | `{ email, password, role, company? }` | `email` válido (máx. 320) · `password` 12–128 · `role` = `student` \| `company` · `company` obligatorio si `role = company`: `{ legal_name (1–200), cuit (11 dígitos, dígito verificador válido), activity (1–160) }` |
| `login` / `token` | `{ email, password }` | `password` 1–128 |
| `token/refresh` | `{ refresh_token }` | 32–256 caracteres |
| `password/change` | `{ current_password, new_password }` | `new_password` 12–128 y distinta de la actual |
| `password/reset` | `{ email }` | — |
| `password/reset/confirm` | `{ token, new_password }` | `token` 32–256 · `new_password` 12–128 |
| `email/change` | `{ email, current_password }` | email distinto del actual y no registrado |
| `email/confirm` | `{ token }` | `token` 32–256 |

Ejemplo de registro de empresa:

```json
{
  "email": "rrhh@empresa.example.test",
  "password": "UnaClaveLarga123!",
  "role": "company",
  "company": { "legal_name": "Empresa de ejemplo S.A.", "cuit": "30712345671", "activity": "Desarrollo de software" }
}
```

---

### 4. Sesión y tokens

- **El registro ya inicia sesión:** devuelve los tokens, no hace falta llamar a `login` después.
- **Refresh de un solo uso:** cada `token/refresh` devuelve un refresh nuevo y revoca el anterior. Reusar uno viejo → `401`. Si dos pedidos renuevan a la vez, compartir una sola llamada (como hace `src/services/api.ts`).
- **Ante un `401`** en cualquier API: renovar una vez y reintentar; si el refresh también falla, cerrar la sesión y volver al login.
- **Cambiar o restablecer la clave revoca todos los refresh tokens** de la cuenta y **también los access tokens ya emitidos** (`token_version`, ver abajo): en auth-service el token actual recibe `401 TOKEN_REVOKED` al instante. Hay que volver a iniciar sesión.
- **Logout:** no hay endpoint; el front borra los tokens. El access token sigue siendo válido hasta que vence (15 min).

#### JWT (access token)

Header: `{ "alg": "RS256", "typ": "JWT", "kid": "bolsa-auth-1" }`

Payload:

```json
{ "sub": "<user.id>", "role": "student", "tv": 0, "iat": 1794000271, "exp": 1794001171, "iss": "bolsa-auth", "aud": "bolsa-api" }
```

Los servicios FastAPI lo validan localmente con el JWKS: firma RS256, `iss = JWT_ISSUER` (`bolsa-auth`), `aud = JWT_AUDIENCE` (`bolsa-api`), `exp` y `role`.

**`tv` (token version):** auth-service además compara `tv` con la `token_version` de la cuenta en **cada request** propio (`/me`, `/password/change`, `/admin/users`…). La versión sube con el reset forzado y el borrado del admin, el cambio de clave y la recuperación de clave: los access tokens emitidos antes reciben `401 TOKEN_REVOKED` sin esperar los 15 min. También da `TOKEN_REVOKED` si la cuenta fue borrada o cambió de rol. Un token sin `tv` (emitido antes de este cambio) vale como versión `0`. Los demás servicios no consultan a auth en cada request: una cuenta borrada la cortan con el evento `account.deleted` (`401 ACCOUNT_DELETED`, [`auth.md`](auth.md) §4).

#### JWKS

```json
{ "keys": [ { "kty": "RSA", "n": "<módulo>", "e": "AQAB", "kid": "bolsa-auth-1", "use": "sig", "alg": "RS256" } ] }
```

---

### 5. Recuperación de clave y cambio de email

Los mails (Mailpit en dev, http://localhost:8025) traen un link **al front** con el token:

| Flujo | Link del mail | El front debe |
|---|---|---|
| Recuperar clave | `{FRONTEND_URL}/auth/password/reset/confirm?token=…` | Pedir la clave nueva y llamar `POST /password/reset/confirm` |
| Cambiar email | `{FRONTEND_URL}/auth/email/confirm?token=…` | Llamar `POST /email/confirm` y avisar el resultado |

- `FRONTEND_URL` por defecto `http://localhost:8080`.
- Token de recuperación: un solo uso, dura `PASSWORD_RESET_TTL` (`1h`). Token de email: un solo uso, `1h`.
- `password/reset` responde **siempre lo mismo**, exista o no el email (no revela cuentas):
  `{"message": "Si el email está registrado, recibirás instrucciones para restablecer la contraseña."}`

---

### 6. Errores

Formato común del servicio:

```json
{ "error": { "code": "CONFLICT", "message": "El email o CUIT ya está registrado", "details": {} } }
```

En los errores de validación `message` es **una lista** y se repite en `details.validation_errors`:

```json
{
  "error": {
    "code": "BAD_REQUEST",
    "message": ["email must be an email", "password must be longer than or equal to 12 characters"],
    "details": { "validation_errors": ["email must be an email", "password must be longer than or equal to 12 characters"] }
  }
}
```

| HTTP | `code` | Cuándo |
|---|---|---|
| 400 | `BAD_REQUEST` | Validación (lista en `details.validation_errors`), CUIT inválido, clave nueva igual a la actual, email nuevo igual al actual, token de recuperación o de email inválido o vencido |
| 401 | `UNAUTHORIZED` | Email o contraseña incorrectos (mismo mensaje para ambos) · clave actual incorrecta · refresh inválido, vencido o ya usado |
| 401 | `HTTP_401` | Falta el Bearer o el access token es inválido o venció (`message: "Unauthorized"`) |
| 401 | `TOKEN_REVOKED` | El access token fue revocado: reset o cambio de clave, cuenta borrada o rol distinto. Si la clave cambió, renovar no sirve: volver al login |
| 403 | `FORBIDDEN` | Un usuario que no es admin usa `/admin/...` · un admin intenta borrar su propia cuenta |
| 404 | `NOT_FOUND` | `/admin/users/{id}` inexistente o borrado |
| 409 | `CONFLICT` | Email o CUIT ya registrado (entre cuentas no borradas) · email pendiente de confirmación en otra cuenta |
| 503 | `SERVICE_UNAVAILABLE` | No se pudo enviar el mail de confirmación de email |

Los mensajes de validación vienen en inglés (class-validator). No dependas del texto: usá el HTTP y `error.code`.

---

### 7. Administración de cuentas (rol `admin`)

Todas las rutas van bajo `/api/v1/auth/admin/users`, piden `Authorization: Bearer <token de admin>` y responden `403 FORBIDDEN` a cualquier otro rol. Estudiantes y empresas se manejan con las mismas rutas (filtrar con `?role=`).

| Método y ruta | Para qué | OK |
|---|---|---|
| `GET /admin/users` | Listar cuentas | `200` `AdminUserList` |
| `GET /admin/users/{id}` | Ver una cuenta (incluye borradas) | `200` `AdminUser` |
| `PATCH /admin/users/{id}` | Editar email y/o datos de empresa | `200` `AdminUser` |
| `POST /admin/users/{id}/password-reset` | Forzar cambio de clave | `200` `{ message, email_sent }` |
| `DELETE /admin/users/{id}` | Borrado lógico (soft delete) | `204` |

#### Filtros de `GET /admin/users`

| Parámetro | Valores | Default |
|---|---|---|
| `role` | `student` · `company` · `admin` | todos |
| `q` | busca en email, razón social y CUIT | — |
| `include_deleted` | `true` para ver también las borradas (auditoría) | `false` |
| `page` · `size` | `page ≥ 1` · `size` 1–100 | `1` · `20` |

Orden: más nuevas primero. Un parámetro desconocido da `400`.

#### `AdminUser`

```json
{
  "id": "64e3d052-54f4-458e-af3f-82f81cadaed7",
  "email": "persona@example.test",
  "role": "company",
  "deleted": false,
  "created_at": "2026-11-06T21:44:39.588Z",
  "updated_at": "2026-11-06T21:44:40.120Z",
  "email_verified_at": null,
  "deleted_at": null,
  "company": { "legal_name": "Empresa Ficticia S.A.", "cuit": "30712345671", "activity": "Software" }
}
```

`AdminUserList` = `{ "items": [AdminUser], "total": 41, "page": 1, "size": 20, "pages": 3 }`.

#### Qué hace cada acción

| Acción | Efecto |
|---|---|
| **Editar** | `{ "email"?: string, "company"?: { "legal_name"?, "cuit"?, "activity"? } }`. El email cambia **sin confirmación** y se normaliza; el CUIT se valida con dígito verificador. `company` sólo para cuentas de empresa. Email/CUIT repetidos → `409` |
| **Forzar cambio de clave** | Invalida la clave actual, cierra todas las sesiones, corta los access tokens vigentes (`401 TOKEN_REVOKED`) y manda el link de recuperación (§5) al email de la cuenta. `email_sent: false` si el mail no salió |
| **Borrar** | Desaparece de los listados (salvo `include_deleted=true`) y no puede entrar (login `401`, como un email inexistente). Se cierran sus sesiones y sus access tokens dejan de valer en auth-service al instante (`401 TOKEN_REVOKED`). El **email y el CUIT quedan libres**: se puede hacer una nueva alta con los mismos datos, que es una cuenta nueva (otro `id`). La cuenta vieja queda para auditoría |

- Un admin no puede borrar su propia cuenta (`403`).
- Editar y borrar avisan a los demás servicios con un evento de cuenta: ver [`auth.md`](auth.md).
- En auth-service, el access token de una cuenta borrada o reseteada deja de valer al instante. En profile-service y jobs-service se corta cuando reciben `account.deleted`, que llega aunque estén caídos un rato (outbox con reintentos, [`auth.md`](auth.md) §1).

## B. Eventos de cuenta (auth-service → servicios)

> Fuente: [`historico/account_events.md`](historico/account_events.md).

Cuando un admin edita o borra una cuenta, auth-service avisa a cada servicio para que actualice u oculte los datos de esa cuenta. Cada servicio sólo cambia sus propios datos (AGENTS §2.1).

### 1. Entrega

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

### 2. Cuerpo

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

### 3. Qué hace cada receptor

| Evento | profile-service | jobs-service |
|---|---|---|
| `account.deleted` | Registra la baja y mueve el perfil de estudiante o de empresa al archivo (`profiles_deleted` / `company_profiles_deleted`); borra el logo. Sale del pool de matching, de los listados y de `/me`. Si la persona se registra de nuevo, es **otro `user_id`** y otro perfil | Registra la baja y mueve todas las ofertas de la empresa a `jobs_deleted`. Salen de `GET /jobs`, del detalle, de `/companies/me/searches` y del matching |
| `account.updated` | Empresa: actualiza la copia de razón social, CUIT y actividad. Estudiante: nada (`personal.email` es un dato de contacto que edita él) | Nada: el `company_snapshot` se arma al crear o editar una oferta |

Detalle de cada receptor: [`profile.md`](profile.md) §8 y [`jobs.md`](jobs.md) §11.

En los listados del admin, un borrado sólo se ve con `include_deleted=true`.

---

### 4. Seguridad y límites

- Al borrar, auth-service revoca los refresh tokens y sube la `token_version` de la cuenta: en auth-service el access token deja de valer al instante (`401 TOKEN_REVOKED`, [`auth.md`](auth.md) §4). profile-service y jobs-service validan el JWT localmente, así que lo rechazan con `401 ACCOUNT_DELETED` cuando reciben `account.deleted`: normalmente en milisegundos y, si estaban caídos, apenas vuelven (outbox, §1).
- Un evento no se pierde aunque el receptor esté caído: queda pendiente en el outbox hasta que responde `2xx`. Alertas sobre entregas que llevan mucho tiempo pendientes: core-service (fase 3 del panel de admin).

## C. Documentación de la API

- Swagger UI `/api/v1/auth/docs`, ReDoc `/api/v1/auth/redoc` y OpenAPI `/api/v1/auth/openapi.json`, generados con `@nestjs/swagger` desde los controllers y DTOs (`class-validator`).
- Las rutas protegidas tienen el esquema `bearer` (JWT): en Swagger UI, "Authorize" acepta un `access_token`.
- El panel de admin enlaza la documentación de los cuatro servicios REST.
