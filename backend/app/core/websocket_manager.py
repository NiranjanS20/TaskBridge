"""
WebSocket connection manager with room-based broadcasting.
"""

from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from typing import Any

from fastapi import WebSocket

from app.utils.logger import get_logger

logger = get_logger(__name__)


class WebSocketManager:
    def __init__(self) -> None:
        self._room_connections: dict[str, set[WebSocket]] = defaultdict(set)
        self._socket_rooms: dict[WebSocket, set[str]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, rooms: list[str]) -> None:
        await websocket.accept()
        async with self._lock:
            for room in rooms:
                if not room:
                    continue
                self._room_connections[room].add(websocket)
                self._socket_rooms[websocket].add(room)
        logger.info("WebSocket connected to rooms=%s", rooms)

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            rooms = list(self._socket_rooms.get(websocket, set()))
            for room in rooms:
                self._room_connections[room].discard(websocket)
                if not self._room_connections[room]:
                    self._room_connections.pop(room, None)
            self._socket_rooms.pop(websocket, None)

    async def broadcast_room(self, room: str, event_type: str, payload: dict[str, Any]) -> None:
        message = json.dumps({"event": event_type, "payload": payload})
        async with self._lock:
            connections = list(self._room_connections.get(room, set()))
        if not connections:
            return
        stale: list[WebSocket] = []
        for ws in connections:
            try:
                await ws.send_text(message)
            except Exception:
                stale.append(ws)
        for ws in stale:
            await self.disconnect(ws)

    async def dispatch_system_event(self, event_type: str, payload: dict[str, Any]) -> None:
        mapped_event = {
            "new_task": "TASK_CREATED",
            "allocation_complete": "TASK_ASSIGNED",
            "task_assigned": "TASK_ASSIGNED",
            "task_accepted": "TASK_ACCEPTED",
        }.get(event_type, event_type.upper())

        ngo_id = payload.get("ngo_id")
        if ngo_id:
            await self.broadcast_room(f"ngo:{ngo_id}", mapped_event, payload)
        else:
            await self.broadcast_room("ngo", mapped_event, payload)
        await self.broadcast_room("authority", mapped_event, payload)

        volunteer_id = payload.get("volunteer_id")
        if volunteer_id:
            await self.broadcast_room(f"volunteer:{volunteer_id}", mapped_event, payload)


websocket_manager = WebSocketManager()
