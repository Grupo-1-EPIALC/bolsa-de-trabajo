# Bitácora de uso de IA

> Resumen para la entrega. El registro completo, prompt por prompt (P-001 a P-047, con fecha, autor, rama, resumen de la respuesta y decisión), está en [PROMPTS.md](../PROMPTS.md). Las reglas que siguieron los asistentes están en [AGENTS.md](../AGENTS.md).

## 1. Dos usos distintos de la IA

| | IA para **desarrollar** el sistema | IA **dentro** del sistema |
|---|---|---|
| Qué es | Asistentes de código que usó el equipo | Agentes que corren en n8n con modelos de NVIDIA NIM |
| Para qué | Planificar, programar, revisar, depurar, documentar | Leer CVs, recomendar formación y candidatos, elegir el diseño del CV, verificar las respuestas |
| Dónde queda registrado | [PROMPTS.md](../PROMPTS.md) | `n8n/agentes/`, `n8n/prompts/`, ejecuciones de n8n |

## 2. Herramientas de desarrollo utilizadas

| Herramienta | Quién | Para qué |
|---|---|---|
| Claude (chat) | Andres | Plan inicial del MVP: arquitectura, requisitos, historias de usuario, plan de 10 días y AGENTS.md (P-001) |
| Claude Code | Andres | La mayor parte del backend, la infraestructura, n8n, `mcp-tools`, el panel de admin y funciones del front (P-002, P-007 en adelante) |
| Google Antigravity | Andres | Primera versión de `mcp-tools`, del router de NVIDIA y de los workflows de agentes (P-003 a P-006) |
| Gemini | Dario | Frontend: maquetación, flujos de autenticación, modales, correcciones y tests (P-009, P-023 a P-029, P-036 a P-039, P-044, P-045) |
| OpenCode con DeepSeek V4.1 Flash y GLM 5.3 Flash (gratuitos) | Elian | Plan, implementación y revisión de `jobs-service` y su contrato (P-010, P-016, P-017) |
| *A completar* | Luciano | `auth-service` inicial (registro, login, JWT). **Falta registrar en PROMPTS.md la herramienta y los prompts usados** |

**Forma de trabajo.** AGENTS.md define un "agente de desarrollo" por servicio (`auth-agent`, `profile-agent`, `n8n-agent`, etc.) con sus reglas: arquitectura por capas, SOLID, contratos, tests y estilo. Cada cambio se hizo en una rama propia, se registró el prompt en PROMPTS.md y entró a `dev` por Pull Request con la plantilla de `.github/`. El CI corre lint, tipos y tests del servicio que cambió. Las respuestas de la IA no se aceptaron sin más: la columna "Decisión" de PROMPTS.md indica si se aceptaron, se aceptaron con cambios o se descartaron.

## 3. Principales decisiones técnicas

1. **Microservicios REST + gateway Nginx** (P-001, P-002). Un servicio por responsabilidad, un schema de PostgreSQL por servicio y comunicación sólo por REST o webhooks.
2. **`auth-service` en NestJS en vez de Django** (P-002). Python queda para la lógica de negocio (perfiles, ofertas, matching, herramientas de IA).
3. **React en lugar de Streamlit.** La consigna admite "Streamlit o similar"; se eligió React porque el sistema tiene tres tipos de usuario con login, rutas protegidas, formularios de varios pasos y sondeo de tareas asíncronas.
4. **Toda la IA en n8n, sin `ai-service`** (P-006). Los agentes usan los nodos nativos de n8n (agente, memoria, cliente MCP) y las herramientas viven en `mcp-tools`, conectado directo a n8n por una red interna.
5. **Puntaje por reglas separado de la IA** (P-001, P-007). El motor de `matching-service` calcula el puntaje con pesos explícitos en `scoring_rules.yaml`; la IA sólo comenta y recomienda, y el verificador rechaza cualquier respuesta que cambie el puntaje.
6. **Verificador anti-alucinación** (P-003). Cada respuesta de un agente pasa por validación de JSON Schema y *grounding*: si menciona una competencia que no está en los datos, se rechaza y se reintenta con la instrucción del verificador.
7. **Workflows generados por código** (P-004, P-014). `n8n/generate_workflows.py` arma los JSON desde el catálogo de agentes y los prompts versionados; `n8n-init` los importa al arrancar. El repositorio es la fuente de verdad.
8. **Pesos ajustados con criterio de negocio** (P-042). Versión 2.0.0 de las reglas: lo técnico (60) y la experiencia (25) pesan más; las condiciones laborales (7) son negociables y sólo los requisitos legales excluyen.
9. **Diccionario de competencias** (P-043). 148 competencias con alias y equivalentes (PostgreSQL ↔ Postgres, MySQL ↔ MariaDB) y herramientas similares (GitHub ↔ GitLab), usado por las reglas y por los agentes.

## 4. Modelo de IA elegido, justificación y límites

**Servicio:** NVIDIA NIM (`https://integrate.api.nvidia.com/v1`), API compatible con OpenAI.

**Por qué:**
- Es **gratuito** para prototipos y desarrollo a través del NVIDIA Developer Program; no requiere pagos, como pide la consigna.
- Con una sola key da acceso a varios modelos grandes de distintos proveedores, con contexto amplio para procesar un CV completo y devolver JSON estructurado.
- Al ser compatible con OpenAI se conecta con el nodo nativo de n8n (`lmChatOpenAi`), sin código adicional.
- Permite armar una lista de modelos de respaldo sin cambiar de proveedor.
- No hace falta una GPU: cualquier integrante puede correr el sistema en su notebook.

**Modelos configurados** (`.env`, en orden de preferencia): `AGENT_MODELS`, `AGENT_MODELS_CV` y `AGENT_MODELS_VERIFIER`. Si un modelo falla o se satura, el router de `mcp-tools` pasa al siguiente (circuit-breaker).

**Límites y cómo se manejan:**

| Límite | Mitigación |
|---|---|
| ~40 pedidos por minuto por key en la cuenta gratuita; con más simultáneos responde 429 | El router lleva la cuenta (`NVIDIA_RPM_LIMIT`); WF-06 manda los pedidos en lotes de 10 con 10 s de pausa (P-047) |
| Uso permitido sólo para prototipos, no para producción | El sistema es un MVP académico con datos ficticios |
| Depende de internet y de un servicio externo | Sin la key o sin conexión, el puntaje por reglas, los perfiles, las ofertas y los avisos siguen funcionando; sólo falta la parte de IA |
| Puede inventar datos o devolver JSON incompleto | Verificador (schema + grounding), recorte a los topes del schema, `maxTokens` alto y reparador de JSON, reintento guiado |
| A veces deja una respuesta colgada | Timeout de 100 s por pedido y un reintento (P-047) |
| Latencia de varios segundos | Contexto compacto, cada agente sólo con sus herramientas, análisis por oferta en paralelo (P-046, P-047): de 46–96 s a 24–38 s para un estudiante |

**Privacidad:** a la IA se envían snapshots del perfil sin nombre ni datos de contacto, y los avisos a empresas no incluyen datos personales del candidato. Para la demo se usan datos ficticios.

## 5. Validación de resultados y supervisión humana

- **CV:** la IA sólo arma un borrador. Los campos que no encuentra quedan como `COMPLETAR_MANUALMENTE` y el estudiante revisa y confirma todo antes de guardar.
- **Recomendaciones:** se muestran aparte del puntaje, con badge ámbar, el modelo, la versión del prompt y un aviso de que son orientativas. La decisión de postularse o de contactar a un candidato es siempre de la persona.
- **Diseño del CV:** la IA sugiere uno, las reglas proponen otro y el estudiante elige (P-040).
- **Puntaje:** lo calcula sólo el motor de reglas; el usuario puede ver el desglose en "¿Por qué este puntaje?".
- **Administrador:** puede ajustar cuántas ofertas y candidatos se recomiendan y recibe por mail los errores de los workflows (WF-05).

## 6. Dificultades encontradas y correcciones

| Problema | Causa | Corrección | Ref. |
|---|---|---|---|
| Desaparecieron los workflows y credenciales de n8n | Se habían recreado los volúmenes con `docker compose down -v` y la importación era manual | Volúmenes externos + servicio `n8n-init` que importa y activa los workflows en cada arranque | P-014 |
| La IA devolvía el JSON del CV cortado | Límite de tokens de salida | `maxTokens: 8192`, reparador de JSON y campos ausentes como `COMPLETAR_MANUALMENTE` en vez de `null` | P-005 |
| Dos ediciones simultáneas de la misma oferta se pisaban | *Lost update* | Bloqueo optimista con `version` y respuesta `409 CONFLICT`; límites de tamaño de las entradas | P-016 |
| El listado de ofertas devolvía 301 y las redirecciones perdían el puerto | Configuración de rutas y del `Host` en Nginx | `location = /api/v1/jobs` y `Host $http_host` | P-020, P-021 |
| WF-06 pedía rankings de IDs que matching no conocía | `mcp-tools` usaba datos ficticios y matching datos reales | `MCP_USE_MOCKS=false` alineado con `MATCHING_USE_MOCKS` | P-021 |
| Se podía perder el aviso de borrado de una cuenta y un token seguía valiendo | Envío "a mejor esfuerzo" después del commit | *Outbox* transaccional con reintentos y `token_version` en el JWT | P-022 |
| El front recibía 422 al guardar el perfil | Mandaba campos calculados por el backend | Se limpian esos campos antes de enviar | P-023 |
| Llegaban mails repetidos | Ejecuciones simultáneas de n8n pisaban `staticData` | Reserva atómica en Postgres (`ON CONFLICT DO NOTHING`); prueba con 6 avisos simultáneos → 1 mail | P-030 |
| La formación sugerida pisaba la recomendación de la oferta | Se guardaban con el mismo tipo | Modo `training` propio con su `request_id` | P-033 |
| Las recomendaciones tardaban mucho | 99 % del tiempo en el modelo; prompts con reglas que el agente no usaba; reintentos por un ítem de más | Herramientas y reglas por agente, recorte antes de verificar, contexto compacto y pedidos en paralelo | P-046, P-047 |
| "Postgres" no coincidía con "PostgreSQL" | Comparación literal de nombres | Diccionario de competencias con alias y equivalentes | P-043 |

## 7. Cómo verificamos el funcionamiento

- **Tests automáticos** en todos los servicios, corridos por el CI en cada PR: 128 en matching, 116 en jobs, 120 en profile y 30 en mcp-tools (cobertura 91–98 %), además de Jest en `auth-service` y Vitest en el front.
- **Pruebas de punta a punta** en Docker: Playwright/Chromium sobre el front, y flujos completos con IA real (CV → borrador; matching → WF-06 → recomendaciones guardadas).
- **Mailpit** para comprobar cada notificación y casos límite (sin consentimiento no hay mail, eventos repetidos no reenvían, WF-05 avisa si cae matching).
- **Ejecuciones de n8n** para medir tiempos y revisar las respuestas de los agentes.
- **Swagger UI** de cada servicio para probar endpoints y errores (401, 403, 404, 409, 422).
