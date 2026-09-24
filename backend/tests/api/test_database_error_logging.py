"""Database failures must not log SQL values or PostgreSQL DETAIL content."""

import io
import json
import logging

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.exc import IntegrityError

from app.core.config import Settings
from app.core.logging import JsonFormatter
from app.main import create_app


@pytest.mark.asyncio
async def test_database_error_does_not_log_token_hash() -> None:
    app = create_app(
        Settings(
            _env_file=None,
            secret_key="test-only-secret",
            database_url="postgresql+asyncpg://test:test@localhost:5432/test_db",
        )
    )
    marker = "synthetic-token-hash-marker"

    @app.get("/database-failure")
    async def database_failure() -> None:
        raise IntegrityError(
            "INSERT INTO refresh_tokens(token_hash) VALUES (:token_hash)",
            {"token_hash": marker},
            RuntimeError(f"duplicate token_hash DETAIL: {marker}"),
            hide_parameters=True,
        )

    output = io.StringIO()
    handler = logging.StreamHandler(output)
    handler.setFormatter(JsonFormatter())
    app.state.logger.addHandler(handler)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/database-failure")
    finally:
        app.state.logger.removeHandler(handler)

    assert response.status_code == 500
    assert marker not in response.text
    assert marker not in output.getvalue()
    events = [json.loads(line) for line in output.getvalue().splitlines()]
    assert any(
        event["message"] == "unhandled_database_error" and event["error_type"] == "IntegrityError"
        for event in events
    )
