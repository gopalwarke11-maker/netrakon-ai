"""Measure concurrent real local-video processing through CameraManager.

This is local hardware validation only. It uses actual YOLO and ByteTrack for a
bounded number of frames per camera and does not claim production scalability.
"""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any

from app.ai.model_manager import create_model_instance
from app.services.camera_processor import CameraManager, FileVideoSource, VideoSource


class LimitedVideoSource(VideoSource):
    def __init__(self, source: str, limit: int) -> None:
        self._inner = FileVideoSource(source)
        self._limit = limit
        self._read = 0

    @property
    def source_type(self):
        return "FILE"

    def open(self) -> bool:
        return self._inner.open()

    def read(self):
        if self._read >= self._limit:
            return False, None
        ok, frame = self._inner.read()
        if ok:
            self._read += 1
        return ok, frame

    def is_opened(self) -> bool:
        return self._inner.is_opened()

    def release(self) -> None:
        self._inner.release()

    @property
    def width(self) -> int:
        return self._inner.width

    @property
    def height(self) -> int:
        return self._inner.height

    @property
    def fps(self) -> float:
        return self._inner.fps


def main() -> int:
    root = Path(__file__).resolve().parent
    sources = {
        "CAM-01": root / "validation_input" / "YOUR_NIGHT_VIDEO.mp4",
        "CAM-02": root / "validation_input" / "night_test.mp4",
    }
    frame_limit = 60
    manager = CameraManager()
    for camera_id, path in sources.items():
        manager.register(
            camera_id,
            str(path),
            source_factory=lambda source, source_type, limit=frame_limit: LimitedVideoSource(source, limit),
            model_factory=create_model_instance,
        )

    started = time.perf_counter()
    manager.start("CAM-01")
    manager.start("CAM-02")
    deadline = started + 300.0
    while time.perf_counter() < deadline:
        statuses = manager.list_status()
        if all(status.frames_processed >= frame_limit or status.status in {"ERROR", "STOPPED"} for status in statuses):
            break
        time.sleep(0.1)
    manager.shutdown()
    duration = time.perf_counter() - started

    statuses = manager.list_status()
    result: dict[str, Any] = {
        "validation": "CONCURRENT REAL LOCAL VIDEO",
        "frame_limit_per_camera": frame_limit,
        "total_processing_seconds": round(duration, 3),
        "combined_fps": round(sum(status.frames_processed for status in statuses) / duration, 3) if duration else 0.0,
        "cameras": [
            {
                "camera_id": status.camera_id,
                "frames": status.frames_processed,
                "detections": status.detections_count,
                "active_tracks": status.active_tracks,
                "processing_fps": status.processing_fps,
                "status": status.status,
                "error": status.error,
            }
            for status in statuses
        ],
        "scope": "Actual YOLO + ByteTrack on two local videos; no RTSP hardware or production scalability claim.",
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
