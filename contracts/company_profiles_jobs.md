# Contrato jobs-service ↔ profile-service · `company_snapshot` desde el perfil de empresa

> **Para:** quien mantiene `jobs-service` (Integrante 3). **Estado:** propuesta. profile-service v0.2.0 ya lo expone; jobs-service no cambia hasta que se acuerde en la daily.
> **Regla que se respeta:** las búsquedas (ofertas) viven sólo en jobs-service. profile-service **no las guarda ni las consulta**.

---

## 1. Problema

Hoy `HttpCompanyDirectory.snapshot_for` arma `company_snapshot` con `GET /api/v1/auth/me` y sólo obtiene `legal_name` y `activity`: **`size` y `logo_url` quedan siempre en `null`**, y el nombre es la razón social, no el comercial.

## 2. Propuesta

Al crear o editar una oferta, jobs-service puede leer el snapshot del perfil de empresa:

`GET http://profile-service:8000/api/v1/profiles/companies/{company_id}` con `X-Service-Token` (red interna).

```json
{
  "company_id": "22222222-2222-4222-8222-000000000001",
  "status": "complete",
  "visibility": "public",
  "snapshot": {
    "name": "PampaTech",
    "industry": "software",
    "size": "51-200",
    "logo_url": "/api/v1/profiles/companies/22222222-2222-4222-8222-000000000001/logo?v=1793937568"
  },
  "...": "resto del perfil (vista de servicio)"
}
```

- `snapshot` tiene **exactamente la forma de `CompanySnapshot`** de jobs-service (`name`, `industry`, `size`, `logo_url`). Los campos sin valor no vienen.
- `size` usa los mismos valores (`1-10`, `11-50`, `51-200`, `201-1000`, `1000+`).
- `logo_url` es una ruta relativa same-origin y pública (sirve en `<img>` sin token).
- `company_id` = `sub` de la empresa en auth-service = `JobOpportunity.company_id`.
- Si la empresa todavía no completó su perfil → `404 COMPANY_PROFILE_NOT_FOUND`. jobs-service sigue con su fallback actual (auth-service).

Sugerencia de implementación (sin cambiar la interfaz `CompanyDirectory`): un `ProfileCompanyDirectory` que pruebe profile-service y, ante un 404 o un error, use el `HttpCompanyDirectory` actual. Necesita `PROFILE_SERVICE_URL` en el compose de jobs-service.

## 3. Seed

profile-service carga 10 perfiles de empresa ficticios (`PROFILE_SEED_DEMO=true`) con los mismos `company_id` y nombres que el seed de jobs-service (`PampaTech S.A.`, `Andes Digital S.R.L.`, …), así los dos seeds son coherentes.

## 4. Pendiente del lado de jobs-service (para el front)

- Un filtro `GET /api/v1/jobs?company_id=…&status=active` para que el perfil público de una empresa muestre sus ofertas a los estudiantes. Hoy el front tiene que filtrar el listado completo.
- **Gateway:** la raíz `/api/v1/jobs` no se puede usar desde afuera. Nginx (`location /api/v1/jobs/`) redirige `/api/v1/jobs` a `/api/v1/jobs/`, y FastAPI redirige `/api/v1/jobs/` a `/api/v1/jobs` **perdiendo el puerto** (`Location: http://localhost/api/v1/jobs`). Pasa en `GET` (listar) y `POST` (crear). Se arregla con un `location = /api/v1/jobs { … }` exacto en `gateway/nginx.conf`, o con `redirect_slashes=False` y la ruta `"/"` en jobs-service.
