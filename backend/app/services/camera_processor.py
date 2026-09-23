"""Camera-scoped video processing and lifecycle management.

Each processor owns one source, one TrackSession, and one worker. The manager
keys processors by camera_id so numeric ByteTrack IDs cannot leak between
cameras at the application boundary.
"""

from __future__ import annotations

import logging
import threading
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import cv2
import numpy as np

from app.ai.low_light import get_processor
from app.ai.behavior_engine import behavior_engine
from app.ai.model_manager import get_model
from app.ai.tracker import TrackSession
from app.services.alert_websocket import alert_connection_manager
from app.services.behavior_service import behavior_service
from app.models.camera_processing import (
    CameraProcessingStatus,
    CameraRuntimeState,
    CameraRuntimeSummary,
    CameraSourceType,
)

logger = logging.getLogger(__name__)


class VideoSource(ABC):
    """Small OpenCV source contract used by file, RTSP, and device inputs."""

    source_type: CameraSourceType

    @abstractmethod
    def open(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def read(self) -> tuple[bool, np.ndarray | None]:
        raise NotImplementedError

    @abstractmethod
    def is_opened(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def release(self) -> None:
        raise NotImplementedError

    @property
    @abstractmethod
    def width(self) -> int:
        raise NotImplementedError

    @property
    @abstractmethod
    def height(self) -> int:
        raise NotImplementedError

    @property
    @abstractmethod
    def fps(self) -> float:
        raise NotImplementedError


class OpenCVVideoSource(VideoSource):
    """OpenCV-backed implementation for files, RTSP URLs, and devices."""

    def __init__(self, source: str | int, source_type: CameraSourceType) -> None:
        self.source = source
        self.source_type = source_type
        self._capture: cv2.VideoCapture | None = None

    def open(self) -> bool:
        self._capture = cv2.VideoCapture(self.source)
        return self.is_opened()

    def read(self) -> tuple[bool, np.ndarray | None]:
        if self._capture is None:
            return False, None
        ok, frame = self._capture.read()
        return ok, frame if ok else None

    def is_opened(self) -> bool:
        return self._capture is not None and self._capture.isOpened()

    def release(self) -> None:
        if self._capture is not None:
            self._capture.release()
            self._capture = None

    @property
    def width(self) -> int:
        return int(self._capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 0) if self._capture else 0

    @property
    def height(self) -> int:
        return int(self._capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0) if self._capture else 0

    @property
    def fps(self) -> float:
        return float(self._capture.get(cv2.CAP_PROP_FPS) or 0.0) if self._capture else 0.0


class FileVideoSource(OpenCVVideoSource):
    def __init__(self, source: str | int) -> None:
        super().__init__(source, "FILE")


class RTSPVideoSource(OpenCVVideoSource):
    def __init__(self, source: str | int) -> None:
        super().__init__(source, "RTSP")


class MJPEGVideoSource(OpenCVVideoSource):
    def __init__(self, source: str | int) -> None:
        super().__init__(source, "MJPEG")


class CameraDeviceSource(OpenCVVideoSource):
    def __init__(self, source: str | int) -> None:
        super().__init__(source, "DEVICE")


def infer_source_type(source: str | int, source_type: CameraSourceType | None = None) -> CameraSourceType:
    if source_type is not None:
        return source_type
    if isinstance(source, int) or (isinstance(source, str) and source.isdigit()):
        return "DEVICE"
    if isinstance(source, str) and source.lower().startswith(("rtsp://", "rtsps://")):
        return "RTSP"
    if isinstance(source, str) and source.lower().startswith(("http://", "https://")):
        return "MJPEG"
    return "FILE"


def create_video_source(source: str | int, source_type: CameraSourceType | None = None) -> VideoSource:
    resolved = infer_source_type(source, source_type)
    if resolved not in {"FILE", "RTSP", "MJPEG", "DEVICE"}:
        raise ValueError(f"Unsupported camera source type: {resolved}")
    if resolved == "RTSP":
        return RTSPVideoSource(source)
    if resolved == "MJPEG":
        return MJPEGVideoSource(source)
    if resolved == "DEVICE":
        return CameraDeviceSource(int(source) if isinstance(source, str) and source.isdigit() else source)
    return FileVideoSource(source)


class CameraProcessor:
    """Own and process one camera stream with isolated transient state."""

    def __init__(
        self,
        camera_id: str,
        source: str | int,
        source_type: CameraSourceType | None = None,
        loop_enabled: bool = False,
        source_factory: Callable[[str | int, CameraSourceType | None], VideoSource] = create_video_source,
        session_factory: Callable[..., TrackSession] = TrackSession,
        model_factory: Callable[[], Any] = get_model,
    ) -> None:
        self.camera_id = camera_id
        self.source_value = source
        self.source_type = infer_source_type(source, source_type)
        self.loop_enabled = loop_enabled
        self._source_factory = source_factory
        self._session_factory = session_factory
        self._model_factory = model_factory
        self._source: VideoSource | None = None
        self._session: TrackSession | None = None
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._lock = threading.RLock()
        self._status = CameraProcessingStatus(
            camera_id=camera_id,
            status="OFFLINE",
            source_type=self.source_type,
            loop_enabled=loop_enabled,
        )
        self._started_at: float | None = None
        self._persisted_behavior_keys: set[tuple[str, int, str, int]] = set()
        self._historical_tracks = []
        self._last_detections = []
        self._detection_class_counts: dict[str, int] = {}
        self._total_detections = 0
        self._confidence_total = 0.0
        self._latest_processed_jpeg: bytes | None = None
        self._network_retry_limit = 5
        self._network_retry_delay = 0.5

    @property
    def status(self) -> CameraProcessingStatus:
        with self._lock:
            return self._status.model_copy(deep=True)

    @property
    def session(self) -> TrackSession | None:
        return self._session

    @property
    def is_running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def start(self) -> CameraProcessingStatus:
        with self._lock:
            if self._thread and self._thread.is_alive():
                raise RuntimeError(f"Camera '{self.camera_id}' is already running.")
            logger.info("[CameraProcessor] Starting stream processing for camera '%s' (type: %s)", self.camera_id, self.source_type)
            self._set_status("CONNECTING", error=None)
            try:
                self._source = self._source_factory(self.source_value, self.source_type)
                opened = self._source.open()
                if not opened and self.source_type not in {"RTSP", "MJPEG"}:
                    raise RuntimeError("Camera source could not be opened.")
                self._session = self._session_factory(
                    session_id=self.camera_id,
                    camera_id=self.camera_id,
                    model=self._model_factory(),
                )
            except Exception as exc:  # noqa: BLE001
                self._release_resources()
                self._set_status("ERROR", error=str(exc))
                raise RuntimeError(f"Camera '{self.camera_id}' failed to start: {exc}") from exc
            self._stop_event.clear()
            self._started_at = time.perf_counter()
            self._persisted_behavior_keys.clear()
            self._historical_tracks = []
            self._last_detections = []
            self._detection_class_counts = {}
            self._total_detections = 0
            self._confidence_total = 0.0
            self._latest_processed_jpeg = None
            self._status = CameraProcessingStatus(
                camera_id=self.camera_id,
                status="ONLINE",
                source_type=self.source_type,
                resolution=self._resolution(),
                fps=self._source.fps,
                loop_enabled=self.loop_enabled,
            )
            if not opened:
                self._set_status("RECONNECTING", error="Camera network stream is unavailable.")
            self._thread = threading.Thread(target=self._run, name=f"camera-{self.camera_id}", daemon=True)
            self._thread.start()
            return self.status

    def set_loop_enabled(self, enabled: bool) -> None:
        with self._lock:
            if self._thread and self._thread.is_alive():
                raise RuntimeError("Loop mode can only be changed while the camera is stopped.")
            self.loop_enabled = enabled
            self._status = self._status.model_copy(update={"loop_enabled": enabled})

    def stop(self) -> CameraProcessingStatus:
        with self._lock:
            thread = self._thread
            self._stop_event.set()
        if thread and thread.is_alive() and thread is not threading.current_thread():
            thread.join(timeout=5.0)
        with self._lock:
            self._release_resources()
            self._last_detections = []
            self._status = self._status.model_copy(update={"active_tracks": 0})
            self._set_status("STOPPED", error=None)
            return self.status

    def restart(self) -> CameraProcessingStatus:
        self.stop()
        return self.start()

    def process_once(self, frame: np.ndarray) -> CameraProcessingStatus:
        """Process one frame synchronously; useful for tests and integrations."""
        with self._lock:
            if self._session is None:
                raise RuntimeError(f"Camera '{self.camera_id}' is not started.")
            session = self._session
            frame_number = self._status.frames_processed + 1
        enhanced_frame, _ = get_processor().process_frame(frame, enable_enhancement=True)
        tracked = session.process_frame(frame=enhanced_frame, frame_number=frame_number)
        self._analyze_behaviors()
        annotated = enhanced_frame.copy()
        for detection in tracked.objects:
            box = getattr(detection, "bounding_box", None)
            if box is None:
                continue
            top_left = (int(box.x1), int(box.y1))
            bottom_right = (int(box.x2), int(box.y2))
            class_name = getattr(detection, "class_name", "OBJECT")
            label = f"{class_name.upper()} {detection.confidence:.0%} | TRACK {detection.track_id}"
            cv2.rectangle(annotated, top_left, bottom_right, (0, 165, 255), 2)
            cv2.putText(
                annotated,
                label,
                (top_left[0], max(18, top_left[1] - 6)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (0, 165, 255),
                2,
            )
        encoded_ok, encoded = cv2.imencode(".jpg", annotated)
        with self._lock:
            self._record_frame(tracked.processing_time_ms, tracked.objects)
            if encoded_ok:
                self._latest_processed_jpeg = encoded.tobytes()
            return self.status

    def latest_processed_frame(self) -> bytes | None:
        with self._lock:
            return self._latest_processed_jpeg

    def summary(self) -> CameraRuntimeSummary:
        with self._lock:
            return CameraRuntimeSummary(
                camera_id=self.camera_id,
                status=self._status.status,
                source_type=self.source_type,
                current_detections=self._last_detections,
                historical_tracks=self._historical_tracks,
                detection_class_counts=self._detection_class_counts,
                total_detections=self._total_detections,
                average_confidence=(
                    self._confidence_total / self._total_detections
                    if self._total_detections
                    else None
                ),
                intrusions=[event.model_dump(mode="json") for event in getattr(self._session, "intrusions", [])]
                if self._session
                else [],
                last_frame_time=self._status.last_frame_time,
            )

    def _analyze_behaviors(self) -> None:
        """Analyze and persist new meaningful assessments for this camera only."""
        session = self._session
        if session is None:
            return
        intrusion_counts: dict[int, int] = {}
        for event in getattr(session, "intrusions", []):
            if event.camera_id == self.camera_id:
                intrusion_counts[event.track_id] = intrusion_counts.get(event.track_id, 0) + 1

        for track in getattr(session.history, "records", []):
            try:
                assessment = behavior_engine.analyze_track(
                    camera_id=self.camera_id,
                    track=track,
                    intrusion_count=intrusion_counts.get(track.track_id, 0),
                )
                if assessment is None or assessment.primary_behavior is None:
                    continue
                key = (self.camera_id, track.track_id, assessment.primary_behavior, assessment.behavior_score)
                if key in self._persisted_behavior_keys:
                    continue
                persisted = behavior_service.create_behavior(assessment)
                if persisted is None:
                    continue
                self._persisted_behavior_keys.add(key)
                if persisted.id == assessment.id:
                    alert_connection_manager.publish_behavior(persisted)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Camera '%s' behavior analysis failed for track %s: %s", self.camera_id, track.track_id, exc)

    def _run(self) -> None:
        try:
            while not self._stop_event.is_set():
                source = self._source
                if source is None:
                    break
                ok, frame = source.read()
                if not ok or frame is None:
                    if self.source_type in {"RTSP", "MJPEG"} and not self._stop_event.is_set():
                        with self._lock:
                            self._last_detections = []
                            self._latest_processed_jpeg = None
                            self._status = self._status.model_copy(update={"active_tracks": 0})
                            self._set_status("RECONNECTING", error="Camera network stream disconnected.")
                        source.release()
                        reconnected = False
                        for _ in range(self._network_retry_limit):
                            if self._stop_event.wait(self._network_retry_delay):
                                break
                            if source.open():
                                reconnected = True
                                with self._lock:
                                    self._set_status("ONLINE", error=None)
                                break
                        if reconnected:
                            continue
                        with self._lock:
                            self._set_status("ERROR", error="Camera network stream reconnect failed.")
                        break
                    if self.loop_enabled and self.source_type == "FILE" and not self._stop_event.is_set():
                        with self._lock:
                            self._last_detections = []
                            self._latest_processed_jpeg = None
                            self._status = self._status.model_copy(update={"active_tracks": 0})
                        source.release()
                        if source.open():
                            continue
                        with self._lock:
                            self._last_detections = []
                            self._status = self._status.model_copy(update={"active_tracks": 0})
                            self._set_status("ERROR", error="Camera file could not be reopened after EOF.")
                        break
                    with self._lock:
                        frames_processed = self._status.frames_processed
                        self._last_detections = []
                        self._latest_processed_jpeg = None
                        self._status = self._status.model_copy(update={"active_tracks": 0})
                        if frames_processed == 0:
                            self._set_status("ERROR", error="Camera source returned no frames.")
                    break
                self.process_once(frame)
            with self._lock:
                if not self._stop_event.is_set() and self._status.status != "ERROR":
                    self._set_status("STOPPED", error=None)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Camera '%s' processing failed", self.camera_id)
            with self._lock:
                self._last_detections = []
                self._status = self._status.model_copy(update={"active_tracks": 0})
                self._set_status("ERROR", error=str(exc))
        finally:
            with self._lock:
                self._release_source_only()

    def _record_frame(self, processing_ms: float, detections: list) -> None:
        now = datetime.now(timezone.utc)
        elapsed = max(time.perf_counter() - (self._started_at or time.perf_counter()), 0.001)
        self._status = self._status.model_copy(update={
            "status": "PROCESSING",
            "resolution": self._resolution(),
            "fps": self._source.fps if self._source else 0.0,
            "last_frame_time": now,
            "frames_processed": self._status.frames_processed + 1,
            "detections_count": self._status.detections_count + len(detections),
            "active_tracks": len({d.track_id for d in detections}),
            "processing_fps": round(self._status.frames_processed / elapsed, 2),
        })
        self._last_detections = detections
        history = getattr(self._session, "history", None)
        self._historical_tracks = history.get_summary() if history and hasattr(history, "get_summary") else []
        for detection in detections:
            class_name = getattr(detection, "class_name", "unknown")
            self._detection_class_counts[class_name] = self._detection_class_counts.get(class_name, 0) + 1
            self._total_detections += 1
            self._confidence_total += getattr(detection, "confidence", 0.0)

    def _set_status(self, status: CameraRuntimeState, error: str | None) -> None:
        self._status = self._status.model_copy(update={"status": status, "error": error})

    def _resolution(self) -> str | None:
        if not self._source or not self._source.width or not self._source.height:
            return None
        return f"{self._source.width}x{self._source.height}"

    def _release_source_only(self) -> None:
        if self._source is not None:
            self._source.release()
            self._source = None

    def _release_resources(self) -> None:
        self._release_source_only()
        if self._session is not None:
            self._session.close()
        self._session = None
        self._thread = None


class CameraManager:
    """Thread-safe registry for independently running camera processors."""

    def __init__(self) -> None:
        self._processors: dict[str, CameraProcessor] = {}
        self._lock = threading.RLock()

    def register(self, camera_id: str, source: str | int, source_type: CameraSourceType | None = None, **kwargs: Any) -> CameraProcessor:
        with self._lock:
            if camera_id in self._processors:
                raise ValueError(f"Camera '{camera_id}' is already registered.")
            processor = CameraProcessor(camera_id, source, source_type, **kwargs)
            self._processors[camera_id] = processor
            return processor

    def unregister(self, camera_id: str) -> None:
        with self._lock:
            processor = self._processors.pop(camera_id, None)
        if processor:
            processor.stop()

    def get(self, camera_id: str) -> CameraProcessor | None:
        with self._lock:
            return self._processors.get(camera_id)

    def start(self, camera_id: str) -> CameraProcessingStatus:
        processor = self._require(camera_id)
        return processor.start()

    def stop(self, camera_id: str) -> CameraProcessingStatus:
        processor = self._require(camera_id)
        return processor.stop()

    def restart(self, camera_id: str) -> CameraProcessingStatus:
        processor = self._require(camera_id)
        return processor.restart()

    def status(self, camera_id: str) -> CameraProcessingStatus:
        return self._require(camera_id).status

    def list_status(self) -> list[CameraProcessingStatus]:
        with self._lock:
            return [processor.status for processor in self._processors.values()]

    def list_summaries(self) -> list[CameraRuntimeSummary]:
        with self._lock:
            return [processor.summary() for processor in self._processors.values()]

    def shutdown(self) -> None:
        with self._lock:
            processors = list(self._processors.values())
        for processor in processors:
            processor.stop()

    def _require(self, camera_id: str) -> CameraProcessor:
        processor = self.get(camera_id)
        if processor is None:
            raise KeyError(f"Camera '{camera_id}' is not registered.")
        return processor


camera_manager = CameraManager()
