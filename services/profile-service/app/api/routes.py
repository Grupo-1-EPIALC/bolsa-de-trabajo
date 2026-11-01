# ruff: noqa: E501
"""Endpoints REST y formulario de prueba de extracción asíncrona de CV en profile-service."""

import base64
from functools import lru_cache
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from app.application.upload_cv_use_case import CvExtractionJobStore, UploadAndExtractCvUseCase
from app.domain.errors import InvalidCvFileError
from app.infrastructure.config import ProfileSettings
from app.infrastructure.n8n_client import HttpN8nCvWebhookGateway
from app.infrastructure.storage_fs import FileSystemCvStorage

router = APIRouter(prefix="/api/v1/profiles", tags=["profiles"])


class CvExtractRequest(BaseModel):
    profile_id: str = "prof-estudiante-01"
    filename: str = "cv.pdf"
    mime_type: str = ""
    content_base64: str


@lru_cache
def get_settings() -> ProfileSettings:
    return ProfileSettings.from_env()


@lru_cache
def get_job_store() -> CvExtractionJobStore:
    return CvExtractionJobStore()


def get_upload_cv_use_case(
    settings: Annotated[ProfileSettings, Depends(get_settings)],
    job_store: Annotated[CvExtractionJobStore, Depends(get_job_store)],
) -> UploadAndExtractCvUseCase:
    storage = FileSystemCvStorage(base_path=settings.cv_storage_path)
    webhook_gateway = HttpN8nCvWebhookGateway(
        webhook_base_url=settings.n8n_webhook_base_url,
        service_token=settings.service_token,
        timeout_seconds=300,
    )
    return UploadAndExtractCvUseCase(
        storage=storage,
        webhook_gateway=webhook_gateway,
        max_size_mb=settings.cv_max_size_mb,
        job_store=job_store,
    )


def _decode_base64_cv(b64: str) -> bytes:
    cleaned = b64.strip()
    try:
        return base64.b64decode(cleaned, validate=False) if cleaned else b""
    except Exception as exc:
        raise InvalidCvFileError("El contenido base64 del CV es inválido.") from exc


CV_TEST_HTML = """<!doctype html>
<html lang="es" data-bs-theme="dark">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Prueba de Extracción de CV · profile-service → n8n</title>
  <link
    href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css"
    rel="stylesheet"
    integrity="sha384-QWTKZyjpPEjISv5WaRU9OFeRpok6YctnYmDr5pNlyT2bRjXh0JMhjY6hW+ALEwIH"
    crossorigin="anonymous"
  />
  <style>
    :root {
      --bg: #0f172a;
      --panel: #1e293b;
      --border: #334155;
      --text: #f8fafc;
      --muted: #94a3b8;
      --primary: #38bdf8;
      --amber-bg: rgba(245, 158, 11, 0.16);
      --amber-border: #f59e0b;
      --amber-text: #fde68a;
      --green-bg: rgba(16, 185, 129, 0.15);
      --green-border: #10b981;
      --green-text: #a7f3d0;
    }
    body {
      background-color: var(--bg);
      color: var(--text);
    }
    /* Ancho fijo en columnas Bootstrap centradas verticalmente */
    .cv-fixed-col {
      max-width: 860px;
      width: 100%;
    }
    .card-custom {
      background-color: var(--panel);
      border: 1px solid var(--border);
      border-radius: 0.75rem;
      overflow: hidden;
    }
    .box-inner {
      background-color: #0b1120;
      border: 1px solid var(--border);
      border-radius: 0.5rem;
      min-width: 0;
    }
    .spinner-custom {
      width: 1rem;
      height: 1rem;
      border: 2.5px solid rgba(56, 189, 248, 0.25);
      border-top-color: var(--primary);
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
      flex-shrink: 0;
    }
    @keyframes spin {
      to { transform: rotate(360deg); }
    }
    .step-item {
      color: var(--muted);
      word-break: break-word;
      overflow-wrap: anywhere;
    }
    .step-item.active {
      color: var(--primary);
      font-weight: 600;
    }
    .step-item.done {
      color: var(--green-text);
    }
    .badge-ai {
      background: var(--amber-bg);
      border: 1px solid var(--amber-border);
      color: var(--amber-text);
    }
    .badge-ok {
      background: var(--green-bg);
      border: 1px solid var(--green-border);
      color: var(--green-text);
    }
    .disclaimer-box {
      background: rgba(245, 158, 11, 0.08);
      border-left: 3px solid var(--amber-border);
      color: var(--amber-text);
      word-break: break-word;
      overflow-wrap: anywhere;
    }
    .chip {
      display: inline-block;
      background: #1e293b;
      border: 1px solid #475569;
      padding: 0.25rem 0.6rem;
      border-radius: 0.35rem;
      font-size: 0.8rem;
      max-width: 100%;
      white-space: normal;
      word-break: break-word;
      overflow-wrap: anywhere;
      text-align: left;
    }
    /* Salto de línea obligatorio en la respuesta JSON y textos largos */
    .json-pre {
      background-color: #020617;
      border: 1px solid var(--border);
      border-radius: 0.5rem;
      color: #e2e8f0;
      font-size: 0.82rem;
      max-height: 560px;
      max-width: 100%;
      width: 100%;
      overflow-y: auto;
      overflow-x: hidden;
      white-space: pre-wrap;
      word-wrap: break-word;
      word-break: break-word;
      overflow-wrap: anywhere;
    }
  </style>
</head>
<body class="py-4">
  <div class="container">
    <div class="row justify-content-center g-4">
      <!-- Encabezado con el mismo ancho fijo de columna -->
      <div class="col-12 col-lg-10 col-xl-9 cv-fixed-col">
        <header class="pb-3 border-bottom border-secondary">
          <h1 class="h3 mb-1">Formulario de Prueba · Subir CV → Webhook n8n (WF-01)</h1>
          <p class="text-secondary mb-0 small text-break">
            Servicio: <strong>profile-service</strong> (<code>POST /api/v1/profiles/cv-extract/async</code>) →
            dispara <code>POST http://n8n:5678/webhook/cv-extract</code> y espera el resultado de forma asíncrona con indicador de progreso en vivo.
          </p>
        </header>
      </div>

      <!-- Tarjeta 1 (Arriba): Carga de CV y Progreso Asíncrono -->
      <div class="col-12 col-lg-10 col-xl-9 cv-fixed-col">
        <section class="card card-custom shadow-sm" aria-labelledby="form-title">
          <div class="card-body p-4">
            <h2 id="form-title" class="h5 mb-3">1. Enviar CV y Progreso de Procesamiento</h2>
            <form id="cv-form">
              <div class="mb-3">
                <label for="profile_id" class="form-label fw-semibold small">
                  ID de Perfil del Estudiante (profile_id)
                </label>
                <input
                  id="profile_id"
                  name="profile_id"
                  type="text"
                  class="form-control bg-dark text-light border-secondary"
                  value="prof-estudiante-01"
                  required
                />
              </div>

              <div class="mb-3">
                <label for="cv_file" class="form-label fw-semibold small">
                  Archivo de CV (.pdf, .docx, .doc, .md — máx. 5 MB)
                </label>
                <input
                  id="cv_file"
                  name="file"
                  type="file"
                  class="form-control bg-dark text-light border-secondary"
                  accept=".pdf,.docx,.doc,.md"
                  required
                />
                <div class="form-text text-secondary">
                  También podés usar el botón "Cargar CV de ejemplo (.md)" para generar un archivo de prueba automáticamente.
                </div>
              </div>

              <div class="d-flex flex-wrap gap-2 mt-3">
                <button type="button" id="btn-sample" class="btn btn-secondary fw-semibold">
                  Cargar CV de ejemplo (.md)
                </button>
                <button type="submit" id="btn-submit" class="btn btn-info fw-semibold text-dark flex-grow-1">
                  Enviar CV y Extraer Perfil JSON
                </button>
              </div>

              <div
                id="progress-panel"
                class="box-inner p-3 mt-3"
                style="display:none;"
                role="region"
                aria-live="polite"
                aria-label="Progreso de extracción de CV"
              >
                <div class="d-flex justify-content-between align-items-center gap-2 mb-2 small">
                  <div class="d-flex align-items-center gap-2 fw-semibold text-info text-break">
                    <span id="spinner-icon" class="spinner-custom"></span>
                    <span id="stage-label" class="text-break">Iniciando extracción...</span>
                  </div>
                  <span id="elapsed-label" class="text-secondary flex-shrink-0" style="font-variant-numeric: tabular-nums;">
                    0.0s
                  </span>
                </div>
                <div class="progress mb-3" style="height: 10px; background-color: #1e293b;">
                  <div
                    id="progress-fill"
                    class="progress-bar bg-info"
                    role="progressbar"
                    style="width: 0%; transition: width 0.35s ease;"
                  ></div>
                </div>
                <ul class="list-unstyled mb-0 small d-grid gap-1">
                  <li id="step-1" class="step-item">1. Validación y guardado en CV_STORAGE_PATH (profile-service)</li>
                  <li id="step-2" class="step-item">2. Extracción de texto del CV vía MCP (parse_cv_file)</li>
                  <li id="step-3" class="step-item">3. Estructuración con Agente IA (Natasha Romanoff · NVIDIA NIM)</li>
                  <li id="step-4" class="step-item">4. Verificación JSON Schema y Grounding anti-alucinación (WF-0V)</li>
                </ul>
              </div>

              <div id="status-msg" class="small text-success mt-2 text-break" role="status" aria-live="polite"></div>
            </form>
          </div>
        </section>
      </div>

      <!-- Tarjeta 2 (Abajo): Respuesta JSON del Perfil con salto de línea adaptable -->
      <div class="col-12 col-lg-10 col-xl-9 cv-fixed-col">
        <section class="card card-custom shadow-sm" aria-labelledby="result-title">
          <div class="card-body p-4">
            <div class="d-flex justify-content-between align-items-center flex-wrap gap-2 mb-3">
              <h2 id="result-title" class="h5 mb-0">2. Respuesta JSON del Perfil</h2>
              <button type="button" id="btn-copy" class="btn btn-sm btn-secondary fw-semibold">
                Copiar JSON
              </button>
            </div>

            <div id="error-container" class="alert alert-danger py-2 px-3 small text-break" style="display:none;"></div>

            <div id="ai-meta" style="display:none;">
              <div class="d-flex flex-wrap gap-2 mb-3">
                <span class="badge rounded-pill badge-ai text-wrap text-break">Sugerido por IA (origin: AI)</span>
                <span class="badge rounded-pill badge-ok text-wrap text-break" id="badge-model">Modelo: -</span>
                <span class="badge rounded-pill badge-ok text-wrap text-break" id="badge-verified">Verificado: -</span>
              </div>
              <div class="disclaimer-box p-2 rounded small mb-3 text-break" id="disclaimer-box"></div>

              <div class="row g-3 mb-3">
                <div class="col-12 col-md-6">
                  <div class="box-inner p-3 h-100">
                    <h3 class="h6 text-secondary text-uppercase small mb-2">Competencias (skills)</h3>
                    <div class="d-flex flex-wrap gap-1" id="skills-list"></div>
                  </div>
                </div>
                <div class="col-12 col-md-6">
                  <div class="box-inner p-3 h-100">
                    <h3 class="h6 text-secondary text-uppercase small mb-2">Idiomas (languages)</h3>
                    <div class="d-flex flex-wrap gap-1" id="languages-list"></div>
                  </div>
                </div>
              </div>

              <div class="box-inner p-3 mb-3">
                <h3 class="h6 text-secondary text-uppercase small mb-2">
                  Campos a completar manualmente (COMPLETAR_MANUALMENTE / [])
                </h3>
                <div class="d-flex flex-wrap gap-1" id="pending-list"></div>
              </div>
            </div>

            <pre id="json-output" class="json-pre p-3 mb-0">{
  "estado": "Esperando envío de CV...",
  "endpoint_asincrono": "POST /api/v1/profiles/cv-extract/async",
  "webhook_destino": "http://n8n:5678/webhook/cv-extract"
}</pre>
          </div>
        </section>
      </div>
    </div>
  </div>

  <script>
    const form = document.getElementById('cv-form');
    const fileInput = document.getElementById('cv_file');
    const profileInput = document.getElementById('profile_id');
    const btnSample = document.getElementById('btn-sample');
    const btnSubmit = document.getElementById('btn-submit');
    const btnCopy = document.getElementById('btn-copy');
    const statusMsg = document.getElementById('status-msg');
    const jsonOutput = document.getElementById('json-output');
    const errorContainer = document.getElementById('error-container');
    const aiMeta = document.getElementById('ai-meta');
    const badgeModel = document.getElementById('badge-model');
    const badgeVerified = document.getElementById('badge-verified');
    const disclaimerBox = document.getElementById('disclaimer-box');
    const skillsList = document.getElementById('skills-list');
    const languagesList = document.getElementById('languages-list');
    const pendingList = document.getElementById('pending-list');
    const progressPanel = document.getElementById('progress-panel');
    const progressFill = document.getElementById('progress-fill');
    const stageLabel = document.getElementById('stage-label');
    const elapsedLabel = document.getElementById('elapsed-label');
    const spinnerIcon = document.getElementById('spinner-icon');
    const stepItems = [
      document.getElementById('step-1'),
      document.getElementById('step-2'),
      document.getElementById('step-3'),
      document.getElementById('step-4'),
    ];

    const SAMPLE_CV_MD = `# Lucía Fernández
Desarrolladora Full Stack / Backend Python

## Experiencia Laboral
- **Desarrolladora Backend Python** en FinTech Sur (2023 - Presente, 2 años)
  Desarrollo de microservicios REST con Python, FastAPI, PostgreSQL, Docker y pruebas automatizadas con Pytest.
- **Desarrolladora Web Junior** en Agencia Digital BA (2022 - 2023, 1 año)
  Interfaces en React y TypeScript integradas con APIs REST.

## Educación
- **Ingeniería en Sistemas de Información** — Universidad Tecnológica Nacional (UTN) · En curso

## Competencias Técnicas
- Python (Avanzado - Nivel 4)
- FastAPI (Intermedio - Nivel 3)
- PostgreSQL (Intermedio - Nivel 3)
- Docker (Intermedio - Nivel 3)
- React (Básico - Nivel 2)
- TypeScript (Básico - Nivel 2)

## Idiomas
- Español: Nativo
- Inglés: Intermedio B2
`;

    const arrayBufferToBase64 = (buffer) => {
      const bytes = new Uint8Array(buffer);
      let binary = '';
      for (let i = 0; i < bytes.byteLength; i++) {
        binary += String.fromCharCode(bytes[i]);
      }
      return btoa(binary);
    };

    const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

    const updateProgressUi = (percent, stageText, activeStepIndex, elapsedSec, finished = false) => {
      progressPanel.style.display = 'block';
      progressFill.style.width = `${Math.min(100, Math.max(5, percent))}%`;
      stageLabel.textContent = stageText;
      elapsedLabel.textContent = `${Number(elapsedSec || 0).toFixed(1)}s`;
      spinnerIcon.style.display = finished ? 'none' : 'inline-block';

      stepItems.forEach((el, idx) => {
        const stepNum = idx + 1;
        el.classList.remove('active', 'done');
        if (finished || stepNum < activeStepIndex) {
          el.classList.add('done');
        } else if (stepNum === activeStepIndex) {
          el.classList.add('active');
        }
      });
    };

    const renderExtractedResult = (data, elapsedSec) => {
      jsonOutput.textContent = JSON.stringify(data, null, 2);
      statusMsg.textContent = `Extracción completada con éxito en ${Number(elapsedSec).toFixed(1)}s.`;
      aiMeta.style.display = 'block';
      badgeModel.textContent = `Modelo: ${data.model || 'nvidia'}`;
      badgeVerified.textContent = `Verificado: ${data.verified ? 'Sí (WF-0V)' : 'No'}`;
      disclaimerBox.textContent = data.disclaimer || '';

      skillsList.innerHTML = '';
      const skills = data.cv_suggestions?.skills || [];
      if (skills.length === 0) {
        skillsList.innerHTML = '<span class="chip">Sin competencias</span>';
      } else {
        for (const s of skills) {
          const sp = document.createElement('span');
          sp.className = 'chip';
          const lvl = s.level_estimado ?? s.level;
          sp.textContent = lvl ? `${s.name} (Nv. ${lvl})` : s.name;
          skillsList.appendChild(sp);
        }
      }

      languagesList.innerHTML = '';
      const langs = data.cv_suggestions?.languages || [];
      if (langs.length === 0) {
        languagesList.innerHTML = '<span class="chip">Sin idiomas</span>';
      } else {
        for (const l of langs) {
          const sp = document.createElement('span');
          sp.className = 'chip';
          const langName = l.language || l.name || 'Idioma';
          sp.textContent = l.level ? `${langName} (${l.level})` : langName;
          languagesList.appendChild(sp);
        }
      }

      pendingList.innerHTML = '';
      const pending = data.cv_suggestions?.pending_manual_fields || [];
      if (pending.length === 0) {
        pendingList.innerHTML = '<span class="chip">Ninguno (CV completo)</span>';
      } else {
        for (const p of pending) {
          const sp = document.createElement('span');
          sp.className = 'chip';
          sp.style.borderColor = '#f59e0b';
          sp.style.color = '#fde68a';
          sp.textContent = p;
          pendingList.appendChild(sp);
        }
      }
    };

    btnSample.addEventListener('click', () => {
      const blob = new Blob([SAMPLE_CV_MD], { type: 'text/markdown' });
      const file = new File([blob], 'cv_lucia_fernandez.md', { type: 'text/markdown' });
      const dt = new DataTransfer();
      dt.items.add(file);
      fileInput.files = dt.files;
      statusMsg.textContent = 'CV de ejemplo cargado: cv_lucia_fernandez.md (listo para enviar)';
    });

    btnCopy.addEventListener('click', async () => {
      await navigator.clipboard.writeText(jsonOutput.textContent || '');
      const prev = btnCopy.textContent;
      btnCopy.textContent = '¡Copiado!';
      setTimeout(() => { btnCopy.textContent = prev; }, 1500);
    });

    form.addEventListener('submit', async (ev) => {
      ev.preventDefault();
      errorContainer.style.display = 'none';
      aiMeta.style.display = 'none';
      statusMsg.textContent = '';

      if (!fileInput.files || fileInput.files.length === 0) {
        errorContainer.textContent = 'Seleccioná un archivo de CV o hacé clic en "Cargar CV de ejemplo (.md)".';
        errorContainer.style.display = 'block';
        return;
      }

      const file = fileInput.files[0];
      btnSubmit.disabled = true;
      updateProgressUi(10, 'Validando y guardando CV en profile-service...', 1, 0.0, false);

      const t0 = performance.now();
      const uiTimer = setInterval(() => {
        const localSec = (performance.now() - t0) / 1000;
        elapsedLabel.textContent = `${localSec.toFixed(1)}s`;
      }, 200);

      try {
        const buf = await file.arrayBuffer();
        const payload = {
          profile_id: profileInput.value.trim() || 'prof-estudiante-01',
          filename: file.name,
          mime_type: file.type || '',
          content_base64: arrayBufferToBase64(buf),
        };

        const startRes = await fetch('/api/v1/profiles/cv-extract/async', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
        const startData = await startRes.json();

        if (!startRes.ok || startData.error) {
          const errMsg = startData.error?.message || `Error HTTP ${startRes.status}`;
          errorContainer.textContent = `Error al iniciar la extracción: ${errMsg}`;
          errorContainer.style.display = 'block';
          jsonOutput.textContent = JSON.stringify(startData, null, 2);
          progressPanel.style.display = 'none';
          return;
        }

        const jobId = startData.job_id;
        jsonOutput.textContent = JSON.stringify(startData, null, 2);

        while (true) {
          await sleep(1200);
          const pollRes = await fetch(`/api/v1/profiles/cv-extract/jobs/${encodeURIComponent(jobId)}`);
          const job = await pollRes.json();
          const localSec = (performance.now() - t0) / 1000;

          if (job.status === 'processing') {
            updateProgressUi(
              job.progress_percent || 45,
              job.stage || 'Procesando CV con agentes IA en n8n...',
              job.step_index || 3,
              localSec,
              false
            );
            jsonOutput.textContent = JSON.stringify(job, null, 2);
            continue;
          }

          if (job.status === 'completed' && job.result) {
            updateProgressUi(100, 'Extracción y verificación completadas', 5, localSec, true);
            renderExtractedResult(job.result, localSec);
            break;
          }

          const failMsg = job.error?.message || 'Falló el procesamiento del CV en n8n';
          updateProgressUi(100, 'Error en el procesamiento', 0, localSec, true);
          errorContainer.textContent = `Error (${localSec.toFixed(1)}s): ${failMsg}`;
          errorContainer.style.display = 'block';
          jsonOutput.textContent = JSON.stringify(job, null, 2);
          break;
        }
      } catch (err) {
        errorContainer.textContent = `Error de red: ${err.message || err}`;
        errorContainer.style.display = 'block';
      } finally {
        clearInterval(uiTimer);
        btnSubmit.disabled = false;
      }
    });
  </script>
</body>
</html>
"""


@router.get("/cv-test", response_class=HTMLResponse, summary="Formulario de prueba para subir CV")
def cv_test_form() -> HTMLResponse:
    """Devuelve la interfaz HTML de prueba para subir un CV y ver el JSON extraído vía n8n."""
    return HTMLResponse(content=CV_TEST_HTML)


@router.post(
    "/cv-extract/async",
    status_code=202,
    summary="Iniciar extracción asíncrona de CV vía webhook n8n",
)
def start_async_extract_cv_endpoint(
    payload: CvExtractRequest,
    use_case: Annotated[UploadAndExtractCvUseCase, Depends(get_upload_cv_use_case)],
) -> JSONResponse:
    """Valida y guarda el CV inmediatamente, lanza el webhook a n8n en segundo plano y devuelve 202 con job_id."""
    content = _decode_base64_cv(payload.content_base64)
    snapshot = use_case.start_async(
        profile_id=payload.profile_id,
        filename=payload.filename,
        content=content,
        mime_type=payload.mime_type,
    )
    return JSONResponse(status_code=202, content=snapshot)


@router.get(
    "/cv-extract/jobs/{job_id}",
    summary="Consultar progreso y resultado de una extracción asíncrona de CV",
)
def get_extract_cv_job_status(
    job_id: str,
    use_case: Annotated[UploadAndExtractCvUseCase, Depends(get_upload_cv_use_case)],
) -> dict[str, Any]:
    """Devuelve el estado de avance (`processing | completed | failed`) y el JSON final cuando termina."""
    return use_case.get_job_status(job_id)


@router.post(
    "/cv-extract",
    summary="Subir CV, guardar en storage y extraer sugerencias vía webhook n8n (síncrono)",
)
def extract_cv_endpoint(
    payload: CvExtractRequest,
    use_case: Annotated[UploadAndExtractCvUseCase, Depends(get_upload_cv_use_case)],
) -> dict[str, Any]:
    """Recibe el CV, lo almacena en CV_STORAGE_PATH y consulta `POST /webhook/cv-extract` en n8n."""
    content = _decode_base64_cv(payload.content_base64)
    result = use_case.execute(
        profile_id=payload.profile_id,
        filename=payload.filename,
        content=content,
        mime_type=payload.mime_type,
    )
    return result.to_dict()
