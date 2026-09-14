"""NETRAKON AI — Phase 3 detection test utility.

Usage
-----
Run with the backend server already started (``uvicorn app.main:app --reload``):

    # Download a test image automatically and run detection
    python test_detection.py

    # Use your own local image
    python test_detection.py path/to/image.jpg

    # Override confidence threshold
    python test_detection.py path/to/image.jpg --conf 0.4

    # Point at a different backend URL
    python test_detection.py --url http://127.0.0.1:8000
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path

# ── CLI args ───────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser(description="Test NETRAKON AI YOLO detection endpoint.")
parser.add_argument(
    "image",
    nargs="?",
    help="Path to a local image file.  Omit to auto-download a sample image.",
)
parser.add_argument(
    "--conf",
    type=float,
    default=0.25,
    help="Confidence threshold [0.01–1.0].  Default: 0.25",
)
parser.add_argument(
    "--url",
    default="http://127.0.0.1:8000",
    help="Backend base URL.  Default: http://127.0.0.1:8000",
)
args = parser.parse_args()

ENDPOINT = f"{args.url.rstrip('/')}/api/ai/detect?conf={args.conf}"

# ── Sample image (CC0 — Pexels, no sign-in required) ─────────────────────────
SAMPLE_IMAGE_URL = (
    "https://images.pexels.com/photos/1427541/pexels-photo-1427541.jpeg"
    "?auto=compress&cs=tinysrgb&w=640"
)
SAMPLE_IMAGE_PATH = Path(__file__).parent / "_test_sample.jpg"


def ensure_sample_image() -> Path:
    """Download the sample image if it does not already exist."""
    if SAMPLE_IMAGE_PATH.exists():
        print(f"[info] Using cached sample image: {SAMPLE_IMAGE_PATH}")
        return SAMPLE_IMAGE_PATH

    print(f"[info] Downloading sample image from Pexels …")
    try:
        headers = {"User-Agent": "netrakon-test/1.0"}
        req = urllib.request.Request(SAMPLE_IMAGE_URL, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
        SAMPLE_IMAGE_PATH.write_bytes(data)
        print(f"[info] Saved to {SAMPLE_IMAGE_PATH} ({len(data) // 1024} KB)")
        return SAMPLE_IMAGE_PATH
    except Exception as exc:  # noqa: BLE001
        print(f"[error] Could not download sample image: {exc}")
        print(
            "\n[hint] Provide your own image path as a CLI argument:\n"
            "       python test_detection.py path/to/image.jpg\n"
        )
        sys.exit(1)


# ── Resolve image path ────────────────────────────────────────────────────────
if args.image:
    image_path = Path(args.image)
    if not image_path.exists():
        print(f"[error] File not found: {image_path}")
        sys.exit(1)
else:
    image_path = ensure_sample_image()

# ── Send request ──────────────────────────────────────────────────────────────
print(f"\n[test] POST {ENDPOINT}")
print(f"[test] Image : {image_path}  ({image_path.stat().st_size // 1024} KB)")
print(f"[test] conf  : {args.conf}\n")

try:
    import urllib.parse

    boundary = "----FormBoundary7MA4YWxkTrZu0gW"
    image_bytes = image_path.read_bytes()
    filename = image_path.name

    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f"Content-Type: image/jpeg\r\n"
        f"\r\n"
    ).encode() + image_bytes + f"\r\n--{boundary}--\r\n".encode()

    req = urllib.request.Request(
        ENDPOINT,
        data=body,
        method="POST",
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )

    with urllib.request.urlopen(req, timeout=120) as resp:
        raw = resp.read()
        result = json.loads(raw)

except urllib.error.HTTPError as exc:
    body = exc.read().decode(errors="replace")
    print(f"[FAILED] HTTP {exc.code}: {body}")
    sys.exit(1)
except Exception as exc:  # noqa: BLE001
    print(f"[FAILED] {exc}")
    print("[hint] Is the backend running?  Start it with: uvicorn app.main:app --reload")
    sys.exit(1)

# ── Pretty-print result ───────────────────────────────────────────────────────
print("=" * 60)
print(f"  Model           : {result.get('model_name', 'N/A')}")
print(f"  Image size      : {result['image_width']} × {result['image_height']} px")
print(f"  Processing time : {result['processing_time_ms']} ms")
print(f"  Detections      : {len(result['detections'])}")
print("=" * 60)

if result["detections"]:
    print(f"  {'#':<4} {'Class':<16} {'Conf':>6}   {'BBox (x1,y1,x2,y2)'}")
    print("  " + "-" * 58)
    for i, det in enumerate(result["detections"], 1):
        bb = det["bounding_box"]
        print(
            f"  {i:<4} {det['class_name']:<16} {det['confidence']:>6.3f}"
            f"   ({bb['x1']:.0f},{bb['y1']:.0f},{bb['x2']:.0f},{bb['y2']:.0f})"
        )
else:
    print("  [no objects detected — try a lower --conf value or a different image]")

print()
print("[raw JSON]")
print(json.dumps(result, indent=2))
