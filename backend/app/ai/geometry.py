"""Geometric calculations for virtual boundaries and line crossings.

Coordinate system:
Standard 2D image pixel coordinates where:
- Origin (0, 0) is at the top-left corner.
- Positive X points to the right.
- Positive Y points downwards.

Orientation formula:
For directed boundary line segment from A(Ax, Ay) to B(Bx, By) and point P(Px, Py):
    orientation(A, B, P) = (Bx - Ax) * (Py - Ay) - (By - Ay) * (Px - Ax)

Interpretation:
- orientation > 0 : P lies to the right-hand side of vector AB (in screen coords:
                    for a left-to-right line, this is below the line).
- orientation < 0 : P lies to the left-hand side of vector AB (in screen coords:
                    for a left-to-right line, this is above the line).
- orientation == 0: P is collinear with line AB.
"""

from __future__ import annotations

import math
from typing import Literal

from app.ai.schemas import BoundingBoxAI
from app.models.boundary import Point2D


def get_bottom_center_anchor(bbox: BoundingBoxAI) -> tuple[float, float]:
    """Calculate the bottom-center anchor point of a bounding box.

    For intrusion detection, this represents where the person's feet
    or the vehicle's tires/base contact the ground plane.

    anchor_x = (x1 + x2) / 2.0
    anchor_y = y2
    """
    anchor_x = (bbox.x1 + bbox.x2) / 2.0
    anchor_y = float(bbox.y2)
    return (round(anchor_x, 2), round(anchor_y, 2))


def orientation(
    a: tuple[float, float] | Point2D,
    b: tuple[float, float] | Point2D,
    p: tuple[float, float] | Point2D,
) -> float:
    """Calculate 2D cross product of vector AB and vector AP.

    Formula:
        (Bx - Ax) * (Py - Ay) - (By - Ay) * (Px - Ax)

    Works reliably for horizontal, vertical, and diagonal lines without division.
    """
    ax = a.x if isinstance(a, Point2D) else a[0]
    ay = a.y if isinstance(a, Point2D) else a[1]
    bx = b.x if isinstance(b, Point2D) else b[0]
    by = b.y if isinstance(b, Point2D) else b[1]
    px = p.x if isinstance(p, Point2D) else p[0]
    py = p.y if isinstance(p, Point2D) else p[1]

    return (bx - ax) * (py - ay) - (by - ay) * (px - ax)


def line_length(
    a: tuple[float, float] | Point2D,
    b: tuple[float, float] | Point2D,
) -> float:
    """Return the Euclidean distance between points A and B."""
    ax = a.x if isinstance(a, Point2D) else a[0]
    ay = a.y if isinstance(a, Point2D) else a[1]
    bx = b.x if isinstance(b, Point2D) else b[0]
    by = b.y if isinstance(b, Point2D) else b[1]
    return math.hypot(bx - ax, by - ay)


def perpendicular_distance(
    a: tuple[float, float] | Point2D,
    b: tuple[float, float] | Point2D,
    p: tuple[float, float] | Point2D,
) -> float:
    """Perpendicular Euclidean distance from point P to the infinite line AB."""
    length = line_length(a, b)
    if length < 1e-9:
        return 0.0
    return abs(orientation(a, b, p)) / length


def signed_perpendicular_distance(
    a: tuple[float, float] | Point2D,
    b: tuple[float, float] | Point2D,
    p: tuple[float, float] | Point2D,
) -> float:
    """Signed perpendicular distance from point P to line AB in pixels.
    
    Sign matches orientation(A, B, P).
    """
    length = line_length(a, b)
    if length < 1e-9:
        return 0.0
    return orientation(a, b, p) / length


def segments_intersect(
    p1: tuple[float, float],
    p2: tuple[float, float],
    q1: tuple[float, float],
    q2: tuple[float, float],
    tolerance: float = 0.0,
) -> bool:
    """Check if line segment p1-p2 and q1-q2 intersect.

    Uses orientation checks for geometric determinism.
    If tolerance > 0, slightly relaxes the segment boundary check.
    """
    o1 = orientation(p1, p2, q1)
    o2 = orientation(p1, p2, q2)
    o3 = orientation(q1, q2, p1)
    o4 = orientation(q1, q2, p2)

    # General crossing
    if ((o1 > 0 and o2 < 0) or (o1 < 0 and o2 > 0)) and (
        (o3 > 0 and o4 < 0) or (o3 < 0 and o4 > 0)
    ):
        return True

    # Collinear / touching checks if points lie on segments
    def on_segment(p: tuple[float, float], q: tuple[float, float], r: tuple[float, float]) -> bool:
        return (
            min(p[0], r[0]) - tolerance <= q[0] <= max(p[0], r[0]) + tolerance
            and min(p[1], r[1]) - tolerance <= q[1] <= max(p[1], r[1]) + tolerance
        )

    if abs(o1) <= 1e-6 and on_segment(p1, q1, p2):
        return True
    if abs(o2) <= 1e-6 and on_segment(p1, q2, p2):
        return True
    if abs(o3) <= 1e-6 and on_segment(q1, p1, q2):
        return True
    if abs(o4) <= 1e-6 and on_segment(q1, p2, q2):
        return True

    return False


def classify_side(
    a: tuple[float, float] | Point2D,
    b: tuple[float, float] | Point2D,
    p: tuple[float, float] | Point2D,
    tolerance: float = 0.0,
) -> Literal["positive", "negative", "on_line"]:
    """Classify which side of boundary line AB point P is on.

    Uses signed perpendicular distance in pixels.
    If within `[-tolerance, +tolerance]` pixels of the line, returns 'on_line'.
    Otherwise returns 'positive' (orientation > 0) or 'negative' (orientation < 0).
    """
    s_dist = signed_perpendicular_distance(a, b, p)
    if abs(s_dist) <= tolerance:
        return "on_line"
    return "positive" if s_dist > 0 else "negative"


def check_boundary_crossing(
    a: tuple[float, float] | Point2D,
    b: tuple[float, float] | Point2D,
    prev_point: tuple[float, float],
    curr_point: tuple[float, float],
    restricted_side: Literal["positive", "negative"] = "positive",
    tolerance: float = 5.0,
) -> tuple[bool, Literal["UNRESTRICTED_TO_RESTRICTED", "RESTRICTED_TO_UNRESTRICTED", "NONE"]]:
    """Determine if moving from prev_point to curr_point crossed the boundary line AB.

    Takes jitter/noise protection into account:
    - Touching the line or oscillating inside [-tolerance, +tolerance] does NOT trigger crossing.
    - Crossing requires transitioning across the boundary line.
    - Also verifies that the movement segment intersects the boundary segment (or within line bounds).

    Returns:
        (crossed_into_restricted, direction)
    """
    # Quick check for identical points (no movement)
    if (
        abs(curr_point[0] - prev_point[0]) < 1e-5
        and abs(curr_point[1] - prev_point[1]) < 1e-5
    ):
        return False, "NONE"

    ax = a.x if isinstance(a, Point2D) else a[0]
    ay = a.y if isinstance(a, Point2D) else a[1]
    bx = b.x if isinstance(b, Point2D) else b[0]
    by = b.y if isinstance(b, Point2D) else b[1]
    boundary_a = (ax, ay)
    boundary_b = (bx, by)

    # 1. Orientation of both points with respect to boundary line AB
    prev_ori = orientation(boundary_a, boundary_b, prev_point)
    curr_ori = orientation(boundary_a, boundary_b, curr_point)

    # Pure touching (one is exactly 0 and other doesn't cross) is not a crossing
    if (prev_ori > 0 and curr_ori > 0) or (prev_ori < 0 and curr_ori < 0):
        return False, "NONE"

    if prev_ori == 0.0 and curr_ori == 0.0:
        return False, "NONE"

    # 2. Check segment intersection (the path must actually span across the boundary line segment)
    # Check intersection between path prev_point->curr_point and boundary segment A->B
    # Allow margin equal to tolerance for segment bounds
    intersects = segments_intersect(prev_point, curr_point, boundary_a, boundary_b, tolerance=tolerance)
    if not intersects:
        # If the track crossed the infinite line far outside segment AB, ignore
        return False, "NONE"

    # 3. Check jitter dead-zone
    # The current point should be beyond the tolerance distance on its destination side
    # to avoid triggering on sensor jitter right on the boundary.
    curr_dist = perpendicular_distance(boundary_a, boundary_b, curr_point)
    prev_dist = perpendicular_distance(boundary_a, boundary_b, prev_point)

    # If both points are within the dead-zone, treat as noise/jitter
    if curr_dist < tolerance and prev_dist < tolerance:
        return False, "NONE"

    # 4. Determine direction
    unrestricted_side = "negative" if restricted_side == "positive" else "positive"

    # Case A: From unrestricted side to restricted side
    if (
        (restricted_side == "positive" and prev_ori <= 0 and curr_ori > 0)
        or (restricted_side == "negative" and prev_ori >= 0 and curr_ori < 0)
    ):
        return True, "UNRESTRICTED_TO_RESTRICTED"

    # Case B: From restricted side to unrestricted side
    if (
        (restricted_side == "positive" and prev_ori >= 0 and curr_ori < 0)
        or (restricted_side == "negative" and prev_ori <= 0 and curr_ori > 0)
    ):
        return False, "RESTRICTED_TO_UNRESTRICTED"

    return False, "NONE"
