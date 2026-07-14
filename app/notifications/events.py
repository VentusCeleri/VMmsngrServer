from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.pair import Pair
from app.models.user import User
from app.notifications.provider import PushPayload
from app.notifications.service import push_notification_service
from app.realtime.manager import realtime_manager

logger = logging.getLogger("vmmsngr.push")


def _trim(text: str, limit: int = 80) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def pair_recipient_ids(pair: Pair, sender_id: UUID) -> list[UUID]:
    ids = [pair.user_a_id, pair.user_b_id]
    return [user_id for user_id in ids if user_id is not None and user_id != sender_id]


async def notify_if_offline(db: Session, user_id: UUID, payload: PushPayload) -> None:
    if realtime_manager.is_user_online(user_id):
        logger.info("Push skipped: user has active WebSocket", extra={"user_id": str(user_id), "event": payload.data.get("type", "")})
        return
    await push_notification_service.notify_user(db, user_id, payload)


async def notify_new_message(db: Session, sender: User, receiver_ids: list[UUID], message_id: UUID, body: str) -> None:
    payload = PushPayload(
        title=sender.display_name,
        body=_trim(body),
        data={"type": "message", "message_id": str(message_id)},
    )
    for receiver_id in receiver_ids:
        await notify_if_offline(db, receiver_id, payload)


async def notify_new_task(db: Session, receiver_ids: list[UUID], task_id: UUID, title: str) -> None:
    payload = PushPayload(
        title="Новая задача",
        body=_trim(title),
        data={"type": "task", "task_id": str(task_id)},
    )
    for receiver_id in receiver_ids:
        await notify_if_offline(db, receiver_id, payload)


async def notify_pair_joined(db: Session, joined_user: User, receiver_ids: list[UUID], pair_id: UUID) -> None:
    payload = PushPayload(
        title="VMmsngr",
        body=f"{joined_user.display_name} присоединился к вашей паре.",
        data={"type": "pair", "pair_id": str(pair_id)},
    )
    for receiver_id in receiver_ids:
        await notify_if_offline(db, receiver_id, payload)
