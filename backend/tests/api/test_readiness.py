"""Readiness requires a database ping; liveness remains cheap."""

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import Settings
from app.core.database import get_db
from app.main import create_app


@pytest.mark.asyncio
async def test_readiness_returns_service_unavailable_without_leaking_error() -> None:
    settings = Settings(
        _env_file=None,
        secret_key="test-only-secret",
        database_url="postgresql+asyncpg://test:test@localhost:5432/test_db",
    )
    app: FastAPI = create_app(settings)

    class FailedSession:
        async def execute(self, _query):
            raise SQLAlchemyError("private connection information")

    async def failed_db():
        yield FailedSession()

    app.dependency_overrides[get_db] = failed_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/ready")
        liveness = await client.get("/api/v1/health")

    assert response.status_code == 503
    assert "private connection information" not in response.text
    assert liveness.status_code == 200
    assert liveness.json()["database"] == "not_checked"
