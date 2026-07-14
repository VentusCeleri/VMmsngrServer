import logging

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import delete, or_, select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.errors import APIError
from app.db.session import get_db
from app.models.device_token import DeviceToken
from app.models.message import Message
from app.models.pair import Pair
from app.models.refresh_token import RefreshToken
from app.models.task import Task
from app.models.user import User
from app.realtime.manager import realtime_manager
from app.schemas.pair import PairRead
from app.schemas.realtime import make_realtime_event
from app.schemas.user import UserRead, UserUpdate

router = APIRouter(prefix="/api/v1/users", tags=["users"])
logger = logging.getLogger("vmmsngr.users")


@router.patch("/me", response_model=UserRead)
async def update_me(
    payload: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    if payload.username is not None and payload.username != current_user.username:
        existing = db.scalar(select(User).where(User.username == payload.username, User.id != current_user.id))
        if existing is not None:
            raise APIError(status.HTTP_409_CONFLICT, "username_already_exists", "Username is already in use")
        current_user.username = payload.username

    if payload.display_name is not None:
        current_user.display_name = payload.display_name

    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    pair = db.scalar(
        select(Pair)
        .where(or_(Pair.user_a_id == current_user.id, Pair.user_b_id == current_user.id))
        .limit(1)
    )
    if pair is not None:
        await realtime_manager.broadcast_pair(
            pair.id,
            make_realtime_event("profile.updated", pair.id, {"user": UserRead.model_validate(current_user).model_dump(mode="json")}),
        )
    return current_user


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    user_id = current_user.id
    pair = db.scalar(
        select(Pair)
        .where(or_(Pair.user_a_id == user_id, Pair.user_b_id == user_id))
        .limit(1)
    )
    pair_id = pair.id if pair is not None else None
    pair_deleted = False
    pair_payload: dict | None = None

    try:
        if pair is not None:
            if pair.user_a_id == user_id:
                pair.user_a_id = None
            if pair.user_b_id == user_id:
                pair.user_b_id = None

            pair_deleted = pair.user_a_id is None and pair.user_b_id is None
            if pair_deleted:
                db.execute(delete(Message).where(Message.pair_id == pair.id))
                db.execute(delete(Task).where(Task.pair_id == pair.id))
                db.delete(pair)
            else:
                db.execute(delete(Message).where(or_(Message.sender_id == user_id, Message.receiver_id == user_id)))
                db.execute(delete(Task).where(Task.owner_id == user_id))
                db.execute(update(Task).where(Task.assignee_id == user_id).values(assignee_id=None))
                db.add(pair)
                db.flush()
                pair_payload = PairRead.model_validate(pair).model_dump(mode="json")
        else:
            db.execute(delete(Message).where(or_(Message.sender_id == user_id, Message.receiver_id == user_id)))
            db.execute(delete(Task).where(Task.owner_id == user_id))
            db.execute(update(Task).where(Task.assignee_id == user_id).values(assignee_id=None))

        db.execute(delete(RefreshToken).where(RefreshToken.user_id == user_id))
        db.execute(delete(DeviceToken).where(DeviceToken.user_id == user_id))
        db.delete(current_user)
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Account delete failed", extra={"user_id": str(user_id)})
        raise APIError(status.HTTP_500_INTERNAL_SERVER_ERROR, "database_error", "Could not delete account") from exc

    logger.info("Account deleted", extra={"user_id": str(user_id), "pair_id": str(pair_id) if pair_id else ""})
    if pair_id is not None:
        await realtime_manager.broadcast_pair(
            pair_id,
            make_realtime_event("user.left", pair_id, {"pair_id": str(pair_id), "user_id": str(user_id)}),
        )
        if pair_deleted:
            await realtime_manager.broadcast_pair(pair_id, make_realtime_event("pair.deleted", pair_id, {"pair_id": str(pair_id)}))
            await realtime_manager.close_pair(pair_id)
        else:
            await realtime_manager.broadcast_pair(
                pair_id,
                make_realtime_event("pair.updated", pair_id, pair_payload or {"pair_id": str(pair_id)}),
            )

    await realtime_manager.close_user(user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
