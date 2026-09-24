"""Config-driven construction of optional adapters, with inert defaults."""

from app.core.config import Settings
from app.integrations.base import (
    BaseAIProvider,
    BaseEmailNotifier,
    BaseMessenger,
    BaseStorage,
    NullAIProvider,
    NullEmailNotifier,
    NullMessenger,
    NullStorage,
)


def ai_provider(settings: Settings) -> BaseAIProvider:
    if settings.ai_provider == "gemini":
        from app.integrations.ai.gemini import GeminiAIProvider

        return GeminiAIProvider(settings.gemini_api_key.get_secret_value(), settings.gemini_model)
    return NullAIProvider()


def messenger_provider(settings: Settings) -> BaseMessenger:
    if settings.messenger_provider == "telegram":
        from app.integrations.messenger.telegram import TelegramMessenger

        return TelegramMessenger(
            settings.telegram_bot_token.get_secret_value(),
            settings.telegram_webhook_secret.get_secret_value(),
        )
    return NullMessenger()


def storage_provider(settings: Settings) -> BaseStorage:
    if settings.storage_provider == "supabase":
        from app.integrations.storage.supabase_storage import SupabaseStorage

        return SupabaseStorage(
            settings.supabase_url,
            settings.supabase_key.get_secret_value(),
            settings.supabase_bucket,
        )
    return NullStorage()


def email_provider(settings: Settings) -> BaseEmailNotifier:
    if settings.email_provider == "smtp":
        from app.integrations.notifications.email import SMTPEmailNotifier

        return SMTPEmailNotifier(
            settings.smtp_host,
            settings.smtp_port,
            settings.smtp_username,
            settings.smtp_password.get_secret_value(),
            settings.smtp_from_email,
            settings.smtp_starttls,
        )
    return NullEmailNotifier()
