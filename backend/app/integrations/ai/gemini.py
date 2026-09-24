"""Minimal Gemini text generation adapter using Google's documented REST API."""

import httpx

from app.integrations.base import ProviderUnavailable


class GeminiAIProvider:
    def __init__(self, api_key: str, model: str) -> None:
        self._api_key = api_key
        self._url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        )

    async def generate(self, prompt: str) -> str:
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.post(
                    self._url,
                    headers={"x-goog-api-key": self._api_key},
                    json={"contents": [{"role": "user", "parts": [{"text": prompt}]}]},
                )
                response.raise_for_status()
                candidates = response.json().get("candidates", [])
                parts = candidates[0]["content"]["parts"] if candidates else []
                answer = "".join(part.get("text", "") for part in parts)
                if answer:
                    return answer
        except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError, AttributeError):
            raise ProviderUnavailable("Gemini request failed") from None
        raise ProviderUnavailable("Gemini returned no text")
