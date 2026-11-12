# Entrega final · TP2

> Correspondencia entre la consigna (§9 Entrega final y §4 Requisitos técnicos) y lo que hay en el repositorio.

## Qué se entrega en el campus

| # | Ítem pedido | Dónde está |
|---|---|---|
| 1 | Enlace al repositorio Git | <https://github.com/Grupo-1-EPIALC/bolsa-de-trabajo> (rama por defecto `dev`; ver pendientes sobre `main`) |
| 2 | Aplicación y archivos para ejecutarla | Todo el repo: `docker-compose.yml`, Dockerfiles, `.env.example`, `requirements.txt`, `package.json` |
| 3 | README con instalación, ejecución y Docker | [README.md](../README.md) |
| 4 | Diagrama de arquitectura y comunicación | [docs/ARQUITECTURA.md](ARQUITECTURA.md) |
| 5 | Workflows de n8n exportados | [n8n/workflows/](../n8n/workflows/) (10 archivos `WF-*.json`) |
| 6 | Bitácora de uso de IA | [docs/BITACORA_IA.md](BITACORA_IA.md) + registro detallado en [PROMPTS.md](../PROMPTS.md) |
| 7 | Responsabilidades de cada integrante | [docs/RESPONSABILIDADES.md](RESPONSABILIDADES.md) |

## Requisitos técnicos

| Requisito | Cómo se cumple |
|---|---|
| **Python** en módulos, validación, excepciones, lógica separada de la interfaz | 3 servicios FastAPI + `mcp-tools`, cada uno en capas `api` / `application` / `domain` / `infrastructure`; errores de dominio propios traducidos a respuestas HTTP en `api/errors.py` |
| **FastAPI**, ≥ 5 endpoints con JSON, métodos adecuados y errores HTTP | Más de 40 endpoints entre `profile-service`, `jobs-service` y `matching-service` (GET, POST, PATCH, PUT, DELETE), validación con Pydantic y respuestas 401, 403, 404, 409, 422. Documentados en `/docs` de cada servicio |
| **Interfaz** (Streamlit o similar) con formularios, resultados, errores de conexión | React + Vite: formularios de perfil, oferta y cuenta; resultados por reglas e IA; el cliente HTTP muestra "No se pudo conectar con el servidor" ante fallas de red |
| **n8n**, ≥ 3 workflows con condiciones, integrados con la API | 10 workflows; 9 con nodos IF/Switch y WF-05 con filtro en código; todos llaman a los servicios por REST o MCP |
| **IA** integrada al proceso, gratuita, justificada, validada y supervisada | Agentes en n8n con NVIDIA NIM (gratuito): lectura del CV, recomendaciones, diseño del CV; verificador de schema y grounding; el usuario confirma lo que propone la IA |
| **Persistencia** | PostgreSQL 17 (schemas `auth`, `profile`, `jobs`; base `n8n`) + volumen de CVs; datos ficticios en los seeds |
| **Docker** | Docker Compose con todos los servicios, override de desarrollo, healthchecks, redes y volúmenes documentados |
| **Repositorio Git** | Ramas por funcionalidad, PRs a `dev`, CI, `.gitignore`, sin credenciales; historial del 01/11 al 12/11/2026 |
| **Distinguir reglas de IA** (Proyecto A) | `origin: "RULES"` / `origin: "AI"` en la API; badges verde y ámbar en el front |
