"""YOLO model manager — loads the model once and keeps it in memory.

Call ``load_model()`` once during application startup (lifespan hook).
All subsequent calls to ``get_model()`` return the cached instance
without touching disk or network again.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import TYPE_CHECKING

from app.core.config import settings

if TYPE_CHECKING:
    from ultralytics import YOLO  # type: ignore[import-untyped]

logger = logging.getLogger(__name__)

_model: "YOLO | None" = None
_model_lock = threading.Lock()


def load_model() -> None:
    """Load the configured YOLO model into memory lazily.

    Reads ``settings.yolo_model_name`` (e.g. ``"yolov8n.pt"``). Ultralytics
    will download or read local model weights, then cache the singleton instance.

    Raises:
        RuntimeError: If the model cannot be loaded for any reason.
    """
    global _model  # noqa: PLW0603

    with _model_lock:
        if _model is not None:
            return

        model_name = settings.yolo_model_name
        logger.info("[YOLO Lazy Load] Initializing YOLO model weights: %s", model_name)
        t0 = time.perf_counter()

        try:
            from ultralytics import YOLO  # noqa: PLC0415 (lazy import — keeps startup fast)

            instance = YOLO(model_name)

            # Run a tiny warm-up inference so the first real request isn't slow.
            import numpy as np  # noqa: PLC0415

            dummy = np.zeros((64, 64, 3), dtype=np.uint8)
            instance.predict(source=dummy, conf=0.25, verbose=False)
            _model = instance

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
            "[YOLO Lazy Load] Model '%s' loaded successfully in %.0f ms (device: %s)",
            model_name,
            elapsed_ms,
            device,
        )


def create_model_instance() -> "YOLO":
    """Return the shared single YOLO model instance.

    Previously created a duplicate model instance per camera. Now returns the
    cached single model to strictly prevent exceeding the 512 MB RAM limit.
    """
    logger.debug("[YOLO Manager] Reusing single YOLO model singleton for stream/session")
    return get_model()


def get_model() -> "YOLO":
    """Return the cached YOLO model, initializing lazily if not loaded yet."""
    if _model is None:
        load_model()
    if _model is None:
        raise RuntimeError("YOLO model failed to initialize.")
    return _model


def is_model_loaded() -> bool:
    """Return ``True`` if the model is currently loaded in memory."""
    return _model is not None

