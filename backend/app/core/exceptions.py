"""Centralized application errors in RFC 7807 problem-details format."""

import logging
from collections.abc import Mapping
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("abdullah_core")


class AppException(Exception):
    def __init__(self, status_code: int, title: str, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.title = title
        self.detail = detail


def problem_response(
    request: Request,
    *,
    status_code: int,
    title: str,
    detail: str,
    errors: list[dict[str, Any]] | None = None,
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    body: dict[str, Any] = {
        "type": "about:blank",
        "title": title,
        "status": status_code,
        "detail": detail,
        "instance": request.url.path,
    }
    if request_id:
        body["request_id"] = request_id
    if errors is not None:
        body["errors"] = errors
    return JSONResponse(
        status_code=status_code,
        content=body,
        media_type="application/problem+json",
        headers=headers,
    )


async def handle_unexpected_error(request: Request, error: Exception) -> JSONResponse:
    if isinstance(error, SQLAlchemyError):
        # PostgreSQL DETAIL may contain a conflicting token hash even when
        # SQLAlchemy hides bound parameters. Never log the DB exception text.
        logger.error("unhandled_database_error", extra={"error_type": type(error).__name__})
    else:
        logger.exception("unhandled_request_error", exc_info=error)
    return problem_response(
        request,
        status_code=500,
        title="Internal Server Error",
        detail="An unexpected error occurred.",
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, error: AppException) -> JSONResponse:
        return problem_response(
            request,
            status_code=error.status_code,
            title=error.title,
            detail=error.detail,
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, error: StarletteHTTPException
    ) -> JSONResponse:
        return problem_response(
            request,
            status_code=error.status_code,
            title="Not Found" if error.status_code == 404 else "HTTP Error",
            detail=str(error.detail),
            headers=error.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, error: RequestValidationError
    ) -> JSONResponse:
        # Keep submitted values out of error responses and logs.
        errors = [
            {
                "location": [str(part) for part in item["loc"]],
                "message": item["msg"],
                "type": item["type"],
            }
            for item in error.errors()
        ]
        return problem_response(
            request,
            status_code=422,
            title="Unprocessable Entity",
            detail="Request validation failed.",
            errors=errors,
        )
