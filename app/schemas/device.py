from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DeviceTokenRead(BaseModel):
    id: UUID
    user_id: UUID
    device_token: str
    platform: str
    last_seen: datetime | None
    active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DeviceRegisterRequest(BaseModel):
    device_token: str = Field(min_length=32, max_length=255)
    platform: str = Field(default="ios", min_length=2, max_length=32)

    @field_validator("device_token")
    @classmethod
    def normalize_token(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("platform")
    @classmethod
    def normalize_platform(cls, value: str) -> str:
        return value.strip().lower()


class DeviceTokenUpdateRequest(BaseModel):
    device_token: str = Field(min_length=32, max_length=255)
    new_device_token: str = Field(min_length=32, max_length=255)
    platform: str | None = Field(default=None, min_length=2, max_length=32)

    @field_validator("device_token", "new_device_token")
    @classmethod
    def normalize_token(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("platform")
    @classmethod
    def normalize_platform(cls, value: str | None) -> str | None:
        return value.strip().lower() if value is not None else None


class DeviceDeleteRequest(BaseModel):
    device_token: str = Field(min_length=32, max_length=255)

    @field_validator("device_token")
    @classmethod
    def normalize_token(cls, value: str) -> str:
        return value.strip().lower()
