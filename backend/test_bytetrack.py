"""Focused unit test suite for pure NumPy ByteTrack tracker (backend/app/ai/bytetrack.py)."""

import sys
from dataclasses import dataclass
import pytest

from app.ai.bytetrack import ByteTracker, STrack, compute_iou_matrix


@dataclass
class DummyDetection:
    x1: float
    y1: float
    x2: float
    y2: float
    confidence: float
    class_id: int
    class_name: str


def test_bytetrack_does_not_import_torch_or_ultralytics():
    """Verify that importing bytetrack does NOT pull in torch or ultralytics."""
    assert "torch" not in sys.modules, "bytetrack MUST NOT import torch!"
    assert "ultralytics" not in sys.modules, "bytetrack MUST NOT import ultralytics!"


def test_new_track_creation():
    tracker = ByteTracker(high_thresh=0.25)
    det = DummyDetection(x1=10, y1=10, x2=50, y2=50, confidence=0.9, class_id=0, class_name="person")
    
    tracks = tracker.update([det], frame_id=1)
    
    assert len(tracks) == 1
    assert tracks[0].track_id == 1
    assert tracks[0].class_name == "person"
    assert tracks[0].confidence == 0.9


def test_same_object_continuity():
    tracker = ByteTracker(high_thresh=0.25)
    det1 = DummyDetection(x1=10, y1=10, x2=50, y2=50, confidence=0.9, class_id=0, class_name="person")
    tracks_f1 = tracker.update([det1], frame_id=1)
    tid = tracks_f1[0].track_id

    # Frame 2: object moves slightly (12, 12, 52, 52)
    det2 = DummyDetection(x1=12, y1=12, x2=52, y2=52, confidence=0.88, class_id=0, class_name="person")
    tracks_f2 = tracker.update([det2], frame_id=2)

    assert len(tracks_f2) == 1
    assert tracks_f2[0].track_id == tid
    assert tracks_f2[0].x1 == 12.0
    assert tracks_f2[0].tracklet_len == 2


def test_multiple_objects_and_movement():
    tracker = ByteTracker(high_thresh=0.25)
    det1 = DummyDetection(x1=10, y1=10, x2=50, y2=50, confidence=0.9, class_id=0, class_name="person")
    det2 = DummyDetection(x1=200, y1=200, x2=250, y2=250, confidence=0.85, class_id=2, class_name="car")

    tracks = tracker.update([det1, det2], frame_id=1)

    assert len(tracks) == 2
    tids = {t.track_id for t in tracks}
    assert len(tids) == 2


def test_temporary_missed_frame_recovery():
    tracker = ByteTracker(high_thresh=0.25, max_lost_frames=5)
    det1 = DummyDetection(x1=10, y1=10, x2=50, y2=50, confidence=0.9, class_id=0, class_name="person")
    tracks_f1 = tracker.update([det1], frame_id=1)
    tid = tracks_f1[0].track_id

    # Frame 2: missed detection (empty)
    tracks_f2 = tracker.update([], frame_id=2)
    assert len(tracks_f2) == 0
    assert len(tracker.lost_stracks) == 1

    # Frame 3: detection reappears at (14, 14, 54, 54)
    det3 = DummyDetection(x1=14, y1=14, x2=54, y2=54, confidence=0.85, class_id=0, class_name="person")
    tracks_f3 = tracker.update([det3], frame_id=3)

    assert len(tracks_f3) == 1
    assert tracks_f3[0].track_id == tid  # Track ID recovered!
    assert len(tracker.lost_stracks) == 0


def test_track_expiration_and_new_id():
    tracker = ByteTracker(high_thresh=0.25, max_lost_frames=2)
    det1 = DummyDetection(x1=10, y1=10, x2=50, y2=50, confidence=0.9, class_id=0, class_name="person")
    tracks_f1 = tracker.update([det1], frame_id=1)
    tid_original = tracks_f1[0].track_id

    # Exceed max_lost_frames (3 empty frames)
    tracker.update([], frame_id=2)
    tracker.update([], frame_id=3)
    tracker.update([], frame_id=4)
    assert len(tracker.lost_stracks) == 0  # Expired and removed

    # Reappear at same spot: should get a NEW track_id
    det_new = DummyDetection(x1=10, y1=10, x2=50, y2=50, confidence=0.9, class_id=0, class_name="person")
    tracks_f5 = tracker.update([det_new], frame_id=5)

    assert len(tracks_f5) == 1
    assert tracks_f5[0].track_id != tid_original


def test_class_aware_matching():
    tracker = ByteTracker(high_thresh=0.25)
    det_person = DummyDetection(x1=10, y1=10, x2=50, y2=50, confidence=0.9, class_id=0, class_name="person")
    tracks1 = tracker.update([det_person], frame_id=1)
    tid_person = tracks1[0].track_id

    # Same bounding box location, but class_id = 2 ("car")
    det_car = DummyDetection(x1=10, y1=10, x2=50, y2=50, confidence=0.9, class_id=2, class_name="car")
    tracks2 = tracker.update([det_car], frame_id=2)

    # Should create a NEW track for the car, not reuse person's track ID
    car_track = [t for t in tracks2 if t.class_name == "car"][0]
    assert car_track.track_id != tid_person


def test_empty_detections_handling():
    tracker = ByteTracker(high_thresh=0.25)
    tracks = tracker.update([], frame_id=1)
    assert tracks == []
    assert tracker.tracked_stracks == []
    assert tracker.lost_stracks == []


def test_bounded_state_no_unbounded_growth():
    tracker = ByteTracker(high_thresh=0.25, max_lost_frames=3)
    
    # Process 100 frames with alternating objects and empty frames
    for f in range(1, 101):
        if f % 5 == 0:
            tracker.update([], frame_id=f)
        else:
            det = DummyDetection(x1=f, y1=f, x2=f+40, y2=f+40, confidence=0.9, class_id=0, class_name="person")
            tracker.update([det], frame_id=f)

    # Verify tracker memory stays strictly bounded
    assert len(tracker.tracked_stracks) <= 2
    assert len(tracker.lost_stracks) <= 2
