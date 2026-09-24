"""Phase 8 adapter contracts, config guards and reference routes (no live credentials)."""

from types import SimpleNamespace

import httpx
import pytest
from pydantic import ValidationError

from app.api.deps import get_current_active_user
from app.core.config import Settings
from app.integrations.ai.gemini import GeminiAIProvider
from app.integrations.base import (
    BaseAIProvider,
    BaseEmailNotifier,
    BaseMessenger,
    BaseStorage,
    ProviderUnavailable,
)
from app.integrations.factory import (
    ai_provider,
    email_provider,
    messenger_provider,
    storage_provider,
)
from app.integrations.messenger.telegram import TelegramMessenger
from app.integrations.notifications.email import SMTPEmailNotifier
from app.integrations.storage.supabase_storage import SupabaseStorage
from app.main import create_app

BASE = {
    "_env_file": None,
    "environment": "development",
    "secret_key": "test-only-secret",
    "database_url": "postgresql+asyncpg://test:test@localhost:5432/test_db",
}


def settings(**overrides) -> Settings:
    return Settings(**(BASE | overrides))


@pytest.mark.asyncio
async def test_null_providers_are_inert_and_match_protocols() -> None:
    config = settings()
    ai = ai_provider(config)
    messenger = messenger_provider(config)
    storage = storage_provider(config)
    email = email_provider(config)
    assert isinstance(ai, BaseAIProvider)
    assert isinstance(messenger, BaseMessenger)
    assert isinstance(storage, BaseStorage)
    assert isinstance(email, BaseEmailNotifier)
    assert await ai.generate("hello") is None
    assert await messenger.send_text("1", "hello") is False
    assert messenger.verify_webhook("x") is False
    assert await storage.upload("avatar.png", b"image", "image/png") is False
    assert await email.send("a@example.com", "subject", "body") is False


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"ai_provider": "unknown"}, "AI_PROVIDER"),
        ({"ai_provider": "gemini"}, "GEMINI_API_KEY"),
        ({"messenger_provider": "telegram"}, "TELEGRAM_BOT_TOKEN"),
        (
            {"messenger_provider": "telegram", "telegram_bot_token": "token"},
            "TELEGRAM_WEBHOOK_SECRET",
        ),
        ({"storage_provider": "supabase"}, "SUPABASE_URL"),
        ({"storage_provider": "supabase", "supabase_url": "http://evil.test"}, "SUPABASE_URL"),
        ({"email_provider": "smtp"}, "SMTP_HOST"),
    ],
)
def test_missing_or_invalid_provider_configuration_fails(overrides, message) -> None:
    with pytest.raises(ValidationError, match=message):
        settings(**overrides)


def test_enabled_provider_selection_and_secret_redaction() -> None:
    config = settings(
        ai_provider="gemini",
        gemini_api_key="gemini-secret",
        messenger_provider="telegram",
        telegram_bot_token="telegram-secret",
        telegram_webhook_secret="s" * 32,
        storage_provider="supabase",
        supabase_url="https://project.supabase.co",
        supabase_key="storage-secret",
        supabase_bucket="avatars",
        email_provider="smtp",
        smtp_host="smtp.example.com",
        smtp_username="user",
        smtp_password="smtp-secret",
        smtp_from_email="noreply@example.com",
    )
    assert isinstance(ai_provider(config), GeminiAIProvider)
    assert isinstance(messenger_provider(config), TelegramMessenger)
    assert isinstance(storage_provider(config), SupabaseStorage)
    assert isinstance(email_provider(config), SMTPEmailNotifier)
    assert all(
        secret not in repr(config)
        for secret in ("gemini-secret", "telegram-secret", "storage-secret", "smtp-secret")
    )
    with pytest.raises(ValidationError, match="SMTP_STARTTLS"):
        Settings(
            **(
                BASE
                | {
                    "environment": "production",
                    "secret_key": "a" * 64,
                    "cors_origins": "https://example.com",
                    "cookie_secure": True,
                    "email_provider": "smtp",
                    "smtp_host": "smtp.example.com",
                    "smtp_username": "user",
                    "smtp_password": "secret",
                    "smtp_from_email": "noreply@example.com",
                    "smtp_starttls": False,
                }
            )
        )


@pytest.mark.asyncio
async def test_gemini_request_and_failure_are_isolated(monkeypatch) -> None:
    seen = []

    def responder(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if len(seen) == 1:
            return httpx.Response(
                200, json={"candidates": [{"content": {"parts": [{"text": "Hi"}]}}]}
            )
        return httpx.Response(503, json={"error": "secret details"})

    real_client = httpx.AsyncClient
    monkeypatch.setattr(
        httpx, "AsyncClient", lambda **kwargs: real_client(transport=httpx.MockTransport(responder))
    )
    provider = GeminiAIProvider("test-key", "gemini-2.5-flash")
    assert await provider.generate("hello") == "Hi"
    assert seen[0].headers["x-goog-api-key"] == "test-key"
    assert seen[0].url.host == "generativelanguage.googleapis.com"
    with pytest.raises(ProviderUnavailable, match="Gemini request failed"):
        await provider.generate("again")


@pytest.mark.asyncio
async def test_telegram_and_storage_requests(monkeypatch) -> None:
    seen = []

    def responder(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"ok": True})

    real_client = httpx.AsyncClient
    monkeypatch.setattr(
        httpx, "AsyncClient", lambda **kwargs: real_client(transport=httpx.MockTransport(responder))
    )
    messenger = TelegramMessenger("bot-token", "s" * 32)
    assert messenger.verify_webhook("s" * 32)
    assert not messenger.verify_webhook("wrong")
    assert await messenger.send_text("42", "hello")
    storage = SupabaseStorage("https://project.supabase.co", "service-key", "avatars")
    assert await storage.upload("user/photo.png", b"png", "image/png")
    assert seen[0].url.host == "api.telegram.org"
    assert seen[1].url.path.endswith("/avatars/user/photo.png")
    assert seen[1].headers["authorization"] == "Bearer service-key"
    with pytest.raises(ValueError, match="object key"):
        await storage.upload("../escape", b"x", "text/plain")


@pytest.mark.asyncio
async def test_smtp_delivery_uses_authenticated_starttls(monkeypatch) -> None:
    calls = []

    class FakeSMTP:
        def __init__(self, host, port, timeout):
            calls.append((host, port, timeout))

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def ehlo(self):
            calls.append("ehlo")

        def starttls(self, context):
            calls.append("tls")

        def login(self, username, password):
            calls.append((username, password))

        def send_message(self, message):
            calls.append(message["To"])

    monkeypatch.setattr("app.integrations.notifications.email.smtplib.SMTP", FakeSMTP)
    provider = SMTPEmailNotifier(
        "smtp.example.com", 587, "user", "secret", "from@example.com", True
    )
    assert await provider.send("to@example.com", "Subject", "Body")
    assert "tls" in calls and ("user", "secret") in calls and "to@example.com" in calls


@pytest.mark.asyncio
async def test_reference_routes_fail_closed_and_do_not_drop_webhooks() -> None:
    app = create_app(
        settings(
            messenger_provider="telegram",
            telegram_bot_token="bot",
            telegram_webhook_secret="s" * 32,
        )
    )
    app.dependency_overrides[get_current_active_user] = lambda: SimpleNamespace(
        is_active=True, role_assignments=[SimpleNamespace(role=SimpleNamespace(name="superadmin"))]
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        ai = await client.post("/api/v1/integrations/ai/generate", json={"prompt": "hi"})
        assert ai.status_code == 503
        blank = await client.post("/api/v1/integrations/ai/generate", json={"prompt": "  "})
        assert blank.status_code == 422
        bad = await client.post("/api/v1/integrations/telegram/webhook", json={"update_id": 1})
        assert bad.status_code == 403
        headers = {"X-Telegram-Bot-Api-Secret-Token": "s" * 32}
        unhandled = await client.post(
            "/api/v1/integrations/telegram/webhook", headers=headers, json={"update_id": 1}
        )
        assert unhandled.status_code == 503
        received = []

        async def handle(update):
            received.append(update)

        app.state.telegram_update_handler = handle
        assert (
            await client.post(
                "/api/v1/integrations/telegram/webhook", headers=headers, json={"update_id": 1}
            )
        ).status_code == 204
        assert received == [{"update_id": 1}]


@pytest.mark.asyncio
async def test_enabled_ai_route_uses_provider_and_sanitizes_upstream_failure(monkeypatch) -> None:
    app = create_app(settings(ai_provider="gemini", gemini_api_key="test-key"))
    app.dependency_overrides[get_current_active_user] = lambda: SimpleNamespace(
        is_active=True, role_assignments=[SimpleNamespace(role=SimpleNamespace(name="superadmin"))]
    )

    class FakeAI:
        def __init__(self):
            self.fail = False

        async def generate(self, prompt):
            if self.fail:
                raise ProviderUnavailable("private upstream detail")
            return f"reply to {prompt}"

    provider = FakeAI()
    monkeypatch.setattr("app.api.v1.integrations.ai_provider", lambda _settings: provider)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        good = await client.post("/api/v1/integrations/ai/generate", json={"prompt": "hi"})
        assert good.status_code == 200 and good.json() == {"text": "reply to hi"}
        provider.fail = True
        failed = await client.post("/api/v1/integrations/ai/generate", json={"prompt": "hi"})
        assert failed.status_code == 502
        assert "private upstream detail" not in failed.text


def test_base_app_import_and_enabled_configuration_startup() -> None:
    from app.main import app

    assert app is not None
    enabled = create_app(settings(ai_provider="gemini", gemini_api_key="test-key"))
    assert enabled.state.settings.ai_provider == "gemini"


def test_production_enabled_provider_configuration() -> None:
    production = Settings(
        **(
            BASE
            | {
                "environment": "production",
                "secret_key": "a" * 64,
                "cors_origins": "https://app.example.com",
                "cookie_secure": True,
                "client_ip_source": "peer",
                "ai_provider": "gemini",
                "gemini_api_key": "test-key",
            }
        )
    )
    assert isinstance(ai_provider(production), GeminiAIProvider)


@pytest.mark.asyncio
async def test_other_provider_failures_do_not_expose_upstream_details(monkeypatch) -> None:
    real_client = httpx.AsyncClient
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kwargs: real_client(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(503, text="private detail")
            )
        ),
    )
    with pytest.raises(ProviderUnavailable, match="Telegram request failed") as telegram_error:
        await TelegramMessenger("token", "s" * 32).send_text("1", "hi")
    with pytest.raises(ProviderUnavailable, match="Storage request failed") as storage_error:
        await SupabaseStorage("https://project.supabase.co", "key", "avatars").upload(
            "one.png", b"data", "image/png"
        )
    assert "private detail" not in str(telegram_error.value)
    assert "private detail" not in str(storage_error.value)


@pytest.mark.asyncio
async def test_smtp_failure_is_wrapped_without_server_text(monkeypatch) -> None:
    class FailingSMTP:
        def __init__(self, *_args, **_kwargs):
            raise OSError("private smtp response")

    monkeypatch.setattr("app.integrations.notifications.email.smtplib.SMTP", FailingSMTP)
    notifier = SMTPEmailNotifier(
        "smtp.example.com", 587, "user", "secret", "from@example.com", True
    )
    with pytest.raises(ProviderUnavailable, match="Email delivery failed") as error:
        await notifier.send("to@example.com", "subject", "body")
    assert "private smtp response" not in str(error.value)
