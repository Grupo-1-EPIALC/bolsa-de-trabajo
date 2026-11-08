# Contrato de Reconocimiento de CV e Instrucciones para `profile-agent` (`profile-service`)

> **Actualización v0.2.0 (P-011):** para el frontend usar `POST /api/v1/profiles/me/cv` (multipart) y `GET /api/v1/profiles/me/cv/jobs/{job_id}`, documentados en [`profile_frontend.md`](profile_frontend.md). Los endpoints `cv-extract*` de este documento siguen funcionando por compatibilidad, pero **ahora piden autenticación**: JWT de estudiante (la extracción se asocia a su perfil y se ignora `profile_id`) o `X-Service-Token`. La versión síncrona (`POST /cv-extract`) es sólo para servicio o admin. El webhook hacia n8n (§2.2) no cambia.

> Documento de integración para la persona responsable de **`services/profile-service`** (Integrante 2) y su asistente de IA de código (**`profile-agent`**).
> Incluye todos los endpoints del cargador de CV, sus tipos exactos de entrada y ejemplos reales de salida (tanto del cargador en `profile-service` como del webhook de `n8n`).

---

## 1. Resumen de Endpoints del Cargador de CV

| Dirección | Método y Ruta | `Content-Type` de Entrada | Código de Éxito | Propósito |
|---|---|---|---|---|
| **Frontend → `profile-service`** | `POST /api/v1/profiles/cv-extract/async` | `application/json` | `202 Accepted` | **Recomendado**: valida y guarda el CV en `/data/cvs`, inicia la extracción en segundo plano hacia `n8n` y devuelve `job_id`. |
| **Frontend → `profile-service`** | `GET /api/v1/profiles/cv-extract/jobs/{job_id}` | Sin body (`path param: job_id`) | `200 OK` | Consulta el progreso en vivo (`processing` → `completed` / `failed`) y devuelve el JSON final extraído en `result`. |
| **Frontend → `profile-service`** | `POST /api/v1/profiles/cv-extract` | `application/json` | `200 OK` | Variante síncrona (espera la respuesta de `n8n` en la misma petición HTTP). |
| **Navegador → `profile-service`** | `GET /api/v1/profiles/cv-test` | Sin body | `200 OK` (`text/html`) | Formulario interactivo de prueba en Bootstrap 5 para subir un CV y ver el progreso y el JSON devuelto. |
| **`profile-service` → `n8n` (interno)** | `POST http://n8n:5678/webhook/cv-extract` | `application/json` + Header `X-Service-Token` | `200 OK` | Webhook interno (`WF-01`) que parsea el archivo vía `mcp-tools` (`parse_cv_file`), estructura con IA y verifica grounding (`WF-0V`). |

---

## 2. Tipo y Esquema de Entrada del Cargador de CV

### 2.1 Entrada en `profile-service`: `POST /api/v1/profiles/cv-extract/async` y `POST /api/v1/profiles/cv-extract`

- **Headers**:
  ```http
  Content-Type: application/json
  Accept: application/json
  ```
- **Modelo Pydantic (`CvExtractRequest` en `app/api/routes.py`)**:

| Campo | Tipo JSON / Python | Requerido | Default | Restricciones y Validaciones (`UploadedCvFile.create`) |
|---|---|---|---|---|
| `profile_id` | `string` (`str`) | No | `"prof-estudiante-01"` | ID del perfil del estudiante al que se asocian las sugerencias. |
| `filename` | `string` (`str`) | No | `"cv.pdf"` | Debe terminar en una extensión permitida: **`.pdf`**, **`.docx`**, **`.doc`** o **`.md`**. |
| `mime_type` | `string` (`str`) | No | `""` | Si se envía, debe estar entre los MIME admitidos: `application/pdf`, `application/vnd.openxmlformats-officedocument.wordprocessingml.document`, `application/msword`, `text/markdown`, `text/plain`, `application/octet-stream`. |
| `content_base64` | `string` (`str`) | **Sí** | — | Archivo codificado en Base64 estándar (sin prefijo `data:...;base64,`). Tamaño decodificado: **`> 0 bytes` y `<= 5 MB` (`5.242.880 bytes`)**. |

- **Ejemplo de JSON de Entrada (`Request Body`)**:
  ```json
  {
    "profile_id": "prof-estudiante-01",
    "filename": "cv_postulante.pdf",
    "mime_type": "application/pdf",
    "content_base64": "JVBERi0xLjQKJcOkw7zDtsOfCjIgMCBvYmoKPDwvTGVuZ3RoID..."
  }
  ```

### 2.2 Entrada del Webhook Interno `profile-service` → `n8n` (`POST http://n8n:5678/webhook/cv-extract`)

`HttpN8nCvWebhookGateway` agrega automáticamente `stored_filename` (el UUID con el que se guardó en `/data/cvs`) y el header `X-Service-Token`:

```json
{
  "profile_id": "prof-estudiante-01",
  "filename": "cv_postulante.pdf",
  "stored_filename": "ca2da99ebfab475f8dbe30269b9a1ab2.pdf",
  "mime_type": "application/pdf",
  "content_base64": "JVBERi0xLjQKJcOkw7zDtsOfCjIgMCBvYmoKPDwvTGVuZ3RoID..."
}
```

---

## 3. Ejemplos de Salida del Cargador de CV

### 3.1 Paso 1 — Respuesta inmediata al iniciar carga asíncrona (`POST /api/v1/profiles/cv-extract/async` → `202 Accepted`)

```json
{
  "job_id": "cvjob-601f60ba3822",
  "profile_id": "prof-estudiante-01",
  "filename": "cv_postulante.pdf",
  "status": "processing",
  "stage": "Extrayendo texto del CV y estructurando perfil con Agentes IA (n8n)...",
  "step_index": 2,
  "progress_percent": 35,
  "elapsed_seconds": 0.1,
  "result": null,
  "error": null
}
```

### 3.2 Paso 2 — Respuesta durante el polling (`GET /api/v1/profiles/cv-extract/jobs/cvjob-601f60ba3822` → `200 OK` en curso)

```json
{
  "job_id": "cvjob-601f60ba3822",
  "profile_id": "prof-estudiante-01",
  "filename": "cv_postulante.pdf",
  "status": "processing",
  "stage": "Agente CV Structurer (NVIDIA NIM) estructurando competencias y experiencia...",
  "step_index": 3,
  "progress_percent": 65,
  "elapsed_seconds": 12.4,
  "result": null,
  "error": null
}
```

### 3.3 Paso 3 — Salida Final Completada (`GET /api/v1/profiles/cv-extract/jobs/{job_id}` o `POST /api/v1/profiles/cv-extract` → `200 OK`)

> En el endpoint síncrono `POST /api/v1/profiles/cv-extract`, la respuesta HTTP `200 OK` devuelve directamente el objeto que aquí aparece dentro de `"result"`.

```json
{
  "job_id": "cvjob-601f60ba3822",
  "profile_id": "prof-estudiante-01",
  "filename": "cv_postulante.pdf",
  "status": "completed",
  "stage": "Extracción y verificación completadas",
  "step_index": 4,
  "progress_percent": 100,
  "elapsed_seconds": 28.6,
  "error": null,
  "result": {
    "profile_id": "prof-estudiante-01",
    "file": {
      "filename": "cv_postulante.pdf",
      "stored_filename": "ca2da99ebfab475f8dbe30269b9a1ab2.pdf",
      "format": "pdf",
      "size_bytes": 74820,
      "truncated": false
    },
    "cv_suggestions": {
      "personal": {
        "name": "Lucía Fernández",
        "email": "lucia.fernandez@est.utn.edu.ar",
        "phone": "COMPLETAR_MANUALMENTE",
        "location": "Ciudad Autónoma de Buenos Aires"
      },
      "summary": "Desarrolladora Backend Python con experiencia en microservicios REST, FastAPI, PostgreSQL y contenedores Docker.",
      "skills": [
        {
          "name": "Python",
          "level": 4
        },
        {
          "name": "FastAPI",
          "level": 3
        },
        {
          "name": "PostgreSQL",
          "level": 3
        },
        {
          "name": "Docker",
          "level": "COMPLETAR_MANUALMENTE"
        }
      ],
      "experience": [
        {
          "company": "FinTech Sur",
          "role": "Desarrolladora Backend Python",
          "start": "2023",
          "end": "Presente",
          "description": "Desarrollo de microservicios REST con Python, FastAPI, PostgreSQL, Docker y pruebas automatizadas con Pytest."
        },
        {
          "company": "Agencia Digital BA",
          "role": "Desarrolladora Web Junior",
          "start": "2022",
          "end": "2023",
          "description": "Interfaces en React y TypeScript integradas con APIs REST."
        }
      ],
      "education": [
        {
          "institution": "Universidad Tecnológica Nacional (UTN)",
          "degree": "Ingeniería en Sistemas de Información",
          "status": "En curso",
          "start": "COMPLETAR_MANUALMENTE",
          "end": "COMPLETAR_MANUALMENTE"
        }
      ],
      "languages": [
        {
          "name": "Español",
          "level": "Nativo"
        },
        {
          "name": "Inglés",
          "level": "B2"
        }
      ],
      "certifications": [
        "Arquitectura de Microservicios con Python"
      ],
      "links": [],
      "pending_manual_fields": [
        "personal.phone",
        "skills[3].level",
        "education[0].start",
        "education[0].end",
        "links"
      ]
    },
    "origin": "AI",
    "model": "nvidia/nemotron-3-ultra-550b-a55b",
    "prompt_version": "1.1.0",
    "generated_at": "2026-11-01T23:50:12.418000+00:00",
    "verified": true,
    "disclaimer": "Sugerencias extraídas automáticamente por IA del CV subido. Los campos con COMPLETAR_MANUALMENTE o listas vacías [] deben completarse manualmente."
  }
}
```

### 3.4 Ejemplo de Salida de Error (`422 Unprocessable Entity` / `503 Service Unavailable`)

```json
{
  "error": {
    "code": "INVALID_CV_FILE",
    "message": "Formato de archivo no soportado ('.exe'). Permitidos: .doc, .docx, .md, .pdf",
    "details": {
      "filename": "instalador.exe",
      "allowed_extensions": ["doc", "docx", "md", "pdf"]
    }
  }
}
```

---

## 4. Prompt Completo para el Agente de `profile-service` (`profile-agent`)

Copiá y pegá el siguiente bloque completo a tu asistente de IA de código cuando trabajes en `services/profile-service`:

````markdown
Actuá como `profile-agent` (desarrollador backend senior en Python 3.12 + FastAPI) trabajando únicamente en `services/profile-service/`.

## 1. Reglas obligatorias de arquitectura (AGENTS.md)
1. **SOLID y 4 capas**: `api/` -> `application/` -> `domain/` <- `infrastructure/`.
   - `domain/` NO importa FastAPI, SQLAlchemy ni clientes HTTP. Define entidades, Value Objects, errores de dominio y puertos (`Protocol`).
2. **Aislamiento de Base de Datos**: persistencia únicamente en PostgreSQL 17 dentro del schema `profile` (`DATABASE_URL=postgresql://profile_svc:...@postgres:5432/bolsa`). Prohibido acceder a schemas de otros servicios.
3. **Sin `ai-service` y sin paso de MCP por Nginx**:
   - Toda la estructuración de CV con IA corre en **`n8n`** (`WF-01`), que consume `mcp-tools` de forma directa por la red interna `mcp_internal`.
   - `profile-service` se comunica con `n8n` mediante webhook HTTP (`POST http://n8n:5678/webhook/cv-extract` con header `X-Service-Token`).
4. **Separación Reglas vs. IA y prohibición de `null`**:
   - Todo lo extraído del CV lleva `"origin": "AI"`, `model`, `prompt_version`, `generated_at` y `disclaimer`.
   - Nunca se devuelve `null` dentro de `cv_suggestions`: los campos escalares ausentes en el CV llevan la constante `"COMPLETAR_MANUALMENTE"` y las secciones de lista vacías llevan `[]`, además de listarse en `pending_manual_fields`.
   - **Nunca sobrescribas el perfil automáticamente** al subir un CV: las sugerencias deben ser confirmadas/editadas por el estudiante antes de persistirse.

## 2. Endpoints del Cargador de CV ya implementados en `services/profile-service` (NO romper)
Ya están implementados y testeados en `app/domain/models.py`, `app/application/upload_cv_use_case.py`, `app/infrastructure/storage_fs.py`, `app/infrastructure/n8n_client.py` y `app/api/routes.py`:

- `POST /api/v1/profiles/cv-extract/async` (`202 Accepted`):
  - Entrada (`application/json`):
    ```json
    {
      "profile_id": "prof-estudiante-01",
      "filename": "cv_postulante.pdf",
      "mime_type": "application/pdf",
      "content_base64": "JVBERi0xLjQK..."
    }
    ```
    Extensiones permitidas: `.pdf`, `.docx`, `.doc`, `.md` (máx. 5 MB). Se guarda con nombre UUID en `CV_STORAGE_PATH` (`/data/cvs`).
  - Salida inmediata (`202 Accepted`):
    ```json
    {
      "job_id": "cvjob-601f60ba3822",
      "profile_id": "prof-estudiante-01",
      "filename": "cv_postulante.pdf",
      "status": "processing",
      "stage": "Extrayendo texto del CV y estructurando perfil con Agentes IA (n8n)...",
      "step_index": 2,
      "progress_percent": 35,
      "elapsed_seconds": 0.1,
      "result": null,
      "error": null
    }
    ```
- `GET /api/v1/profiles/cv-extract/jobs/{job_id}` (`200 OK`):
  - Devuelve el avance y, cuando `status == "completed"`, incluye en `result` el objeto completo de extracción (el mismo que devuelve `POST /api/v1/profiles/cv-extract` en modo síncrono):
    ```json
    {
      "profile_id": "prof-estudiante-01",
      "file": {
        "filename": "cv_postulante.pdf",
        "stored_filename": "ca2da99ebfab475f8dbe30269b9a1ab2.pdf",
        "format": "pdf",
        "size_bytes": 74820,
        "truncated": false
      },
      "cv_suggestions": {
        "personal": {
          "name": "Lucía Fernández",
          "email": "lucia.fernandez@est.utn.edu.ar",
          "phone": "COMPLETAR_MANUALMENTE",
          "location": "Ciudad Autónoma de Buenos Aires"
        },
        "summary": "Desarrolladora Backend Python con experiencia en microservicios REST, FastAPI, PostgreSQL y Docker.",
        "skills": [
          { "name": "Python", "level": 4 },
          { "name": "Docker", "level": "COMPLETAR_MANUALMENTE" }
        ],
        "experience": [
          {
            "company": "FinTech Sur",
            "role": "Desarrolladora Backend Python",
            "start": "2023",
            "end": "Presente",
            "description": "Desarrollo de microservicios REST con Python, FastAPI y PostgreSQL."
          }
        ],
        "education": [
          {
            "institution": "Universidad Tecnológica Nacional (UTN)",
            "degree": "Ingeniería en Sistemas de Información",
            "status": "En curso",
            "start": "COMPLETAR_MANUALMENTE",
            "end": "COMPLETAR_MANUALMENTE"
          }
        ],
        "languages": [
          { "name": "Español", "level": "Nativo" },
          { "name": "Inglés", "level": "B2" }
        ],
        "certifications": ["Arquitectura de Microservicios con Python"],
        "links": [],
        "pending_manual_fields": [
          "personal.phone",
          "skills[1].level",
          "education[0].start",
          "education[0].end",
          "links"
        ]
      },
      "origin": "AI",
      "model": "nvidia/nemotron-3-ultra-550b-a55b",
      "prompt_version": "1.1.0",
      "generated_at": "2026-11-01T23:50:12.418000+00:00",
      "verified": true,
      "disclaimer": "Sugerencias extraídas automáticamente por IA del CV subido. Los campos con COMPLETAR_MANUALMENTE o listas vacías [] deben completarse manualmente."
    }
    ```
- `GET /api/v1/profiles/cv-test` (`200 OK`): interfaz HTML en Bootstrap 5 para probar la carga de CV.

## 3. Tu tarea a desarrollar en `services/profile-service`
1. **Persistencia del Perfil en el schema `profile` (PostgreSQL 17)**:
   - Entidades de dominio y tablas: `Profile`, `Skill(name, level 1..5)`, `Experience`, `Education`, `Language`, `Certification`, `Link`.
   - Normalizador `SkillExtractor` con diccionario y sinónimos (`data/skills_catalog.json`).
2. **Endpoints de Confirmación y Consulta de Perfil (`/api/v1/profiles`)**:
   - `GET /api/v1/profiles/{profile_id}` y `GET /api/v1/profiles?skills=...&limit=...` (respetando el contrato de `contracts/mock_endpoints.yaml` que consume `mcp-tools`).
   - `PUT /api/v1/profiles/{profile_id}` (o `POST /api/v1/profiles/{profile_id}/cv-confirm`): recibe los datos revisados/confirmados por el estudiante a partir de `cv_suggestions`, valida que los campos obligatorios ya hayan sido completados (que no conserven el valor `"COMPLETAR_MANUALMENTE"` y que `skills[].level` sea un entero entre `1` y `5`), persiste en el schema `profile` y emite el webhook `profile.updated` a `n8n` mediante un puerto `EventPublisher` (`Protocol`).
   - `GET /api/v1/profiles/{profile_id}/cv.pdf`: genera y descarga el CV en PDF usando WeasyPrint + plantilla Jinja2 (`templates/cv.html`).
3. **Calidad obligatoria**:
   - Mantener en verde los tests existentes en `tests/test_cv_upload.py` y agregar `UT-PROF-01` a `UT-PROF-07` (cobertura >= 70 % en `domain/` y `application/`).
   - Pasar `ruff check .`, `black --check .` y `mypy app` sin errores.
   - Registrar el prompt en `PROMPTS.md`.
````
