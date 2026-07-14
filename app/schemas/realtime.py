from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class RealtimeEnvelope(BaseModel):
    version: int = 1
    event: str
    event_id: UUID = Field(default_factory=uuid4)
    pair_id: UUID
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    data: dict[str, Any]


def make_realtime_event(event: str, pair_id: UUID, data: dict[str, Any]) -> dict[str, Any]:
    return RealtimeEnvelope(event=event, pair_id=pair_id, data=data).model_dump(mode="json")
