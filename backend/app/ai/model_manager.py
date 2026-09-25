"""ONNX model manager — loads the ONNX session once and keeps it in memory.

Call ``load_model()`` once during application startup (lifespan hook).
All subsequent calls to ``get_model()`` return the cached ONNX session instance
without touching disk again.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from app.ai.onnx_engine import get_onnx_session
from app.core.config import settings

logger = logging.getLogger(__name__)


def load_model() -> None:
    """Load the configured ONNX model into memory lazily.

    Reads ``settings.yolo_model_name`` (e.g. ``"yolov8n.onnx"``).

    Raises:
        RuntimeError: If the model cannot be loaded for any reason.
    """
    model_name = settings.yolo_model_name
    logger.info("[ONNX Lazy Load] Initializing ONNX model session: %s", model_name)
    t0 = time.perf_counter()

    try:
        session = get_onnx_session(model_name)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        logger.info(
            "[ONNX Lazy Load] Model '%s' loaded successfully in %.0f ms (provider: CPUExecutionProvider)",
            model_name,
            elapsed_ms,
        )
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"Failed to load ONNX model '{model_name}': {exc}") from exc


def create_model_instance() -> Any:
    """Return the shared single ONNX model session."""
    logger.debug("[ONNX Manager] Reusing single ONNX session singleton")
    return get_model()


def get_model() -> Any:
    """Return the cached ONNX session, initializing lazily if not loaded yet."""
    return get_onnx_session(settings.yolo_model_name)


def is_model_loaded() -> bool:
    """Return ``True`` if the ONNX session is currently loaded in memory."""
    try:
        session = get_onnx_session(settings.yolo_model_name)
        return session is not None
    except Exception:  # noqa: BLE001
        return False
