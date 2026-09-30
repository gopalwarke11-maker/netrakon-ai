"""Comprehensive test suite for Alert Deduplication and Event Lifecycle (Part 3 Tests 1 to 10)."""

from datetime import datetime, timezone
import pytest
from app.ai.geometry import Point2D
from app.ai.intrusion_detector import IntrusionDetector, TrackBoundaryState
from app.ai.schemas import BoundingBoxAI, TrackedObject
from app.models.boundary import VirtualBoundary
from app.services.alert_service import alert_service
from app.services.intrusion_service import intrusion_service


def _make_track(track_id: int, cx: float, cy: float, class_name: str = "person") -> TrackedObject:
    """Helper to construct a TrackedObject with anchor at (cx, cy)."""
    x1, y1, x2, y2 = cx - 10.0, cy - 40.0, cx + 10.0, cy
    return TrackedObject(
        track_id=track_id,
        class_id=0 if class_name == "person" else 1,
        class_name=class_name,
        confidence=0.9,
        center_x=cx,
        center_y=cy - 20.0,
        bounding_box=BoundingBoxAI(
            x1=x1,
            y1=y1,
            x2=x2,
            y2=y2,
            width=x2 - x1,
            height=y2 - y1,
        ),
    )


@pytest.fixture
def clean_detector():
    detector = IntrusionDetector()
    detector.clear()
    return detector


@pytest.fixture
def horizontal_boundary():
    """Boundary at y=300, restricted side = positive (below line, y > 300)."""
    return VirtualBoundary(
        id="BND-TEST-01",
        camera_id="CAM-01",
        name="Test Line",
        point_a=Point2D(x=100.0, y=300.0),
        point_b=Point2D(x=800.0, y=300.0),
        restricted_side="positive",
        severity="HIGH",
        tolerance=5.0,
        enabled=True,
    )


def test_1_one_crossing_one_alert(clean_detector, horizontal_boundary):
    """TEST 1: One video, 1 track, 1 boundary crossing -> 1 alert only."""
    # Frame 1: Track 1 at y=200 (SAFE)
    clean_detector.process_tracks("CAM-01", 1, [_make_track(1, 400.0, 200.0)], [horizontal_boundary])
    assert len(clean_detector.get_events()) == 0

    # Frame 2: Track 1 crosses to y=350 (RESTRICTED)
    events = clean_detector.process_tracks("CAM-01", 2, [_make_track(1, 400.0, 350.0)], [horizontal_boundary])
    assert len(events) == 1
    assert len(clean_detector.get_events()) == 1


def test_2_staying_inside_boundary_generates_no_additional_alerts(clean_detector, horizontal_boundary):
    """TEST 2: Same track remains inside boundary for 100+ processed frames -> still only 1 alert."""
    # Frame 1: SAFE
    clean_detector.process_tracks("CAM-01", 1, [_make_track(1, 400.0, 200.0)], [horizontal_boundary])
    # Frame 2: Crosses
    clean_detector.process_tracks("CAM-01", 2, [_make_track(1, 400.0, 350.0)], [horizontal_boundary])
    assert len(clean_detector.get_events()) == 1

    # Frames 3 to 120: Track moves around inside restricted side (y=360..400)
    for f in range(3, 121):
        events = clean_detector.process_tracks(
            "CAM-01", f, [_make_track(1, 400.0, 350.0 + (f % 20))], [horizontal_boundary]
        )
        assert len(events) == 0, f"Frame {f} generated duplicate alert!"

    assert len(clean_detector.get_events()) == 1


def test_3_leaving_and_reentering_creates_new_alert(clean_detector, horizontal_boundary):
    """TEST 3: Same track leaves boundary firmly and re-enters -> 2 alerts total."""
    # 1st Entry
    clean_detector.process_tracks("CAM-01", 1, [_make_track(1, 400.0, 200.0)], [horizontal_boundary])
    clean_detector.process_tracks("CAM-01", 2, [_make_track(1, 400.0, 350.0)], [horizontal_boundary])
    assert len(clean_detector.get_events()) == 1

    # Firm Exit back to y=200 (distance 100 > tolerance * 1.5)
    clean_detector.process_tracks("CAM-01", 3, [_make_track(1, 400.0, 200.0)], [horizontal_boundary])

    # 2nd Entry
    events_reenter = clean_detector.process_tracks("CAM-01", 4, [_make_track(1, 400.0, 360.0)], [horizontal_boundary])
    assert len(events_reenter) == 1
    assert len(clean_detector.get_events()) == 2


def test_4_two_different_tracks_generate_two_alerts(clean_detector, horizontal_boundary):
    """TEST 4: Two different tracks enter -> 2 alerts."""
    # Track 1
    clean_detector.process_tracks("CAM-01", 1, [_make_track(1, 200.0, 200.0)], [horizontal_boundary])
    clean_detector.process_tracks("CAM-01", 2, [_make_track(1, 200.0, 350.0)], [horizontal_boundary])

    # Track 2
    clean_detector.process_tracks("CAM-01", 3, [_make_track(2, 600.0, 200.0)], [horizontal_boundary])
    clean_detector.process_tracks("CAM-01", 4, [_make_track(2, 600.0, 350.0)], [horizontal_boundary])

    assert len(clean_detector.get_events()) == 2


def test_5_multicamera_isolation(clean_detector):
    """TEST 5: Camera 1 Track 3 and Camera 2 Track 3 -> 2 independent events."""
    bnd_c1 = VirtualBoundary(
        id="BND-C1", camera_id="CAM-01", name="B1",
        point_a=Point2D(x=0.0, y=300.0), point_b=Point2D(x=1000.0, y=300.0),
        restricted_side="positive", severity="HIGH", tolerance=5.0, enabled=True,
    )
    bnd_c2 = VirtualBoundary(
        id="BND-C2", camera_id="CAM-02", name="B2",
        point_a=Point2D(x=0.0, y=300.0), point_b=Point2D(x=1000.0, y=300.0),
        restricted_side="positive", severity="HIGH", tolerance=5.0, enabled=True,
    )

    # CAM-01 Track 3
    clean_detector.process_tracks("CAM-01", 1, [_make_track(3, 400.0, 200.0)], [bnd_c1])
    ev1 = clean_detector.process_tracks("CAM-01", 2, [_make_track(3, 400.0, 350.0)], [bnd_c1])
    assert len(ev1) == 1

    # CAM-02 Track 3
    clean_detector.process_tracks("CAM-02", 1, [_make_track(3, 400.0, 200.0)], [bnd_c2])
    ev2 = clean_detector.process_tracks("CAM-02", 2, [_make_track(3, 400.0, 350.0)], [bnd_c2])
    assert len(ev2) == 1

    assert len(clean_detector.get_events()) == 2


def test_6_multi_boundary_independence(clean_detector):
    """TEST 6: Same track interacts with Boundary A and Boundary B independently."""
    bnd_a = VirtualBoundary(
        id="BND-A", camera_id="CAM-01", name="Boundary A",
        point_a=Point2D(x=0.0, y=200.0), point_b=Point2D(x=1000.0, y=200.0),
        restricted_side="positive", severity="HIGH", tolerance=5.0, enabled=True,
    )
    bnd_b = VirtualBoundary(
        id="BND-B", camera_id="CAM-01", name="Boundary B",
        point_a=Point2D(x=0.0, y=400.0), point_b=Point2D(x=1000.0, y=400.0),
        restricted_side="positive", severity="HIGH", tolerance=5.0, enabled=True,
    )

    # Track 1 starts at y=100
    clean_detector.process_tracks("CAM-01", 1, [_make_track(1, 300.0, 100.0)], [bnd_a, bnd_b])

    # Crosses Boundary A (y=250)
    ev_a = clean_detector.process_tracks("CAM-01", 2, [_make_track(1, 300.0, 250.0)], [bnd_a, bnd_b])
    assert len(ev_a) == 1
    assert ev_a[0].boundary_id == "BND-A"

    # Crosses Boundary B (y=450)
    ev_b = clean_detector.process_tracks("CAM-01", 3, [_make_track(1, 300.0, 450.0)], [bnd_a, bnd_b])
    assert len(ev_b) == 1
    assert ev_b[0].boundary_id == "BND-B"


def test_7_video_loop_reset(clean_detector, horizontal_boundary):
    """TEST 7: Video loops -> no frame-by-frame duplicate alert storm."""
    # Loop 1
    clean_detector.process_tracks("CAM-01", 1, [_make_track(1, 400.0, 200.0)], [horizontal_boundary])
    clean_detector.process_tracks("CAM-01", 50, [_make_track(1, 400.0, 350.0)], [horizontal_boundary])
    assert len(clean_detector.get_events()) == 1

    # Video rewinds: frame number goes back to 1
    clean_detector.clear_camera("CAM-01")

    # Loop 2 frame 1 to 50
    clean_detector.process_tracks("CAM-01", 1, [_make_track(1, 400.0, 200.0)], [horizontal_boundary])
    for f in range(2, 51):
        clean_detector.process_tracks("CAM-01", f, [_make_track(1, 400.0, 350.0)], [horizontal_boundary])

    # No duplicate alert storm triggered
    assert len(clean_detector.get_events()) <= 1


def test_9_database_query_idempotence():
    """TEST 9: Database queries return unique alerts without duplicate insertion."""
    alerts = alert_service.list(camera_id="CAM-01")
    ids = [a.id for a in alerts]
    assert len(ids) == len(set(ids)), "Database alert query returned duplicate alert IDs!"
