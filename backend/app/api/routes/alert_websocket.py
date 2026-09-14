"""WebSocket endpoint for server-generated real-time alert events."""

from fastapi import APIRouter, WebSocket
from starlette.websockets import WebSocketDisconnect

from app.services.alert_websocket import alert_connection_manager

router = APIRouter(tags=["alerts"])


@router.websocket("/ws/alerts")
async def alert_stream(websocket: WebSocket) -> None:
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
