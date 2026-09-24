"""Small contracts shared by optional provider slots (ADR 006)."""

from typing import Protocol, runtime_checkable


class ProviderUnavailable(Exception):
    """A configured external service failed; details must stay out of API responses."""


@runtime_checkable
class BaseAIProvider(Protocol):
    async def generate(self, prompt: str) -> str | None: ...


@runtime_checkable
class BaseMessenger(Protocol):
    async def send_text(self, recipient: str, text: str) -> bool: ...

    def verify_webhook(self, presented_secret: str) -> bool: ...


@runtime_checkable
class BaseStorage(Protocol):
    async def upload(self, key: str, content: bytes, content_type: str) -> bool: ...


@runtime_checkable
class BaseEmailNotifier(Protocol):
    async def send(self, recipient: str, subject: str, body: str) -> bool: ...


class NullAIProvider:
    async def generate(self, prompt: str) -> None:
        return None


class NullMessenger:
    async def send_text(self, recipient: str, text: str) -> bool:
        return False

    def verify_webhook(self, presented_secret: str) -> bool:
        return False


class NullStorage:
    async def upload(self, key: str, content: bytes, content_type: str) -> bool:
        return False


class NullEmailNotifier:
    async def send(self, recipient: str, subject: str, body: str) -> bool:
        return False
