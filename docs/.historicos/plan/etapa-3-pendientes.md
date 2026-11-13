# Etapa 3 · Lo que queda (front)

> **Para:** el equipo, en especial quien mantiene el front (Integrante 4) y quien lo revisa (Integrante 3).
> **Estado al 2026-11-08:** de la etapa 3 ya está hecha la formación sugerida por IA ("¿Cómo mejorar para esta oferta?", PR #35, front 0.7.0). Este documento detalla lo que falta, con el orden sugerido y cómo dar cada ítem por terminado.
> **Antes de arrancar:** mergear los PR #29 a #35 en orden. Esta etapa parte de ahí (front 0.7.0, matching 0.2.0).

---

## Resumen

| # | Ítem | Servicios | Tamaño | Prioridad |
|---|---|---|---|---|
| 1 | Mensajes claros cuando un admin borra o resetea la cuenta (`401 ACCOUNT_DELETED` / `TOKEN_REVOKED`) | front | S | Alta |
| 2 | Perfil público de la empresa desde una oferta | front + matching (un campo) | M | Media |
| 3 | Volver a poner "Todas las ofertas" en el menú del estudiante | front | XS | Media |
| 4 | Tests UT-FE-01 a UT-FE-04 del plan | front | M | Media |
| 5 | Poner al día `docs/frontend/pendientes.md` | docs | XS | Baja |
| 6 | Decidir la deuda técnica de AGENTS §4.7 (React Router, TanStack Query, React Hook Form + Zod) | daily + docs | — | Para decidir |

**Rama sugerida:** `feature/frontend/v0.8.0-pendientes-etapa-3` (ítems 1, 3, 4 y 5). Del ítem 2, el campo que falta en matching va en `feature/matching/v0.2.1-company-id-en-snapshot`.
Tamaños: XS < 1 h · S ≈ medio día · M ≈ un día.

---

## 1. Mensajes claros cuando un admin borra o resetea la cuenta

**Problema.** Cuando un admin borra una cuenta o fuerza el cambio de clave, el próximo pedido del usuario recibe `401`:
- `ACCOUNT_DELETED` desde profile-service o jobs-service;
- `TOKEN_REVOKED` desde auth-service.

Hoy `src/services/api.ts` intenta renovar el token, falla, borra la sesión y muestra el genérico "Tu sesión venció. Volvé a ingresar.". El usuario no entiende qué pasó.

**Qué hacer**
- En `apiRequest`, si la respuesta es `401` con `error.code` igual a `ACCOUNT_DELETED` o `TOKEN_REVOKED`, **no renovar**: cerrar la sesión con un motivo.
  - `ACCOUNT_DELETED` → "Tu cuenta fue dada de baja. Si creés que es un error, escribinos."
  - `TOKEN_REVOKED` → "Tu clave cambió o tu sesión fue cerrada. Ingresá de nuevo." Si el admin forzó el reset, el mail de recuperación ya está en camino.
- `session.clear(reason?)` guarda el motivo y `AuthPage` lo muestra una vez arriba del formulario (`role="alert"`).
- El código se lee del cuerpo con el formato común `{"error": {"code", ...}}`, que `toApiError` ya parsea.

**Contratos:** [`contracts/auth.md`](../../contracts/auth.md) parte A §4 y §6 (`TOKEN_REVOKED`) y [`contracts/profile.md`](../../contracts/profile.md) parte C §8 (`ACCOUNT_DELETED`; jobs igual).

**Terminado cuando**
- [ ] Un admin borra la cuenta de un estudiante con sesión abierta → al navegar, el estudiante vuelve al login con el mensaje de baja, sin pasar por el refresh.
- [ ] Un admin fuerza el cambio de clave → el usuario ve el mensaje de clave cambiada.
- [ ] Un access token vencido común sigue renovándose solo (sin cambios de comportamiento).
- [ ] Tests de `api.ts` con `fetch` simulado: los dos códigos no llaman a `/token/refresh` y dejan el motivo; un `401` sin código sí renueva.

---

## 2. Perfil público de la empresa desde una oferta

**Problema.** El estudiante ve el nombre de la empresa en cada oferta, pero no puede ver su perfil (logo, descripción, beneficios, links), que profile-service ya expone.

**Qué hay**
- `GET /api/v1/profiles/companies/{company_id}` con el JWT del estudiante devuelve la vista pública: nombre, frase, descripción, rubro, tamaño, sedes, web, links, beneficios, valores y contacto sólo si es público. Sin CUIT.
- Si la empresa ocultó su perfil o no lo creó: `404`.
- Logo público: `GET /api/v1/profiles/companies/{company_id}/logo` (sirve directo en `<img>`).
- **jobs-service** trae el `company_id` en el detalle de la oferta (`JobOpportunity.company_id`).
- **matching-service** no lo trae en el resumen de oferta de "Ofertas para vos" (`job_snapshot`: `job_id`, `title`, `company_name`…).

**Qué hacer**
1. **matching (PATCH 0.2.1):** sumar `company_id` a `job_snapshot` en `app/application/serializers.py`. Es un campo nuevo, no rompe nada. Actualizar [`contracts/matching.md`](../../contracts/matching.md) parte A §4.1.
2. **front:**
   - Componente `CompanyProfileModal` (o una vista `company/:id` si se suma React Router, ver ítem 6) que pide `GET /profiles/companies/{company_id}` y muestra logo, datos y links.
   - El nombre de la empresa pasa a ser un botón "Ver empresa" en: el detalle de oferta (`JobDetail`, usa `job.company_id`), la tarjeta de "Ofertas para vos" (`JobRecommendations`, usa `job.company_id` del snapshot) y el listado de "Todas las ofertas" (`JobSummary`).
   - `404` → "Esta empresa todavía no publicó su perfil."
   - Logo con `alt` = nombre de la empresa; links externos con `rel="noopener noreferrer"`.

**Contratos:** [`contracts/profile.md`](../../contracts/profile.md) parte B §3 y §8 (vista pública) · `docs/frontend/pendientes.md` §7.

**Terminado cuando**
- [ ] Desde las tres pantallas se abre el perfil público con logo, descripción, beneficios y links.
- [ ] Una empresa sin perfil (o con perfil oculto) muestra el aviso, no un error.
- [ ] No aparecen ni el CUIT ni el contacto si `contact.public = false`.
- [ ] Test de matching: `job_snapshot` trae `company_id`.
- [ ] Test del front: el armado de la vista pública (labels de tamaño y rubro, links) con datos ficticios.

---

## 3. Volver a poner "Todas las ofertas" en el menú del estudiante

**Problema.** Desde el front 0.5.0, el menú del estudiante tiene sólo "Mi panel", "Ofertas para vos" y "Mi perfil". "Todas las ofertas" quedó accesible únicamente desde el footer (lo detectamos en el E2E de la etapa 2).

**Qué hacer:** sumar `{ section: 'jobs', label: 'Todas las ofertas', icon: 'bi-briefcase' }` a `STUDENT_NAV` en `src/components/layout/SiteHeader.tsx`, respetando el orden previo (después de "Ofertas para vos"). Si se sacó a propósito, por espacio en mobile, confirmarlo con Integrante 4 y en ese caso anotarlo acá.

**Terminado cuando**
- [ ] El ítem aparece en desktop y en el menú mobile, marcado como activo en esa sección.
- [ ] `navigation.test.ts` cubre la sección `jobs` para el rol estudiante.

---

## 4. Tests UT-FE-01 a UT-FE-04 del plan

El plan pide cuatro tests mínimos del front que hoy no existen con esos IDs. El PDF original no está en el repo, así que se proponen así (confirmar en la daily):

| ID | Qué cubre | Dónde |
|---|---|---|
| UT-FE-01 | Rutas por rol: sin sesión nunca se ve el área privada; estudiante, empresa y admin ven su área | `navigation.ts` (`resolveView`) y el armado de las áreas en `App.tsx` |
| UT-FE-02 | Panel de reglas: badge verde "Calculado por reglas", puntaje y faltantes | `RuleMatch` |
| UT-FE-03 | Panel de IA: badge ámbar "Sugerido por IA", disclaimer y **sin puntaje** | `AiAdvice` (ofertas), panel de candidatos, `TrainingAdvice` |
| UT-FE-04 | Flujo de CV: aceptar, editar y descartar sugerencias; `COMPLETAR_MANUALMENTE` no se guarda | `src/profile/draft.ts` (lógica) y `ProfileWizard` |

**Decisión previa (AGENTS §2.4, librería nueva):**
- **Opción A (recomendada):** sumar `@testing-library/react` + `jsdom` para probar los componentes de 02 y 03, que son los que garantizan la separación reglas/IA (AGENTS §2.2).
- **Opción B:** sólo lógica pura. 01 y 04 ya se pueden cubrir así: extraer de los componentes la decisión de qué badge y qué campos se muestran y testear esas funciones.

**Terminado cuando**
- [ ] Los cuatro IDs aparecen en los `describe` de Vitest y pasan en CI.
- [ ] UT-FE-03 falla si un ítem de IA trae `score` y el componente lo muestra.

---

## 5. Poner al día `docs/frontend/pendientes.md`

- Los ítems 1, 2 y 3 (recuperar clave, confirmar email, "Mi cuenta") se hicieron en el front 0.5.0 y siguen sin tachar.
- El ítem 6 ("¿Por qué este puntaje?") está resuelto como desplegable en `RuleMatch` y tampoco figura.
- Tachar con la versión y el PR, y mover a este documento lo que siga abierto.

---

## 6. Decidir la deuda técnica de AGENTS §4.7

AGENTS §4.7 nombra React Router, TanStack Query y React Hook Form + Zod, pero el front no los usa: navegación propia por estado, `useEffect` + `useState` y validación a mano.

- **Recomendación:** actualizar AGENTS para que describa lo que hay y no migrar antes de la entrega. Migrar toca todas las pantallas y no suma funcionalidad.
- **Si se decide sumar React Router**, conviene hacerlo antes del ítem 2: el perfil de empresa quedaría en una URL compartible (`/empresas/:id`).
- Lo que se decida va a AGENTS §4.7 en un PR `docs/agents/...`.

---

## Orden sugerido

1. Ítem 3 (XS) y ítem 5 (XS) para arrancar.
2. Ítem 1: alta prioridad, porque hoy afecta a usuarios reales del panel de admin.
3. Decisión del ítem 6 y de la librería del ítem 4 en la daily.
4. Ítem 2 (matching 0.2.1 + front).
5. Ítem 4, con lo que se haya decidido.

Después de la etapa 3 siguen las etapas 4 (calidad: eslint en auth y front, configuración de matching persistente, README con las claves JWT) y 5 (releases `v0.9.0` y `v1.0.0`) del plan.
