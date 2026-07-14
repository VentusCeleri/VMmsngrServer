from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.services.users import normalize_username, validate_username


class UserRead(BaseModel):
    id: UUID
    email: EmailStr
    username: str
    display_name: str
    last_seen_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserUpdate(BaseModel):
    username: str | None = Field(default=None, min_length=3, max_length=30)
    display_name: str | None = Field(default=None, min_length=1, max_length=50)

    @field_validator("username")
    @classmethod
    def validate_username_field(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = normalize_username(value)
        validate_username(normalized)
        return normalized

    @field_validator("display_name")
    @classmethod
    def validate_display_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("display_name cannot be empty")
        return trimmed


class PartnerPresenceRead(BaseModel):
    user_id: UUID
    is_online: bool
    last_seen_at: datetime | None


class PartnerProfileRead(BaseModel):
    user: UserRead
    presence: PartnerPresenceRead
