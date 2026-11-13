# Propuesta · Monitor de salud, logs y alertas en el panel de admin

> **Para:** el equipo, para decidir en la daily. Es la **fase 3 del panel de admin** que ya estaba acordada: un `core-service` nuevo para lo transversal (salud de servicios, eventos y alertas).
> **Estado:** propuesta, sin código. Al final hay decisiones abiertas y un plan por fases.

---

## 1. Qué queremos

Que un admin, desde el panel, pueda:

1. **Ver la salud de cada servicio de un vistazo:** arriba o caído, versión, tiempo de respuesta, disponibilidad de las últimas 24 h y último incidente.
2. **Buscar en los logs** de todos los servicios desde un solo lugar: por servicio, nivel, texto y período, y seguir un pedido de punta a punta con su id.
3. **Enterarse sin mirar:** recibir una alerta por mail cuando algo se rompe, verla en el panel, reconocerla (*ack*) y saber cuándo se resolvió.

**Fuera de alcance:** métricas de negocio (cuántas ofertas, postulaciones), APM con trazas distribuidas y alta disponibilidad del propio monitor.

---

## 2. Qué hay hoy

| Tema | Situación |
|---|---|
| Healthchecks | Todos los contenedores tienen `HEALTHCHECK` en Docker y un `GET /health` (n8n: `/healthz`). Son **superficiales**: responden `ok` aunque la base o una dependencia estén caídas |
| Versión en `/health` | profile 0.4.1, jobs 0.2.1, matching 0.2.0 y mcp-tools 0.4.0 bien; **auth-service dice `0.0.1`** (va por la 0.2.0) |
| Logs | Texto plano por stdout. Docker los guarda con `json-file`, rotados a 10 MB × 3 por contenedor. Hay que mirar cada contenedor con `docker compose logs` |
| Correlación | El gateway genera un `X-Request-ID` (`rid=` en su log) y lo manda a los servicios, pero **ningún servicio lo registra** |
| Datos sensibles en logs | mcp-tools enmascara `key=***`. El gateway registra la query string completa (hoy sólo el token del HMR de Vite en dev) |
| Señales de falla que ya existen | auth: entregas pendientes del outbox (`auth.account_event_deliveries`) · n8n: WF-05 avisa por mail cada workflow que falla · matching: pedidos de IA en `failed` · mcp-tools: `GET /router/status` (modelos NVIDIA en cooldown) |

---

## 3. Propuesta

### 3.1 Arquitectura

```
                 ┌────────────── panel de admin (front) ───────────────┐
                 │   Salud        Logs        Alertas        Reglas    │
                 └───────────────────────┬─────────────────────────────┘
                                         │ /api/v1/core/* (JWT admin)
                                ┌────────▼────────┐        ┌──────────────┐
  sondeo cada 30 s ───────────► │   core-service  │──────► │ Postgres     │ schema core:
  /health/ready de cada         │   (FastAPI)     │        │ (historial,  │ checks, incidentes,
  servicio + señales internas   │                 │        │  alertas)    │ alertas, reglas
                                └──┬───────────┬──┘        └──────────────┘
                     consulta logs │           │ alerta nueva / resuelta
                         ┌─────────▼──┐   ┌────▼──────────────────────┐
     promtail ─────────► │   Loki     │   │ n8n WF-07 Alertas → mail  │
  (lee los logs de       └─────┬──────┘   │ (SMTP y reserva de        │
   Docker, sólo lectura)       │          │  notification_key de WF-05)│
                         ┌─────▼──────┐   └───────────────────────────┘
                         │  Grafana   │  ← "Abrir en Grafana" desde el panel (opcional)
                         └────────────┘
```

- **core-service** (FastAPI, mismas capas que el resto) es el dueño de los datos de salud y de las alertas. No lee la base de nadie (AGENTS §2.1): pregunta por REST.
- **Logs:** no los guarda core-service. Se suma **Loki + Promtail**: Promtail lee los logs que Docker ya escribe y los manda a Loki, y core-service consulta la API de Loki con límites. Grafana es opcional, para análisis más profundo.
- **Alertas:** las evalúa core-service y las manda por mail **n8n (WF-07)**, reutilizando la credencial SMTP y la reserva de claves que ya usan WF-02 a WF-05.

### 3.2 Requisitos previos en los servicios (fase 0)

1. **`/health/ready` profundo** en cada servicio, sin token y sólo en la red interna:

   ```json
   { "status": "ok | degraded | down", "service": "profile-service", "version": "0.4.1",
     "checks": { "database": { "status": "ok", "latency_ms": 3 }, "n8n": { "status": "degraded", "error": "timeout" } } }
   ```

   Qué verifica cada uno:
   - auth: base de datos;
   - profile y jobs: base de datos y auth (JWKS);
   - matching: profile y jobs;
   - mcp-tools: profile, jobs y matching.

   `/health` sigue como está para el healthcheck de Docker.
2. **Logs estructurados en JSON** (una línea por evento) con `timestamp`, `level`, `service`, `request_id`, `message` y campos extra.
   - FastAPI: un `logging.Formatter` común y un middleware que lee `X-Request-ID`.
   - NestJS: logger JSON y el mismo middleware.
3. **Propagar `X-Request-ID`:** cada servicio lo registra y lo reenvía en sus llamadas a otros servicios y a n8n. Así se sigue un pedido gateway → matching → profile.
4. **Enmascarar** tokens, `Authorization`, `X-Service-Token`, contraseñas y emails en los logs (filtro común). El gateway no registra la query string de rutas sensibles.
5. **Corregir la versión de auth en `/health`:** que la lea del `package.json`, como ya hace la documentación de la API.

### 3.3 Monitor de salud

- core-service sondea cada servicio cada **30 s** (`CORE_PROBE_INTERVAL_SECONDS`) con timeout de 3 s y guarda cada resultado:
  - `core.health_checks`: servicio, estado, latencia, versión, chequeos internos y fecha. Se depuran a los 7 días.
- Estado de cada servicio:
  - **caído** después de 2 fallas seguidas;
  - **degradado** si responde `degraded` o la latencia p95 de los últimos 5 minutos supera el umbral;
  - **arriba** en el resto de los casos.
- Cada caída abre un **incidente** (`core.incidents`: inicio, fin, duración, causa) y lo cierra al volver.
- **Señales internas**, que se leen por REST con `X-Service-Token`. Cada una es un endpoint chico en su servicio dueño:
  - auth `GET /api/v1/auth/internal/outbox/stats` → entregas pendientes y la más vieja;
  - matching `GET /api/v1/matches/internal/requests/stats` → pedidos de IA fallidos o colgados;
  - mcp-tools `GET /router/status` → modelos NVIDIA disponibles y en cooldown;
  - n8n → WF-05, además de mandar el mail, avisa a core-service (`POST /api/v1/core/internal/events`) cada workflow que falla.

### 3.4 Logs

- **Promtail** descubre los contenedores del proyecto por Docker (lectura del socket en modo sólo lectura) y manda sus logs a **Loki**, con etiquetas `service` y `level`. Retención de **7 días** (`LOKI_RETENTION`).
- core-service expone una búsqueda acotada que traduce a LogQL:
  - `GET /api/v1/core/logs?service=&level=&q=&request_id=&since=1h&limit=200`: como mucho 24 h y 500 líneas por consulta;
  - `GET /api/v1/core/logs/summary?since=1h`: errores y advertencias por servicio, para las tarjetas.
- Desde el panel, "Abrir en Grafana" lleva a Grafana Explore con el mismo filtro (si se levanta Grafana).
- Loki, Promtail y Grafana van en un **perfil de compose `observability`**: `docker compose --profile observability up -d`. Quien no los necesite no los levanta.

### 3.5 Alertas

**Reglas iniciales** (editables por el admin y guardadas en `core.alert_rules`):

| Regla | Dispara cuando | Severidad |
|---|---|---|
| Servicio caído | 2 sondeos seguidos fallan (≈ 1 min) | crítica |
| Servicio degradado | `degraded` o p95 de latencia > 1 s durante 5 min | advertencia |
| Errores 5xx | > 5 % de respuestas 5xx en el gateway durante 5 min (desde Loki) | crítica |
| Eventos de cuenta atrasados | outbox de auth con entregas pendientes de más de 10 min | advertencia |
| Workflows que fallan | ≥ 3 fallas de n8n en 15 min (avisos de WF-05) | advertencia |
| IA sin modelos | todos los modelos NVIDIA en cooldown | crítica |
| Pedidos de IA fallidos | > 3 pedidos `failed` en 30 min | advertencia |

**Ciclo de vida** (`core.alerts`):
1. Una alerta pasa a `firing` cuando se cumple la regla; si sigue activa, no se repite.
2. Pasa a `resolved` cuando deja de cumplirse durante 2 evaluaciones seguidas.
3. El admin puede reconocerla (`ack`, con quién y cuándo) o silenciar la regla por un tiempo.

**Aviso:** al abrir y al resolver, core-service llama a n8n `POST /webhook/core-alert`. WF-07 manda el mail a `notifications.admin_email` y reserva `alert:{id}:{estado}` para no repetir. Las alertas críticas sin reconocer se recuerdan cada 30 minutos, como mucho 3 veces.

### 3.6 API de core-service

Va bajo `/api/v1/core/` (ruta nueva en el gateway) y tiene su propio Swagger/ReDoc en `/api/v1/core/docs`. Contrato en `contracts/core.md`.

| Método y ruta | Quién | Para qué |
|---|---|---|
| `GET /api/v1/core/health/services` | admin | Estado actual de cada servicio + disponibilidad de 24 h + último incidente |
| `GET /api/v1/core/health/services/{service}/history?since=24h` | admin | Serie de latencia y estado (para el gráfico) |
| `GET /api/v1/core/incidents?since=7d` | admin | Incidentes abiertos y cerrados |
| `GET /api/v1/core/logs` · `/logs/summary` | admin | Búsqueda y resumen de logs (§3.4) |
| `GET /api/v1/core/alerts?state=firing\|resolved` | admin | Alertas |
| `POST /api/v1/core/alerts/{id}/ack` | admin | Reconocer una alerta |
| `GET` / `PUT /api/v1/core/alert-rules` · `POST /alert-rules/{id}/silence` | admin | Ver, ajustar y silenciar reglas |
| `POST /api/v1/core/internal/events` | servicio (`X-Service-Token`) | n8n (WF-05) y otros servicios informan una falla |

---

## 4. Pantallas en el panel de admin

Una sección nueva **"Salud"** en el menú del admin, con tres pestañas.

```
┌ Salud ─────────────────────────────────────────────────────────────────────┐
│ [Servicios]  Logs  Alertas (2)                     Actualizado hace 12 s ⟳ │
│                                                                            │
│ ┌ auth-service ──────┐ ┌ profile-service ───┐ ┌ jobs-service ──────┐       │
│ │ ● Arriba   v0.2.0  │ │ ● Arriba   v0.4.1  │ │ ▲ Degradado v0.2.1 │       │
│ │ 18 ms · 99,9 % 24h │ │ 25 ms · 100 % 24h  │ │ 1,4 s · 98,7 % 24h │       │
│ │ ▁▁▂▁▁▁▂▁▁▁         │ │ ▁▁▁▁▂▁▁▁▁▁         │ │ ▁▂▃▅▇▆▅▃▂▃  base 3s│       │
│ └────────────────────┘ └────────────────────┘ └────────────────────┘       │
│ ┌ matching-service ──┐ ┌ mcp-tools ─────────┐ ┌ n8n ───────────────┐       │
│ │ ● Arriba   v0.2.0  │ │ ● Arriba  v0.4.0   │ │ ✕ Caído hace 3 min │       │
│ │ 40 ms · 100 % 24h  │ │ 2/3 modelos NVIDIA │ │ incidente abierto  │       │
│ └────────────────────┘ └────────────────────┘ └────────────────────┘       │
│ Señales: outbox de auth 0 pendientes · pedidos de IA fallidos 1 (30 min)   │
└────────────────────────────────────────────────────────────────────────────┘

┌ Logs ──────────────────────────────────────────────────────────────────────┐
│ Servicio [todos ▾]  Nivel [≥ warning ▾]  Texto [________]  Período [1 h ▾] │
│ request_id [________________]                        [Buscar] [Grafana ↗]  │
│ 20:58:37  ERROR  matching-service  rid=b667…  GET profile-service: timeout │
│ 20:58:37  WARN   gateway           rid=b667…  /api/v1/matches/… 504 3,0 s  │
│ …                                              (clic en rid = filtrar)     │
└────────────────────────────────────────────────────────────────────────────┘

┌ Alertas ───────────────────────────────────────────────────────────────────┐
│ ● CRÍTICA  n8n caído              desde 20:55 · sin reconocer  [Reconocer] │
│ ▲ ADVERT.  jobs-service degradado desde 20:51 · reconocida por admin@…     │
│ ✓ resuelta auth outbox atrasado   20:10–20:22 (12 min)                     │
│ [Reglas]  umbrales · silenciar 1 h · destinatario: admin@bolsa.local       │
└────────────────────────────────────────────────────────────────────────────┘
```

- El resumen del panel suma una fila "Salud del sistema": cuántos servicios están arriba y cuántas alertas siguen activas, con link a la sección.
- Actualización cada 15 s mientras la pestaña está visible; estados con ícono y texto, nunca sólo con color (contraste AA, AGENTS §4.7).

---

## 5. Seguridad y privacidad

- Todo `/api/v1/core/*` es sólo para `admin` (JWT validado con el JWKS de auth, como el resto); `/internal/*` sólo con `X-Service-Token`.
- Los logs pueden tener datos personales: enmascarar en origen (§3.2), retención corta (7 días) y búsqueda sólo para admin. Nunca mostrar tokens ni contraseñas.
- Promtail necesita leer el socket de Docker: montarlo **sólo lectura** y sólo en ese contenedor. core-service no lo toca.
- Loki y Grafana no se publican por el gateway sin autenticación. Grafana en dev, con usuario y clave en `.env`.

---

## 6. Plan por fases

| Fase | Qué | Servicios / rama | Tamaño |
|---|---|---|---|
| **0 · Base** | `/health/ready` profundo, logs JSON con `request_id`, propagación del header, enmascarado y versión de auth | un PR por servicio (`feature/<servicio>/vX.Y.Z-observabilidad`) | M |
| **1 · Salud** | core-service (esqueleto, schema `core`, sondeo, incidentes, señales internas), ruta en el gateway, pestaña "Servicios" | `feature/core/v0.1.0-monitor-salud` + front | L |
| **2 · Alertas** | reglas, ciclo de vida, WF-07 por mail, WF-05 → `/internal/events`, pestaña "Alertas" | core + n8n + front | M |
| **3 · Logs** | perfil `observability` (Loki, Promtail, Grafana opcional), `/logs` y `/logs/summary`, pestaña "Logs" | infra + core + front | M |
| **4 · Extras (después)** | métricas Prometheus (`/metrics`), objetivos de disponibilidad, tablero de Grafana | — | — |

Tamaños: M ≈ 1–2 días · L ≈ 3 días, para una persona. Cada fase se puede entregar sola; la 1 ya da valor sin Loki.

**Terminado cuando** (por fase):
- [ ] F1: apagar un servicio → en ≤ 1 min la tarjeta pasa a "Caído" y se abre un incidente; al levantarlo se cierra con su duración.
- [ ] F2: el mismo caso manda **un** mail al admin (sin repetir) y otro al resolverse; reconocer la alerta queda registrado.
- [ ] F3: un error en matching se encuentra por texto y por `request_id`, junto con la línea del gateway del mismo pedido.
- [ ] Tests unitarios del evaluador de reglas, de la lógica de incidentes y de la traducción a LogQL (≥ 70 % en `domain/` y `application/`).

---

## 7. Decisiones para la daily

1. **¿Loki + Promtail (+ Grafana) o algo más simple?**
   - La alternativa mínima es un visor como Dozzle (sin búsqueda entre servicios ni alertas por logs).
   - Recomendación: Loki, porque es liviano, lee lo que Docker ya escribe y deja las alertas por tasa de errores.
2. **Librerías nuevas** (AGENTS §2.4): Loki, Promtail, Grafana (imágenes) y un logger JSON para NestJS (`pino` o el logger de Nest con formato JSON).
3. **Retención** de logs e historial: ¿7 días alcanza?
4. **Quién recibe las alertas:** ¿sólo `NOTIFY_ADMIN_EMAIL` o una lista? ¿Hace falta otro canal (Slack, Telegram) además del mail?
5. **¿core-service guarda en Postgres desde el día 1** (schema `core`, como el resto) o arranca en memoria como matching y pasa a Postgres después? Recomendación: Postgres, porque el historial es el valor principal.
6. **Prioridad frente a la entrega:** fases 0 y 1 antes de `v1.0.0`; 2 y 3 después si no hay tiempo.

---

## 8. Impacto en el resto

- **AGENTS.md:** nuevo agente `core-agent` (§4) y sección de observabilidad en §2.3 (logs JSON, `request_id`, enmascarado). La tabla de servicios suma core-service con dueño y revisor.
- **Contratos:** `contracts/core.md` nuevo. Los contratos de auth, matching y mcp-tools suman sus endpoints internos de señales; `n8n.md` suma WF-07 y el aviso de WF-05 a core-service.
- **Compose y gateway:** servicio `core-service` (schema y rol `core` en `infra/postgres/init/`), `location /api/v1/core/` en Nginx y perfil `observability`.
- **`.env.example`:** `CORE_PROBE_INTERVAL_SECONDS`, `CORE_DB_PASSWORD`, `LOKI_RETENTION`, `GRAFANA_ADMIN_USER` / `GRAFANA_ADMIN_PASSWORD`.
