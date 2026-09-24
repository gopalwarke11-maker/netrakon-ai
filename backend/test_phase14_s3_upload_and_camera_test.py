"""Tests for Phase 14 S3 Presigned Upload Architecture and Camera Connectivity Testing."""

from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.camera_connectivity import (
    check_private_network,
    is_private_ip,
    test_camera_stream_connectivity as run_connectivity_test,
)
from app.services.object_storage import object_storage_service

client = TestClient(app)


def test_private_ip_detection():
    """Verify private LAN IP detection across IPv4, IPv6, loopback, and local hostnames."""
    assert is_private_ip("10.78.26.161") is True
    assert is_private_ip("192.168.1.100") is True
    assert is_private_ip("172.16.0.5") is True
    assert is_private_ip("127.0.0.1") is True
    assert is_private_ip("8.8.8.8") is False
    assert is_private_ip("1.1.1.1") is False

    is_priv, _ = check_private_network("10.78.26.161")
    assert is_priv is True

    is_priv, _ = check_private_network("localhost")
    assert is_priv is True

    is_priv, _ = check_private_network("camera.local")
    assert is_priv is True


def test_camera_connectivity_private_lan():
    """Verify private LAN cameras report PRIVATE_NETWORK_NOT_REACHABLE clearly."""
    res = run_connectivity_test("MJPEG", "http://10.78.26.161:8080/video")
    assert res.is_reachable is False
    assert res.status == "PRIVATE_NETWORK_NOT_REACHABLE"
    assert "Private network address (10.78.26.161)" in res.message
    assert res.details is not None
    assert res.details["hostname"] == "10.78.26.161"


def test_camera_connectivity_invalid_url():
    """Verify invalid URL schemes/formats return INVALID_URL status."""
    res = run_connectivity_test("RTSP", "http://example.com/video")
    assert res.is_reachable is False
    assert res.status == "INVALID_URL"

    res = run_connectivity_test("MJPEG", "rtsp://example.com/stream")
    assert res.is_reachable is False
    assert res.status == "INVALID_URL"


def test_camera_connectivity_api_endpoint_private_lan():
    """Verify POST /api/cameras/test-connection for a private LAN camera."""
    response = client.post(
        "/api/cameras/test-connection",
        json={"source_type": "MJPEG", "stream_url": "http://10.78.26.161:8080/video"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_reachable"] is False
    assert data["status"] == "PRIVATE_NETWORK_NOT_REACHABLE"
    assert "private network" in data["message"].lower()


def test_presigned_upload_url_flow(tmp_path: Path):
    """Verify requesting a presigned upload URL, performing upload, and confirming metadata storage."""
    # 1. Request presigned upload URL
    req_resp = client.post(
        "/api/cameras/presigned-upload-url",
        json={"filename": "test_feed.mp4", "content_type": "video/mp4"},
    )
    assert req_resp.status_code == 200
    upload_info = req_resp.json()
    assert "upload_url" in upload_info
    assert "object_key" in upload_info
    assert upload_info["method"] == "PUT"
    object_key = upload_info["object_key"]

    # 2. Perform direct upload to upload_url (using dev fallback in local test mode)
    upload_url = upload_info["upload_url"]
    fake_mp4_bytes = b"\x00\x00\x00\x1cftypisom\x00\x00\x02\x00isomiso2avc1mp41"
    
    put_resp = client.put(
        upload_url,
        content=fake_mp4_bytes,
        headers={"Content-Type": "video/mp4"},
    )
    assert put_resp.status_code == 200

    # 3. Confirm upload with FastAPI
    confirm_resp = client.post(
        "/api/cameras/confirm-upload",
        json={
            "object_key": object_key,
            "name": "S3 Test Camera",
            "sector": "Border North",
            "location": "Post 14",
            "file_size_bytes": len(fake_mp4_bytes),
        },
    )
    assert confirm_resp.status_code == 200
    cam_data = confirm_resp.json()
    assert cam_data["storage_key"] == object_key
    assert cam_data["source_type"] == "FILE"
    assert cam_data["storage_metadata"] is not None
    assert cam_data["storage_metadata"]["file_size_bytes"] == len(fake_mp4_bytes)

    # Clean up test camera
    camera_id = cam_data["id"]
    client.delete(f"/api/cameras/{camera_id}")
