"""Tests unitarios UT-MCP-01 y UT-MCP-02: herramientas MCP, gateways HTTP, mocks y auth."""

import base64

import httpx
import pytest
import respx
from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from app.domain.errors import NotFoundError, UpstreamError
from app.infrastructure.gateways_http import (
    HttpJobsGateway,
    HttpMatchingGateway,
    HttpProfileGateway,
    HttpRecommendationStore,
)
from app.infrastructure.security import MaskKeyLogFilter, ServiceTokenMiddleware
from app.infrastructure.settings_env import EnvSettingsProvider, PanelSettingsProvider
from app.infrastructure.skills_fs import FileSystemSkillRepository
from app.tools.registry import build_container, register_tools


@pytest.mark.asyncio
async def test_ut_mcp_01_all_tools_with_mocks() -> None:
    """UT-MCP-01: Todas las herramientas MCP responden con el contrato esperado usando mocks."""
    env = {
        "MCP_USE_MOCKS": "true",
        "AGENT_SETTINGS_SOURCE": "env",
        "RECO_MAX_JOBS_PER_STUDENT": "5",
        "RECO_MAX_PROFILES_PER_JOB": "10",
        "RECO_MAX_ITEMS_PER_JOB": "3",
    }
    container = build_container(env)
    server = FastMCP("test-mcp")
    tools = register_tools(server, container)

    settings_res = await tools["get_agent_settings"]()
    assert settings_res["ok"] is True
    assert settings_res["recommendations"]["max_items_per_job"] == 3

    prof_res = await tools["get_profile"]("stu-001")
    assert prof_res["ok"] is True
    assert prof_res["full_name"] == "Valentina Gómez"

    not_found_res = await tools["get_profile"]("stu-999")
    assert not_found_res["ok"] is False
    assert not_found_res["error"]["code"] == "not_found"

    list_prof = await tools["list_candidate_profiles"](skills=["Python"], limit=5)
    assert list_prof["ok"] is True
    assert len(list_prof["data"]) == 2

    job_res = await tools["get_job"]("job-001")
    assert job_res["ok"] is True
    assert job_res["title"] == "Desarrollador/a Backend Python Jr."

    jobs_list = await tools["list_active_jobs"](limit=2)
    assert jobs_list["ok"] is True
    assert len(jobs_list["data"]) == 2

    # compute_match siempre devuelve origin="RULES"
    match_res = await tools["compute_match"]("stu-001", "job-001")
    assert match_res["ok"] is True
    assert match_res["origin"] == "RULES"
    assert match_res["score"] > 70

    # Regla excluyente: stu-002 no tiene Python (excluyente en job-003) -> score <= 40
    excl_res = await tools["compute_match"]("stu-002", "job-003")
    assert excl_res["ok"] is True
    assert excl_res["score"] <= 40.0

    gaps_res = await tools["missing_skills"]("stu-001", "job-001")
    assert gaps_res["ok"] is True
    skills_missing = [g["skill"] for g in gaps_res["data"]]
    assert "Docker" in skills_missing

    courses_res = tools["search_courses"](["Docker", "Testing"], limit=3)
    assert courses_res["ok"] is True
    assert len(courses_res["data"]) >= 2

    # save_recommendation sella origin="AI" y recorta a max_items_per_job (3)
    items = [
        {"type": "course", "skill": "Docker", "text": "Hacer curso Docker", "priority": "alta"}
        for _ in range(5)
    ]
    saved_res = await tools["save_recommendation"](
        profile_id="stu-001",
        job_id="job-001",
        items=items,
        model="deepseek-ai/deepseek-v4.1-flash",
        prompt_version="1.0.0",
    )
    assert saved_res["ok"] is True
    assert saved_res["origin"] == "AI"
    assert len(saved_res["items"]) == 3

    cv_b64 = base64.b64encode(b"# CV de prueba\nSkills: Python, SQL").decode("ascii")
    cv_res = await tools["parse_cv_file"](cv_b64, "cv.md")
    assert cv_res["ok"] is True
    assert "Python" in cv_res["text"]

    cv_alias = await tools["parse_cv_text"](cv_b64, "cv.md")
    assert cv_alias["ok"] is True

    leer_arch = await tools["leer_archivo"](cv_b64, "cv.md")
    assert leer_arch["ok"] is True
    assert leer_arch["archivo"] == "cv.md"
    assert "Python" in leer_arch["texto"]

    fh_res = tools["fecha_hora"]()
    assert fh_res["ok"] is True
    assert "today" in fh_res

    skills_list_res = tools["list_skills"]()
    assert skills_list_res["ok"] is True
    skill_ids = [s["id"] for s in skills_list_res["skills"]]
    assert "extraccion-cv" in skill_ids
    assert "orientacion-postulante" in skill_ids

    skill_read = tools["leer_skill"]("extraccion-cv")
    assert skill_read["ok"] is True
    assert "cv_standard" in skill_read["content"]

    skill_missing = tools["leer_skill"]("no-existe-skill")
    assert skill_missing["ok"] is False
    assert skill_missing["error"]["code"] == "not_found"

    r_res = await tools["router_reserve"](role="cv")
    assert r_res["ok"] is True
    assert r_res["action"] == "call"
    chosen = r_res["model"]

    f_res = tools["router_report_failure"](chosen, "429 rate limit")
    assert f_res["ok"] is True
    assert f_res["kind"] == "rate_limit"

    s_res = tools["router_report_success"](chosen)
    assert s_res["ok"] is True

    st_res = tools["router_status"]()
    assert st_res["ok"] is True
    assert chosen in st_res["models"]


@pytest.mark.asyncio
async def test_ut_mcp_02_http_gateways_with_respx() -> None:
    """UT-MCP-02: Los adaptadores HTTP envían X-Service-Token y traducen errores 404/5xx."""
    svc_key = "test-service-header-value"
    with respx.mock(assert_all_called=False) as mock:
        prof_route = mock.get("http://profile-service:8000/api/v1/profiles/stu-10").mock(
            return_value=httpx.Response(200, json={"id": "stu-10", "full_name": "Ana"})
        )
        mock.get("http://profile-service:8000/api/v1/profiles/missing").mock(
            return_value=httpx.Response(404, json={"error": "not found"})
        )
        mock.get("http://jobs-service:8000/api/v1/jobs").mock(
            return_value=httpx.Response(200, json={"items": [{"id": "job-10"}]})
        )
        mock.post("http://matching-service:8000/api/v1/matches").mock(
            return_value=httpx.Response(
                200,
                json={"score": 88.0, "origin": "RULES", "engine_version": "1.0.0"},
            )
        )
        mock.post("http://matching-service:8000/api/v1/matches/recommendations").mock(
            return_value=httpx.Response(500, text="Internal Server Error")
        )
        mock.get("http://panel:8000/api/v1/settings").mock(
            return_value=httpx.Response(
                200,
                json={
                    "rpm_limit": 30,
                    "recommendations": {"max_jobs_per_student": 4},
                    "notifications": {"min_score": 80, "admin_email": "ops@example.test"},
                },
            )
        )

        profiles = HttpProfileGateway("http://profile-service:8000", svc_key)
        jobs = HttpJobsGateway("http://jobs-service:8000", svc_key)
        matching = HttpMatchingGateway("http://matching-service:8000", svc_key)
        recos = HttpRecommendationStore("http://matching-service:8000", svc_key)
        panel = PanelSettingsProvider(
            "http://panel:8000/api/v1/settings",
            svc_key,
            fallback=EnvSettingsProvider(),
        )

        p = await profiles.get_profile("stu-10")
        assert p["id"] == "stu-10"
        assert prof_route.calls.last.request.headers["X-Service-Token"] == svc_key

        with pytest.raises(NotFoundError):
            await profiles.get_profile("missing")

        j_list = await jobs.list_active_jobs(limit=5)
        assert j_list == [{"id": "job-10"}]

        m = await matching.compute_match("stu-10", "job-10")
        assert m["score"] == 88.0

        with pytest.raises(UpstreamError):
            await recos.save({"profile_id": "stu-10"})

        cfg = await panel.get()
        assert cfg.source == "panel"
        assert cfg.rpm_limit == 30
        assert cfg.recommendations.max_jobs_per_student == 4
        assert cfg.notifications.min_score == 80
        assert cfg.notifications.admin_email == "ops@example.test"


def test_service_token_middleware() -> None:
    async def ok_endpoint(_: Request) -> JSONResponse:
        return JSONResponse({"ok": True})

    inner = Starlette(
        routes=[
            Route("/health", ok_endpoint),
            Route("/mcp", ok_endpoint),
            Route("/router/status", ok_endpoint),
        ]
    )
    app = ServiceTokenMiddleware(inner, expected_token="my-secret")  # noqa: S106
    client = TestClient(app)

    # /health es público
    assert client.get("/health").status_code == 200
    # /mcp y /router exigen token
    assert client.get("/mcp").status_code == 401
    assert client.get("/router/status").status_code == 401
    # Con X-Service-Token, Authorization Bearer o ?key= pasa
    assert client.get("/mcp", headers={"X-Service-Token": "my-secret"}).status_code == 200
    assert (
        client.get("/router/status", headers={"Authorization": "Bearer my-secret"}).status_code
        == 200
    )
    assert client.get("/mcp?key=my-secret").status_code == 200


def test_skill_repository_loop_protection_and_mask_filter() -> None:
    import logging

    repo = FileSystemSkillRepository(max_reads_per_session=2)
    first = repo.read_skill("extraccion-cv", session_id="ses-1")
    assert first["loop_stopped"] is False
    # Releer la misma skill en la misma sesión corta el bucle
    dup = repo.read_skill("extraccion-cv", session_id="ses-1")
    assert dup["loop_stopped"] is True
    assert "Ya leíste esta parte" in dup["content"]

    second = repo.read_skill("orientacion-postulante", session_id="ses-1")
    assert second["loop_stopped"] is False
    # Tercera lectura supera max_reads_per_session=2
    third = repo.read_skill("seleccion-candidatos", session_id="ses-1")
    assert third["loop_stopped"] is True
    assert "Ya leíste 2 skills" in third["content"]

    rec = logging.LogRecord(
        "uvicorn.access", logging.INFO, "", 1, "%s", ("GET /mcp?key=secret123&perfil=cv",), None
    )
    flt = MaskKeyLogFilter()
    assert flt.filter(rec) is True
    assert "key=***" in str(rec.args)


def test_ut_mcp_04_cv_design_schema_and_skill() -> None:
    """UT-MCP-04: la skill `diseno-cv` se lista y lee, y `cv_design` acepta sólo el catálogo."""
    container = build_container({"MCP_USE_MOCKS": "true", "AGENT_SETTINGS_SOURCE": "env"})
    tools = register_tools(FastMCP("test-mcp"), container)

    skill_ids = [s["id"] for s in tools["list_skills"]()["skills"]]
    assert "diseno-cv" in skill_ids
    skill = tools["leer_skill"]("diseno-cv")
    assert skill["ok"] is True
    assert "cv_design" in skill["content"]
    assert "primer_empleo" in skill["content"]

    verification = container.verification
    good = (
        '{"layout": "primer_empleo", "section_order": ["summary", "education", "projects"],'
        ' "rationale": "Sin experiencia laboral, pero con proyectos alineados al puesto."}'
    )
    assert verification.validate_json("cv_design", good)["valid"] is True

    for bad in (
        '{"layout": "dos_columnas", "section_order": ["summary"], "rationale": "Más visual."}',
        '{"layout": "cronologico", "section_order": ["summary", "summary"],'
        ' "rationale": "Repite una sección del CV."}',
        '{"layout": "cronologico", "section_order": ["summary", "fotos"],'
        ' "rationale": "Sección fuera del catálogo."}',
        '{"layout": "cronologico", "section_order": ["summary"], "rationale": "ok",'
        ' "score": 90}',
    ):
        assert verification.validate_json("cv_design", bad)["valid"] is False, bad
