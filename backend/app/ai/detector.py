"""YOLO inference logic — decodes an image and returns structured detections.

The public entry point is ``run_detection()``.  It accepts raw image bytes
(the content of any uploaded file), runs YOLO, and returns a ``DetectResponse``
Pydantic model.  Raw Ultralytics result objects never leave this module.
"""

from __future__ import annotations

import logging
import time

import cv2
import numpy as np

from app.ai.model_manager import get_model
from app.ai.onnx_engine import detect_objects
from app.ai.schemas import BoundingBoxAI, DetectResponse, DetectionResult
from app.ai.low_light import get_processor
from app.core.config import settings

logger = logging.getLogger(__name__)


def run_detection(
    image_bytes: bytes,
    conf_threshold: float | None = None,
    enhance_low_light: bool = True,
) -> DetectResponse:
    """Run YOLO inference on raw image bytes with optional low-light enhancement.

    Args:
        image_bytes: The binary content of an uploaded image file.
        conf_threshold: Minimum confidence score [0, 1].  Defaults to
            ``settings.yolo_conf_threshold``.
        enhance_low_light: If True and low-light is detected, apply CLAHE
            enhancement before YOLO inference. Defaults to True.

    Returns:
        A fully populated :class:`DetectResponse`.

    Raises:
        ValueError: If ``image_bytes`` cannot be decoded as an image.
        RuntimeError: If the YOLO model is not loaded.
    """
    if conf_threshold is None:
        conf_threshold = settings.yolo_conf_threshold

    # ── 1. Decode image ──────────────────────────────────────────────────────
    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)

    if frame is None:
        raise ValueError(
            "Could not decode the uploaded file as an image.  "
            "Supported formats: JPEG, PNG, BMP, TIFF, WEBP."
        )

    image_height, image_width = frame.shape[:2]
    logger.debug("Image decoded: %d×%d px", image_width, image_height)

    # ── 2. Low-light detection and optional enhancement ─────────────────────
    low_light_metadata = {}
    if settings.low_light_enabled and enhance_low_light:
        processor = get_processor()
        frame, low_light_metadata = processor.process_frame(
            frame, enable_enhancement=True
        )
        if low_light_metadata["enhancement_applied"]:
            logger.info(
                "Low-light enhancement applied: mean_luminance=%.2f (threshold=%.2f)",
                low_light_metadata["mean_luminance"],
                low_light_metadata["threshold"],
            )

    # ── 3. Run ONNX inference ─────────────────────────────────────────────────────
    onnx_dets, processing_time_ms = detect_objects(frame, conf_threshold=conf_threshold)

    # ── 4. Convert ONNX results → application schemas ────────────────────────────
    detections: list[DetectionResult] = []
    for det in onnx_dets:
        detections.append(
            DetectionResult(
                class_id=det.class_id,
                class_name=det.class_name,
                confidence=det.confidence,
                bounding_box=det.bounding_box,
            )
        )

    logger.info(
        "Inference complete: %d detection(s) in %.1f ms (conf≥%.2f, image %dx%d)",
        len(detections),
        processing_time_ms,
        conf_threshold,
        image_width,
        image_height,
    )

    return DetectResponse(
        detections=detections,
        image_width=image_width,
        image_height=image_height,
        processing_time_ms=round(processing_time_ms, 2),
        model_name=settings.yolo_model_name,
    )
