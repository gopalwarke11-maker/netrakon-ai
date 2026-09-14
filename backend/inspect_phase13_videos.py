"""Inspect local video metadata and low-light suitability for Phase 13."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np

from app.core.config import settings


def inspect(path: Path) -> dict:
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        return {"video": str(path), "error": "Unable to open"}
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
    reported = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    values = []
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        values.append(float(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).mean()))
    cap.release()
    low = sum(value < settings.low_light_threshold for value in values)
    fraction = low / len(values) if values else 0.0
    return {
        "video": str(path.resolve()),
        "file_size_bytes": path.stat().st_size,
        "resolution": f"{width}x{height}",
        "fps": round(fps, 3),
        "duration_seconds": round(len(values) / fps, 3) if fps else 0.0,
        "frame_count_reported": reported,
        "decoded_frames": len(values),
        "average_luminance": round(float(np.mean(values)), 3) if values else None,
        "low_light_percentage": round(100.0 * fraction, 2),
        "night_suitability": "HIGHLY SUITABLE" if fraction > 0.5 else "SUITABLE" if fraction >= 0.2 else "WEAK" if fraction >= 0.05 else "NOT SUITABLE",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args()
    print(json.dumps([inspect(path) for path in args.paths], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
