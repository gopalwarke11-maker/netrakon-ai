"""Native WebSocket delivery for real-time intrusion alerts."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable

from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect, WebSocketState

from app.models.alert import Alert
from app.models.intrusion import IntrusionEvent
from app.ai.behavior_schemas import BehaviorAssessment

logger = logging.getLogger(__name__)


class AlertConnectionManager:
    """Keep alert stream clients and safely fan out server-generated events."""

    def __init__(self) -> None:
        self._connections: list[WebSocket] = []
        self._loop: asyncio.AbstractEventLoop | None = None

    @property
    def connection_count(self) -> int:
        return len(self._connections)

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        if websocket not in self._connections:
            self._connections.append(websocket)
        await self._send_one(
            websocket,
            {"type": "connected", "message": "NETRAKON AI alert stream connected"},
        )

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self._connections:
            self._connections.remove(websocket)

    async def _send_one(self, websocket: WebSocket, message: dict) -> bool:
        try:
            if websocket.application_state != WebSocketState.CONNECTED:
                self.disconnect(websocket)
                return False
            await websocket.send_json(message)
            return True
        except (WebSocketDisconnect, RuntimeError, OSError) as exc:
            logger.info("Alert WebSocket client disconnected during send: %s", exc)
            self.disconnect(websocket)
            return False
        except Exception:
            logger.exception("Failed to deliver alert WebSocket message")
            self.disconnect(websocket)
            return False

    async def broadcast(self, message: dict) -> None:
        for websocket in list(self._connections):
            await self._send_one(websocket, message)

    def publish_intrusion(self, event: IntrusionEvent, alert: Alert) -> None:
        """Schedule delivery without blocking the detection/tracking path.
        
        Includes risk assessment information if available.
        """
        message = {
            "type": "intrusion",
            "event_id": event.id,
            "alert_id": alert.id,
            "timestamp": event.timestamp.isoformat(),
            "camera_id": event.camera_id,
            "boundary_id": event.boundary_id,
            "boundary_name": event.boundary_name,
            "track_id": str(event.track_id),
            "severity": event.severity,
            "direction": event.crossing_direction,
            "object_class": event.object_class,
            "confidence": event.confidence,
            "message": alert.message,
            "sector": alert.sector,
            "status": alert.status,
        }
        
        # Add risk information if available (Phase 8)
        if hasattr(alert, 'risk_score') and alert.risk_score is not None:
            message["risk_score"] = alert.risk_score
            message["risk_level"] = getattr(alert, 'risk_level', None)
        
        if self._loop is None or self._loop.is_closed():
            logger.debug("Alert WebSocket loop is not available; event remains available via REST")
            return
        self._loop.call_soon_threadsafe(asyncio.create_task, self.broadcast(message))

    def publish_behavior(self, behavior: BehaviorAssessment) -> None:
        """Publish a persisted behavior assessment without changing intrusion clients."""
        message = {
            "type": "behavior",
            "behavior_id": behavior.id,
            "camera_id": behavior.camera_id,
            "track_id": str(behavior.track_id),
            "behavior_type": behavior.primary_behavior,
            "behavior_score": behavior.behavior_score,
            "observations": [observation.model_dump(mode="json") for observation in behavior.observations],
            "assessed_at": behavior.assessed_at.isoformat(),
        }
        if self._loop is None or self._loop.is_closed():
            logger.debug("Alert WebSocket loop is not available; behavior remains available via REST")
            return
        self._loop.call_soon_threadsafe(asyncio.create_task, self.broadcast(message))


alert_connection_manager = AlertConnectionManager()
