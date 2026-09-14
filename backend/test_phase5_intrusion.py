"""Unit tests for NETRAKON AI Phase 5 — Virtual Security Boundaries & Intrusion Detection.

Covers all 20 required test scenarios:
1.  Horizontal boundary
2.  Vertical boundary
3.  Diagonal boundary
4.  Positive -> negative crossing
5.  Negative -> positive crossing
6.  Touching boundary without crossing
7.  Jitter around boundary
8.  Repeated frames after crossing
9.  Duplicate alert prevention
10. Multiple tracks
11. Multiple cameras
12. Multiple boundaries
13. Invalid boundary points (A == B)
14. Missing camera
15. Disabled boundary
16. Restricted positive side
17. Restricted negative side
18. Track disappears and reappears
19. New track ID
20. Bottom-center anchor correctness

Also tests boundary CRUD API, camera-boundary endpoint, and intrusion-test endpoint.
"""

from __future__ import annotations

from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient

from app.ai.geometry import (
    check_boundary_crossing,
    classify_side,
    get_bottom_center_anchor,
    orientation,
    perpendicular_distance,
)
from app.ai.intrusion_detector import IntrusionDetector, calculate_deterministic_severity

from app.ai.schemas import BoundingBoxAI, TrackedObject
from app.main import app
from app.models.boundary import Point2D, VirtualBoundary, VirtualBoundaryCreate, VirtualBoundaryUpdate
from app.services.alert_service import alert_service
from app.services.boundary_service import boundary_service
from app.services.camera_service import camera_service


client = TestClient(app)


# ─────────────────────────────────────────────────────────────────────────────
# 1. Geometry Unit Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_01_horizontal_boundary_orientation():
    """Horizontal line: A=(100, 200), B=(800, 200).
    In standard screen coords (y downwards):
    Points below the line (y > 200) have orientation > 0.
    Points above the line (y < 200) have orientation < 0.
    """
    a = (100.0, 200.0)
    b = (800.0, 200.0)

    # Point below line (y = 250) -> positive
    ori_below = orientation(a, b, (450.0, 250.0))
    assert ori_below > 0, f"Expected positive orientation, got {ori_below}"

    # Point above line (y = 150) -> negative
    ori_above = orientation(a, b, (450.0, 150.0))
    assert ori_above < 0, f"Expected negative orientation, got {ori_above}"

    # Point directly on line (y = 200) -> 0
    ori_on = orientation(a, b, (450.0, 200.0))
    assert abs(ori_on) < 1e-6, f"Expected 0 orientation, got {ori_on}"


def test_02_vertical_boundary_orientation():
    """Vertical line: A=(300, 100), B=(300, 600).
    Points to the right (x > 300) have orientation < 0 (left-hand turn in screen coords),
    or depending on cross product:
    (Bx - Ax)*(Py - Ay) - (By - Ay)*(Px - Ax) = 0 - 500*(Px - 300) = -500*(Px - 300).
    For Px > 300, orientation is negative. For Px < 300, orientation is positive.
    Works without division by zero!
    """
    a = (300.0, 100.0)
    b = (300.0, 600.0)

    # Left of vertical line (x = 200)
    ori_left = orientation(a, b, (200.0, 350.0))
    assert ori_left > 0, f"Expected positive orientation, got {ori_left}"

    # Right of vertical line (x = 400)
    ori_right = orientation(a, b, (400.0, 350.0))
    assert ori_right < 0, f"Expected negative orientation, got {ori_right}"

    # On vertical line
    ori_on = orientation(a, b, (300.0, 350.0))
    assert abs(ori_on) < 1e-6


def test_03_diagonal_boundary_orientation():
    """Diagonal line: A=(100, 100), B=(500, 500)."""
    a = (100.0, 100.0)
    b = (500.0, 500.0)

    # Point below/right of diagonal: (400, 200) vs (200, 400)
    ori_1 = orientation(a, b, (200.0, 400.0))
    ori_2 = orientation(a, b, (400.0, 200.0))

    assert ori_1 > 0
    assert ori_2 < 0
    assert orientation(a, b, (300.0, 300.0)) == 0.0


def test_04_positive_to_negative_crossing():
    """Object moves from positive side to negative side across horizontal boundary."""
    a = (100.0, 200.0)
    b = (800.0, 200.0)

    # Move from y=250 (positive) to y=150 (negative)
    crossed_pos_res, dir_pos_res = check_boundary_crossing(
        a, b, prev_point=(400.0, 250.0), curr_point=(400.0, 150.0),
        restricted_side="positive", tolerance=5.0
    )
    # Since restricted side is positive, moving from positive to negative is EXIT
    assert not crossed_pos_res
    assert dir_pos_res == "RESTRICTED_TO_UNRESTRICTED"

    # Now if restricted side is negative: moving from positive to negative IS intrusion
    crossed_neg_res, dir_neg_res = check_boundary_crossing(
        a, b, prev_point=(400.0, 250.0), curr_point=(400.0, 150.0),
        restricted_side="negative", tolerance=5.0
    )
    assert crossed_neg_res
    assert dir_neg_res == "UNRESTRICTED_TO_RESTRICTED"


def test_05_negative_to_positive_crossing():
    """Object moves from negative side to positive side across horizontal boundary."""
    a = (100.0, 200.0)
    b = (800.0, 200.0)

    # Move from y=150 (negative) to y=250 (positive)
    crossed, direction = check_boundary_crossing(
        a, b, prev_point=(400.0, 150.0), curr_point=(400.0, 250.0),
        restricted_side="positive", tolerance=5.0
    )
    assert crossed
    assert direction == "UNRESTRICTED_TO_RESTRICTED"


def test_06_touching_boundary_without_crossing():
    """Touching the boundary (orientation == 0) from one side does not trigger crossing."""
    a = (100.0, 200.0)
    b = (800.0, 200.0)

    # Moves from y=150 to exactly y=200 (touching)
    crossed, direction = check_boundary_crossing(
        a, b, prev_point=(400.0, 150.0), curr_point=(400.0, 200.0),
        restricted_side="positive", tolerance=5.0
    )
    assert not crossed
    assert direction == "NONE"


def test_07_jitter_around_boundary():
    """Jittering within the tolerance deadzone (e.g. y=198 to y=202) is suppressed."""
    a = (100.0, 200.0)
    b = (800.0, 200.0)

    # Moves 2 pixels across the line (tolerance is 5.0)
    crossed, direction = check_boundary_crossing(
        a, b, prev_point=(400.0, 198.0), curr_point=(400.0, 202.0),
        restricted_side="positive", tolerance=5.0
    )
    assert not crossed
    assert direction == "NONE"


def test_20_bottom_center_anchor_correctness():
    """Validate anchor is (x1 + x2)/2, y2, not bounding box center."""
    bbox = BoundingBoxAI(x1=100.0, y1=50.0, x2=200.0, y2=250.0, width=100.0, height=200.0)
    anchor = get_bottom_center_anchor(bbox)

    assert anchor[0] == 150.0, f"Expected anchor_x 150.0, got {anchor[0]}"
    assert anchor[1] == 250.0, f"Expected anchor_y 250.0 (bottom), got {anchor[1]}"
    # Confirm it is NOT center_y (which would be 150.0)
    assert anchor[1] != 150.0


# ─────────────────────────────────────────────────────────────────────────────
# 2. State Machine & Intrusion Tests
# ─────────────────────────────────────────────────────────────────────────────

def _make_track(track_id: int, anchor_x: float, anchor_y: float, class_name: str = "person") -> TrackedObject:
    """Helper to construct a TrackedObject with bottom-center anchor at (anchor_x, anchor_y)."""
    w, h = 40.0, 80.0
    bbox = BoundingBoxAI(
        x1=anchor_x - w / 2.0,
        y1=anchor_y - h,
        x2=anchor_x + w / 2.0,
        y2=anchor_y,
        width=w,
        height=h,
    )
    return TrackedObject(
        track_id=track_id,
        class_id=0 if class_name == "person" else 1,
        class_name=class_name,
        confidence=0.92,
        bounding_box=bbox,
        center_x=anchor_x,
        center_y=anchor_y - h / 2.0,
    )


def test_08_and_09_repeated_frames_and_duplicate_alert_prevention():
    """Object crosses boundary, then stays on restricted side for 10 frames.
    Must generate exactly ONE alert event.
    """
    detector = IntrusionDetector()
    boundary = VirtualBoundary(
        id="BND-TEST-01",
        camera_id="CAM-01",
        name="Test Line",
        enabled=True,
        point_a=Point2D(x=100.0, y=300.0),
        point_b=Point2D(x=700.0, y=300.0),
        restricted_side="positive",
        severity="HIGH",
        tolerance=5.0,
    )

    all_events = []

    # Frame 1: Outside (y = 200, orientation < 0)
    ev1 = detector.process_tracks("CAM-01", 1, [_make_track(1, 400.0, 200.0)], [boundary])
    all_events.extend(ev1)
    assert len(ev1) == 0

    # Frame 2: Still outside (y = 250)
    ev2 = detector.process_tracks("CAM-01", 2, [_make_track(1, 400.0, 250.0)], [boundary])
    all_events.extend(ev2)
    assert len(ev2) == 0

    # Frame 3: Crosses to inside (y = 350) -> INTRUSION!
    ev3 = detector.process_tracks("CAM-01", 3, [_make_track(1, 400.0, 350.0)], [boundary])
    all_events.extend(ev3)
    assert len(ev3) == 1
    assert ev3[0].track_id == 1
    assert ev3[0].severity == "HIGH"
    assert ev3[0].alert_id is not None

    # Frames 4 to 15: Remains on restricted side (y = 360 .. 450)
    for f in range(4, 16):
        ev = detector.process_tracks("CAM-01", f, [_make_track(1, 400.0, 350.0 + f)], [boundary])
        all_events.extend(ev)
        assert len(ev) == 0, f"Frame {f} generated duplicate alert!"

    # Total events across all 15 frames must be exactly 1
    assert len(all_events) == 1


def test_10_multiple_tracks():
    """Two different tracks: Track 1 crosses, Track 2 stays outside."""
    detector = IntrusionDetector()
    boundary = VirtualBoundary(
        id="BND-MULTI",
        camera_id="CAM-01",
        name="Multi-track line",
        enabled=True,
        point_a=Point2D(x=50.0, y=300.0),
        point_b=Point2D(x=800.0, y=300.0),
        restricted_side="positive",
        severity="HIGH",
        tolerance=5.0,
    )

    # Frame 1: Both outside
    t1 = _make_track(1, 200.0, 200.0)
    t2 = _make_track(2, 600.0, 220.0)
    ev1 = detector.process_tracks("CAM-01", 1, [t1, t2], [boundary])
    assert len(ev1) == 0

    # Frame 2: Track 1 crosses (y=380), Track 2 moves slightly (y=240, still outside)
    t1_cross = _make_track(1, 200.0, 380.0)
    t2_safe = _make_track(2, 600.0, 240.0)
    ev2 = detector.process_tracks("CAM-01", 2, [t1_cross, t2_safe], [boundary])

    assert len(ev2) == 1
    assert ev2[0].track_id == 1


def test_11_multiple_cameras():
    """State is isolated across cameras. Track 1 on CAM-01 does not affect CAM-02."""
    detector = IntrusionDetector()
    bnd_cam1 = VirtualBoundary(
        id="BND-C1",
        camera_id="CAM-01",
        name="Cam 1 Line",
        enabled=True,
        point_a=Point2D(x=50.0, y=300.0),
        point_b=Point2D(x=500.0, y=300.0),
        restricted_side="positive",
    )
    bnd_cam2 = VirtualBoundary(
        id="BND-C2",
        camera_id="CAM-02",
        name="Cam 2 Line",
        enabled=True,
        point_a=Point2D(x=50.0, y=300.0),
        point_b=Point2D(x=500.0, y=300.0),
        restricted_side="positive",
    )

    # Frame 1 on CAM-01: Track 1 outside
    detector.process_tracks("CAM-01", 1, [_make_track(1, 250.0, 200.0)], [bnd_cam1])

    # Frame 1 on CAM-02: Track 1 outside
    detector.process_tracks("CAM-02", 1, [_make_track(1, 250.0, 200.0)], [bnd_cam2])

    # Frame 2 on CAM-01: Track 1 crosses
    ev_c1 = detector.process_tracks("CAM-01", 2, [_make_track(1, 250.0, 350.0)], [bnd_cam1])
    assert len(ev_c1) == 1
    assert ev_c1[0].camera_id == "CAM-01"

    # Frame 2 on CAM-02: Track 1 does NOT cross
    ev_c2 = detector.process_tracks("CAM-02", 2, [_make_track(1, 250.0, 220.0)], [bnd_cam2])
    assert len(ev_c2) == 0


def test_12_multiple_boundaries():
    """Single camera has two boundaries. Track crosses boundary A, not boundary B."""
    detector = IntrusionDetector()
    bnd_a = VirtualBoundary(
        id="BND-A",
        camera_id="CAM-01",
        name="Line A (y=200)",
        enabled=True,
        point_a=Point2D(x=50.0, y=200.0),
        point_b=Point2D(x=500.0, y=200.0),
        restricted_side="positive",
    )
    bnd_b = VirtualBoundary(
        id="BND-B",
        camera_id="CAM-01",
        name="Line B (y=600)",
        enabled=True,
        point_a=Point2D(x=50.0, y=600.0),
        point_b=Point2D(x=500.0, y=600.0),
        restricted_side="positive",
    )

    # Start at y=100
    detector.process_tracks("CAM-01", 1, [_make_track(1, 250.0, 100.0)], [bnd_a, bnd_b])

    # Move to y=300 (crosses A, far from B)
    ev = detector.process_tracks("CAM-01", 2, [_make_track(1, 250.0, 300.0)], [bnd_a, bnd_b])
    assert len(ev) == 1
    assert ev[0].boundary_id == "BND-A"


def test_13_invalid_boundary_identical_points():
    """Boundary creation must fail if point A and point B are identical."""
    with pytest.raises(ValueError, match="cannot be identical"):
        VirtualBoundaryCreate(
            name="Invalid Line",
            camera_id="CAM-01",
            point_a=Point2D(x=100.0, y=100.0),
            point_b=Point2D(x=100.0, y=100.0),
        )


def test_14_invalid_camera():
    """Boundary creation via service must fail if camera does not exist."""
    payload = VirtualBoundaryCreate(
        name="Ghost Cam Line",
        camera_id="CAM-NONEXISTENT",
        point_a=Point2D(x=100.0, y=100.0),
        point_b=Point2D(x=500.0, y=100.0),
    )
    with pytest.raises(ValueError, match="does not exist"):
        boundary_service.create(payload)


def test_15_disabled_boundary():
    """Disabled boundary must never produce intrusion events."""
    detector = IntrusionDetector()
    boundary = VirtualBoundary(
        id="BND-DISABLED",
        camera_id="CAM-01",
        name="Disabled Line",
        enabled=False,  # DISABLED
        point_a=Point2D(x=100.0, y=300.0),
        point_b=Point2D(x=700.0, y=300.0),
        restricted_side="positive",
    )

    detector.process_tracks("CAM-01", 1, [_make_track(1, 400.0, 200.0)], [boundary])
    ev = detector.process_tracks("CAM-01", 2, [_make_track(1, 400.0, 400.0)], [boundary])
    assert len(ev) == 0


def test_16_restricted_positive_side():
    """restricted_side='positive': crossing from negative to positive triggers intrusion."""
    detector = IntrusionDetector()
    boundary = VirtualBoundary(
        id="BND-POS",
        camera_id="CAM-01",
        name="Pos Restricted",
        enabled=True,
        point_a=Point2D(x=100.0, y=300.0),
        point_b=Point2D(x=700.0, y=300.0),
        restricted_side="positive",
    )

    detector.process_tracks("CAM-01", 1, [_make_track(1, 400.0, 200.0)], [boundary])
    ev = detector.process_tracks("CAM-01", 2, [_make_track(1, 400.0, 400.0)], [boundary])
    assert len(ev) == 1
    assert ev[0].crossing_direction == "UNRESTRICTED_TO_RESTRICTED"


def test_17_restricted_negative_side():
    """restricted_side='negative': crossing from positive to negative triggers intrusion."""
    detector = IntrusionDetector()
    boundary = VirtualBoundary(
        id="BND-NEG",
        camera_id="CAM-01",
        name="Neg Restricted",
        enabled=True,
        point_a=Point2D(x=100.0, y=300.0),
        point_b=Point2D(x=700.0, y=300.0),
        restricted_side="negative",
    )

    # Start at positive side (y=400)
    detector.process_tracks("CAM-01", 1, [_make_track(1, 400.0, 400.0)], [boundary])
    # Cross to negative side (y=200)
    ev = detector.process_tracks("CAM-01", 2, [_make_track(1, 400.0, 200.0)], [boundary])
    assert len(ev) == 1
    assert ev[0].crossing_direction == "UNRESTRICTED_TO_RESTRICTED"


def test_18_track_disappears_and_reappears():
    """Track crosses, is alerted, leaves frame, comes back inside: remains alerted, no duplicate."""
    detector = IntrusionDetector(max_idle_frames=50)
    boundary = VirtualBoundary(
        id="BND-DISAPP",
        camera_id="CAM-01",
        name="Disappear Test",
        enabled=True,
        point_a=Point2D(x=100.0, y=300.0),
        point_b=Point2D(x=700.0, y=300.0),
        restricted_side="positive",
    )

    # Frame 1: Outside
    detector.process_tracks("CAM-01", 1, [_make_track(1, 400.0, 200.0)], [boundary])
    # Frame 2: Crosses inside
    ev = detector.process_tracks("CAM-01", 2, [_make_track(1, 400.0, 350.0)], [boundary])
    assert len(ev) == 1

    # Frames 3-5: Track disappears (not in list)
    for f in range(3, 6):
        detector.process_tracks("CAM-01", f, [], [boundary])

    # Frame 6: Reappears at y=360 (still in restricted zone, memory intact)
    ev_reappear = detector.process_tracks("CAM-01", 6, [_make_track(1, 400.0, 360.0)], [boundary])
    assert len(ev_reappear) == 0, "Reappearing track inside restricted zone should not re-trigger alert!"


def test_19_new_track_id():
    """A new track ID crossing generates its own alert even if another track was already alerted."""
    detector = IntrusionDetector()
    boundary = VirtualBoundary(
        id="BND-NEWID",
        camera_id="CAM-01",
        name="New Track Test",
        enabled=True,
        point_a=Point2D(x=100.0, y=300.0),
        point_b=Point2D(x=700.0, y=300.0),
        restricted_side="positive",
    )

    # Track 1 crosses
    detector.process_tracks("CAM-01", 1, [_make_track(1, 400.0, 200.0)], [boundary])
    ev1 = detector.process_tracks("CAM-01", 2, [_make_track(1, 400.0, 350.0)], [boundary])
    assert len(ev1) == 1

    # Track 2 arrives and crosses in frame 3 & 4
    detector.process_tracks("CAM-01", 3, [_make_track(2, 450.0, 200.0)], [boundary])
    ev2 = detector.process_tracks("CAM-01", 4, [_make_track(2, 450.0, 350.0)], [boundary])
    assert len(ev2) == 1
    assert ev2[0].track_id == 2


def test_deterministic_severity():
    """Verify deterministic severity assignment based on class and boundary."""
    # Vehicle -> CRITICAL
    assert calculate_deterministic_severity("HIGH", "car") == "CRITICAL"
    assert calculate_deterministic_severity("MEDIUM", "truck") == "CRITICAL"
    # Animal -> LOW
    assert calculate_deterministic_severity("HIGH", "dog") == "LOW"
    assert calculate_deterministic_severity("CRITICAL", "bird") == "LOW"
    # Person -> boundary severity
    assert calculate_deterministic_severity("HIGH", "person") == "HIGH"
    assert calculate_deterministic_severity("MEDIUM", "person") == "MEDIUM"


# ─────────────────────────────────────────────────────────────────────────────
# 3. HTTP API Integration Tests (FastAPI TestClient)
# ─────────────────────────────────────────────────────────────────────────────

def test_boundary_crud_api():
    """Verify full CRUD lifecycle via /api/boundaries."""
    # 1. List existing
    resp = client.get("/api/boundaries")
    assert resp.status_code == 200
    initial_count = len(resp.json())

    # 2. Create boundary
    create_payload = {
        "camera_id": "CAM-01",
        "name": "East Gate Fence",
        "enabled": True,
        "point_a": {"x": 50.0, "y": 150.0},
        "point_b": {"x": 450.0, "y": 150.0},
        "restricted_side": "positive",
        "severity": "HIGH",
        "tolerance": 8.0,
    }
    resp = client.post("/api/boundaries", json=create_payload)
    assert resp.status_code == 201
    created = resp.json()
    bnd_id = created["id"]
    assert created["name"] == "East Gate Fence"
    assert created["camera_id"] == "CAM-01"

    # 3. Get created
    resp = client.get(f"/api/boundaries/{bnd_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == bnd_id

    # 4. Update boundary
    resp = client.put(f"/api/boundaries/{bnd_id}", json={"name": "East Gate Perimeter Modified"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "East Gate Perimeter Modified"

    # 5. Camera-specific boundaries
    resp = client.get("/api/cameras/CAM-01/boundaries")
    assert resp.status_code == 200
    cam_bnds = resp.json()
    assert any(b["id"] == bnd_id for b in cam_bnds)

    # 6. Delete boundary
    resp = client.delete(f"/api/boundaries/{bnd_id}")
    assert resp.status_code == 204

    # 7. Confirm 404 after delete
    resp = client.get(f"/api/boundaries/{bnd_id}")
    assert resp.status_code == 404


def test_boundary_crud_validation_errors():
    """Verify error responses for invalid inputs."""
    # Non-existent camera -> 400
    resp = client.post(
        "/api/boundaries",
        json={
            "camera_id": "CAM-DOES-NOT-EXIST",
            "name": "Invalid",
            "point_a": {"x": 0.0, "y": 0.0},
            "point_b": {"x": 100.0, "y": 100.0},
        },
    )
    assert resp.status_code == 400

    # Identical points A and B -> 422
    resp = client.post(
        "/api/boundaries",
        json={
            "camera_id": "CAM-01",
            "name": "Zero length",
            "point_a": {"x": 100.0, "y": 100.0},
            "point_b": {"x": 100.0, "y": 100.0},
        },
    )
    assert resp.status_code == 422

    # A partial update must also be unable to collapse an existing line.
    resp = client.put(
        "/api/boundaries/BND-0001",
        json={"point_b": {"x": 100.0, "y": 300.0}},
    )
    assert resp.status_code == 400

    # Get non-existent -> 404
    resp = client.get("/api/boundaries/BND-GHOST")
    assert resp.status_code == 404

    # Delete non-existent -> 404
    resp = client.delete("/api/boundaries/BND-GHOST")
    assert resp.status_code == 404


def test_intrusion_test_endpoint():
    """Verify POST /api/ai/intrusion-test with synthetic multi-frame track."""
    req = {
        "camera_id": "CAM-01",
        "custom_boundary": {
            "name": "Synthetic Test Boundary",
            "camera_id": "CAM-01",
            "enabled": True,
            "point_a": {"x": 100.0, "y": 250.0},
            "point_b": {"x": 700.0, "y": 250.0},
            "restricted_side": "positive",
            "severity": "HIGH",
            "tolerance": 5.0,
        },
        "frames": [
            {
                "frame_number": 1,
                "tracks": [
                    {"track_id": 101, "class_name": "person", "anchor_x": 400.0, "anchor_y": 180.0}
                ],
            },
            {
                "frame_number": 2,
                "tracks": [
                    {"track_id": 101, "class_name": "person", "anchor_x": 400.0, "anchor_y": 220.0}
                ],
            },
            {
                "frame_number": 3,
                "tracks": [
                    {"track_id": 101, "class_name": "person", "anchor_x": 400.0, "anchor_y": 320.0}
                ],
            },
            {
                "frame_number": 4,
                "tracks": [
                    {"track_id": 101, "class_name": "person", "anchor_x": 400.0, "anchor_y": 350.0}
                ],
            },
        ],
    }

    resp = client.post("/api/ai/intrusion-test", json=req)
    assert resp.status_code == 200
    data = resp.json()

    assert data["is_simulation"] is True
    assert data["frames_evaluated"] == 4
    assert data["tracks_evaluated"] == 1
    assert data["intrusions_detected"] == 1
    assert len(data["events"]) == 1
    assert data["events"][0]["track_id"] == 101
    assert len(data["alerts_generated"]) == 1
    assert data["alerts_generated"][0]["type"] == "INTRUSION"
