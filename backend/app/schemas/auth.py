"""Public authentication input; unknown fields cannot grant privileges."""

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.schemas.user import clean_full_name


class EmailInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailStr

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: object) -> object:
        return value.strip().lower() if isinstance(value, str) else value


class RegisterRequest(EmailInput):
    password: str = Field(min_length=12, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)

    @field_validator("full_name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        return clean_full_name(value)


class LoginRequest(EmailInput):
    password: str = Field(min_length=1, max_length=128)
