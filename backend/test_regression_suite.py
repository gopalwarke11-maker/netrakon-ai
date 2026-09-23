"""Full regression test suite covering Phases 1, 2, 3, 4, and 5 via FastAPI TestClient."""

import io
import tempfile
from pathlib import Path
import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.ai import model_manager
from app.main import app


@pytest.fixture(scope="module", autouse=True)
def setup_lifespan():
    """Ensure YOLO model is loaded for inference during tests."""
    with TestClient(app) as test_client:
        yield test_client


def test_phase1_and_phase2_endpoints(setup_lifespan):
    """Verify health, cameras, alerts, and detections endpoints."""
    client = setup_lifespan
    # Health
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

    # Root
    r = client.get("/")
    assert r.status_code == 200
    assert "service" in r.json()

    # Cameras
    r = client.get("/api/cameras")
    assert r.status_code == 200
    assert len(r.json()) >= 2

    # Alerts
    r = client.get("/api/alerts")
    assert r.status_code == 200

    # Detections
    r = client.get("/api/detections")
    assert r.status_code == 200


def test_phase3_ai_detect_regression(setup_lifespan):
    """Verify Phase 3 POST /api/ai/detect with synthetic image."""
    client = setup_lifespan
    img = np.zeros((300, 300, 3), dtype=np.uint8)
    cv2.rectangle(img, (50, 50), (200, 200), (0, 255, 0), -1)
    ok, img_bytes = cv2.imencode(".jpg", img)
    assert ok

    files = {"file": ("test_detect.jpg", io.BytesIO(img_bytes.tobytes()), "image/jpeg")}
    r = client.post("/api/ai/detect?conf=0.25", files=files)
    assert r.status_code == 200
    data = r.json()
    assert "detections" in data
    assert "image_width" in data
    assert "image_height" in data
    assert data["image_width"] == 300
    assert data["image_height"] == 300


def test_phase4_ai_track_regression(setup_lifespan):
    """Verify Phase 4 POST /api/ai/track with synthetic video."""
    client = setup_lifespan
    width, height, fps, n_frames = 320, 240, 15, 10

    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(tmp_path, fourcc, fps, (width, height))
        for _ in range(n_frames):
            f = np.zeros((height, width, 3), dtype=np.uint8)
            cv2.rectangle(f, (50, 50), (100, 150), (255, 255, 255), -1)
            writer.write(f)
        writer.release()

        video_bytes = Path(tmp_path).read_bytes()
        files = {"file": ("test_track.mp4", io.BytesIO(video_bytes), "video/mp4")}
        r = client.post("/api/ai/track?conf=0.25&max_frames=5", files=files)
        assert r.status_code == 200
        data = r.json()
        assert "tracks" in data
        assert "total_frames_processed" in data
        assert data["total_frames_processed"] == 5
        assert "intrusions" in data
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def test_phase4_invalid_input_regression(setup_lifespan):
    """Verify graceful 400 rejection on non-video file."""
    client = setup_lifespan
    files = {"file": ("test.txt", io.BytesIO(b"Hello world not a video"), "text/plain")}
    r = client.post("/api/ai/track", files=files)
    assert r.status_code == 400


def test_phase5_camera_boundary_integration(setup_lifespan):
    """Verify boundary retrieval per camera."""
    client = setup_lifespan
    r = client.get("/api/cameras/CAM-01/boundaries")
    assert r.status_code == 200
    boundaries = r.json()
    assert isinstance(boundaries, list)
    for b in boundaries:
        assert b["camera_id"] == "CAM-01"


def test_cors_preflight_and_origin_headers(setup_lifespan):
    """Verify CORS headers for production Netlify origin and preflight OPTIONS request."""
    client = setup_lifespan
    prod_origin = "https://netrakon-ai.netlify.app"

    # Preflight request
    headers = {
        "Origin": prod_origin,
        "Access-Control-Request-Method": "GET",
        "Access-Control-Request-Headers": "authorization,content-type",
    }
    r = client.options("/api/health", headers=headers)
    assert r.status_code == 200
    assert r.headers.get("access-control-allow-origin") == prod_origin
    assert r.headers.get("access-control-allow-credentials") == "true"

    # Actual request with Origin
    r = client.get("/api/health", headers={"Origin": prod_origin})
    assert r.status_code == 200
    assert r.headers.get("access-control-allow-origin") == prod_origin
    assert r.headers.get("access-control-allow-credentials") == "true"

