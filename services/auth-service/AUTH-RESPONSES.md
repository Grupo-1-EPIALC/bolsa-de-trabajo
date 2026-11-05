# Respuestas de registro e inicio de sesión

Este documento describe las respuestas de `POST /api/v1/auth/register` y
`POST /api/v1/auth/login` del servicio de autenticación.

Todas las respuestas están en JSON. Los ejemplos usan valores ficticios: no
compartas ni guardes tokens reales en documentación, logs o repositorios.

## `POST /api/v1/auth/register`

Crea una cuenta y devuelve la información pública del usuario junto con los
tokens de autenticación.

- **Éxito:** `201 Created`
- **Content-Type:** `application/json`
- **Roles admitidos:** `student` y `company`
- Para una cuenta `company`, el objeto `user` incluye además `company`.

Ejemplo de respuesta para un estudiante:

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

Ejemplo del objeto `user` para una empresa:

```json
{
  "id": "6e80d17c-8fd1-4ba9-9f31-cfb56cde8bea",
  "email": "empresa@example.test",
  "role": "company",
  "company": {
    "legal_name": "Empresa de ejemplo",
    "cuit": "30712345678",
    "activity": "Servicios"
  }
}
```

## `POST /api/v1/auth/login`

Valida las credenciales y devuelve la información pública del usuario y tokens
con el mismo formato que el registro.

- **Éxito:** `200 OK`
- **Content-Type:** `application/json`

Ejemplo:

```json
{
  "user": {
    "id": "58520abc-5e13-4daf-aa39-a80072346381",
    "email": "estudiante@example.test",
    "role": "student"
  },
  "access_token": "<access-token>",
  "refresh_token": "<refresh-token>",
  "token_type": "Bearer",
  "expires_in": "15m"
}
```

## Campos de respuesta

| Campo | Tipo | Descripción |
|---|---|---|
| `user.id` | string (UUID) | Identificador de la cuenta. |
| `user.email` | string | Email de la cuenta. |
| `user.role` | string | Rol: `student` o `company` para cuentas creadas por registro. |
| `user.company` | object | Datos públicos de la empresa; sólo se incluye para cuentas de empresa. |
| `user.company.legal_name` | string | Razón social. |
| `user.company.cuit` | string | CUIT registrado. |
| `user.company.activity` | string | Actividad de la empresa. |
| `access_token` | string | JWT de acceso. Enviarlo en el encabezado `Authorization` con el esquema `Bearer`. |
| `refresh_token` | string | Token para solicitar un nuevo par de tokens. Tratarlo como secreto. |
| `token_type` | string | Es `Bearer`. |
| `expires_in` | string | Duración del access token; por defecto `15m`, configurable mediante `JWT_ACCESS_TTL`. |

El email se normaliza quitando espacios al principio y al final y convirtiéndolo
a minúsculas. La respuesta no expone la contraseña ni su hash.

## Errores

Los errores siguen el formato común del servicio:

```json
{
  "error": {
    "code": "CODIGO_DEL_ERROR",
    "message": "Descripción del error",
    "details": {}
  }
}
```

| Endpoint | HTTP | Situación |
|---|---:|---|
| Registro | `400 Bad Request` | Datos inválidos o CUIT de empresa no válido. |
| Registro | `409 Conflict` | Email o CUIT ya registrado. |
| Login | `400 Bad Request` | Datos de entrada inválidos. |
| Login | `401 Unauthorized` | Email o contraseña incorrectos. El mensaje es el mismo para ambos casos. |

Para errores de validación, `details.validation_errors` contiene la lista de
errores de validación. No dependas de un texto de error específico para
controlar el flujo del cliente; usa el código HTTP y `error.code`.
