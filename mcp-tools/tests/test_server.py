from app.main import mcp


def test_server_is_named() -> None:
    assert mcp.name == "bolsa-mcp-tools"
