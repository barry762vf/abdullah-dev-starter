"""Application liveness endpoint for Phase 1."""

from time import monotonic
from typing import Literal

from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter(tags=["system"])


class HealthResponse(BaseModel):
    status: Literal["healthy"]
    environment: str
    uptime_seconds: float
    database: Literal["not_configured"]


@router.get("/health", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    return HealthResponse(
        status="healthy",
        environment=request.app.state.settings.environment,
        uptime_seconds=round(max(0.0, monotonic() - request.app.state.started_at), 3),
        database="not_configured",
    )
