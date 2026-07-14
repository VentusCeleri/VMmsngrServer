from datetime import date, datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TaskPriority(StrEnum):
    low = "low"
    normal = "normal"
    important = "important"
    urgent = "urgent"


def normalize_priority(value: TaskPriority | str | int | None) -> TaskPriority:
    if value is None:
        return TaskPriority.normal
    if isinstance(value, TaskPriority):
        return value
    if isinstance(value, int):
        return {
            0: TaskPriority.low,
            1: TaskPriority.normal,
            2: TaskPriority.important,
            3: TaskPriority.urgent,
        }.get(value, TaskPriority.normal)
    lowered = value.lower()
    return TaskPriority(lowered) if lowered in TaskPriority._value2member_map_ else TaskPriority.normal


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    details: str | None = None
    due_date: date | None = None
    is_completed: bool = False
    priority: TaskPriority = TaskPriority.normal
    assignee_id: UUID | None = None

    @field_validator("priority", mode="before")
    @classmethod
    def validate_priority(cls, value: TaskPriority | str | int | None) -> TaskPriority:
        return normalize_priority(value)


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    details: str | None = None
    due_date: date | None = None
    is_completed: bool | None = None
    priority: TaskPriority | None = None
    assignee_id: UUID | None = None

    @field_validator("priority", mode="before")
    @classmethod
    def validate_priority(cls, value: TaskPriority | str | int | None) -> TaskPriority | None:
        return None if value is None else normalize_priority(value)


class TaskRead(BaseModel):
    id: UUID
    pair_id: UUID
    title: str
    details: str | None
    due_date: date | None
    is_completed: bool
    priority: TaskPriority
    owner_id: UUID
    assignee_id: UUID | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None

    model_config = ConfigDict(from_attributes=True)
