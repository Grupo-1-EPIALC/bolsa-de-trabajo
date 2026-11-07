# Contrato de eventos de cuenta · auth-service → servicios

> **Para:** quienes mantienen profile-service, jobs-service y core-service.
> **Emisor:** `auth-service` (dueño de las cuentas). **Origen:** acciones del panel de administración (`contracts/auth_frontend.md` §7).

Cuando un admin edita o borra una cuenta, auth-service avisa a cada servicio para que actualice u oculte los datos de esa cuenta. Cada servicio sólo cambia sus propios datos (AGENTS §2.1).

---

## 1. Entrega

- `POST` a cada URL de `ACCOUNT_EVENT_WEBHOOKS` (separadas por coma, en el `.env` de auth-service).
- Header `X-Service-Token: <SERVICE_TOKEN>`. El receptor rechaza cualquier otro pedido con `401`/`403`.
- `Content-Type: application/json`. Timeout de 5 s por suscriptor.
- **Best effort:** si un suscriptor falla o no responde, auth-service lo registra en su log y sigue. La operación del admin no se revierte.
- El receptor responde `2xx` rápido y **tiene que ser idempotente**: el mismo evento puede llegar dos veces.
- Ruta sugerida para cada receptor: `POST /api/v1/<recurso>/internal/account-events` (interna, nunca para usuarios).

---

## 2. Cuerpo

```json
{
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
| `account.deleted` | Perfil marcado como borrado: no aparece en ningún listado ni en el matching. Si la persona se registra de nuevo, es **otro `user_id`** y otro perfil | Búsquedas de la empresa marcadas como borradas y fuera de todos los listados |
| `account.updated` | Actualizar la copia del email (`personal.email` sólo si el estudiante no lo cambió) y de los datos legales de la empresa | Actualizar `company_snapshot` si cambió la razón social |

En los listados del admin, un borrado sólo se ve con `include_deleted=true`.

---

## 4. Seguridad y límites

- El access token (JWT) de una cuenta borrada sigue siendo válido hasta que vence (15 min): auth-service revoca los refresh tokens, así no puede renovarlo. Los receptores deben chequear la marca de borrado que guardaron con este evento en los endpoints sensibles.
- Si un evento se pierde (servicio caído), hoy no hay reintento automático. Lo va a cubrir core-service (registro de eventos y alertas, fase 3 del panel de admin).
