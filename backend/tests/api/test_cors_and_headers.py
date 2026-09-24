"""CORS allowlist and security headers as a browser would observe them."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.main import create_app

ALLOWED = "http://localhost:5173"
PREFLIGHT = {
    "Access-Control-Request-Method": "PATCH",
    "Access-Control-Request-Headers": "content-type,x-requested-with",
}


def app_for(**overrides):
    values = {
        "_env_file": None,
        "environment": "development",
        "secret_key": "test-only-secret",
        "database_url": "postgresql+asyncpg://test:test@localhost:5432/test_db",
        "cors_origins": ALLOWED,
        "client_ip_source": "peer",
    }
    return create_app(Settings(**(values | overrides)))


async def request(app, method: str, path: str, headers: dict[str, str] | None = None):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        return await client.request(method, path, headers=headers)


@pytest.mark.asyncio
async def test_allowed_origin_preflight_permits_credentials_and_csrf_header() -> None:
    response = await request(
        app_for(), "OPTIONS", "/api/v1/users/me", {"Origin": ALLOWED, **PREFLIGHT}
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == ALLOWED
    assert response.headers["access-control-allow-credentials"] == "true"
    assert "x-requested-with" in response.headers["access-control-allow-headers"].lower()
    assert "PATCH" in response.headers["access-control-allow-methods"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "origin", ["https://evil.example", "http://localhost:5174", "null", "http://localhost"]
)
async def test_other_origins_get_no_cors_grant(origin: str) -> None:
    app = app_for()
    preflight = await request(app, "OPTIONS", "/api/v1/users/me", {"Origin": origin, **PREFLIGHT})
    assert preflight.status_code == 400
    assert "access-control-allow-origin" not in preflight.headers
    simple = await request(app, "GET", "/api/v1/health", {"Origin": origin})
    assert simple.status_code == 200  # The browser, not the server, withholds the body.
    # Starlette always sends Allow-Credentials on simple responses; without a matching
    # Allow-Origin the browser ignores it, so the missing origin grant is the security property.
    assert "access-control-allow-origin" not in simple.headers


@pytest.mark.asyncio
async def test_api_responses_carry_security_headers_without_hsts_in_development() -> None:
    response = await request(app_for(), "GET", "/api/v1/health")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert "camera=()" in response.headers["permissions-policy"]
    assert response.headers["content-security-policy"] == (
        "default-src 'none'; frame-ancestors 'none'"
    )
    assert "strict-transport-security" not in response.headers
    # Error responses get the same headers.
    missing = await request(app_for(), "GET", "/api/v1/does-not-exist")
    assert missing.status_code == 404
    assert missing.headers["x-frame-options"] == "DENY"


@pytest.mark.asyncio
async def test_docs_csp_is_relaxed_only_for_the_docs_page() -> None:
    docs = await request(app_for(), "GET", "/docs")
    assert "cdn.jsdelivr.net" in docs.headers["content-security-policy"]
    assert "frame-ancestors 'none'" in docs.headers["content-security-policy"]


@pytest.mark.asyncio
async def test_production_adds_hsts_and_keeps_exact_https_origin() -> None:
    app = app_for(
        environment="production",
        secret_key="a" * 64,
        cookie_secure=True,
        cors_origins="https://app.example.com",
    )
    response = await request(app, "GET", "/api/v1/health", {"Origin": "https://app.example.com"})
    assert response.headers["strict-transport-security"] == "max-age=31536000; includeSubDomains"
    assert response.headers["access-control-allow-origin"] == "https://app.example.com"
    plain = await request(app, "GET", "/api/v1/health", {"Origin": "http://app.example.com"})
    assert "access-control-allow-origin" not in plain.headers
