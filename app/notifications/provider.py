from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import httpx
import jwt

from app.core.config import settings

logger = logging.getLogger("vmmsngr.push")


@dataclass(frozen=True)
class PushPayload:
    title: str
    body: str
    data: dict[str, str]


@dataclass(frozen=True)
class PushSendResult:
    sent: bool
    invalid_token: bool = False
    reason: str | None = None


class NotificationProvider(Protocol):
    async def send(self, device_token: str, payload: PushPayload) -> PushSendResult:
        ...


class APNsNotificationProvider:
    def __init__(self) -> None:
        self._configured = self._is_configured()
        self._private_key: str | None = None

    def _is_configured(self) -> bool:
        if not settings.apns_enabled:
            return False
        required = [
            settings.apns_team_id,
            settings.apns_key_id,
            settings.apns_bundle_id,
            settings.apns_private_key_path,
        ]
        return all(value.strip() for value in required)

    async def send(self, device_token: str, payload: PushPayload) -> PushSendResult:
        if not self._configured:
            logger.info("APNs not configured; push skipped", extra={"platform": "ios"})
            return PushSendResult(sent=False, reason="apns_not_configured")

        try:
            token = self._authorization_token()
            endpoint = self._endpoint(device_token)
            apns_payload = {
                "aps": {
                    "alert": {
                        "title": payload.title,
                        "body": payload.body,
                    },
                    "sound": "default",
                },
                "vmmsngr": payload.data,
            }
            headers = {
                "authorization": f"bearer {token}",
                "apns-topic": settings.apns_bundle_id,
                "apns-push-type": "alert",
                "apns-priority": "10",
            }
            async with httpx.AsyncClient(http2=True, timeout=10) as client:
                response = await client.post(endpoint, json=apns_payload, headers=headers)

            if response.status_code == 200:
                logger.info("Push sent", extra={"provider": "apns"})
                return PushSendResult(sent=True)

            reason = self._apns_reason(response)
            invalid = reason in {"BadDeviceToken", "Unregistered", "DeviceTokenNotForTopic"}
            if invalid:
                logger.error("APNs invalid device token", extra={"reason": reason})
            else:
                logger.error("APNs send failed", extra={"status_code": response.status_code, "reason": reason})
            return PushSendResult(sent=False, invalid_token=invalid, reason=reason)
        except Exception as exc:
            logger.exception("APNs error")
            return PushSendResult(sent=False, reason=str(exc))

    def _authorization_token(self) -> str:
        private_key = self._load_private_key()
        return jwt.encode(
            {"iss": settings.apns_team_id, "iat": int(time.time())},
            private_key,
            algorithm="ES256",
            headers={"alg": "ES256", "kid": settings.apns_key_id},
        )

    def _load_private_key(self) -> str:
        if self._private_key is None:
            self._private_key = Path(settings.apns_private_key_path).read_text(encoding="utf-8")
        return self._private_key

    def _endpoint(self, device_token: str) -> str:
        host = "api.push.apple.com" if settings.apns_environment == "production" else "api.sandbox.push.apple.com"
        return f"https://{host}/3/device/{device_token}"

    def _apns_reason(self, response: httpx.Response) -> str:
        try:
            body = response.json()
        except ValueError:
            return response.text[:120]
        reason = body.get("reason")
        return str(reason) if reason else response.text[:120]
