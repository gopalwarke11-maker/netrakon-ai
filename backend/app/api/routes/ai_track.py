"""AI tracking route — POST /api/ai/track.

Accepts an uploaded video file, processes it frame-by-frame through
YOLO + ByteTrack, and returns a structured tracking summary.

This is a development/testing endpoint.  Live RTSP / WebSocket streaming
is NOT implemented here — it belongs to Phase 5+.
"""

from __future__ import annotations

import logging
import tempfile
import time
from pathlib import Path

import cv2
from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status

from app.ai import model_manager
from app.ai.schemas import TrackResponse
from app.ai.tracker import TrackSession
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["AI Tracking"])

_ALLOWED_VIDEO_TYPES = {
    "video/mp4",
    "video/mpeg",
    "video/x-msvideo",       # .avi
    "video/quicktime",        # .mov
    "video/x-matroska",       # .mkv
    "video/webm",
    "application/octet-stream",  # generic binary — let OpenCV decide
}


@router.post(
    "/track",
    response_model=TrackResponse,
    summary="Run YOLO + ByteTrack object tracking on an uploaded video",
    description=(
        "Upload a video file (MP4 / AVI / MOV / MKV) and receive a structured "
        "tracking summary.  Each detected object is assigned a **persistent Track ID** "
        "across frames using ByteTrack.\n\n"
        "The response includes per-track summaries (first/last seen, frame count, "
        "latest position) and overall performance metrics.\n\n"
        "**Note — this endpoint processes the entire video synchronously.  "
        "Long videos will take proportionally longer.  "
        "Live RTSP / WebSocket streaming is planned for Phase 5.**"
    ),
)
async def track_objects(
    file: UploadFile = File(
        ...,
        description="Video file to run YOLO + ByteTrack tracking on (MP4 / AVI / MOV / MKV).",
    ),
    conf: float = Query(
        default=0.25,
        ge=0.01,
        le=1.0,
        description="Minimum detection confidence threshold [0.01 – 1.0].  Default: 0.25.",
    ),
    max_frames: int = Query(
        default=0,
        ge=0,
        description=(
            "Maximum number of frames to process.  0 = process all frames.  "
            "Useful for quick validation of long videos."
        ),
    ),
    camera_id: str | None = Query(
        default=None,
        description="Optional camera ID (e.g. 'CAM-01') to evaluate against virtual security boundaries.",
    ),
) -> TrackResponse:

    """Run ByteTrack tracking on the uploaded video and return a summary.

    Raises:
        HTTP 400: Empty file, oversized file, or unreadable video.
        HTTP 503: YOLO model not loaded.
        HTTP 500: Unexpected tracking error.
    """
    # ── Guard: model must be ready / loadable ──────────────────────────────────
    try:
        model_manager.get_model()
    except Exception as exc:
        logger.error("Tracking requested but YOLO model failed to load: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI model is not available. The YOLO model failed to initialize — check server logs.",
        ) from exc

    # ── Validate content type (relaxed — let OpenCV be the final judge) ──────
    content_type = (file.content_type or "").lower()
    if content_type and content_type not in _ALLOWED_VIDEO_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Unsupported content type: '{content_type}'.  "
                "Please upload a video file (MP4, AVI, MOV, MKV)."
            ),
        )

    # ── Read file bytes ───────────────────────────────────────────────────────
    max_bytes = settings.track_max_video_size_mb * 1024 * 1024
    try:
        video_bytes = await file.read()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to read uploaded video: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not read the uploaded file.",
        ) from exc

    if not video_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    if len(video_bytes) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"File too large.  Maximum allowed size is "
                f"{settings.track_max_video_size_mb} MB."
            ),
        )

    filename = file.filename or "uploaded_video"

    # ── Save to temp file (OpenCV needs a real path) ─────────────────────────
    suffix = Path(filename).suffix or ".mp4"
    tmp_path: str | None = None

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(video_bytes)
            tmp_path = tmp.name

        # ── Open video with OpenCV ────────────────────────────────────────────
        cap = cv2.VideoCapture(tmp_path)
        if not cap.isOpened():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Could not open the uploaded file as a video.  "
                    "Ensure it is a valid MP4, AVI, MOV, or MKV file."
                ),
            )

        try:
            total_frames_in_video = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps_reported = cap.get(cv2.CAP_PROP_FPS) or 25.0

            logger.info(
                "Tracking '%s': %d frames reported, %.1f fps",
                filename,
                total_frames_in_video,
                fps_reported,
            )

            # ── Run tracking session ──────────────────────────────────────────
            session = TrackSession(conf=conf, session_id=filename, camera_id=camera_id)
            frame_number = 0
            frame_times: list[float] = []
            wall_t0 = time.perf_counter()

            while True:
                ret, frame = cap.read()
                if not ret:
                    break  # end of video

                frame_number += 1
                timestamp_ms = cap.get(cv2.CAP_PROP_POS_MSEC)

                try:
                    track_frame = session.process_frame(
                        frame=frame,
                        frame_number=frame_number,
                        timestamp_ms=timestamp_ms,
                    )
                    frame_times.append(track_frame.processing_time_ms)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Frame %d failed, skipping: %s", frame_number, exc)
                    continue

                if max_frames and frame_number >= max_frames:
                    logger.info("Reached max_frames=%d, stopping early.", max_frames)
                    break

            total_wall_ms = (time.perf_counter() - wall_t0) * 1000
            session.close()

        finally:
            cap.release()

        # ── Build response ────────────────────────────────────────────────────
        if not frame_times:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No frames could be processed from the video.  The file may be corrupted or unsupported.",
            )

        avg_ms = sum(frame_times) / len(frame_times)
        estimated_fps = round(1000.0 / avg_ms, 2) if avg_ms > 0 else 0.0

        logger.info(
            "Tracking complete for '%s': %d frames, %d tracks, %d intrusions, %.0f ms total",
            filename,
            frame_number,
            len(session.history),
            len(session.intrusions),
            total_wall_ms,
        )

        return TrackResponse(
            filename=filename,
            total_frames_in_video=total_frames_in_video,
            total_frames_processed=frame_number,
            tracks=session.history.get_summary(),
            total_processing_time_ms=round(total_wall_ms, 2),
            avg_frame_time_ms=round(avg_ms, 2),
            estimated_fps=estimated_fps,
            model_name=settings.yolo_model_name,
            tracker=settings.yolo_tracker.replace(".yaml", ""),
            intrusions=[ev.model_dump() for ev in session.intrusions],
        )


    except HTTPException:
        raise  # re-raise controlled errors unchanged

    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected tracking error for '%s': %s", filename, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during tracking.  Check server logs.",
        ) from exc

    finally:
        # Always clean up the temp file
        if tmp_path:
            try:
                Path(tmp_path).unlink(missing_ok=True)
            except Exception:  # noqa: BLE001
                pass
