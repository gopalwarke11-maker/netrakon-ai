"""Deterministic Phase 6 WebSocket integration tests."""

from fastapi.testclient import TestClient

from app.main import app
from app.services.alert_service import alert_service
from app.services.alert_websocket import alert_connection_manager


def _intrusion_payload() -> dict:
    return {
        "camera_id": "CAM-01",
        "custom_boundary": {
            "id": "BND-WS-01",
            "name": "WebSocket Test Boundary",
            "camera_id": "CAM-01",
            "enabled": True,
            "point_a": {"x": 100.0, "y": 250.0},
            "point_b": {"x": 700.0, "y": 250.0},
            "restricted_side": "positive",
            "severity": "HIGH",
            "tolerance": 5.0,
        },
        "frames": [
            {"frame_number": 1, "tracks": [{"track_id": 901, "anchor_x": 400.0, "anchor_y": 180.0}]},
            {"frame_number": 2, "tracks": [{"track_id": 901, "anchor_x": 400.0, "anchor_y": 320.0}]},
        ],
    }


def test_alert_websocket_connection_and_disconnect() -> None:
    with TestClient(app) as client:
        assert alert_connection_manager.connection_count == 0
        with client.websocket_connect("/ws/alerts") as stream:
            assert stream.receive_json()["type"] == "connected"
            assert alert_connection_manager.connection_count == 1
        assert alert_connection_manager.connection_count == 0


def test_intrusion_event_is_broadcast_to_multiple_clients_and_rest() -> None:
    with TestClient(app) as client:
        with client.websocket_connect("/ws/alerts") as one, client.websocket_connect("/ws/alerts") as two:
            assert one.receive_json()["type"] == "connected"
            assert two.receive_json()["type"] == "connected"
            response = client.post("/api/ai/intrusion-test", json=_intrusion_payload())
            assert response.status_code == 200
            event_one = one.receive_json()
            event_two = two.receive_json()

            for event in (event_one, event_two):
                assert event["type"] == "intrusion"
                assert event["event_id"].startswith("EVT-")
                assert event["camera_id"] == "CAM-01"
                assert event["boundary_id"] == "BND-WS-01"
                assert event["track_id"] == "901"
                assert event["severity"] == "HIGH"
                assert event["direction"] == "UNRESTRICTED_TO_RESTRICTED"
                assert event["timestamp"]

            rest_alerts = client.get("/api/alerts")
            assert rest_alerts.status_code == 200
            assert any(alert["id"] == event_one["alert_id"] for alert in rest_alerts.json())


def test_disconnected_client_does_not_block_real_intrusion_broadcast() -> None:
    with TestClient(app) as client:
        with client.websocket_connect("/ws/alerts") as closed_stream:
            assert closed_stream.receive_json()["type"] == "connected"
        with client.websocket_connect("/ws/alerts") as active_stream:
            assert active_stream.receive_json()["type"] == "connected"
            response = client.post("/api/ai/intrusion-test", json=_intrusion_payload())
            assert response.status_code == 200
            assert active_stream.receive_json()["type"] == "intrusion"
