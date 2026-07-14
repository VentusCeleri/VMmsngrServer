from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.device_token import DeviceToken
from app.notifications.provider import APNsNotificationProvider, NotificationProvider, PushPayload

logger = logging.getLogger("vmmsngr.push")


class PushNotificationService:
    def __init__(self, provider: NotificationProvider | None = None) -> None:
        self.provider = provider or APNsNotificationProvider()

    async def notify_user(self, db: Session, user_id: UUID, payload: PushPayload) -> None:
        tokens = list(
            db.scalars(
                select(DeviceToken).where(
                    DeviceToken.user_id == user_id,
                    DeviceToken.active.is_(True),
                )
            )
        )
        if not tokens:
            logger.info("Push skipped: no active device tokens", extra={"user_id": str(user_id)})
            return

        for token in tokens:
            result = await self.provider.send(token.device_token, payload)
            if result.invalid_token:
                token.active = False
                db.add(token)
                db.commit()
                logger.error("Device token deactivated", extra={"device_id": str(token.id), "reason": result.reason or ""})


push_notification_service = PushNotificationService()
