from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import ensure_pair_user, get_current_pair, get_current_user
from app.db.session import get_db
from app.models.pair import Pair
from app.models.task import Task
from app.models.user import User
from app.schemas.task import TaskCreate, TaskRead, TaskUpdate

router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])


@router.get("", response_model=list[TaskRead])
def list_tasks(pair: Pair = Depends(get_current_pair), db: Session = Depends(get_db)) -> list[Task]:
    return list(
        db.scalars(
            select(Task)
            .where(Task.pair_id == pair.id, Task.deleted_at.is_(None))
            .order_by(Task.is_completed.asc(), Task.priority.desc(), Task.created_at.desc())
        )
    )


@router.post("", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
def create_task(
    payload: TaskCreate,
    current_user: User = Depends(get_current_user),
    pair: Pair = Depends(get_current_pair),
    db: Session = Depends(get_db),
) -> Task:
    ensure_pair_user(pair, payload.assignee_id)
    task = Task(
        pair_id=pair.id,
        title=payload.title,
        details=payload.details,
        due_date=payload.due_date,
        is_completed=payload.is_completed,
        priority=payload.priority,
        owner_id=current_user.id,
        assignee_id=payload.assignee_id,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.patch("/{task_id}", response_model=TaskRead)
def update_task(
    task_id: UUID,
    payload: TaskUpdate,
    pair: Pair = Depends(get_current_pair),
    db: Session = Depends(get_db),
) -> Task:
    task = db.scalar(select(Task).where(Task.id == task_id, Task.pair_id == pair.id, Task.deleted_at.is_(None)))
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    updates = payload.model_dump(exclude_unset=True)
    if "assignee_id" in updates:
        ensure_pair_user(pair, updates["assignee_id"])
    for key, value in updates.items():
        setattr(task, key, value)

    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    task_id: UUID,
    pair: Pair = Depends(get_current_pair),
    db: Session = Depends(get_db),
) -> None:
    task = db.scalar(select(Task).where(Task.id == task_id, Task.pair_id == pair.id, Task.deleted_at.is_(None)))
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    task.deleted_at = datetime.now(timezone.utc)
    db.add(task)
    db.commit()
