import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.errors import APIError
from app.db.session import get_db
from app.models.device_token import DeviceToken
from app.models.user import User
from app.schemas.device import DeviceDeleteRequest, DeviceRegisterRequest, DeviceTokenRead, DeviceTokenUpdateRequest

router = APIRouter(prefix="/api/v1/devices", tags=["devices"])
logger = logging.getLogger("vmmsngr.devices")


@router.post("/register", response_model=DeviceTokenRead, status_code=status.HTTP_201_CREATED)
def register_device(
    payload: DeviceRegisterRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DeviceToken:
    now = datetime.now(timezone.utc)
    device = db.scalar(select(DeviceToken).where(DeviceToken.device_token == payload.device_token))
    if device is None:
        device = DeviceToken(
            user_id=current_user.id,
            device_token=payload.device_token,
            platform=payload.platform,
            last_seen=now,
            active=True,
        )
    else:
        device.user_id = current_user.id
        device.platform = payload.platform
        device.last_seen = now
        device.active = True

    db.add(device)
    db.commit()
    db.refresh(device)
    logger.info("Device registered", extra={"user_id": str(current_user.id), "device_id": str(device.id), "platform": device.platform})
    return device


@router.patch("/token", response_model=DeviceTokenRead)
def update_device_token(
    payload: DeviceTokenUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DeviceToken:
    device = db.scalar(
        select(DeviceToken).where(
            DeviceToken.device_token == payload.device_token,
            DeviceToken.user_id == current_user.id,
        )
    )
    if device is None:
        raise APIError(status.HTTP_404_NOT_FOUND, "device_not_found", "Device token not found")

    existing_new_token = db.scalar(select(DeviceToken).where(DeviceToken.device_token == payload.new_device_token))
    if existing_new_token is not None and existing_new_token.id != device.id:
        db.delete(existing_new_token)
        db.flush()

    device.device_token = payload.new_device_token
    if payload.platform is not None:
        device.platform = payload.platform
    device.last_seen = datetime.now(timezone.utc)
    device.active = True
    db.add(device)
    db.commit()
    db.refresh(device)
    logger.info("Device token updated", extra={"user_id": str(current_user.id), "device_id": str(device.id), "platform": device.platform})
    return device


@router.delete("/current", status_code=status.HTTP_204_NO_CONTENT)
def delete_current_device(
    payload: DeviceDeleteRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    device = db.scalar(
        select(DeviceToken).where(
            DeviceToken.device_token == payload.device_token,
            DeviceToken.user_id == current_user.id,
        )
    )
    if device is not None:
        device.active = False
        device.last_seen = datetime.now(timezone.utc)
        db.add(device)
        db.commit()
        logger.info("Device deactivated", extra={"user_id": str(current_user.id), "device_id": str(device.id)})

    return Response(status_code=status.HTTP_204_NO_CONTENT)
