"""NETRAKON AI — Phase 4 tracking test utility.

Usage
-----
Run with the backend server already started (``uvicorn app.main:app --reload``):

    # Generate a synthetic test video and run tracking
    python test_tracking.py

    # Use your own local video file
    python test_tracking.py path/to/video.mp4

    # Process only the first 30 frames (fast dev test)
    python test_tracking.py --max-frames 30

    # Override confidence threshold
    python test_tracking.py video.mp4 --conf 0.3 --max-frames 50

    # Point at a different backend URL
    python test_tracking.py --url http://127.0.0.1:8000
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

# ── CLI args ───────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser(description="Test NETRAKON AI YOLO tracking endpoint.")
parser.add_argument(
    "video",
    nargs="?",
    help="Path to a local video file.  Omit to auto-generate a synthetic test video.",
)
parser.add_argument(
    "--conf",
    type=float,
    default=0.25,
    help="Confidence threshold [0.01–1.0].  Default: 0.25",
)
parser.add_argument(
    "--max-frames",
    type=int,
    default=60,
    help="Maximum frames to process (0 = all).  Default: 60",
)
parser.add_argument(
    "--url",
    default="http://127.0.0.1:8000",
    help="Backend base URL.  Default: http://127.0.0.1:8000",
)
args = parser.parse_args()

ENDPOINT = (
    f"{args.url.rstrip('/')}/api/ai/track"
    f"?conf={args.conf}&max_frames={args.max_frames}"
)

# ── Synthetic video generator ─────────────────────────────────────────────────
SYNTH_PATH = Path(__file__).parent / "_test_synth.mp4"


def generate_synthetic_video(path: Path) -> None:
    """Create a short MP4 with moving coloured rectangles using OpenCV.

    This gives the tracker something real to follow without needing a download.
    Generates 90 frames at 15 fps (6 seconds).
    """
    try:
        import cv2
        import numpy as np
    except ImportError:
        print("[error] OpenCV / NumPy not installed.  Provide a real video path instead.")
        sys.exit(1)

    width, height, fps, n_frames = 640, 480, 15, 90
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(path), fourcc, fps, (width, height))

    if not writer.isOpened():
        print(f"[error] Could not create synthetic video at {path}")
        sys.exit(1)

    print(f"[info] Generating synthetic video ({n_frames} frames) …")

    # Two rectangles moving across the frame
    rects = [
        {"x": 50,  "y": 100, "dx": 4,  "dy": 2,  "color": (0, 200, 0),   "label": "rect-A"},
        {"x": 400, "y": 300, "dx": -3, "dy": -1, "color": (0, 100, 255), "label": "rect-B"},
    ]

    for _ in range(n_frames):
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        for r in rects:
            x1, y1 = int(r["x"]), int(r["y"])
            x2, y2 = x1 + 80, y1 + 120
            cv2.rectangle(frame, (x1, y1), (x2, y2), r["color"], -1)
            # Bounce off edges
            if x1 <= 0 or x2 >= width:
                r["dx"] *= -1
            if y1 <= 0 or y2 >= height:
                r["dy"] *= -1
            r["x"] += r["dx"]
            r["y"] += r["dy"]
        writer.write(frame)

    writer.release()
    print(f"[info] Synthetic video saved: {path}  ({path.stat().st_size // 1024} KB)")


# ── Resolve video path ────────────────────────────────────────────────────────
if args.video:
    video_path = Path(args.video)
    if not video_path.exists():
        print(f"[error] File not found: {video_path}")
        sys.exit(1)
else:
    generate_synthetic_video(SYNTH_PATH)
    video_path = SYNTH_PATH

# ── Send request ──────────────────────────────────────────────────────────────
print(f"\n[test] POST {ENDPOINT}")
print(f"[test] Video      : {video_path}  ({video_path.stat().st_size // 1024} KB)")
print(f"[test] conf       : {args.conf}")
print(f"[test] max_frames : {args.max_frames}  (0 = all)\n")

boundary = "----TrackBoundary7MA4YWxkTrZu0gW"
video_bytes = video_path.read_bytes()
filename = video_path.name

body = (
    f"--{boundary}\r\n"
    f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
    f"Content-Type: video/mp4\r\n"
    f"\r\n"
).encode() + video_bytes + f"\r\n--{boundary}--\r\n".encode()

try:
    req = urllib.request.Request(
        ENDPOINT,
        data=body,
        method="POST",
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    with urllib.request.urlopen(req, timeout=300) as resp:
        result = json.loads(resp.read())

except urllib.error.HTTPError as exc:
    body_err = exc.read().decode(errors="replace")
    print(f"[FAILED] HTTP {exc.code}: {body_err}")
    sys.exit(1)
except Exception as exc:  # noqa: BLE001
    print(f"[FAILED] {exc}")
    print("[hint] Is the backend running?  Start it with: uvicorn app.main:app --reload")
    sys.exit(1)

# ── Pretty-print result ───────────────────────────────────────────────────────
print("=" * 65)
print(f"  Model            : {result.get('model_name', 'N/A')}")
print(f"  Tracker          : {result.get('tracker', 'N/A')}")
print(f"  File             : {result['filename']}")
print(f"  Frames in video  : {result['total_frames_in_video']}")
print(f"  Frames processed : {result['total_frames_processed']}")
print(f"  Unique tracks    : {len(result['tracks'])}")
print(f"  Total time       : {result['total_processing_time_ms']:.0f} ms")
print(f"  Avg/frame        : {result['avg_frame_time_ms']:.1f} ms")
print(f"  Est. FPS         : {result['estimated_fps']}")
print("=" * 65)

if result["tracks"]:
    print(f"\n  {'ID':>4}  {'Class':<14}  {'First':>6}  {'Last':>6}  {'Seen':>6}  {'Center (last)'}")
    print("  " + "-" * 62)
    for t in result["tracks"]:
        print(
            f"  {t['track_id']:>4}  {t['class_name']:<14}  "
            f"{t['first_seen_frame']:>6}  {t['last_seen_frame']:>6}  "
            f"{t['frames_seen']:>6}  "
            f"({t['latest_center_x']:.0f}, {t['latest_center_y']:.0f})"
        )
else:
    print("\n  [no tracks found — try a lower --conf or a video with visible objects]")

print()
print("[raw JSON]")
print(json.dumps(result, indent=2))
