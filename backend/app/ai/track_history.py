"""Lightweight in-memory track history.

Maintains a per-track record for every active or completed track seen during
a tracking session.  This is the foundation for later movement / behaviour
analysis (Phase 5+).  No database is used; everything lives in Python memory
for the duration of the session.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

from app.ai.schemas import BoundingBoxAI, TrackSummaryEntry


@dataclass
class TrackRecord:
    """All accumulated data for a single track ID."""

    track_id: int
    class_name: str
    first_seen_frame: int
    last_seen_frame: int
    frames_seen: int = 0

    # Bounded position log — oldest entries are dropped automatically once the
    # deque reaches maxlen.  Each entry is (center_x, center_y).
    position_log: deque[tuple[float, float]] = field(default_factory=deque)

    # Most recent bounding box (updated every frame this track is visible)
    latest_bbox: BoundingBoxAI | None = None
    latest_center_x: float = 0.0
    latest_center_y: float = 0.0

    def update(
        self,
        frame_number: int,
        center_x: float,
        center_y: float,
        bbox: BoundingBoxAI,
    ) -> None:
        """Update this record with data from the latest frame."""
        self.last_seen_frame = frame_number
        self.frames_seen += 1
        self.latest_center_x = center_x
        self.latest_center_y = center_y
        self.latest_bbox = bbox
        self.position_log.append((center_x, center_y))

    def to_summary(self) -> TrackSummaryEntry:
        """Convert to the Pydantic summary schema for API responses."""
        return TrackSummaryEntry(
            track_id=self.track_id,
            class_name=self.class_name,
            first_seen_frame=self.first_seen_frame,
            last_seen_frame=self.last_seen_frame,
            frames_seen=self.frames_seen,
            latest_center_x=round(self.latest_center_x, 2),
            latest_center_y=round(self.latest_center_y, 2),
            latest_bounding_box=self.latest_bbox
            or BoundingBoxAI(x1=0, y1=0, x2=0, y2=0, width=0, height=0),
        )


class TrackHistory:
    """Accumulates track records across all frames of a tracking session.

    Args:
        position_history_limit: Maximum number of (center_x, center_y) positions
            stored per track.  Older positions are discarded automatically.
            Prevents unbounded memory growth for long videos.
    """

    def __init__(self, position_history_limit: int = 50) -> None:
        self._position_history_limit = position_history_limit
        self._tracks: dict[int, TrackRecord] = {}

    # ── Public interface ──────────────────────────────────────────────────────

    def update(
        self,
        track_id: int,
        class_name: str,
        frame_number: int,
        center_x: float,
        center_y: float,
        bbox: BoundingBoxAI,
    ) -> None:
        """Register one observation of a track in the current frame."""
        if track_id not in self._tracks:
            self._tracks[track_id] = TrackRecord(
                track_id=track_id,
                class_name=class_name,
                first_seen_frame=frame_number,
                last_seen_frame=frame_number,
                position_log=deque(maxlen=self._position_history_limit),
            )
        self._tracks[track_id].update(frame_number, center_x, center_y, bbox)

    def get_summary(self) -> list[TrackSummaryEntry]:
        """Return Pydantic summaries for all known tracks, sorted by track_id."""
        return [rec.to_summary() for rec in sorted(self._tracks.values(), key=lambda r: r.track_id)]

    @property
    def records(self) -> list[TrackRecord]:
        """Return camera-local records for downstream behavior analysis."""
        return list(self._tracks.values())

    @property
    def active_count(self) -> int:
        """Total number of unique tracks seen so far."""
        return len(self._tracks)

    def __len__(self) -> int:
        return self.active_count
