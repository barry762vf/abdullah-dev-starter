"""Guard migration tests from ever targeting the normal development database."""

import os
from pathlib import Path

import pytest
from dotenv import dotenv_values
from sqlalchemy.engine import make_url

from alembic import command
from alembic.config import Config

ROOT = Path(__file__).resolve().parents[3]
BACKEND = ROOT / "backend"


@pytest.fixture(scope="module")
def test_database_url() -> str:
    local = dotenv_values(ROOT / ".env")
    raw = os.environ.get("TEST_DATABASE_URL") or local.get("TEST_DATABASE_URL")
    normal = local.get("DATABASE_URL")
    if not raw:
        pytest.fail("Set TEST_DATABASE_URL to an isolated PostgreSQL test database")
    url = make_url(raw)
    if (
        url.drivername != "postgresql+asyncpg"
        or not url.database
        or not url.database.endswith("_test")
        or (normal and raw == normal)
    ):
        pytest.fail("TEST_DATABASE_URL must use asyncpg and a distinct *_test database")
    return raw


@pytest.fixture(scope="module")
def migration_config(test_database_url: str) -> Config:
    config = Config(str(BACKEND / "alembic.ini"))
    config.attributes["database_url"] = test_database_url
    return config


@pytest.fixture(scope="module", autouse=True)
def migrated_test_database(migration_config: Config) -> None:
    command.upgrade(migration_config, "head")
