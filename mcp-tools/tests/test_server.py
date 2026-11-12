from app.main import TOOL_PROFILES, allowed_tools, mcp


def test_server_is_named() -> None:
    assert mcp.name == "bolsa-mcp-tools"


def test_without_herramientas_the_profile_rules() -> None:
    assert allowed_tools("postulante", None) == TOOL_PROFILES["postulante"]
    assert allowed_tools(None, None) is None
    assert allowed_tools("desconocido", None) is None


def test_herramientas_narrows_the_profile() -> None:
    assert allowed_tools("postulante", "resolver_skills") == {"resolver_skills"}
    assert allowed_tools("verificador", " validate_json_schema , check_grounding ") == {
        "validate_json_schema",
        "check_grounding",
    }


def test_herramientas_never_adds_tools_outside_the_profile() -> None:
    # `parse_cv_file` es del perfil `adjuntos`: pedirla desde `postulante` no la habilita.
    assert allowed_tools("postulante", "resolver_skills,parse_cv_file") == {"resolver_skills"}


def test_empty_herramientas_means_no_tools() -> None:
    assert allowed_tools("cv", "") == set()
    assert allowed_tools(None, "") == set()
