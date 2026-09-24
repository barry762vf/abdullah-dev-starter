"""Telegram send and authenticated webhook primitives.

The host app must supply durable handling before acknowledging webhook updates.
"""

import hmac

import httpx

from app.integrations.base import ProviderUnavailable


class TelegramMessenger:
    def __init__(self, bot_token: str, webhook_secret: str) -> None:
        self._bot_token = bot_token
        self._webhook_secret = webhook_secret

    def verify_webhook(self, presented_secret: str) -> bool:
        return hmac.compare_digest(presented_secret, self._webhook_secret)

    async def send_text(self, recipient: str, text: str) -> bool:
        # Telegram's Bot API requires the token in the path. Never surface the URL or
        # exception text in logs or API responses.
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(
                    f"https://api.telegram.org/bot{self._bot_token}/sendMessage",
                    json={"chat_id": recipient, "text": text},
                )
                response.raise_for_status()
                return response.json().get("ok") is True
        except (httpx.HTTPError, ValueError, TypeError, AttributeError):
            raise ProviderUnavailable("Telegram request failed") from None
