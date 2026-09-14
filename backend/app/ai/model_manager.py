"""YOLO model manager — loads the model once and keeps it in memory.

Call ``load_model()`` once during application startup (lifespan hook).
All subsequent calls to ``get_model()`` return the cached instance
without touching disk or network again.
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

from app.core.config import settings

if TYPE_CHECKING:
    from ultralytics import YOLO  # type: ignore[import-untyped]

logger = logging.getLogger(__name__)

_model: "YOLO | None" = None


def load_model() -> None:
    """Load the configured YOLO model into memory.

    Reads ``settings.yolo_model_name`` (e.g. ``"yolov8n.pt"``).  Ultralytics
    will download the model weights to its local cache the first time, then
    reuse them on subsequent runs.

    Raises:
        RuntimeError: If the model cannot be loaded for any reason.
    """
    global _model  # noqa: PLW0603

    model_name = settings.yolo_model_name
    logger.info("Loading YOLO model: %s", model_name)
    t0 = time.perf_counter()

    try:
        from ultralytics import YOLO  # noqa: PLC0415 (lazy import — keeps startup fast if package missing)

        _model = YOLO(model_name)

        # Run a tiny warm-up inference so the first real request isn't slow.
        import numpy as np  # noqa: PLC0415

        dummy = np.zeros((64, 64, 3), dtype=np.uint8)
        _model.predict(source=dummy, conf=0.25, verbose=False)

    except Exception as exc:  # noqa: BLE001
        _model = None
        raise RuntimeError(f"Failed to load YOLO model '{model_name}': {exc}") from exc

    elapsed_ms = (time.perf_counter() - t0) * 1000

    # Log device info (CPU vs CUDA)
    try:
        device = str(_model.device)
    except Exception:  # noqa: BLE001
        device = "unknown"

    logger.info(
        "YOLO model '%s' loaded successfully in %.0f ms  (device: %s)",
        model_name,
        elapsed_ms,
        device,
    )


def create_model_instance() -> "YOLO":
    """Create an isolated YOLO instance using the configured model weights.

    The shared startup model remains the default for existing API routes. Camera
    processors use this factory so Ultralytics tracker state is not interleaved
    between independent camera streams.
    """
    from ultralytics import YOLO  # noqa: PLC0415

    return YOLO(settings.yolo_model_name)


def get_model() -> "YOLO":
    """Return the cached YOLO model.

    Raises:
        RuntimeError: If ``load_model()`` has not been called yet or failed.
    """
    if _model is None:
        raise RuntimeError(
            "YOLO model is not loaded.  "
            "Ensure load_model() was called during application startup."
        )
    return _model


def is_model_loaded() -> bool:
    """Return ``True`` if the model is ready for inference."""
    return _model is not None
