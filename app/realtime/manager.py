from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from uuid import UUID

from fastapi import WebSocket
from starlette.websockets import WebSocketState

logger = logging.getLogger("vmmsngr.realtime")


@dataclass(frozen=True)
class ConnectionInfo:
    user_id: UUID
    pair_id: UUID


class RealtimeConnectionManager:
    def __init__(self) -> None:
        self._connections_by_pair: dict[UUID, set[WebSocket]] = {}
        self._connections_by_user: dict[UUID, set[WebSocket]] = {}
        self._connection_info: dict[WebSocket, ConnectionInfo] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, user_id: UUID, pair_id: UUID) -> bool:
        await websocket.accept()
        async with self._lock:
            was_offline = not self._connections_by_user.get(user_id)
            self._connections_by_pair.setdefault(pair_id, set()).add(websocket)
            self._connections_by_user.setdefault(user_id, set()).add(websocket)
            self._connection_info[websocket] = ConnectionInfo(user_id=user_id, pair_id=pair_id)
            logger.info("WebSocket connected", extra={"user_id": str(user_id), "pair_id": str(pair_id)})
            return was_offline

    async def disconnect(self, websocket: WebSocket) -> tuple[ConnectionInfo | None, bool]:
        async with self._lock:
            info = self._connection_info.pop(websocket, None)
            if info is None:
                return None, False

            pair_connections = self._connections_by_pair.get(info.pair_id)
            if pair_connections is not None:
                pair_connections.discard(websocket)
                if not pair_connections:
                    self._connections_by_pair.pop(info.pair_id, None)

            user_connections = self._connections_by_user.get(info.user_id)
            if user_connections is not None:
                user_connections.discard(websocket)
                is_last_user_connection = not user_connections
                if is_last_user_connection:
                    self._connections_by_user.pop(info.user_id, None)
            else:
                is_last_user_connection = True

            logger.info("WebSocket disconnected", extra={"user_id": str(info.user_id), "pair_id": str(info.pair_id)})
            return info, is_last_user_connection

    async def send_to(self, websocket: WebSocket, event: dict) -> bool:
        try:
            if websocket.client_state != WebSocketState.CONNECTED:
                return False
            await websocket.send_json(event)
            return True
        except RuntimeError:
            return False

    async def broadcast_pair(self, pair_id: UUID, event: dict) -> None:
        async with self._lock:
            connections = list(self._connections_by_pair.get(pair_id, set()))

        stale_connections: list[WebSocket] = []
        for websocket in connections:
            did_send = await self.send_to(websocket, event)
            if not did_send:
                stale_connections.append(websocket)

        for websocket in stale_connections:
            await self.disconnect(websocket)

    async def close_pair(self, pair_id: UUID, code: int = 1000) -> None:
        async with self._lock:
            connections = list(self._connections_by_pair.get(pair_id, set()))

        for websocket in connections:
            await self._close_socket(websocket, code)
            await self.disconnect(websocket)

    async def close_user(self, user_id: UUID, code: int = 1000) -> None:
        async with self._lock:
            connections = list(self._connections_by_user.get(user_id, set()))

        for websocket in connections:
            await self._close_socket(websocket, code)
            await self.disconnect(websocket)

    async def _close_socket(self, websocket: WebSocket, code: int) -> None:
        try:
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.close(code=code)
        except RuntimeError:
            logger.exception("WebSocket close failed")

    def is_user_online(self, user_id: UUID) -> bool:
        return bool(self._connections_by_user.get(user_id))

    def active_connection_count(self, pair_id: UUID | None = None) -> int:
        if pair_id is not None:
            return len(self._connections_by_pair.get(pair_id, set()))
        return len(self._connection_info)


realtime_manager = RealtimeConnectionManager()
