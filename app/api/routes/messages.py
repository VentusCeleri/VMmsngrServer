from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import ensure_pair_user, get_current_pair, get_current_user
from app.db.session import get_db
from app.models.message import Message
from app.models.pair import Pair
from app.models.user import User
from app.schemas.message import MessageCreate, MessageRead

router = APIRouter(prefix="/api/v1/messages", tags=["messages"])


@router.get("", response_model=list[MessageRead])
def list_messages(pair: Pair = Depends(get_current_pair), db: Session = Depends(get_db)) -> list[Message]:
    return list(
        db.scalars(
            select(Message)
            .where(Message.pair_id == pair.id, Message.deleted_at.is_(None))
            .order_by(Message.created_at.asc())
        )
    )


@router.post("", response_model=MessageRead, status_code=status.HTTP_201_CREATED)
def send_message(
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
    return message
