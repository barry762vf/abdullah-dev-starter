"""Server-side Supabase Storage object upload slot."""

from urllib.parse import quote

import httpx

from app.integrations.base import ProviderUnavailable


class SupabaseStorage:
    def __init__(self, url: str, key: str, bucket: str) -> None:
        self._url = url.rstrip("/")
        self._key = key
        self._bucket = bucket

    async def upload(self, key: str, content: bytes, content_type: str) -> bool:
        if not key or key.startswith("/") or ".." in key.split("/") or "\\" in key:
            raise ValueError("Invalid storage object key")
        if not content_type or "\r" in content_type or "\n" in content_type:
            raise ValueError("Invalid content type")
        path = f"{quote(self._bucket, safe='')}/{quote(key, safe='/')}"
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.post(
                    f"{self._url}/storage/v1/object/{path}",
                    headers={
                        "apikey": self._key,
                        "Authorization": f"Bearer {self._key}",
                        "Content-Type": content_type,
                        "x-upsert": "false",
                    },
                    content=content,
                )
                response.raise_for_status()
                return True
        except httpx.HTTPError:
            raise ProviderUnavailable("Storage request failed") from None
