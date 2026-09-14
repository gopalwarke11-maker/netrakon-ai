"""AI detection route — POST /api/ai/detect.

Accepts an uploaded image file and returns structured YOLO detection results.
This is a development/testing endpoint; real CCTV/RTSP integration is Phase 4+.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status

from app.ai import detector, model_manager
from app.ai.schemas import DetectResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["AI Detection"])

_MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB hard limit


@router.post(
    "/detect",
    response_model=DetectResponse,
    summary="Run YOLO object detection on an uploaded image",
    description=(
        "Upload any image (JPEG / PNG / BMP / WEBP) and receive structured YOLO "
        "detection results including class labels, confidence scores, and bounding "
        "boxes in absolute pixel coordinates (x1, y1, x2, y2).\n\n"
        "**This endpoint is for development and testing.  "
        "Live RTSP / camera stream integration is planned for Phase 4.**"
    ),
)
async def detect_objects(
    file: UploadFile = File(
        ...,
        description="Image file to run YOLO inference on (JPEG / PNG / BMP / WEBP).",
    ),
    conf: float = Query(
        default=0.25,
        ge=0.01,
        le=1.0,
        description="Minimum confidence threshold [0.01 – 1.0].  Default: 0.25.",
    ),
) -> DetectResponse:
    """Run YOLO inference on the uploaded image.

    Returns:
        DetectResponse with detections, image dimensions, and processing time.

    Raises:
        HTTP 400: Missing file, oversized file, or non-image content type.
        HTTP 503: YOLO model not loaded (startup failure).
        HTTP 500: Unexpected inference error.
    """
    # ── Guard: model must be loaded ──────────────────────────────────────────
    if not model_manager.is_model_loaded():
        logger.error("AI detection requested but YOLO model is not loaded")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "AI model is not available.  "
                "The YOLO model may have failed to load at startup — check server logs."
            ),
        )

    # ── Validate content type ─────────────────────────────────────────────────
    allowed_types = {
        "image/jpeg",
        "image/jpg",
        "image/png",
        "image/bmp",
        "image/webp",
        "image/tiff",
        "image/x-bmp",
    }
    content_type = (file.content_type or "").lower()
    if content_type and content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Unsupported content type: '{content_type}'.  "
                "Please upload a JPEG, PNG, BMP, or WEBP image."
            ),
        )

    # ── Read file bytes ───────────────────────────────────────────────────────
    try:
        image_bytes = await file.read()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to read uploaded file: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not read the uploaded file.",
        ) from exc

    if not image_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    if len(image_bytes) > _MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large.  Maximum allowed size is {_MAX_FILE_SIZE // (1024 * 1024)} MB.",
        )

    # ── Run inference ────────────────────────────────────────────────────────
    try:
        result = detector.run_detection(image_bytes, conf_threshold=conf)
    except ValueError as exc:
        # Invalid image data (could not decode)
        logger.warning("Invalid image uploaded: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except RuntimeError as exc:
        # Model not ready
        logger.error("Model runtime error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except Exception as exc:  # noqa: BLE001
        # Unexpected inference failure — log full traceback, return generic message
        logger.exception("Unexpected inference error for file '%s': %s", file.filename, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during inference.  Check server logs.",
        ) from exc

    return result
