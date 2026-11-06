"""UT-PROF-07: flujo completo por HTTP (alta → CV → confirmar → completar → descargar CV)."""

import base64
import copy

from fastapi.testclient import TestClient

from tests import jwt_helpers
from tests.conftest import COMPLETE_PROFILE, service_headers, student_headers, wait_job

MD_CV = b"# Lucia Ficticia\nPython y FastAPI"


def _error(response: object) -> dict[str, object]:
    body = response.json()  # type: ignore[attr-defined]
    assert set(body) == {"error"} and {"code", "message", "details"} <= set(body["error"])
    return body["error"]  # type: ignore[no-any-return]


def test_ut_prof_07_requiere_autenticacion(client: TestClient) -> None:
    assert _error(client.get("/api/v1/profiles/me"))["code"] == "UNAUTHORIZED"
    bad = client.get("/api/v1/profiles/me", headers={"X-Service-Token": "falso"})
    assert bad.status_code == 401
    otra_clave = {
        "Authorization": f"Bearer {jwt_helpers.make_token('u', 'student', other_key=True)}"
    }
    assert client.get("/api/v1/profiles/me", headers=otra_clave).status_code == 401
    # El token de servicio nunca se acepta como Bearer.
    as_bearer = {"Authorization": "Bearer token-de-servicio-de-prueba"}
    assert client.get("/api/v1/profiles/me", headers=as_bearer).status_code == 401
    company = jwt_helpers.bearer(jwt_helpers.COMPANY_001, "company")
    assert _error(client.get("/api/v1/profiles/me", headers=company))["code"] == "FORBIDDEN"


def test_ut_prof_07_flujo_cv_a_perfil_completo(client: TestClient) -> None:
    h = student_headers()
    missing = client.get("/api/v1/profiles/me", headers=h)
    assert missing.status_code == 404 and _error(missing)["code"] == "PROFILE_NOT_FOUND"

    upload = client.post(
        "/api/v1/profiles/me/cv",
        headers=h,
        files={"file": ("mi_cv.md", MD_CV, "text/markdown")},
    )
    assert upload.status_code == 202, upload.text
    job_id = upload.json()["job_id"]
    done = wait_job(
        lambda j: client.get(f"/api/v1/profiles/me/cv/jobs/{j}", headers=h).json(), job_id
    )
    assert done["status"] == "completed"
    draft = done["result"]["profile_draft"]

    # Guardar el borrador tal cual falla: tiene campos COMPLETAR_MANUALMENTE.
    raw = client.patch("/api/v1/profiles/me", headers=h, json={"headline": draft["headline"]})
    assert raw.status_code == 422 and _error(raw)["code"] == "INVALID_INPUT"

    # Paso 1: el usuario confirma lo reconocido y completa lo que faltaba.
    skills = [
        {
            "name": s["name"],
            "level": s["level"] if isinstance(s["level"], int) else 3,
            "source": "cv_ai",
        }
        for s in draft["skills"]
    ]
    step1 = {
        "personal": {**draft["personal"], "phone": "+54 11 5555-0000"},
        "headline": "Estudiante de Sistemas · Backend",
        "summary": draft["summary"],
        "skills": skills,
        "experience": draft["experience"],
        "education": draft["education"],
        "languages": [
            {"name": lang["name"], "level": lang["level"]} for lang in draft["languages"]
        ],
        "links": draft["links"],
    }
    saved = client.patch("/api/v1/profiles/me", headers=h, json=step1)
    assert saved.status_code == 200, saved.text
    body = saved.json()
    assert body["status"] == "draft" and body["completion"]["can_generate_cv"] is True
    steps = {s["step"]: s["complete"] for s in body["completion"]["steps"]}
    assert steps == {"cv": True, "preferences": False, "privacy": False}

    # Paso 2 y 3: preferencias y consentimiento.
    step2 = {
        "work_conditions": COMPLETE_PROFILE["work_conditions"],
        "target": COMPLETE_PROFILE["target"],
        "consents": {"data_processing": True},
    }
    final = client.patch("/api/v1/profiles/me", headers=h, json=step2)
    assert final.status_code == 200 and final.json()["status"] == "complete"

    pdf_or_docx = client.get("/api/v1/profiles/me/cv.docx", headers=h)
    assert pdf_or_docx.status_code == 200
    assert (
        pdf_or_docx.headers["content-disposition"]
        == 'attachment; filename="CV_Lucia_Fernandez.docx"'
    )
    preview = client.get("/api/v1/profiles/me/cv.html", headers=h)
    assert preview.headers["content-type"].startswith("text/html")
    assert "inline" in preview.headers["content-disposition"]

    discard = client.delete("/api/v1/profiles/me/cv-suggestions", headers=h)
    assert discard.status_code == 204
    assert client.get("/api/v1/profiles/me/cv-suggestions", headers=h).status_code == 404


def test_ut_prof_07_alta_manual_y_validaciones(client: TestClient) -> None:
    h = student_headers()
    created = client.post("/api/v1/profiles/me", headers=h, json=copy.deepcopy(COMPLETE_PROFILE))
    assert created.status_code == 201 and created.json()["status"] == "complete"
    again = client.post("/api/v1/profiles/me", headers=h)
    assert again.status_code == 409 and _error(again)["code"] == "PROFILE_ALREADY_EXISTS"

    invalid = client.patch(
        "/api/v1/profiles/me",
        headers=h,
        json={"work_conditions": {"work_modality": ["teletrabajo"]}, "extra": 1},
    )
    assert invalid.status_code == 422
    locs = [e["loc"] for e in _error(invalid)["details"]["errors"]]  # type: ignore[index]
    assert ["body", "extra"] in locs

    bad_salary = client.patch(
        "/api/v1/profiles/me",
        headers=h,
        json={
            "work_conditions": {
                "salary": {"min": 100, "max": 50, "currency": "ARS", "period": "month"}
            }
        },
    )
    assert bad_salary.status_code == 422
    to_agree = client.patch(
        "/api/v1/profiles/me", headers=h, json={"work_conditions": {"salary": {"to_agree": True}}}
    )
    assert to_agree.status_code == 200


def test_ut_prof_07_cv_incompleto_y_archivo_invalido(client: TestClient) -> None:
    h = student_headers()
    client.post("/api/v1/profiles/me", headers=h)
    incomplete = client.get("/api/v1/profiles/me/cv.pdf", headers=h)
    assert incomplete.status_code == 409 and _error(incomplete)["code"] == "PROFILE_INCOMPLETE"

    exe = client.post(
        "/api/v1/profiles/me/cv",
        headers=h,
        files={"file": ("virus.exe", b"MZ", "application/octet-stream")},
    )
    assert exe.status_code == 422 and _error(exe)["code"] == "INVALID_CV_FILE"
    big = client.post(
        "/api/v1/profiles/me/cv",
        headers=h,
        files={"file": ("cv.pdf", b"x" * (5 * 1024 * 1024 + 1), "application/pdf")},
    )
    assert big.status_code == 422
    unknown_job = client.get("/api/v1/profiles/me/cv/jobs/cvjob-nada", headers=h)
    assert unknown_job.status_code == 404


def test_ut_prof_07_endpoints_internos(client: TestClient) -> None:
    h = student_headers()
    profile_id = client.post(
        "/api/v1/profiles/me", headers=h, json=copy.deepcopy(COMPLETE_PROFILE)
    ).json()["id"]

    pool = client.get("/api/v1/profiles?limit=10&skills=python", headers=service_headers())
    assert pool.status_code == 200 and pool.json()["items"][0]["id"] == profile_id
    assert client.get("/api/v1/profiles", headers=h).status_code == 403

    detail = client.get(f"/api/v1/profiles/{profile_id}", headers=service_headers())
    assert detail.status_code == 200 and "inclusion" not in detail.json()
    other = jwt_helpers.bearer(jwt_helpers.STUDENT_001, "student")
    assert client.get(f"/api/v1/profiles/{profile_id}", headers=other).status_code == 404
    admin = jwt_helpers.bearer(jwt_helpers.ADMIN_001, "admin")
    assert client.get(f"/api/v1/profiles/{profile_id}", headers=admin).json()["completion"]
    assert client.delete("/api/v1/profiles/me", headers=h).status_code == 405


def test_endpoints_de_compatibilidad_cv_extract(client: TestClient) -> None:
    page = client.get("/api/v1/profiles/cv-test")
    assert page.status_code == 200 and 'id="access_token"' in page.text

    payload = {
        "profile_id": "prof-test-99",
        "filename": "cv.md",
        "mime_type": "text/markdown",
        "content_base64": base64.b64encode(MD_CV).decode("ascii"),
    }
    assert client.post("/api/v1/profiles/cv-extract/async", json=payload).status_code == 401

    sync = client.post("/api/v1/profiles/cv-extract", json=payload, headers=service_headers())
    assert sync.status_code == 200 and sync.json()["profile_id"] == "prof-test-99"
    forbidden = client.post("/api/v1/profiles/cv-extract", json=payload, headers=student_headers())
    assert forbidden.status_code == 403

    started = client.post(
        "/api/v1/profiles/cv-extract/async", json=payload, headers=student_headers()
    )
    assert started.status_code == 202
    job = started.json()
    assert job["profile_id"] == "prof-test-001"  # se usa el perfil del estudiante
    status = client.get(
        f"/api/v1/profiles/cv-extract/jobs/{job['job_id']}", headers=student_headers()
    )
    assert status.status_code == 200

    svc = client.post("/api/v1/profiles/cv-extract/async", json=payload, headers=service_headers())
    svc_job = svc.json()["job_id"]
    assert (
        client.get(
            f"/api/v1/profiles/cv-extract/jobs/{svc_job}", headers=service_headers()
        ).status_code
        == 200
    )
    company = jwt_helpers.bearer(jwt_helpers.COMPANY_001, "company")
    assert (
        client.post("/api/v1/profiles/cv-extract/async", json=payload, headers=company).status_code
        == 403
    )
    bad = {**payload, "filename": "virus.bat"}
    assert (
        client.post("/api/v1/profiles/cv-extract", json=bad, headers=service_headers()).status_code
        == 422
    )
