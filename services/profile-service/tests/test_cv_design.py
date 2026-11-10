"""UT-PROF-10 (reglas del diseño del CV) y UT-PROF-11 (pedido a la IA, elección y descarga)."""

import copy
import dataclasses
import json
import re
from datetime import timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.domain.cv_design import (
    CHRONOLOGICAL,
    FIRST_JOB,
    SKILLS_BASED,
    CvLayoutSelector,
    CvSection,
    DesignSource,
    normalize_section_order,
    resolve_design,
    summarize_content,
)
from app.domain.cv_design_state import AiCvDesign, AiDesignStatus, CvDesignState, UserCvDesign
from app.domain.errors import CvDesignGatewayError
from app.domain.profile import StudentProfile
from app.infrastructure.container import Container
from app.infrastructure.n8n_cv_design import HttpN8nCvDesignGateway
from tests.conftest import COMPLETE_PROFILE, student_headers
from tests.fakes import FakeCvDesignGateway, FixedClock

DESIGN = "/api/v1/profiles/me/cv-design"


def _profile(container: Container, client: TestClient, **overrides: Any) -> StudentProfile:
    data = copy.deepcopy(COMPLETE_PROFILE)
    data.update(overrides)
    created = client.post("/api/v1/profiles/me", json=data, headers=student_headers())
    assert created.status_code == 201, created.text
    found = container.repository.get(created.json()["id"])
    assert found is not None
    return found


def _skills(n: int) -> list[dict[str, Any]]:
    return [{"name": f"Herramienta Ficticia {i}", "level": 3} for i in range(n)]


# ------------------------------------------------------------- UT-PROF-10 ---


def test_ut_prof_10_reglas_eligen_segun_el_contenido(
    container: Container, client: TestClient
) -> None:
    selector = CvLayoutSelector()
    with_experience = _profile(container, client)  # 21 meses de experiencia
    assert selector.select(summarize_content(with_experience)).layout is CHRONOLOGICAL

    first_job = dataclasses.replace(with_experience, experience=())
    verdict = selector.select(summarize_content(first_job))
    assert verdict.layout is FIRST_JOB
    assert verdict.section_order[1] is CvSection.EDUCATION
    assert verdict.reasons


def test_ut_prof_10_perfil_tecnico_va_por_competencias(
    container: Container, client: TestClient
) -> None:
    profile = _profile(
        container,
        client,
        experience=[],
        skills=_skills(9),
        projects=[{"name": "Proyecto Demo A"}, {"name": "Proyecto Demo B"}],
    )
    assert CvLayoutSelector().select(summarize_content(profile)).layout is SKILLS_BASED


def test_ut_prof_10_resumen_sin_datos_personales(container: Container, client: TestClient) -> None:
    profile = _profile(container, client)
    content = summarize_content(profile)
    raw = json.dumps(content.__dict__, ensure_ascii=False)
    for private in ("Lucía", "lucia.ficticia@example.com", "5555", "FinTech Ficticia", "UTN"):
        assert private not in raw
    assert content.experience_roles == ("Desarrolladora Backend",)
    assert content.fingerprint() == summarize_content(profile).fingerprint()
    assert len(content.fingerprint()) == 16
    changed = summarize_content(dataclasses.replace(profile, experience=()))
    assert changed.fingerprint() != content.fingerprint()


def test_ut_prof_10_normaliza_el_orden_pedido() -> None:
    order = normalize_section_order(
        ["projects", "summary", "PROJECTS", "fotos", " skills "], FIRST_JOB
    )
    assert order[:3] == (CvSection.SUMMARY, CvSection.PROJECTS, CvSection.SKILLS)
    assert len(order) == len(CvSection) and len(set(order)) == len(order)
    assert normalize_section_order([], CHRONOLOGICAL) == CHRONOLOGICAL.section_order


def test_ut_prof_10_prioridad_estudiante_ia_reglas(
    container: Container, client: TestClient
) -> None:
    profile = _profile(container, client)
    content = summarize_content(profile)
    rules = CvLayoutSelector().select(content)
    now = FixedClock().now()
    ai = AiCvDesign(
        status=AiDesignStatus.COMPLETED,
        request_id="cvd-1",
        requested_at=now,
        fingerprint=content.fingerprint(),
        layout="competencias",
        section_order=("summary", "projects"),
    )
    assert resolve_design(None, rules, content.fingerprint()).source is DesignSource.RULES
    by_ai = resolve_design(CvDesignState(ai=ai), rules, content.fingerprint())
    assert (by_ai.source, by_ai.layout) == (DesignSource.AI, SKILLS_BASED)
    assert by_ai.section_order[1] is CvSection.PROJECTS
    stale = resolve_design(CvDesignState(ai=ai), rules, "otra-huella")
    assert stale.source is DesignSource.RULES
    outside = dataclasses.replace(ai, layout="dos_columnas")
    assert resolve_design(CvDesignState(ai=outside), rules, content.fingerprint()).source is (
        DesignSource.RULES
    )
    user = CvDesignState(ai=ai, user=UserCvDesign("primer_empleo", now))
    assert resolve_design(user, rules, content.fingerprint()).layout is FIRST_JOB
    preview = resolve_design(user, rules, content.fingerprint(), override="cronologico")
    assert preview.layout is CHRONOLOGICAL


# ------------------------------------------------------------- UT-PROF-11 ---


def test_ut_prof_11_vista_por_reglas_y_catalogo(container: Container, client: TestClient) -> None:
    _profile(container, client)
    body = client.get(DESIGN, headers=student_headers()).json()
    assert body["effective"]["id"] == "cronologico"
    assert body["effective"]["source"] == "rules"
    assert body["rule_based"]["origin"] == "RULES"
    assert body["rule_based"]["engine_version"]
    assert body["ai_recommendation"] is None
    assert [x["id"] for x in body["catalog"]] == ["cronologico", "primer_empleo", "competencias"]
    # El perfil no expone el estado del diseño: se pide aparte.
    assert "cv_design" not in client.get("/api/v1/profiles/me", headers=student_headers()).json()


def test_ut_prof_11_pedido_a_la_ia_sin_datos_personales(
    container: Container, client: TestClient, design_gateway: FakeCvDesignGateway
) -> None:
    _profile(container, client)
    res = client.post(f"{DESIGN}/requests", headers=student_headers())
    assert res.status_code == 202
    body = client.get(DESIGN, headers=student_headers()).json()
    ai = body["ai_recommendation"]
    assert ai["origin"] == "AI" and ai["status"] == "completed"
    assert ai["model"] == "nvidia/modelo-ficticio" and ai["disclaimer"]
    assert ai["stale"] is False
    assert body["effective"]["source"] == "ai"
    assert body["effective"]["id"] == "primer_empleo"
    assert body["effective"]["section_order"][:4] == ["summary", "education", "projects", "skills"]
    assert len(body["effective"]["section_order"]) == len(CvSection)

    payload = design_gateway.payloads[0]
    assert payload["rule_based"]["layout"] == "cronologico"
    assert {x["id"] for x in payload["catalog"]} == {"cronologico", "primer_empleo", "competencias"}
    raw = json.dumps(payload, ensure_ascii=False)
    for private in ("Lucía", "lucia.ficticia@example.com", "5555", "FinTech Ficticia", "600000"):
        assert private not in raw


def test_ut_prof_11_requiere_consentimiento_de_ia(container: Container, client: TestClient) -> None:
    _profile(container, client, consents={"data_processing": True, "ai_processing": False})
    res = client.post(f"{DESIGN}/requests", headers=student_headers())
    assert res.status_code == 409
    assert res.json()["error"]["code"] == "AI_CONSENT_REQUIRED"


@pytest.mark.parametrize(
    "error",
    [CvDesignGatewayError("n8n caído"), RuntimeError("bug")],
)
def test_ut_prof_11_falla_de_la_ia_deja_las_reglas(
    container: Container,
    client: TestClient,
    design_gateway: FakeCvDesignGateway,
    error: Exception,
) -> None:
    _profile(container, client)
    design_gateway.error = error
    client.post(f"{DESIGN}/requests", headers=student_headers())
    body = client.get(DESIGN, headers=student_headers()).json()
    assert body["ai_recommendation"]["status"] == "failed"
    assert body["ai_recommendation"]["error"]
    assert body["effective"]["source"] == "rules"


def test_ut_prof_11_diseno_fuera_del_catalogo_se_descarta(
    container: Container, client: TestClient, design_gateway: FakeCvDesignGateway
) -> None:
    _profile(container, client)
    design_gateway.layout = "dos_columnas"
    client.post(f"{DESIGN}/requests", headers=student_headers())
    body = client.get(DESIGN, headers=student_headers()).json()
    assert body["ai_recommendation"]["status"] == "failed"
    assert body["effective"]["source"] == "rules"


def test_ut_prof_11_cambio_de_perfil_deja_vieja_la_sugerencia(
    container: Container, client: TestClient
) -> None:
    _profile(container, client)
    client.post(f"{DESIGN}/requests", headers=student_headers())
    client.patch(
        "/api/v1/profiles/me",
        json={"projects": [{"name": "Proyecto Demo nuevo"}]},
        headers=student_headers(),
    )
    body = client.get(DESIGN, headers=student_headers()).json()
    assert body["ai_recommendation"]["stale"] is True
    assert body["effective"]["source"] == "rules"


def test_ut_prof_11_pedido_colgado_vence(
    container: Container,
    client: TestClient,
    design_gateway: FakeCvDesignGateway,
    clock: FixedClock,
) -> None:
    profile = _profile(container, client)
    hung = AiCvDesign(
        status=AiDesignStatus.PROCESSING,
        request_id="cvd-colgado",
        requested_at=clock.now(),
        fingerprint="x",
    )
    container.repository.update(dataclasses.replace(profile, cv_design=CvDesignState(ai=hung)))
    client.post(f"{DESIGN}/requests", headers=student_headers())
    assert design_gateway.payloads == []  # en curso: no se repite
    clock.current += timedelta(minutes=11)
    view = client.get(DESIGN, headers=student_headers()).json()
    assert view["ai_recommendation"]["status"] == "failed"
    client.post(f"{DESIGN}/requests", headers=student_headers())
    assert len(design_gateway.payloads) == 1


def test_ut_prof_11_eleccion_del_estudiante(container: Container, client: TestClient) -> None:
    _profile(container, client)
    chosen = client.put(DESIGN, json={"layout": "competencias"}, headers=student_headers())
    assert chosen.status_code == 200
    assert chosen.json()["effective"] == {
        **chosen.json()["effective"],
        "id": "competencias",
        "source": "user",
    }
    assert chosen.json()["user_choice"]["layout"] == "competencias"
    back = client.put(DESIGN, json={"layout": None}, headers=student_headers()).json()
    assert back["effective"]["source"] == "rules" and back["user_choice"] is None
    bad = client.put(DESIGN, json={"layout": "dos_columnas"}, headers=student_headers())
    assert bad.status_code == 422
    assert bad.json()["error"]["code"] == "UNKNOWN_CV_LAYOUT"


def _headings(html: str) -> list[str]:
    return re.findall(r"<h2>([^<]+)</h2>", html)


def test_ut_prof_11_el_cv_respeta_el_diseno(container: Container, client: TestClient) -> None:
    _profile(container, client)
    rules = client.get("/api/v1/profiles/me/cv.html", headers=student_headers())
    assert rules.headers["x-cv-layout"] == "cronologico"
    headings = _headings(rules.text)
    assert headings.index("Experiencia") < headings.index("Educación")

    client.put(DESIGN, json={"layout": "primer_empleo"}, headers=student_headers())
    chosen = client.get("/api/v1/profiles/me/cv.html", headers=student_headers())
    headings = _headings(chosen.text)
    assert headings.index("Educación") < headings.index("Experiencia")

    preview = client.get(
        "/api/v1/profiles/me/cv.html?layout=competencias", headers=student_headers()
    )
    assert preview.headers["x-cv-layout"] == "competencias"
    assert _headings(preview.text)[:2] == ["Perfil profesional", "Competencias"]
    docx = client.get("/api/v1/profiles/me/cv.docx?layout=primer_empleo", headers=student_headers())
    assert docx.status_code == 200 and docx.headers["x-cv-layout"] == "primer_empleo"
    bad = client.get("/api/v1/profiles/me/cv.html?layout=fotos", headers=student_headers())
    assert bad.status_code == 422


def test_ut_prof_11_parsea_la_respuesta_de_n8n() -> None:
    parsed = HttpN8nCvDesignGateway.parse(
        json.dumps(
            {
                "design": {
                    "layout": "competencias",
                    "section_order": ["summary", "skills"],
                    "rationale": "Muchas competencias con proyectos.",
                },
                "model": "nvidia/modelo-ficticio",
                "generated_at": "2026-11-05T12:00:00Z",
            }
        )
    )
    assert parsed.layout == "competencias" and parsed.section_order == ("summary", "skills")
    assert parsed.generated_at.tzinfo is not None
    for raw in ("no-json", "[]", '{"error": {"message": "sin cupo"}}', '{"design": {}}'):
        with pytest.raises(CvDesignGatewayError):
            HttpN8nCvDesignGateway.parse(raw)
