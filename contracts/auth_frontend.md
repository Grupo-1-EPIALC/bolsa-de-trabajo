# Contrato frontend ↔ auth-service · Cuentas, sesión y tokens

> **Para:** quien desarrolla el frontend (Integrante 4) y los servicios que validan el JWT.
> **Servicio:** `auth-service` (NestJS). Fuente de verdad: `services/auth-service/src/auth/` (controller + DTOs).
> **Base URL:** same-origin detrás del gateway → `/api/v1/auth` (en dev `http://localhost:8080/api/v1/auth`).
> Todos los ejemplos usan datos ficticios. No guardes tokens reales en documentación, logs ni repositorios.

---

## 1. Endpoints

| Método y ruta | Auth | Para qué | OK |
|---|---|---|---|
| `POST /register` | — | Alta de `student` o `company` (devuelve sesión) | `201` `AuthResponse` |
| `POST /login` · alias `POST /token` | — | Iniciar sesión | `200` `AuthResponse` |
| `POST /token/refresh` | — | Renovar el par de tokens (rota el refresh) | `200` `TokenPair` |
| `GET /me` | Bearer | Datos públicos de la cuenta | `200` `PublicUser` |
| `POST /password/change` | Bearer | Cambiar la clave (cierra todas las sesiones) | `200` `Message` |
| `POST /password/reset` | — | Pedir el mail de recuperación | `200` `Message` (siempre igual) |
| `POST /password/reset/confirm` | — | Fijar clave nueva con el token del mail | `200` `Message` |
| `POST /email/change` | Bearer | Pedir cambio de email (manda mail al nuevo) | `200` `Message` |
| `POST /email/confirm` | — | Confirmar el email nuevo con el token del mail | `200` `Message` |
| `GET /.well-known/jwks.json` | — | Clave pública para validar el JWT | `200` JWKS |
| `/admin/users/...` | Bearer (admin) | Administración de cuentas y empresas (§7) | ver §7 |

- "Bearer" = header `Authorization: Bearer <access_token>`.
- Las cuentas `admin` no se crean por `/register`: se dan de alta directamente en la base.
- Una cuenta puede estar `active` o `suspended`, y además borrada (soft delete). Ver §7.

---

## 2. Respuestas

### `AuthResponse` (register y login)

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

### `TokenPair` (token/refresh)

Igual que `AuthResponse` pero **sin** `user`: `{ access_token, refresh_token, token_type, expires_in }`.

### `PublicUser` (me)

El objeto `user` de arriba: `{ id, email, role, company? }`.

### `Message`

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

## 3. Pedidos

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

## 4. Sesión y tokens

- **El registro ya inicia sesión:** devuelve los tokens, no hace falta llamar a `login` después.
- **Refresh de un solo uso:** cada `token/refresh` devuelve un refresh nuevo y revoca el anterior. Reusar uno viejo → `401`. Si dos pedidos renuevan a la vez, compartir una sola llamada (como hace `src/services/api.ts`).
- **Ante un `401`** en cualquier API: renovar una vez y reintentar; si el refresh también falla, cerrar la sesión y volver al login.
- **Cambiar o restablecer la clave revoca todos los refresh tokens** de la cuenta: hay que volver a iniciar sesión.
- **Logout:** no hay endpoint; el front borra los tokens. El access token sigue siendo válido hasta que vence (15 min).

### JWT (access token)

Header: `{ "alg": "RS256", "typ": "JWT", "kid": "bolsa-auth-1" }`

Payload:

```json
{ "sub": "<user.id>", "role": "student", "iat": 1794000271, "exp": 1794001171, "iss": "bolsa-auth", "aud": "bolsa-api" }
```

Los servicios FastAPI lo validan localmente con el JWKS: firma RS256, `iss = JWT_ISSUER` (`bolsa-auth`), `aud = JWT_AUDIENCE` (`bolsa-api`), `exp` y `role`.

### JWKS

```json
{ "keys": [ { "kty": "RSA", "n": "<módulo>", "e": "AQAB", "kid": "bolsa-auth-1", "use": "sig", "alg": "RS256" } ] }
```

---

## 5. Recuperación de clave y cambio de email

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

## 6. Errores

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
| 403 | `ACCOUNT_SUSPENDED` | Login, refresh o `/me` de una cuenta suspendida (sólo después de validar la clave) |
| 403 | `FORBIDDEN` | Un usuario que no es admin usa `/admin/...` · un admin intenta suspender o borrar su propia cuenta |
| 404 | `NOT_FOUND` | `/admin/users/{id}` inexistente o borrado |
| 409 | `CONFLICT` | Email o CUIT ya registrado (entre cuentas no borradas) · email pendiente de confirmación en otra cuenta |
| 503 | `SERVICE_UNAVAILABLE` | No se pudo enviar el mail de confirmación de email |

Los mensajes de validación vienen en inglés (class-validator). No dependas del texto: usá el HTTP y `error.code`.

---

## 7. Administración de cuentas (rol `admin`)

Todas las rutas van bajo `/api/v1/auth/admin/users`, piden `Authorization: Bearer <token de admin>` y responden `403 FORBIDDEN` a cualquier otro rol. Estudiantes y empresas se manejan con las mismas rutas (filtrar con `?role=`).

| Método y ruta | Para qué | OK |
|---|---|---|
| `GET /admin/users` | Listar cuentas | `200` `AdminUserList` |
| `GET /admin/users/{id}` | Ver una cuenta (incluye borradas) | `200` `AdminUser` |
| `PATCH /admin/users/{id}` | Editar email y/o datos de empresa | `200` `AdminUser` |
| `POST /admin/users/{id}/password-reset` | Forzar cambio de clave | `200` `{ message, email_sent }` |
| `POST /admin/users/{id}/suspend` | Suspender (body opcional `{ "reason": "…" }`, máx. 500) | `200` `AdminUser` |
| `POST /admin/users/{id}/reactivate` | Quitar la suspensión | `200` `AdminUser` |
| `DELETE /admin/users/{id}` | Borrado lógico (soft delete) | `204` |

### Filtros de `GET /admin/users`

| Parámetro | Valores | Default |
|---|---|---|
| `role` | `student` · `company` · `admin` | todos |
| `status` | `active` · `suspended` | todos |
| `q` | busca en email, razón social y CUIT | — |
| `include_deleted` | `true` para ver también las borradas (auditoría) | `false` |
| `page` · `size` | `page ≥ 1` · `size` 1–100 | `1` · `20` |

Orden: más nuevas primero.

### `AdminUser`

```json
{
  "id": "64e3d052-54f4-458e-af3f-82f81cadaed7",
  "email": "persona@example.test",
  "role": "company",
  "status": "suspended",
  "deleted": false,
  "created_at": "2026-11-06T21:44:39.588Z",
  "updated_at": "2026-11-06T21:44:40.120Z",
  "email_verified_at": null,
  "suspended_at": "2026-11-06T21:44:40.118Z",
  "suspension_reason": "Uso indebido",
  "deleted_at": null,
  "company": { "legal_name": "Empresa Ficticia S.A.", "cuit": "30712345671", "activity": "Software" }
}
```

`AdminUserList` = `{ "items": [AdminUser], "total": 41, "page": 1, "size": 20, "pages": 3 }`.

### Qué hace cada acción

| Acción | Efecto |
|---|---|
| **Editar** | `{ "email"?: string, "company"?: { "legal_name"?, "cuit"?, "activity"? } }`. El email cambia **sin confirmación** y se normaliza; el CUIT se valida con dígito verificador. `company` sólo para cuentas de empresa. Email/CUIT repetidos → `409` |
| **Forzar cambio de clave** | Invalida la clave actual, cierra todas las sesiones y manda el link de recuperación (§5) al email de la cuenta. `email_sent: false` si el mail no salió |
| **Suspender** | La cuenta sigue en los listados, pero no puede iniciar sesión ni renovar el token (`403 ACCOUNT_SUSPENDED`). Se cierran sus sesiones |
| **Reactivar** | Vuelve a `active` y borra el motivo |
| **Borrar** | Desaparece de los listados (salvo `include_deleted=true`) y no puede entrar. El **email y el CUIT quedan libres**: se puede hacer una nueva alta con los mismos datos, que es una cuenta nueva (otro `id`). La cuenta vieja queda para auditoría |

- Un admin no puede suspender ni borrar su propia cuenta (`403`).
- Suspender, reactivar, editar y borrar avisan a los demás servicios con un evento de cuenta: ver [`account_events.md`](account_events.md).
- El access token de una cuenta suspendida o borrada sigue siendo válido hasta que vence (15 min); no se puede renovar.
