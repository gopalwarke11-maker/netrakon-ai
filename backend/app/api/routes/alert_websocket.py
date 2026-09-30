"""WebSocket endpoint for server-generated real-time alert events using HttpOnly cookie authentication."""

from fastapi import APIRouter, WebSocket, status
from starlette.websockets import WebSocketDisconnect

from app.core.security import decode_access_token
from app.services.alert_websocket import alert_connection_manager

router = APIRouter(tags=["alerts"])


@router.websocket("/ws/alerts")
async def alert_stream(websocket: WebSocket) -> None:
    # Authenticate handshake strictly via HttpOnly netrakon_auth cookie if present
    auth_cookie = websocket.cookies.get("netrakon_auth")
    if auth_cookie:
        payload = decode_access_token(auth_cookie)
        if not payload or not payload.get("sub"):
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

    await alert_connection_manager.connect(websocket)
    try:
        # Clients do not create alerts. Receiving keeps the connection open and
        # safely consumes any accidental client messages.
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        alert_connection_manager.disconnect(websocket)
