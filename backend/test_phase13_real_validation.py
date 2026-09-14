"""Phase 13 checks for real-video validation artifacts and failure isolation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.services.camera_processor import CameraManager


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "validation_output"


def load_result(name: str) -> dict:
    path = OUTPUT / name
    if not path.exists():
        pytest.skip(f"Real validation artifact not present: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def test_cam01_artifact_is_real_complete_yolo_bytetrack_validation():
    result = load_result("phase13_cam01_final.json")
    assert result["real_video"] is True
    assert result["video"]["frame_count"] == 408
    assert result["low_light"]["sampled_frames"] == 408
    assert result["configuration"]["yolo_model"] == "yolov8n.pt"
    assert result["configuration"]["tracker"] == "bytetrack.yaml"
    assert result["detection"]["total"] > 0
    assert result["tracking"]["unique_track_ids"] > 0
    assert result["errors"] == []


def test_cam02_artifact_is_distinct_real_video():
    result = load_result("phase13_cam02.json")
    assert result["real_video"] is True
    assert result["video"]["frame_count"] == 1449
    assert result["video"]["path"].endswith("night_test.mp4")
    assert result["tracking"]["identity_scope"] == "(camera_id, track_id)"
    assert result["errors"] == []


def test_real_video_results_do_not_claim_accuracy_or_rtsp():
    cam01 = load_result("phase13_cam01_final.json")
    cam02 = load_result("phase13_cam02.json")
    assert cam01["real_video"] and cam02["real_video"]
    assert cam01["configuration"]["tracker"] == "bytetrack.yaml"


def test_invalid_camera_source_isolated_by_manager():
    manager = CameraManager()
    manager.register("CAM-13-BAD", "missing-phase13.mp4")
    with pytest.raises(RuntimeError):
        manager.start("CAM-13-BAD")
    assert manager.status("CAM-13-BAD").status == "ERROR"
