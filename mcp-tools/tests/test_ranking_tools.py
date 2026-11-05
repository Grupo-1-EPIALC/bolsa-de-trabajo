"""Herramientas MCP de ranking por reglas: rank_jobs_for_student y rank_candidates_for_job."""

import httpx
import pytest
import respx
from mcp.server.fastmcp import FastMCP

from app.infrastructure.gateways_http import HttpMatchingGateway
from app.main import TOOL_PROFILES
from app.tools.registry import build_container, register_tools

ENV = {"MCP_USE_MOCKS": "true", "AGENT_SETTINGS_SOURCE": "env"}


@pytest.fixture
def tools() -> dict[str, object]:
    return register_tools(FastMCP("test-ranking"), build_container(ENV))


@pytest.mark.asyncio
async def test_rank_jobs_for_student_with_mocks(tools: dict[str, object]) -> None:
    rank = tools["rank_jobs_for_student"]
    result = await rank("stu-001")  # type: ignore[operator]

    assert result["ok"] is True
    assert result["origin"] == "RULES"
    items = result["items"]
    assert [i["rank"] for i in items] == list(range(1, len(items) + 1))
    scores = [i["match"]["score"] for i in items]
    assert scores == sorted(scores, reverse=True)
    assert {"job_id", "title"} <= set(items[0]["job"])
    assert "full_name" not in result["profile"]

    limited = await rank("stu-001", limit=1)  # type: ignore[operator]
    assert len(limited["items"]) == 1


@pytest.mark.asyncio
async def test_rank_candidates_for_job_with_mocks(tools: dict[str, object]) -> None:
    rank = tools["rank_candidates_for_job"]
    result = await rank("job-001", limit=2)  # type: ignore[operator]

    assert result["ok"] is True
    assert len(result["items"]) == 2
    first = result["items"][0]
    assert first["candidate"]["profile_id"].startswith("stu-")
    assert "full_name" not in first["candidate"]  # sin datos personales
    assert first["match"]["origin"] == "RULES"


@pytest.mark.asyncio
async def test_rank_tools_report_errors(tools: dict[str, object]) -> None:
    missing = await tools["rank_candidates_for_job"]("job-999")  # type: ignore[operator]
    empty = await tools["rank_jobs_for_student"]("  ")  # type: ignore[operator]
    negative = await tools["rank_jobs_for_student"]("stu-001", limit=-1)  # type: ignore[operator]

    assert missing["ok"] is False and missing["error"]["code"] == "not_found"
    assert empty["ok"] is False and empty["error"]["code"] == "invalid_input"
    assert negative["ok"] is False and negative["error"]["code"] == "invalid_input"


@pytest.mark.asyncio
async def test_http_ranking_uses_matching_service_endpoints() -> None:
    svc_key = "valor-ficticio"
    with respx.mock(assert_all_called=True) as mock:
        jobs_route = mock.get(
            "http://matching-service:8000/api/v1/matches/students/stu-1/jobs"
        ).mock(return_value=httpx.Response(200, json={"origin": "RULES", "items": []}))
        cands_route = mock.get(
            "http://matching-service:8000/api/v1/matches/jobs/job-1/candidates"
        ).mock(return_value=httpx.Response(200, json={"origin": "RULES", "items": []}))

        gateway = HttpMatchingGateway("http://matching-service:8000", svc_key)
        await gateway.rank_jobs_for_student("stu-1", None)
        await gateway.rank_candidates_for_job("job-1", 3)

        # Sin limit => matching-service usa la cantidad configurada por el admin
        assert "limit" not in jobs_route.calls.last.request.url.params
        assert cands_route.calls.last.request.url.params["limit"] == "3"
        assert cands_route.calls.last.request.headers["X-Service-Token"] == svc_key


def test_ranking_tools_are_in_the_right_profiles() -> None:
    assert "rank_jobs_for_student" in TOOL_PROFILES["postulante"]
    assert "rank_candidates_for_job" in TOOL_PROFILES["empresa"]
    assert "rank_candidates_for_job" not in TOOL_PROFILES["postulante"]
