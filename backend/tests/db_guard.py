"""Decide whether a URL may be used by destructive integration tests."""

from sqlalchemy.engine import make_url


def _target(url: str) -> tuple[str, int, str]:
    parsed = make_url(url)
    host = (parsed.host or "").lower()
    host = "localhost" if host in {"127.0.0.1", "::1"} else host
    return host, parsed.port or 5432, parsed.database or ""


def unsafe_test_database_reason(raw: str | None, normal: str | None) -> str | None:
    """Return why `raw` must not be used, or None when it is a dedicated *_test database."""
    if not raw:
        return "Set TEST_DATABASE_URL to an isolated PostgreSQL test database"
    parsed = make_url(raw)
    if parsed.drivername != "postgresql+asyncpg":
        return "TEST_DATABASE_URL must use postgresql+asyncpg"
    if not parsed.database or not parsed.database.endswith("_test"):
        return "TEST_DATABASE_URL must name a database ending in _test"
    if normal and _target(raw) == _target(normal):
        return "TEST_DATABASE_URL must not point at the DATABASE_URL database"
    return None
