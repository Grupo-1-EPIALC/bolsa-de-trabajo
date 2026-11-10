"""UT-MCP-06: herramienta `resolver_skills` (diccionario de competencias de matching-service)."""

import json
from typing import Any

import httpx
import pytest
import respx
from mcp.server.fastmcp import FastMCP

from app.infrastructure.gateways_http import HttpMatchingGateway
from app.main import TOOL_PROFILES
from app.tools.registry import build_container, register_tools

ENV = {"MCP_USE_MOCKS": "true", "AGENT_SETTINGS_SOURCE": "env"}


@pytest.fixture
def tools() -> dict[str, Any]:
    return register_tools(FastMCP("test-resolver"), build_container(ENV))


@pytest.mark.asyncio
async def test_ut_mcp_06_resolver_skills_with_mocks(tools: dict[str, Any]) -> None:
    result = await tools["resolver_skills"](
        ["Postgres", "MySQL", "GitLab", "SQL", "Cobol"], ["MariaDB", "GitHub", "PostgreSQL"]
    )
    assert result["ok"] is True and result["origin"] == "RULES"
    items = {i["key"]: i for i in result["items"]}
    assert items["postgresql"]["covered_by"]["relation"] == "exact"
    assert items["mysql"]["covered_by"]["relation"] == "equivalent"
    assert items["gitlab"]["covered_by"] == {
        "relation": "similar",
        "credit": 0.75,
        "via": "github",
        "full": False,
    }
    assert items["sql"]["covered_by"]["relation"] == "implied"
    assert items["cobol"]["covered_by"] is None


@pytest.mark.asyncio
async def test_resolver_skills_validates_input(tools: dict[str, Any]) -> None:
    empty = await tools["resolver_skills"]([" "])
    assert empty["ok"] is False
    too_many = await tools["resolver_skills"]([f"s{i}" for i in range(51)])
    assert too_many["ok"] is False


@pytest.mark.asyncio
async def test_http_resolver_calls_matching_service() -> None:
    with respx.mock(assert_all_called=True) as mock:
        route = mock.post("http://matching-service:8000/api/v1/matches/skills/resolve").mock(
            return_value=httpx.Response(200, json={"origin": "RULES", "items": []})
        )
        gateway = HttpMatchingGateway("http://matching-service:8000", "valor-ficticio")
        await gateway.resolve_skills(["GitLab"], ["GitHub"])
        body = json.loads(route.calls.last.request.content)
        assert body == {"skills": ["GitLab"], "profile_skills": ["GitHub"]}


def test_resolver_skills_is_available_to_the_agents() -> None:
    for profile in ("cv", "postulante", "empresa", "verificador"):
        assert "resolver_skills" in TOOL_PROFILES[profile], profile
    assert "resolver_skills" not in TOOL_PROFILES["adjuntos"]
