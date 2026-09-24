"""Production-mode boundary: proxy authentication, client IP, docs, caching and bootstrap secret."""

import pytest
from fastapi import Request
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.main import create_app

SECRET = "edge-proxy-secret-for-tests-0123456789"
PRODUCTION = {
    "_env_file": None,
    "environment": "production",
    "secret_key": "a" * 64,
    "database_url": "postgresql+asyncpg://test:test@localhost:5432/test_db",
    "cors_origins": "https://app.example.com",
    "cookie_secure": True,
}


def edge_app(**overrides):
    app = create_app(
        Settings(
            **(PRODUCTION | {"client_ip_source": "edge_header", "edge_proxy_secret": SECRET})
            | overrides
        )
    )

    @app.get("/api/v1/_probe")
    async def probe(request: Request) -> dict[str, object]:
        return {
            "client": request.client.host if request.client else None,
            "secret_seen": "x-edge-proxy-secret" in request.headers,
        }

    return app


async def get(app, path: str, headers: dict[str, str] | None = None, client=("198.51.100.20", 1)):
    transport = ASGITransport(app=app, client=client)
    async with AsyncClient(transport=transport, base_url="http://test") as http:
        return await http.get(path, headers=headers)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "headers", [{}, {"X-Edge-Proxy-Secret": "wrong"}, {"X-Edge-Proxy-Secret": ""}]
)
async def test_edge_mode_refuses_requests_that_bypass_the_proxy(headers) -> None:
    response = await get(edge_app(), "/api/v1/_probe", headers | {"X-Edge-Client-IP": "6.6.6.6"})
    assert response.status_code == 403
    assert response.headers["content-type"] == "application/problem+json"
    assert response.headers["cache-control"] == "no-store"


@pytest.mark.asyncio
async def test_liveness_stays_reachable_for_platform_health_checks() -> None:
    assert (await get(edge_app(), "/api/v1/health")).status_code == 200


@pytest.mark.asyncio
async def test_edge_mode_takes_client_ip_only_from_the_authenticated_proxy() -> None:
    proxied = {
        "X-Edge-Proxy-Secret": SECRET,
        "X-Edge-Client-IP": "203.0.113.7",
        "X-Forwarded-For": "6.6.6.6",
    }
    body = (await get(edge_app(), "/api/v1/_probe", proxied)).json()
    assert body == {"client": "203.0.113.7", "secret_seen": False}  # credential stripped
    ipv6 = await get(edge_app(), "/api/v1/_probe", proxied | {"X-Edge-Client-IP": "2001:db8::1"})
    assert ipv6.json()["client"] == "2001:db8::1"
    for invalid in ("not-an-ip", "", "203.0.113.7, 6.6.6.6"):
        response = await get(edge_app(), "/api/v1/_probe", proxied | {"X-Edge-Client-IP": invalid})
        assert response.json()["client"] is None  # rate limits and audit fall back to "unknown"


@pytest.mark.asyncio
async def test_peer_mode_never_trusts_forwarding_headers() -> None:
    app = edge_app(client_ip_source="peer", edge_proxy_secret="")
    spoofed = {"X-Forwarded-For": "6.6.6.6", "X-Edge-Client-IP": "6.6.6.6", "X-Real-IP": "6.6.6.6"}
    assert (await get(app, "/api/v1/_probe", spoofed)).json()["client"] == "198.51.100.20"


@pytest.mark.asyncio
async def test_production_hides_api_docs_and_marks_api_responses_no_store() -> None:
    app = edge_app(client_ip_source="peer", edge_proxy_secret="")
    for path in ("/docs", "/redoc", "/openapi.json"):
        assert (await get(app, path)).status_code == 404
    health = await get(app, "/api/v1/health")
    assert health.headers["cache-control"] == "no-store"
    assert health.headers["strict-transport-security"].startswith("max-age=")


def test_api_refuses_to_start_with_the_bootstrap_password() -> None:
    settings = Settings(
        **(
            PRODUCTION
            | {"client_ip_source": "peer", "initial_admin_password": "Leftover-pass-123!"}
        )
    )
    with pytest.raises(RuntimeError, match="INITIAL_ADMIN_PASSWORD"):
        create_app(settings)
