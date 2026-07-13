from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    details: str | None = None
    due_date: date | None = None
    is_completed: bool = False
    priority: int = 0
    assignee_id: UUID | None = None


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    details: str | None = None
    due_date: date | None = None
    is_completed: bool | None = None
    priority: int | None = None
    assignee_id: UUID | None = None


class TaskRead(BaseModel):
    id: UUID
    pair_id: UUID
    title: str
    details: str | None
    due_date: date | None
    is_completed: bool
    priority: int
    owner_id: UUID
    assignee_id: UUID | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None

    model_config = ConfigDict(from_attributes=True)
