"""ByteTrack-powered object tracking session.

A ``TrackSession`` wraps the shared YOLO model and processes video frames
one at a time, maintaining persistent Track IDs across frames via
Ultralytics' ``persist=True`` flag.

Design principle
----------------
The model is loaded once at startup (by ``model_manager``).  Calling
``model.track(..., persist=True)`` on the same model object between frames
causes Ultralytics to keep the ByteTrack state alive internally — the same
physical object receives the same Track ID as long as the tracker can match it.

This is the correct session-oriented approach.  Do NOT create a new model
instance per frame or per session.
"""

from __future__ import annotations

import logging
import time
from typing import Any

import cv2
import numpy as np

from app.ai.model_manager import get_model
from app.ai.schemas import BoundingBoxAI, TrackFrame, TrackedObject
from app.ai.track_history import TrackHistory
from app.core.config import settings

logger = logging.getLogger(__name__)


class TrackSession:
    """A stateful tracking session that processes frames sequentially.

    Args:
        conf: Minimum detection confidence threshold.
        session_id: Optional label used for logging (e.g. video filename).
        position_history_limit: Max positions stored per track in history.
    """

    def __init__(
        self,
        conf: float | None = None,
        session_id: str = "session",
        position_history_limit: int | None = None,
        camera_id: str | None = None,
        model: Any | None = None,
    ) -> None:
        self._conf = conf if conf is not None else settings.track_conf_threshold
        self._tracker = settings.yolo_tracker
        self._session_id = session_id
        self._camera_id = camera_id
        self._model = model
        self._intrusions: list = []
        self._history = TrackHistory(
            position_history_limit=(
                position_history_limit
                if position_history_limit is not None
                else settings.track_position_history_limit
            )
        )
        logger.info(
            "TrackSession '%s' created  (conf=%.2f, tracker=%s, camera_id=%s)",
            session_id,
            self._conf,
            self._tracker,
            self._camera_id,
        )


    # ── Public API ────────────────────────────────────────────────────────────

    def process_frame(
        self,
        frame: np.ndarray,
        frame_number: int,
        timestamp_ms: float = 0.0,
    ) -> TrackFrame:
        """Run YOLO + ByteTrack on one BGR frame.

        Args:
            frame: OpenCV BGR image array (H, W, 3).
            frame_number: 1-based frame index (used for history).
            timestamp_ms: Position of the frame in the video (milliseconds).

        Returns:
            A :class:`TrackFrame` with all tracked objects and timing info.

        Raises:
            RuntimeError: If the YOLO model is not loaded.
            ValueError: If ``frame`` is empty/invalid.
        """
        if frame is None or frame.size == 0:
            raise ValueError("Received an empty or invalid frame.")

        image_height, image_width = frame.shape[:2]
        model = self._model or get_model()

        t0 = time.perf_counter()

        # persist=True is the critical flag — keeps ByteTrack state between calls
        results = model.track(
            source=frame,
            conf=self._conf,
            tracker=self._tracker,
            persist=True,
            verbose=False,
        )

        processing_time_ms = (time.perf_counter() - t0) * 1000

        tracked_objects: list[TrackedObject] = []

        if results:
            result = results[0]
            boxes = result.boxes

            if boxes is not None and boxes.id is not None:
                # boxes.id is None when the tracker hasn't assigned IDs yet
                ids = boxes.id.int().tolist()
                xyxys = boxes.xyxy.tolist()
                confs = boxes.conf.tolist()
                classes = boxes.cls.int().tolist()

                for track_id, xyxy, conf, cls_id in zip(ids, xyxys, confs, classes):
                    x1, y1, x2, y2 = xyxy
                    cx = (x1 + x2) / 2.0
                    cy = (y1 + y2) / 2.0
                    cls_name = model.names.get(cls_id, str(cls_id))

                    bbox = BoundingBoxAI(
                        x1=round(x1, 2),
                        y1=round(y1, 2),
                        x2=round(x2, 2),
                        y2=round(y2, 2),
                        width=round(x2 - x1, 2),
                        height=round(y2 - y1, 2),
                    )

                    tracked_objects.append(
                        TrackedObject(
                            track_id=track_id,
                            class_id=cls_id,
                            class_name=cls_name,
                            confidence=round(float(conf), 4),
                            bounding_box=bbox,
                            center_x=round(cx, 2),
                            center_y=round(cy, 2),
                            frame_number=frame_number,
                            image_width=image_width,
                            image_height=image_height,
                        )
                    )

                    # Update persistent history
                    self._history.update(
                        track_id=track_id,
                        class_name=cls_name,
                        frame_number=frame_number,
                        center_x=cx,
                        center_y=cy,
                        bbox=bbox,
                    )

        # Evaluate virtual boundaries if camera_id is configured
        if self._camera_id and tracked_objects:
            try:
                from app.services.boundary_service import boundary_service
                from app.ai.intrusion_detector import intrusion_detector
                active_boundaries = boundary_service.get_by_camera(self._camera_id)
                if active_boundaries:
                    new_events = intrusion_detector.process_tracks(
                        camera_id=self._camera_id,
                        frame_number=frame_number,
                        tracked_objects=tracked_objects,
                        boundaries=active_boundaries,
                    )
                    self._intrusions.extend(new_events)
            except Exception as exc:  # noqa: BLE001
                logger.warning("[%s] Intrusion evaluation error on frame %d: %s", self._session_id, frame_number, exc)

        logger.debug(
            "[%s] Frame %d — %d tracked object(s) in %.1f ms",
            self._session_id,
            frame_number,
            len(tracked_objects),
            processing_time_ms,
        )

        return TrackFrame(
            frame_number=frame_number,
            timestamp_ms=round(timestamp_ms, 2),
            image_width=image_width,
            image_height=image_height,
            processing_time_ms=round(processing_time_ms, 2),
            objects=tracked_objects,
        )

    @property
    def history(self) -> TrackHistory:
        """Access the accumulated track history for this session."""
        return self._history

    @property
    def intrusions(self) -> list:
        """Access the accumulated intrusion events for this session."""
        return self._intrusions

    def close(self) -> None:
        """Release session resources (reserved for future cleanup)."""
        if self._camera_id:
            from app.ai.intrusion_detector import intrusion_detector
            intrusion_detector.clear_camera(self._camera_id)
        logger.info(

            "TrackSession '%s' closed.  Total unique tracks: %d",
            self._session_id,
            len(self._history),
        )
