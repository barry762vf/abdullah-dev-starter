"""ASGI-level checks for health, documentation, and centralized errors."""

from uuid import UUID

import pytest
from fastapi import FastAPI, HTTPException
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.core.exceptions import AppException
from app.main import create_app


@pytest.fixture
def application() -> FastAPI:
    settings = Settings(
        _env_file=None,
        secret_key="test-only-secret",
        database_url="postgresql+asyncpg://test:test@localhost:5432/test_db",
        cors_origins="http://localhost:5173",
    )
    return create_app(settings)


@pytest.mark.asyncio
async def test_health_reports_liveness_without_claiming_database_connection(
    application: FastAPI,
) -> None:
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health", headers={"Origin": "http://localhost:5173"})
        another_response = await client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    assert response.json()["database"] == "not_checked"
    assert response.json()["environment"] == "development"
    assert response.json()["uptime_seconds"] >= 0
    UUID(response.headers["X-Request-ID"])
    assert response.headers["X-Request-ID"] != another_response.headers["X-Request-ID"]
    assert response.headers["Access-Control-Allow-Origin"] == "http://localhost:5173"
    assert response.headers["X-Content-Type-Options"] == "nosniff"


@pytest.mark.asyncio
async def test_swagger_and_openapi_are_available(application: FastAPI) -> None:
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        docs = await client.get("/docs")
        schema = await client.get("/openapi.json")

    assert docs.status_code == 200
    assert "Swagger UI" in docs.text
    assert schema.status_code == 200
    assert "/api/v1/health" in schema.json()["paths"]


@pytest.mark.asyncio
async def test_unhandled_error_is_sanitized_and_correlated(application: FastAPI) -> None:
    @application.get("/explode")
    async def explode() -> None:
        raise RuntimeError("internal secret must stay private")

    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/explode", headers={"Origin": "http://localhost:5173"})

    assert response.status_code == 500
    assert response.headers["content-type"] == "application/problem+json"
    assert response.headers["Access-Control-Allow-Origin"] == "http://localhost:5173"
    assert response.json()["request_id"] == response.headers["X-Request-ID"]
    assert "internal secret" not in response.text


@pytest.mark.asyncio
async def test_application_and_validation_errors_use_problem_details(application: FastAPI) -> None:
    @application.get("/expected")
    async def expected() -> None:
        raise AppException(409, "Conflict", "A known conflict occurred.")

    @application.get("/validated")
    async def validated(limit: int) -> dict[str, int]:
        return {"limit": limit}

    @application.get("/auth-required")
    async def auth_required() -> None:
        raise HTTPException(401, "Credentials required", headers={"WWW-Authenticate": "Bearer"})

    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        expected_response = await client.get("/expected")
        validation_response = await client.get("/validated?limit=private-input")
        auth_response = await client.get("/auth-required")

    assert expected_response.status_code == 409
    assert expected_response.json()["detail"] == "A known conflict occurred."
    assert expected_response.headers["content-type"] == "application/problem+json"
    assert validation_response.status_code == 422
    assert validation_response.json()["errors"][0]["location"] == ["query", "limit"]
    assert "private-input" not in validation_response.text
    assert auth_response.status_code == 401
    assert auth_response.headers["WWW-Authenticate"] == "Bearer"
