import logging

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import ensure_pair_user, get_current_pair, get_current_user
from app.core.config import settings
from app.core.rate_limit import rate_limit
from app.db.session import get_db
from app.models.message import Message
from app.models.pair import Pair
from app.models.user import User
from app.notifications.events import notify_new_message, pair_recipient_ids
from app.schemas.message import MessageCreate, MessageRead
from app.realtime.manager import realtime_manager
from app.schemas.realtime import make_realtime_event

router = APIRouter(prefix="/api/v1/messages", tags=["messages"])
logger = logging.getLogger("vmmsngr.messages")


@router.get("", response_model=list[MessageRead])
def list_messages(pair: Pair = Depends(get_current_pair), db: Session = Depends(get_db)) -> list[Message]:
    return list(
        db.scalars(
            select(Message)
            .where(Message.pair_id == pair.id, Message.deleted_at.is_(None))
            .order_by(Message.created_at.asc())
        )
    )


@router.post(
    "",
    response_model=MessageRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit("messages", lambda: settings.rate_limit_messages_max_requests))],
)
async def send_message(
    payload: MessageCreate,
    current_user: User = Depends(get_current_user),
    pair: Pair = Depends(get_current_pair),
    db: Session = Depends(get_db),
) -> Message:
    ensure_pair_user(pair, payload.receiver_id)
    message = Message(
        pair_id=pair.id,
        sender_id=current_user.id,
        receiver_id=payload.receiver_id,
        body=payload.body,
        status="sent",
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    logger.info("Message created", extra={"message_id": str(message.id), "pair_id": str(pair.id), "user_id": str(current_user.id)})
    await realtime_manager.broadcast_pair(
        pair.id,
        make_realtime_event(
            "message.created",
            pair.id,
            MessageRead.model_validate(message).model_dump(mode="json"),
        ),
    )
    receiver_ids = [payload.receiver_id] if payload.receiver_id is not None and payload.receiver_id != current_user.id else pair_recipient_ids(pair, current_user.id)
    await notify_new_message(db, current_user, receiver_ids, message.id, message.body)
    return message
