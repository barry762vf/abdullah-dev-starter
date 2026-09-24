"""Minimal reference routes for the enabled AI and Telegram slots."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, Field, field_validator

from app.api.deps import require_role
from app.core.exceptions import AppException
from app.integrations.base import ProviderUnavailable
from app.integrations.factory import ai_provider, messenger_provider
from app.models import User

router = APIRouter(prefix="/integrations", tags=["integrations"])


class GenerateRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=4000)

    @field_validator("prompt")
    @classmethod
    def nonblank_prompt(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Prompt must not be blank")
        return value


class GenerateResponse(BaseModel):
    text: str


@router.post("/ai/generate", response_model=GenerateResponse)
async def generate(
    data: GenerateRequest,
    request: Request,
    _user: Annotated[User, Depends(require_role(["superadmin"]))],
) -> GenerateResponse:
    if request.app.state.settings.ai_provider == "disabled":
        raise AppException(503, "Service Unavailable", "AI integration is disabled.")
    try:
        text = await ai_provider(request.app.state.settings).generate(data.prompt)
    except ProviderUnavailable:
        raise AppException(502, "Bad Gateway", "AI provider unavailable.") from None
    if text is None:
        raise AppException(502, "Bad Gateway", "AI provider returned no result.")
    return GenerateResponse(text=text)


@router.post("/telegram/webhook", status_code=204)
async def telegram_webhook(request: Request) -> Response:
    settings = request.app.state.settings
    if settings.messenger_provider != "telegram":
        raise AppException(404, "Not Found", "Webhook is disabled.")
    provider = messenger_provider(settings)
    if not provider.verify_webhook(request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")):
        raise AppException(403, "Forbidden", "Invalid webhook token.")
    # A clone must install a durable handler before Telegram can receive 2xx. Returning 503
    # here makes Telegram retry rather than silently losing an update.
    handler = getattr(request.app.state, "telegram_update_handler", None)
    if handler is None:
        raise AppException(503, "Service Unavailable", "Webhook handler is not configured.")
    try:
        declared_length = int(request.headers.get("content-length", "0") or 0)
    except ValueError:
        raise AppException(400, "Bad Request", "Invalid content length.") from None
    if declared_length > 65536:
        raise AppException(413, "Payload Too Large", "Webhook payload is too large.")
    body = await request.body()
    if len(body) > 65536:
        raise AppException(413, "Payload Too Large", "Webhook payload is too large.")
    try:
        import json

        update = json.loads(body)
        if not isinstance(update, dict) or type(update.get("update_id")) is not int:
            raise ValueError
    except (ValueError, UnicodeDecodeError):
        raise AppException(422, "Unprocessable Entity", "Invalid Telegram update.") from None
    await handler(update)
    return Response(status_code=204)
