"""Cheap application liveness and explicit database readiness checks."""

from time import monotonic
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db

router = APIRouter(tags=["system"])


class HealthResponse(BaseModel):
    status: Literal["healthy"]
    environment: str
    uptime_seconds: float
    database: Literal["not_checked"]


class ReadinessResponse(BaseModel):
    status: Literal["ready", "unavailable"]
    database: Literal["connected", "unavailable"]


@router.get("/health", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    return HealthResponse(
        status="healthy",
        environment=request.app.state.settings.environment,
        uptime_seconds=round(max(0.0, monotonic() - request.app.state.started_at), 3),
        database="not_checked",
    )


@router.get("/ready", response_model=ReadinessResponse)
async def ready(
    request: Request, db: Annotated[AsyncSession, Depends(get_db)]
) -> ReadinessResponse:
    try:
        await db.execute(text("SELECT 1"))
    except (SQLAlchemyError, OSError, TimeoutError):
        request.app.state.logger.warning("database_readiness_failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable",
        ) from None
    return ReadinessResponse(status="ready", database="connected")
