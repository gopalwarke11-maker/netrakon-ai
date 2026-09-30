"""Demo video directory and path resolution module.

Provides application-relative path resolution for fixed demo videos (e.g., camera_1.mp4 and camera_2.mp4)
stored in backend/demo_videos/, robust against arbitrary server working directories.
"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Base directory for the backend package (parent of app/)
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
DEMO_VIDEOS_DIR = (BACKEND_DIR / "demo_videos").resolve()
FALLBACK_VIDEOS_DIR = (BACKEND_DIR / "videos").resolve()

ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".webm", ".mov", ".avi", ".mkv"}


def get_backend_dir() -> Path:
    """Return the absolute path to the backend root directory."""
    return BACKEND_DIR


def get_demo_videos_dir() -> Path:
    """Return the absolute path to backend/demo_videos/."""
    DEMO_VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
    return DEMO_VIDEOS_DIR


def get_demo_video_path(filename: str) -> Path:
    """Return the absolute path to a named video in demo_videos/.

    Args:
        filename: Name of the video file (e.g. 'camera_1.mp4').

    Returns:
        Absolute Path to the target video file.
    """
    clean_name = Path(filename).name
    target = DEMO_VIDEOS_DIR / clean_name
    return target


def is_path_safe_and_allowed(target_path: Path) -> bool:
    """Check whether target_path is inside DEMO_VIDEOS_DIR or FALLBACK_VIDEOS_DIR and has a valid video extension."""
    try:
        resolved = target_path.resolve()
    except (ValueError, RuntimeError, OSError):
        return False

    if resolved.suffix.lower() not in ALLOWED_VIDEO_EXTENSIONS:
        return False

    in_demo = False
    in_fallback = False

    try:
        in_demo = resolved.is_relative_to(DEMO_VIDEOS_DIR)
    except AttributeError:
        # Fallback for Python < 3.9 if needed, though 3.9+ is standard
        try:
            resolved.relative_to(DEMO_VIDEOS_DIR)
            in_demo = True
        except ValueError:
            in_demo = False

    try:
        in_fallback = resolved.is_relative_to(FALLBACK_VIDEOS_DIR)
    except AttributeError:
        try:
            resolved.relative_to(FALLBACK_VIDEOS_DIR)
            in_fallback = True
        except ValueError:
            in_fallback = False

    return in_demo or in_fallback


def resolve_video_file_path(source: str | Path | None) -> Path | None:
    """Resolve a raw source string or key to an absolute filesystem Path if valid.

    Handles:
    - Bare filenames: 'camera_1.mp4' -> backend/demo_videos/camera_1.mp4
    - Relative paths: 'demo_videos/camera_1.mp4', 'backend/demo_videos/camera_1.mp4'
    - Absolute paths pointing inside demo_videos or videos directory

    Returns:
        Resolved absolute Path if valid, safe, and exists on disk; otherwise None.
    """
    if not source:
        return None

    raw_str = str(source).strip()

    # Remote URLs (http, rtsp) are not local files
    if raw_str.lower().startswith(("http://", "https://", "rtsp://", "rtsps://")):
        return None

    candidate_paths: list[Path] = []

    p = Path(raw_str)
    if p.is_absolute():
        candidate_paths.append(p)
    else:
        # Try relative to BACKEND_DIR
        candidate_paths.append(BACKEND_DIR / p)
        # Try direct in DEMO_VIDEOS_DIR if bare filename
        candidate_paths.append(DEMO_VIDEOS_DIR / p.name)
        # Try direct in FALLBACK_VIDEOS_DIR
        candidate_paths.append(FALLBACK_VIDEOS_DIR / p.name)

    for cand in candidate_paths:
        if cand.is_file() and is_path_safe_and_allowed(cand):
            return cand.resolve()

    return None
