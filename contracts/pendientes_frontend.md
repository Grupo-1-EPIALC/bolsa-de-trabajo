# Front · Lo que falta construir

> Relevado sobre `dev-tmp` (front 0.3.0) contra los contratos de `contracts/`. Sólo lista pantallas y llamadas que el backend **ya ofrece** y el front todavía no usa, más lo que pide `AGENTS.md` §4.7.

## Resumen

| # | Qué | Backend | Prioridad |
|---|---|---|---|
| 1 | ~~Recuperar clave (pedir mail + pantalla del link)~~ | ✅ Hecho en PR v0.5.0 | Alta |
| 2 | ~~Confirmar cambio de email (pantalla del link)~~ | ✅ Hecho en PR v0.5.0 | Alta |
| 3 | ~~"Mi cuenta": cambiar clave y email~~ | ✅ Hecho en PR v0.5.0 | Alta |
| 4 | ~~Panel de administración de cuentas~~ ✅ hecho en front 0.4.0 (P-025) | auth ✅ | Alta (fase 2) |
| 5 | ~~Admin: configuración de matching~~ ✅ hecho en front 0.4.0 (P-025) | matching ✅ | Media |
| 6 | Modal "¿Por qué este puntaje?" | matching ✅ | Media |
| 7 | Perfil público de la empresa desde una oferta | profile ✅ | Media |
| 8 | Recomendaciones de formación (`mode=training`) | n8n WF-06 ✅ / matching ❓ | Media |
| 9 | Manejo de `401 ACCOUNT_DELETED` | profile/jobs ✅ | Baja |
| 10 | Deuda técnica de `AGENTS.md` §4.7 | — | Para discutir |

---

## 1. Recuperar clave

> Implementado en front 0.5.0.

**Contrato:** `auth_frontend.md` §1, §3 y §5.

- **Pedir el mail:** un link "¿Olvidaste tu clave?" en `AuthForm` llama a `POST /api/v1/auth/password/reset` con `{ email }`.
  - La respuesta es **siempre la misma**, exista o no la cuenta. El front muestra un mensaje genérico ("Si el email está registrado, te enviamos un link") y nunca dice si la cuenta existe.
- **Pantalla del link del mail:** `{FRONTEND_URL}/auth/password/reset/confirm?token=…`.
  - Lee el `token` de la URL y pide la clave nueva dos veces (12–128 caracteres, igual que el alta).
  - Llama a `POST /password/reset/confirm` con `{ token, new_password }`.
  - Si sale bien, manda a "Ingresar". Si el token es inválido o venció, muestra un error y ofrece pedir otro mail.
- **Sin router:** hoy la SPA navega por estado (`navigation.ts`), así que al arrancar hay que leer `window.location.pathname` y `search` para abrir estas pantallas (ver punto 10).
- **Probar** con Mailpit (`http://localhost:8025`).

## 2. Confirmar el cambio de email

> Implementado en front 0.5.0. 

**Contrato:** `auth_frontend.md` §5.

- **Pantalla del link:** `{FRONTEND_URL}/auth/email/confirm?token=…`.
  - Llama a `POST /api/v1/auth/email/confirm` con `{ token }` y muestra el resultado.
  - Como el cambio rota la sesión, conviene pedir que vuelva a ingresar.

## 3. "Mi cuenta" (estudiante y empresa)

> Implementado en front 0.5.0.

**Contrato:** `auth_frontend.md` §1, §3 y §6.

- Una sección nueva en el menú (`StudentSection` + header y footer).
- **Datos de la cuenta:** se muestran con `GET /auth/me` (email y rol).
- **Cambiar clave:** `POST /password/change` con `{ current_password, new_password }`.
  - Cierra **todas** las sesiones, así que después hay que limpiar la sesión (`session.clear()`) y mandar a ingresar.
- **Cambiar email:** `POST /email/change` con `{ email, current_password }`.
  - Avisar "Te mandamos un mail al nuevo email para confirmarlo".
  - `409`: email ya usado. `503`: no se pudo mandar el mail.
- **Servicio:** sumar a `authService` los métodos `me`, `changePassword`, `requestEmailChange`, `confirmEmail`, `requestPasswordReset` y `confirmPasswordReset`.

## 4. Panel de administración de cuentas (fase 2) · ✅ hecho

> Implementado en front 0.4.0 (`pages/AdminArea.tsx`, `components/admin/`). Se deja el detalle como referencia.

**Contrato:** `auth_frontend.md` §7. Hoy `CompanyArea` muestra "La consola de administración todavía no está disponible" para el rol `admin`.

- **Área propia para `admin`:** separarla de `CompanyArea` en `AdminArea`. El usuario de demo es `admin@bolsa.local`.
- **Listado:** `GET /api/v1/auth/admin/users`, con los filtros de §7 (rol, búsqueda, incluir borradas, paginación).
- **Detalle:** `GET /admin/users/{id}`, que también trae las cuentas borradas.
- **Editar:** `PATCH /admin/users/{id}` con el email y, si es empresa, la razón social, el CUIT y la actividad.
  - El CUIT se valida en el cliente con el dígito verificador, reutilizando la validación de `AuthForm`.
  - `409` si el email o el CUIT ya existen.
- **Forzar cambio de clave:** `POST /admin/users/{id}/password-reset`. Mostrar `email_sent`.
- **Borrar:** `DELETE /admin/users/{id}` es un borrado lógico.
  - Pedir confirmación y avisar que el perfil y las búsquedas se archivan.
  - El admin no puede borrarse a sí mismo (`403`), así que el botón se oculta en su propia fila.
- **Tipos:** `AdminUser` y `AdminUserList` en `types/admin.ts`.

## 5. Admin: configuración de matching · ✅ hecho

> Implementado en front 0.4.0 (`components/admin/MatchingSettings.tsx`).

**Contrato:** `matching_frontend.md` §3 y §4.5.

- Se lee con `GET /api/v1/matches/settings` y se guarda con `PATCH /api/v1/matches/settings`.
- Edita `student_jobs_limit` (por defecto 5) y `company_candidates_limit` (por defecto 10), cada uno de 1 a 20.
- Hay que aclarar en la pantalla que hoy se guarda **en memoria**: se pierde al reiniciar matching (§8).

## 6. Modal "¿Por qué este puntaje?"

**Contrato:** `matching_frontend.md` §3, §4.4 y §5.

- Lo abre un botón en `RuleMatch`, tanto en las recomendaciones del estudiante como en los candidatos de la empresa.
- Llama a `POST /api/v1/matches` con `{ profile_id, job_id }` y muestra el desglose de los 6 criterios (requeridas 50, deseables 15, niveles 15, experiencia 10, formación 5, idiomas 5).
  - Si se aplicó la **regla excluyente**, lo indica (tope de 40).
  - Debajo, `conditions_fit` y `salary_fit` en un bloque separado, porque no suman al score.
- Lleva el badge verde "Calculado por reglas".

## 7. Perfil público de la empresa desde una oferta

**Contrato:** `company_profile_frontend.md` §3 y §8.

- En `JobDetail`, el nombre de la empresa (`company_snapshot.name`) pasa a ser un link.
  - Abre `GET /api/v1/profiles/companies/{job.company_id}` con la marca empleadora, la descripción, los beneficios y los links.
  - El logo se carga directo en un `<img src="/api/v1/profiles/companies/{id}/logo">`, sin token.
- `CompanyLogo` ya existe y se puede reutilizar.

## 8. Recomendaciones de formación (`mode=training`)

**Contrato:** `AGENTS.md` §5 (Training Advisor, `student_recommendations.schema.json`).

- **Ubicación:** en una oferta recomendada o en el modal del punto 6, un botón "¿Cómo me preparo para esta oferta?". Muestra cursos, proyectos y tips priorizados (alta, media o baja) con el badge ámbar "Sugerido por IA" y el disclaimer.
- **⚠ Antes de construirlo:** confirmar con matching y n8n cómo se pide desde el front. `POST /matches/recommendations/requests` hoy acepta `mode=student|company`, y no está claro que `training` pase por ahí ni dónde se lee el resultado.

## 9. `401 ACCOUNT_DELETED`

**Contrato:** `account_events.md`, `profiles_matching.md` §8 y `jobs_matching.md` §11.

- Si un admin borra la cuenta, profile y jobs responden `401` con el código `ACCOUNT_DELETED`.
- Hoy `api.ts` intenta renovar el token y después muestra "Tu sesión venció". Con ese código conviene no reintentar, cerrar la sesión y avisar "Tu cuenta fue dada de baja".

## 10. Deuda técnica frente a `AGENTS.md` §4.7

`AGENTS.md` §4.7 nombra herramientas que el front todavía no usa. Hay que decidir en la daily si se suman o si se actualiza `AGENTS.md`; agregar una librería se discute antes (§2.4).

| Pide `AGENTS.md` | Hoy | Comentario |
|---|---|---|
| React Router | Navegación por estado (`navigation.ts`) | Los links de los mails (puntos 1 y 2) **necesitan** leer la URL: con router es directo; sin router, se resuelve leyendo `location` al iniciar |
| TanStack Query | `useEffect` + estado propio | Opcional; simplificaría el polling de los pedidos de IA y del CV |
| React Hook Form + Zod | Validación a mano (`jobs/form.ts`, `profile/draft.ts`) | Funciona y tiene tests |
| Cliente en `src/api/client.ts` | `src/services/api.ts` | Sólo cambia el nombre o la ubicación |
| Tests UT-FE-01 a UT-FE-04 | 34 tests Vitest, sin esos IDs | Etiquetar los existentes con los IDs del plan |

## Fuera del front (pero bloquea o afecta pantallas)

- **Postulaciones:** fase 5. Todavía no hay backend; cuando exista, falta el botón "Postularme" y las vistas "Mis postulaciones" y "Postulantes".
- **Panel de salud, eventos y alertas:** espera a `core-service` (fase 3).
- **Pesos y score mínimo del matching:** fase 4. Hoy viven en `scoring_rules.yaml` y no tienen endpoint.
- **Persistencia de matching:** las recomendaciones de IA, los pedidos y la configuración se guardan en memoria.
- **Skills duplicadas:** una skill puede aparecer a la vez como "tiene" y como "le falta". Es un problema de matching, pero se nota en `RuleMatch`.
