"""
WebSocket routes for real-time role-based updates.
"""

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.core.security import decode_access_token
from app.core.websocket_manager import websocket_manager

router = APIRouter(prefix="/ws", tags=["WebSocket"])


@router.websocket("/connect")
async def websocket_connect(
    websocket: WebSocket,
    role: str = Query(default="VOLUNTEER"),
    user_id: str | None = Query(default=None),
    token: str | None = Query(default=None),
):
    if token:
        payload = decode_access_token(token)
        if payload:
            role = str(payload.get("role") or role)
            user_id = str(payload.get("sub") or user_id)
            ngo_id = payload.get("ngo_id")
        else:
            ngo_id = None
    else:
        ngo_id = None

    rooms = []
    role_normalized = (role or "VOLUNTEER").upper()
    if role_normalized in {"NGO_ADMIN", "NGO_MANAGER"}:
        rooms.append(f"ngo:{ngo_id}" if ngo_id else "ngo")
    if role_normalized in {"authority", "gov", "government"}:
        rooms.append("authority")
    if user_id:
        rooms.append(f"volunteer:{user_id}")

    await websocket_manager.connect(websocket, rooms=rooms)
    try:
        while True:
            message = await websocket.receive_text()
            if message == "ping":
                await websocket.send_text('{"event":"pong"}')
    except WebSocketDisconnect:
        await websocket_manager.disconnect(websocket)
    except Exception:
        await websocket_manager.disconnect(websocket)
