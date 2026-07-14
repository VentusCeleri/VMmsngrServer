from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class MessageCreate(BaseModel):
    body: str = Field(min_length=1, max_length=4000)
    receiver_id: UUID | None = None


class MessageRead(BaseModel):
    id: UUID
    pair_id: UUID
    sender_id: UUID
    receiver_id: UUID | None
    body: str
    status: str
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None

    model_config = ConfigDict(from_attributes=True)
