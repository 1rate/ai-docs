from app.main import app


def test_openapi_contains_core_paths() -> None:
    schema = app.openapi()
    paths = schema["paths"]
    assert "/api/v1/health" in paths
    assert "/api/v1/auth/login" in paths
    assert "/api/v1/auth/refresh" in paths
    assert "/api/v1/auth/logout" in paths
    assert "/api/v1/documents" in paths
