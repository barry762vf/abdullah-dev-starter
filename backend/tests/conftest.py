"""Keep application import independent of the developer's local .env file."""

import os

import pytest

# app.main builds the ASGI app on import. These values are test-only and never
# reach a real database; explicit Settings values in tests take precedence.
os.environ["ENVIRONMENT"] = "development"
os.environ["DEBUG"] = "false"
os.environ["SECRET_KEY"] = "test-only-secret-do-not-use-outside-pytest"
os.environ["DATABASE_URL"] = "postgresql+asyncpg://test:test@localhost:5432/test_db"
os.environ["CORS_ORIGINS"] = "http://localhost:5173"
os.environ["COOKIE_SECURE"] = "false"


def pytest_collection_modifyitems(items):
    """Mark tests by folder so `pytest -m unit` runs without PostgreSQL."""
    for item in items:
        folder = "integration" if "integration" in item.path.parts else "unit"
        item.add_marker(getattr(pytest.mark, folder))
