import json
import logging
from datetime import datetime, timezone
from uuid import UUID

import jwt
from fastapi import APIRouter, WebSocket
from sqlalchemy import or_, select
from starlette.websockets import WebSocketDisconnect

from app.core.security import decode_token
from app.db.session import SessionLocal
from app.models.pair import Pair
from app.models.user import User
from app.realtime.manager import realtime_manager
from app.schemas.realtime import make_realtime_event

router = APIRouter(prefix="/api/v1", tags=["websocket"])
logger = logging.getLogger("vmmsngr.websocket")

MAX_CLIENT_PAYLOAD_BYTES = 4096
WS_CLOSE_UNAUTHORIZED = 4401
WS_CLOSE_FORBIDDEN = 4403


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str | None = None) -> None:
    if not token:
        logger.error("WebSocket auth failed: missing token")
        await websocket.close(code=WS_CLOSE_UNAUTHORIZED)
        return

    try:
        decoded = decode_token(token)
    except jwt.PyJWTError:
        logger.error("WebSocket JWT decode failed")
        await websocket.close(code=WS_CLOSE_UNAUTHORIZED)
        return

    if decoded.get("type") != "access" or not decoded.get("sub"):
        logger.error("WebSocket auth failed: invalid token type")
        await websocket.close(code=WS_CLOSE_UNAUTHORIZED)
        return

    try:
        user_id = UUID(decoded["sub"])
    except ValueError:
        logger.error("WebSocket auth failed: invalid user id")
        await websocket.close(code=WS_CLOSE_UNAUTHORIZED)
        return

    with SessionLocal() as db:
        user = db.get(User, user_id)
        if user is None:
            logger.error("WebSocket auth failed: user not found", extra={"user_id": str(user_id)})
            await websocket.close(code=WS_CLOSE_UNAUTHORIZED)
            return

        pair = db.scalar(select(Pair).where(or_(Pair.user_a_id == user.id, Pair.user_b_id == user.id)).limit(1))
        if pair is None:
            logger.error("WebSocket forbidden: pair not found", extra={"user_id": str(user_id)})
            await websocket.close(code=WS_CLOSE_FORBIDDEN)
            return
        pair_id = pair.id

    became_online = await realtime_manager.connect(websocket, user_id=user_id, pair_id=pair_id)
    await realtime_manager.send_to(
        websocket,
        make_realtime_event("connection.ready", pair_id, {"user_id": str(user_id)}),
    )
    if became_online:
        await realtime_manager.broadcast_pair(
            pair_id,
            make_realtime_event(
                "presence.updated",
                pair_id,
                {"user_id": str(user_id), "is_online": True, "last_seen_at": None},
            ),
        )

    try:
        while True:
            raw_message = await websocket.receive_text()
            if len(raw_message.encode("utf-8")) > MAX_CLIENT_PAYLOAD_BYTES:
                await websocket.close(code=1009)
                return

            try:
                payload = json.loads(raw_message)
            except json.JSONDecodeError:
                await realtime_manager.send_to(websocket, make_realtime_event("error", pair_id, {"message": "Invalid JSON"}))
                continue

            if payload.get("event") == "ping":
                await realtime_manager.send_to(websocket, make_realtime_event("pong", pair_id, {}))
            else:
                await realtime_manager.send_to(websocket, make_realtime_event("error", pair_id, {"message": "Unsupported event"}))
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("WebSocket error", extra={"user_id": str(user_id), "pair_id": str(pair_id)})
    finally:
        info, is_last_user_connection = await realtime_manager.disconnect(websocket)
        if info is not None and is_last_user_connection:
            last_seen_at = datetime.now(timezone.utc)
            with SessionLocal() as db:
                user = db.get(User, info.user_id)
                if user is not None:
                    user.last_seen_at = last_seen_at
                    db.add(user)
                    db.commit()

            await realtime_manager.broadcast_pair(
                info.pair_id,
                make_realtime_event(
                    "presence.updated",
                    info.pair_id,
                    {
                        "user_id": str(info.user_id),
                        "is_online": False,
                        "last_seen_at": last_seen_at.isoformat(),
                    },
                ),
            )
