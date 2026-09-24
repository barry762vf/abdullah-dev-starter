"""Client-IP resolution and proxy-bypass protection (ADR 014).

`peer` mode: the socket peer is the client (Uvicorn runs with --no-proxy-headers, so no
forwarding header is ever trusted).

`edge_header` mode: the app sits behind our own same-origin proxy (the Nginx web image or the
Cloudflare Pages Function). That proxy overwrites `X-Edge-Client-IP` with the address it observed
and authenticates itself with `X-Edge-Proxy-Secret`. Requests without the secret are refused, so
the API cannot be reached around the proxy and no client can choose its own IP. Liveness stays
reachable for platform health checks.
"""

import hmac
import ipaddress
import json

from starlette.types import ASGIApp, Receive, Scope, Send

EDGE_IP_HEADER = b"x-edge-client-ip"
EDGE_SECRET_HEADER = b"x-edge-proxy-secret"
UNAUTHENTICATED_PATHS = frozenset({"/api/v1/health"})


def _valid_ip(raw: bytes | None) -> str | None:
    if not raw:
        return None
    try:
        return str(ipaddress.ip_address(raw.decode("latin-1").strip()))
    except ValueError:
        return None


class EdgeClientIPMiddleware:
    def __init__(self, app: ASGIApp, secret: str) -> None:
        self.app = app
        self.secret = secret.encode()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = dict(scope["headers"])
        presented = headers.get(EDGE_SECRET_HEADER, b"")
        if not hmac.compare_digest(presented, self.secret):
            if scope["path"] in UNAUTHENTICATED_PATHS:
                await self.app(scope, receive, send)
                return
            await _refuse(send)
            return
        client_ip = _valid_ip(headers.get(EDGE_IP_HEADER))
        scope = dict(scope)
        # Remove the proxy credential so it never reaches handlers or logs.
        scope["headers"] = [(k, v) for k, v in scope["headers"] if k != EDGE_SECRET_HEADER]
        scope["client"] = (client_ip, 0) if client_ip else None
        await self.app(scope, receive, send)


async def _refuse(send: Send) -> None:
    body = json.dumps(
        {
            "type": "about:blank",
            "title": "Forbidden",
            "status": 403,
            "detail": "Requests must pass through the application proxy.",
        }
    ).encode()
    await send(
        {
            "type": "http.response.start",
            "status": 403,
            "headers": [
                (b"content-type", b"application/problem+json"),
                (b"content-length", str(len(body)).encode()),
                (b"cache-control", b"no-store"),
            ],
        }
    )
    await send({"type": "http.response.body", "body": body})
