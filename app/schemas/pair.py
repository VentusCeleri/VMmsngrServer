from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PairRead(BaseModel):
    id: UUID
    invite_code: str
    user_a_id: UUID | None
    user_b_id: UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class JoinPairRequest(BaseModel):
    invite_code: str = Field(min_length=4, max_length=16)
