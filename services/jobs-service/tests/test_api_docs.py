"""UT-JOBS-04: Swagger UI, ReDoc y OpenAPI bajo el prefijo del servicio (pasan por el gateway)."""

from fastapi.testclient import TestClient

from app.main import SERVICE_VERSION, app


def test_api_docs_bajo_el_prefijo_del_servicio() -> None:
    client = TestClient(app)
    spec = client.get("/api/v1/jobs/openapi.json")
    assert spec.status_code == 200
    assert spec.json()["info"]["version"] == SERVICE_VERSION
    assert "swagger-ui" in client.get("/api/v1/jobs/docs").text
    assert "redoc" in client.get("/api/v1/jobs/redoc").text.lower()
    # Las rutas por defecto de FastAPI ya no existen: el gateway no las expone.
    assert client.get("/docs").status_code == 404
    assert client.get("/openapi.json").status_code == 404
