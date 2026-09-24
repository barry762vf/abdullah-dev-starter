"""Explicit safe user profile serialization."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


def clean_full_name(value: str) -> str:
    cleaned = "".join(char for char in value if char not in "\u200b\u200c\u200d\ufeff").strip()
    if not cleaned or any(
        ord(char) < 32 or char in "\u202a\u202b\u202c\u202d\u202e" for char in cleaned
    ):
        raise ValueError("Invalid full name")
    return cleaned


class UserResponse(BaseModel):
    id: UUID
    email: EmailStr
    full_name: str
    is_active: bool
    is_verified: bool
    roles: list[str]
    created_at: datetime


class UserUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    full_name: str = Field(min_length=1, max_length=255)

    @field_validator("full_name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        return clean_full_name(value)
