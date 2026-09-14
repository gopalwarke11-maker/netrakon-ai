"""Pydantic schemas for the AI inference layer.

These are intentionally separate from the existing Phase-1/2 Detection
schemas in app/models/detection.py, which represent the in-memory detection
store.  These schemas represent a single real-time YOLO inference result.
"""

from pydantic import BaseModel, Field


class BoundingBoxAI(BaseModel):
    """Axis-aligned bounding box in absolute pixel coordinates (xyxy format)."""

    x1: float = Field(description="Left edge (pixels)")
    y1: float = Field(description="Top edge (pixels)")
    x2: float = Field(description="Right edge (pixels)")
    y2: float = Field(description="Bottom edge (pixels)")
    width: float = Field(description="Box width  (x2 - x1)")
    height: float = Field(description="Box height (y2 - y1)")


class DetectionResult(BaseModel):
    """Single detected object returned by the YOLO model."""

    class_id: int = Field(description="COCO class index")
    class_name: str = Field(description="Human-readable class label")
    confidence: float = Field(ge=0.0, le=1.0, description="Model confidence [0, 1]")
    bounding_box: BoundingBoxAI


class DetectResponse(BaseModel):
    """Full response payload for POST /api/ai/detect."""

    detections: list[DetectionResult] = Field(
        description="All objects detected in the image"
    )
    image_width: int = Field(description="Input image width in pixels")
    image_height: int = Field(description="Input image height in pixels")
    processing_time_ms: float = Field(
        description="Total YOLO inference time in milliseconds"
    )
    model_name: str = Field(description="YOLO model variant that produced these results")


# ─────────────────────────────────────────────────────────────────────────────
# Phase 4 — Tracking schemas
# ─────────────────────────────────────────────────────────────────────────────


class TrackedObject(BaseModel):
    """A single detected+tracked object within one video frame."""

    track_id: int = Field(description="Persistent ByteTrack ID across frames")
    class_id: int = Field(description="COCO class index")
    class_name: str = Field(description="Human-readable class label")
    confidence: float = Field(ge=0.0, le=1.0, description="Model confidence [0, 1]")
    bounding_box: BoundingBoxAI
    center_x: float = Field(description="Horizontal centre of bounding box (pixels)")
    center_y: float = Field(description="Vertical centre of bounding box (pixels)")
    frame_number: int | None = Field(default=None, description="Source frame carrying this detection")
    image_width: int | None = Field(default=None, description="Source frame width in pixels")
    image_height: int | None = Field(default=None, description="Source frame height in pixels")


class TrackFrame(BaseModel):
    """All tracked objects detected in a single video frame."""

    frame_number: int = Field(description="1-based frame index within the video")
    timestamp_ms: float = Field(description="Frame position in the video (milliseconds)")
    image_width: int = Field(description="Frame width in pixels")
    image_height: int = Field(description="Frame height in pixels")
    processing_time_ms: float = Field(description="Inference + tracking time for this frame")
    objects: list[TrackedObject] = Field(
        description="All objects with assigned Track IDs in this frame"
    )


class TrackSummaryEntry(BaseModel):
    """Per-track summary accumulated across all processed frames."""

    track_id: int
    class_name: str
    first_seen_frame: int = Field(description="Frame number where this track first appeared")
    last_seen_frame: int = Field(description="Frame number where this track was last seen")
    frames_seen: int = Field(description="Total number of frames this track appeared in")
    latest_center_x: float
    latest_center_y: float
    latest_bounding_box: BoundingBoxAI


class TrackResponse(BaseModel):
    """Full API response payload for POST /api/ai/track."""

    filename: str = Field(description="Name of the uploaded video file")
    total_frames_in_video: int = Field(description="Total frame count reported by the video")
    total_frames_processed: int = Field(description="Frames actually run through the tracker")
    tracks: list[TrackSummaryEntry] = Field(
        description="Summary of every unique track seen across all processed frames"
    )
    total_processing_time_ms: float = Field(description="Wall-clock time for full video processing")
    avg_frame_time_ms: float = Field(description="Average per-frame inference+tracking time")
    estimated_fps: float = Field(description="Frames processed per second (1000 / avg_frame_time_ms)")
    model_name: str = Field(description="YOLO model variant used")
    tracker: str = Field(description="Tracker algorithm used (e.g. 'bytetrack')")
    intrusions: list[dict] = Field(
        default_factory=list,
        description="Any virtual security boundary intrusion events detected during tracking",
    )

