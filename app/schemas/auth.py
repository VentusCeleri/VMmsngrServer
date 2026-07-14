from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.user import UserRead
from app.services.users import normalize_username, validate_username


class RegisterRequest(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=30)
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=1, max_length=50)

    @field_validator("username")
    @classmethod
    def validate_username_field(cls, value: str) -> str:
        normalized = normalize_username(value)
        validate_username(normalized)
        return normalized

    @field_validator("display_name")
    @classmethod
    def validate_display_name(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("display_name cannot be empty")
        return trimmed


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str | None = None


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class AuthResponse(TokenPair):
    user: UserRead


class TokenPayload(BaseModel):
    sub: UUID
    type: str
    jti: str | None = None
