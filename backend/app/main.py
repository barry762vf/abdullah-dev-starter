"""FastAPI application assembly."""

from contextlib import asynccontextmanager
from time import monotonic
from uuid import uuid4

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import Settings, get_settings
from app.core.database import create_engine, create_session_factory
from app.core.exceptions import handle_unexpected_error, register_exception_handlers
from app.core.logging import configure_logging, request_id_context
from app.core.rate_limit import AuthRateLimiter


def _add_security_headers(response: Response, request: Request, settings: Settings) -> None:
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    if request.url.path in {"/docs", "/redoc"}:
        # FastAPI's interactive docs load assets from jsDelivr and contain inline setup code.
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "img-src 'self' data: https://fastapi.tiangolo.com; "
            "frame-ancestors 'none'"
        )
    else:
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
    if settings.environment == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    logger = configure_logging(settings.debug)
    engine = create_engine(settings)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        try:
            yield
        finally:
            await engine.dispose()

    app = FastAPI(title="Abdullah Developer Core", debug=settings.debug, lifespan=lifespan)
    app.state.settings = settings
    app.state.logger = logger
    app.state.engine = engine
    app.state.session_factory = create_session_factory(engine)
    app.state.started_at = monotonic()
    app.state.auth_rate_limiter = AuthRateLimiter()
    register_exception_handlers(app)
    app.include_router(api_router, prefix="/api/v1")

    @app.middleware("http")
    async def request_context(request: Request, call_next) -> Response:
        request_id = str(uuid4())
        request.state.request_id = request_id
        context_token = request_id_context.set(request_id)
        start = monotonic()
        try:
            try:
                response = await call_next(request)
            except Exception as error:
                response = await handle_unexpected_error(request, error)
            response.headers["X-Request-ID"] = request_id
            _add_security_headers(response, request, settings)
            logger.info(
                "request_completed",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": round((monotonic() - start) * 1000, 3),
                    "client_ip": request.client.host if request.client else None,
                },
            )
            return response
        finally:
            request_id_context.reset(context_token)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Requested-With", "X-CSRF-Token"],
    )
    return app


app = create_app()
