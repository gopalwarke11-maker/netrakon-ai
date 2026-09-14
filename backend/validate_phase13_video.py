"""Real local-video Phase 13 validator using the production YOLO + ByteTrack path."""

from __future__ import annotations

import argparse
import json
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from app.ai.behavior_engine import behavior_engine
from app.ai.low_light import get_processor
from app.ai.model_manager import create_model_instance
from app.ai.tracker import TrackSession
from app.core.config import settings
from app.services.behavior_service import behavior_service
from app.services.boundary_service import boundary_service
from app.db.models import IntrusionEventRecord
from app.db.session import SessionLocal
from sqlalchemy import select


def metadata(video_path: Path) -> dict[str, Any]:
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise ValueError(f"Unable to open video: {video_path}")
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
    reported_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    cap.release()
    return {
        "path": str(video_path.resolve()),
        "resolution": f"{width}x{height}" if width and height else "unknown",
        "width": width,
        "height": height,
        "fps": round(fps, 3),
        "frame_count": reported_frames,
        "duration_seconds": round(reported_frames / fps, 3) if fps else 0.0,
        "file_size_bytes": video_path.stat().st_size,
    }


def run_validation(
    video_path: str | Path,
    camera_id: str,
    boundary_id: str | None = None,
    enhance_low_light: bool = False,
    max_frames: int | None = None,
    persist_behavior: bool = True,
) -> dict[str, Any]:
    """Process a real local video through low-light, YOLO, ByteTrack, and behavior."""
    path = Path(video_path).expanduser()
    if not path.is_file():
        raise FileNotFoundError(f"Video does not exist: {path}")
    info = metadata(path)
    processor = get_processor()
    session = TrackSession(
        conf=settings.track_conf_threshold,
        session_id=f"phase13-{camera_id}",
        camera_id=camera_id,
        model=create_model_instance(),
    )
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise ValueError(f"Unable to open video: {path}")

    low_light_frames = 0
    luminance: list[float] = []
    detections = 0
    confidences: list[float] = []
    classes: Counter[str] = Counter()
    observations: list[dict[str, Any]] = []
    frame_times: list[float] = []
    processed_frames = 0
    errors: list[str] = []
    started = time.perf_counter()
    behavior_keys: set[tuple[int, str, int]] = set()
    configured_boundaries = boundary_service.get_by_camera(camera_id)

    try:
        while True:
            if max_frames and processed_frames >= max_frames:
                break
            ok, frame = cap.read()
            if not ok:
                break
            processed_frames += 1
            frame_started = time.perf_counter()
            try:
                analysis = processor.analyze_frame(frame)
                luminance.append(float(analysis.mean_luminance))
                low_light_frames += int(analysis.low_light)
                working_frame = frame
                if enhance_low_light and analysis.low_light:
                    working_frame, _ = processor.process_frame(frame, enable_enhancement=True)
                tracked = session.process_frame(
                    working_frame,
                    frame_number=processed_frames,
                    timestamp_ms=processed_frames * 1000.0 / max(info["fps"], 1.0),
                )
                detections += len(tracked.objects)
                for obj in tracked.objects:
                    classes[obj.class_name] += 1
                    confidences.append(float(obj.confidence))
                    observations.append({
                        "camera_id": camera_id,
                        "track_id": obj.track_id,
                        "frame_number": processed_frames,
                        "class_name": obj.class_name,
                        "confidence": float(obj.confidence),
                    })
                for track in session.history.records:
                    assessment = behavior_engine.analyze_track(camera_id, track, 0)
                    if assessment is None or assessment.primary_behavior is None:
                        continue
                    key = (track.track_id, assessment.primary_behavior, assessment.behavior_score)
                    if key in behavior_keys:
                        continue
                    behavior_keys.add(key)
                    if persist_behavior:
                        behavior_service.create_behavior(assessment)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"frame {processed_frames}: {exc}")
            frame_times.append((time.perf_counter() - frame_started) * 1000.0)
    finally:
        cap.release()
        session.close()

    by_track: dict[int, list[int]] = {}
    for observation in observations:
        by_track.setdefault(int(observation["track_id"]), []).append(int(observation["frame_number"]))
    durations = [len(frames) for frames in by_track.values()]
    multi_frame = sum(1 for duration in durations if duration >= 2)
    intrusion_events = list(session.intrusions)
    event_ids = [event.id for event in intrusion_events if event.id and event.id != "PENDING"]
    persisted_events = []
    if event_ids:
        with SessionLocal() as db:
            persisted_events = list(db.scalars(
                select(IntrusionEventRecord).where(IntrusionEventRecord.id.in_(event_ids))
            ).all())
    risk_scores = [int(row.risk_score) for row in persisted_events if row.risk_score is not None]

    result = {
        "camera_id": camera_id,
        "real_video": True,
        "video": info,
        "configuration": {
            "yolo_model": settings.yolo_model_name,
            "tracker": settings.yolo_tracker,
            "confidence": settings.track_conf_threshold,
            "low_light_enabled": settings.low_light_enabled,
            "low_light_threshold": settings.low_light_threshold,
            "enhance_low_light": enhance_low_light,
            "boundary_id": boundary_id,
            "configured_boundary_ids": [boundary.id for boundary in configured_boundaries],
        },
        "low_light": {
            "sampled_frames": processed_frames,
            "low_light_frames": low_light_frames,
            "percentage_low_light": round(100.0 * low_light_frames / processed_frames, 2) if processed_frames else 0.0,
            "average_luminance": round(float(np.mean(luminance)), 3) if luminance else None,
        },
        "detection": {
            "total": detections,
            "per_frame": round(detections / processed_frames, 3) if processed_frames else 0.0,
            "average_confidence": round(float(np.mean(confidences)), 4) if confidences else None,
            "class_counts": dict(classes),
        },
        "tracking": {
            "unique_track_ids": len(by_track),
            "multi_frame_tracks": multi_frame,
            "multi_frame_track_ratio": round(multi_frame / len(by_track), 4) if by_track else 0.0,
            "average_track_duration": round(float(np.mean(durations)), 3) if durations else 0.0,
            "maximum_track_duration": max(durations) if durations else 0,
            "total_observations": len(observations),
            "identity_scope": "(camera_id, track_id)",
        },
        "intrusion": {
            "status": "EXERCISED" if configured_boundaries else "NOT EXERCISED",
            "events": len(intrusion_events),
            "severity_distribution": dict(Counter(event.severity for event in intrusion_events)),
            "direction_distribution": dict(Counter(event.crossing_direction for event in intrusion_events)),
        },
        "risk": {
            "status": "EXERCISED" if persisted_events else "NOT EXERCISED",
            "assessments": len(risk_scores),
            "average_score": round(float(np.mean(risk_scores)), 3) if risk_scores else None,
            "levels": dict(Counter(row.risk_level or "UNKNOWN" for row in persisted_events)),
            "events": [
                {
                    "event_id": row.id,
                    "camera_id": row.camera_id,
                    "boundary_id": row.boundary_id,
                    "track_id": row.track_id,
                    "severity": row.severity,
                    "object_class": row.object_class,
                    "confidence": row.confidence,
                    "direction": row.crossing_direction,
                    "risk_score": row.risk_score,
                    "risk_level": row.risk_level,
                    "risk_factors": row.risk_factors,
                }
                for row in persisted_events
            ],
        },
        "behavior": {
            "status": "EXERCISED" if behavior_keys else "INSUFFICIENT TRACK HISTORY",
            "observations": len(behavior_keys),
            "types": dict(Counter(key[1] for key in behavior_keys)),
            "average_score": round(float(np.mean([key[2] for key in behavior_keys])), 3) if behavior_keys else None,
        },
        "performance": {
            "processing_seconds": round(time.perf_counter() - started, 3),
            "average_ms_per_frame": round(float(np.mean(frame_times)), 3) if frame_times else None,
            "estimated_fps": round(1000.0 / float(np.mean(frame_times)), 3) if frame_times and np.mean(frame_times) else 0.0,
            "local_hardware_validation": True,
        },
        "errors": errors,
        "websocket": "EVENTS PUBLISHED BY PRODUCTION PATH" if intrusion_events or behavior_keys else "NOT EXERCISED",
        "validated_at": datetime.now(timezone.utc).isoformat(),
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a real local video through the Phase 13 pipeline.")
    parser.add_argument("--video", required=True)
    parser.add_argument("--camera-id", required=True)
    parser.add_argument("--boundary-id")
    parser.add_argument("--enhance-low-light", action="store_true")
    parser.add_argument("--max-frames", type=int)
    parser.add_argument("--output-json")
    args = parser.parse_args()
    result = run_validation(args.video, args.camera_id, args.boundary_id, args.enhance_low_light, args.max_frames)
    encoded = json.dumps(result, indent=2)
    if args.output_json:
        Path(args.output_json).write_text(encoded, encoding="utf-8")
    print(encoded)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
