"""Measure the deterministic pipeline orchestration benchmark.

The source and tracker are deterministic injected edges so this benchmark does
not claim to measure hardware-specific YOLO throughput. Low-light processing,
worker orchestration, and frame accounting are measured directly.
"""

from __future__ import annotations

import json
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace

import cv2
import numpy as np

from app.ai.schemas import BoundingBoxAI, TrackFrame, TrackedObject
from app.services.camera_processor import CameraProcessor, FileVideoSource


class MeasurementSession:
    def __init__(self, session_id, camera_id, model):
        self.history = SimpleNamespace(records=[])
        self.intrusions = []

    def process_frame(self, frame, frame_number, timestamp_ms=0.0):
        bbox = BoundingBoxAI(x1=20, y1=15, x2=45, y2=55, width=25, height=40)
        if not self.history.records:
            self.history.records.append(SimpleNamespace(
                track_id=1,
                first_seen_frame=1,
                last_seen_frame=frame_number,
                position_log=[(32.5, 35.0)] * 5,
            ))
        self.history.records[0].last_seen_frame = frame_number
        return TrackFrame(
            frame_number=frame_number,
            timestamp_ms=timestamp_ms,
            image_width=frame.shape[1],
            image_height=frame.shape[0],
            processing_time_ms=0.0,
            objects=[TrackedObject(
                track_id=1,
                class_id=0,
                class_name="person",
                confidence=0.9,
                bounding_box=bbox,
                center_x=32.5,
                center_y=35.0,
            )],
        )

    def close(self):
        pass


def create_video(path: Path, frames: int = 60) -> None:
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 15.0, (160, 120))
    if not writer.isOpened():
        raise RuntimeError("Unable to create benchmark video")
    for index in range(frames):
        frame = np.full((120, 160, 3), 20 + (index % 8), dtype=np.uint8)
        cv2.rectangle(frame, (20 + index % 40, 20), (60 + index % 40, 80), (180, 180, 180), -1)
        writer.write(frame)
    writer.release()


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="netrakon-phase12-") as directory:
        video_path = Path(directory) / "measurement.mp4"
        create_video(video_path)
        processor = CameraProcessor(
            "CAM-MEASURE",
            str(video_path),
            source_factory=lambda source, source_type: FileVideoSource(source),
            session_factory=MeasurementSession,
            model_factory=object,
        )
        started = time.perf_counter()
        processor.start()
        while processor.status.status in {"ONLINE", "PROCESSING"} and processor.status.frames_processed < 60:
            time.sleep(0.005)
        processor.stop()
        duration = time.perf_counter() - started
        status = processor.status

    result = {
        "benchmark": "Deterministic pipeline orchestration benchmark",
        "frames_processed": status.frames_processed,
        "duration_seconds": round(duration, 6),
        "average_frame_processing_ms": round(duration * 1000 / status.frames_processed, 4) if status.frames_processed else None,
        "estimated_fps": round(status.frames_processed / duration, 3) if duration else 0.0,
        "detection_time": "NOT MEASURED (injected tracker)",
        "tracking_time": "NOT MEASURED (injected tracker)",
        "intrusion_processing_time": "NOT MEASURED (no boundary configured)",
        "behavior_processing_time": "NOT MEASURED (persistence disabled for benchmark)",
        "persistence_overhead": "NOT MEASURED",
        "websocket_publication_overhead": "NOT MEASURED",
        "end_to_end_event_latency": "NOT MEASURED",
        "scope": "Deterministic local source plus real low-light worker orchestration; not production FPS or scalability.",
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
