"""Deterministic behavior analysis engine for tracked objects.

Analyzes track history and produces behavioral observations:
- LOITERING: Object remains in limited area for sustained period
- STATIONARY: Very little movement over time
- RAPID_MOVEMENT: Fast movement based on speed calculation
- DIRECTION_REVERSAL: Meaningful change in movement direction
- REPEATED_APPROACH: Repeated approaches to boundary without crossing
- REPEATED_INTRUSION: Same subject repeatedly crosses boundary
- ABNORMAL_MOVEMENT: Combination of unusual behaviors

All behaviors are deterministic and explainable.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

from app.ai.behavior_schemas import (
    BEHAVIOR_CONTRIBUTIONS,
    BehaviorAssessment,
    BehaviorObservationSchema,
    BehaviorSeverity,
    BehaviorType,
)
from app.ai.track_history import TrackRecord

logger = logging.getLogger(__name__)

# Configuration constants (tunable)
DEFAULT_LOITERING_MIN_DURATION_SECONDS = 30
DEFAULT_LOITERING_MAX_DISPLACEMENT_PIXELS = 50
DEFAULT_STATIONARY_MAX_DISPLACEMENT_PIXELS = 20
DEFAULT_STATIONARY_MIN_FRAMES = 10
DEFAULT_RAPID_MOVEMENT_THRESHOLD_PIXELS_PER_SECOND = 100  # pixels/sec
DEFAULT_DIRECTION_REVERSAL_ANGLE_THRESHOLD_DEGREES = 120
DEFAULT_MIN_HISTORY_FRAMES = 5


def calculate_distance(p1: tuple[float, float], p2: tuple[float, float]) -> float:
    """Calculate Euclidean distance between two points."""
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    return math.sqrt(dx * dx + dy * dy)


def calculate_angle(vector: tuple[float, float]) -> float:
    """Calculate angle of a vector in degrees [0, 360)."""
    if vector == (0, 0):
        return 0
    angle_rad = math.atan2(vector[1], vector[0])
    angle_deg = math.degrees(angle_rad)
    return (angle_deg + 360) % 360


def calculate_angle_difference(angle1: float, angle2: float) -> float:
    """Calculate minimum angle difference between two angles in degrees [0, 180]."""
    diff = abs(angle1 - angle2)
    if diff > 180:
        diff = 360 - diff
    return diff


def get_behavior_severity(
    behavior_type: BehaviorType,
    confidence: float,
) -> BehaviorSeverity:
    """Determine behavior severity deterministically based on type and confidence.
    
    Args:
        behavior_type: Type of detected behavior
        confidence: Confidence in detection [0, 1]
        
    Returns:
        Severity classification: LOW, MEDIUM, HIGH, or CRITICAL
    """
    # High-confidence observations are more concerning
    if confidence >= 0.9:
        if behavior_type in ("REPEATED_INTRUSION", "ABNORMAL_MOVEMENT"):
            return "CRITICAL"
        elif behavior_type in ("DIRECTION_REVERSAL", "RAPID_MOVEMENT"):
            return "HIGH"
        elif behavior_type in ("REPEATED_APPROACH", "LOITERING"):
            return "MEDIUM"
        else:
            return "LOW"
    elif confidence >= 0.7:
        if behavior_type in ("REPEATED_INTRUSION",):
            return "HIGH"
        elif behavior_type in ("ABNORMAL_MOVEMENT", "DIRECTION_REVERSAL"):
            return "MEDIUM"
        else:
            return "LOW"
    else:
        # Lower confidence behaviors
        return "LOW"


def detect_loitering(
    track: TrackRecord,
    min_duration_seconds: float = DEFAULT_LOITERING_MIN_DURATION_SECONDS,
    max_displacement_pixels: float = DEFAULT_LOITERING_MAX_DISPLACEMENT_PIXELS,
    fps: float = 30.0,  # Assumed FPS if timestamps unavailable
) -> BehaviorObservationSchema | None:
    """Detect if object is loitering (staying in limited area for sustained period).
    
    Args:
        track: TrackRecord from track history
        min_duration_seconds: Minimum duration to classify as loitering
        max_displacement_pixels: Maximum movement radius within which to consider loitering
        fps: Assumed frames per second if timestamps unavailable
        
    Returns:
        BehaviorObservationSchema if loitering detected, None otherwise
    """
    if not track.position_log or len(track.position_log) < DEFAULT_MIN_HISTORY_FRAMES:
        return None
    
    positions = list(track.position_log)
    
    # Calculate total displacement (from first to last position)
    if len(positions) < 2:
        return None
    
    first_pos = positions[0]
    last_pos = positions[-1]
    total_displacement = calculate_distance(first_pos, last_pos)
    
    # Calculate frames span
    frames_span = track.last_seen_frame - track.first_seen_frame
    if frames_span == 0:
        frames_span = len(positions) - 1
    
    # Estimate duration
    estimated_duration_seconds = frames_span / fps
    
    # Check loitering criteria
    if (total_displacement <= max_displacement_pixels and 
        estimated_duration_seconds >= min_duration_seconds):
        
        # Calculate max distance from starting point (to characterize the area)
        max_displacement_from_start = max(
            calculate_distance(first_pos, pos) for pos in positions
        )
        
        severity = get_behavior_severity("LOITERING", 0.8)
        
        return BehaviorObservationSchema(
            behavior_type="LOITERING",
            severity=severity,
            confidence=0.8,  # Deterministic based on data quality
            duration_seconds=estimated_duration_seconds,
            evidence={
                "total_displacement_pixels": round(total_displacement, 2),
                "max_radius_pixels": round(max_displacement_from_start, 2),
                "duration_seconds": round(estimated_duration_seconds, 2),
            },
            reason=(
                f"Object remained in area with {max_displacement_from_start:.1f}px radius "
                f"for {estimated_duration_seconds:.1f}s (>= {min_duration_seconds}s threshold)"
            ),
            detected_at=datetime.now(timezone.utc),
        )
    
    return None


def detect_stationary(
    track: TrackRecord,
    max_displacement_pixels: float = DEFAULT_STATIONARY_MAX_DISPLACEMENT_PIXELS,
    min_frames: int = DEFAULT_STATIONARY_MIN_FRAMES,
    fps: float = 30.0,
) -> BehaviorObservationSchema | None:
    """Detect if object is stationary (very little movement).
    
    Args:
        track: TrackRecord from track history
        max_displacement_pixels: Maximum movement to classify as stationary
        min_frames: Minimum frames required for stationary classification
        fps: Assumed frames per second
        
    Returns:
        BehaviorObservationSchema if stationary detected, None otherwise
    """
    if not track.position_log or len(track.position_log) < min_frames:
        return None
    
    positions = list(track.position_log)
    
    # Calculate total displacement
    first_pos = positions[0]
    last_pos = positions[-1]
    total_displacement = calculate_distance(first_pos, last_pos)
    
    if total_displacement <= max_displacement_pixels:
        frames_span = max(track.last_seen_frame - track.first_seen_frame, len(positions) - 1)
        duration_seconds = frames_span / fps
        
        severity = get_behavior_severity("STATIONARY", 0.85)
        
        return BehaviorObservationSchema(
            behavior_type="STATIONARY",
            severity=severity,
            confidence=0.85,
            duration_seconds=duration_seconds,
            evidence={
                "total_displacement_pixels": round(total_displacement, 2),
                "max_displacement_threshold": max_displacement_pixels,
                "frame_duration": frames_span,
            },
            reason=(
                f"Object moved only {total_displacement:.1f}px over {frames_span} frames "
                f"(<= {max_displacement_pixels}px threshold)"
            ),
            detected_at=datetime.now(timezone.utc),
        )
    
    return None


def detect_rapid_movement(
    track: TrackRecord,
    threshold_pixels_per_second: float = DEFAULT_RAPID_MOVEMENT_THRESHOLD_PIXELS_PER_SECOND,
    fps: float = 30.0,
) -> BehaviorObservationSchema | None:
    """Detect rapid movement based on speed.
    
    Args:
        track: TrackRecord from track history
        threshold_pixels_per_second: Threshold speed in pixels/second
        fps: Assumed frames per second
        
    Returns:
        BehaviorObservationSchema if rapid movement detected, None otherwise
    """
    if not track.position_log or len(track.position_log) < 3:
        return None
    
    positions = list(track.position_log)
    
    # Calculate speeds between consecutive frames
    frame_interval_seconds = 1.0 / fps
    speeds = []
    
    for i in range(1, len(positions)):
        distance = calculate_distance(positions[i-1], positions[i])
        speed = distance / frame_interval_seconds
        speeds.append(speed)
    
    # Check if any speed exceeds threshold
    max_speed = max(speeds) if speeds else 0
    
    if max_speed >= threshold_pixels_per_second:
        avg_speed = sum(speeds) / len(speeds) if speeds else 0
        
        severity = get_behavior_severity("RAPID_MOVEMENT", 0.8)
        
        return BehaviorObservationSchema(
            behavior_type="RAPID_MOVEMENT",
            severity=severity,
            confidence=0.8,
            evidence={
                "max_speed_pixels_per_second": round(max_speed, 2),
                "avg_speed_pixels_per_second": round(avg_speed, 2),
                "threshold_pixels_per_second": threshold_pixels_per_second,
            },
            reason=(
                f"Object reached speed of {max_speed:.1f}px/s "
                f"(>= {threshold_pixels_per_second}px/s threshold)"
            ),
            detected_at=datetime.now(timezone.utc),
        )
    
    return None


def detect_direction_reversal(
    track: TrackRecord,
    angle_threshold_degrees: float = DEFAULT_DIRECTION_REVERSAL_ANGLE_THRESHOLD_DEGREES,
    fps: float = 30.0,
) -> BehaviorObservationSchema | None:
    """Detect meaningful change in movement direction.
    
    Args:
        track: TrackRecord from track history
        angle_threshold_degrees: Minimum angle change to classify as reversal
        fps: Assumed frames per second
        
    Returns:
        BehaviorObservationSchema if direction reversal detected, None otherwise
    """
    if not track.position_log or len(track.position_log) < 3:
        return None
    
    positions = list(track.position_log)
    
    # Calculate movement vectors between consecutive position pairs
    vectors = []
    for i in range(1, len(positions)):
        dx = positions[i][0] - positions[i-1][0]
        dy = positions[i][1] - positions[i-1][1]
        if (dx, dy) != (0, 0):  # Only add non-zero vectors
            vectors.append((dx, dy))
    
    if len(vectors) < 2:
        return None
    
    # Find the maximum angle change between consecutive vectors
    max_angle_change = 0
    angle_change_index = -1
    
    for i in range(1, len(vectors)):
        angle1 = calculate_angle(vectors[i-1])
        angle2 = calculate_angle(vectors[i])
        angle_diff = calculate_angle_difference(angle1, angle2)
        
        if angle_diff > max_angle_change:
            max_angle_change = angle_diff
            angle_change_index = i
    
    if max_angle_change >= angle_threshold_degrees:
        severity = get_behavior_severity("DIRECTION_REVERSAL", 0.75)
        
        return BehaviorObservationSchema(
            behavior_type="DIRECTION_REVERSAL",
            severity=severity,
            confidence=0.75,
            evidence={
                "max_angle_change_degrees": round(max_angle_change, 2),
                "threshold_degrees": angle_threshold_degrees,
                "vector_count": len(vectors),
            },
            reason=(
                f"Movement direction changed by {max_angle_change:.1f}° "
                f"(>= {angle_threshold_degrees}° threshold)"
            ),
            detected_at=datetime.now(timezone.utc),
        )
    
    return None


def detect_repeated_approach(
    track: TrackRecord,
    approach_history: dict[int, list[tuple[int, float]]] | None = None,
    boundary_distance_threshold_pixels: float = 100.0,
    min_approach_count: int = 2,
) -> BehaviorObservationSchema | None:
    """Detect repeated approaches toward a boundary.
    
    This is a simplified detector that requires external context (boundary position).
    In a full implementation, this would be called with actual boundary coordinates.
    For now, we return None to indicate this detection requires boundary context.
    
    Args:
        track: TrackRecord from track history
        approach_history: Historical approach records (not used in base implementation)
        boundary_distance_threshold_pixels: Distance threshold for "approaching"
        min_approach_count: Minimum repetitions to classify as repeated
        
    Returns:
        BehaviorObservationSchema if repeated approach detected, None otherwise
    """
    # Requires boundary context which isn't available in basic track record
    # Implementation would be called at higher level with boundary data
    return None


def detect_repeated_intrusion(
    track: TrackRecord,
    intrusion_count: int = 1,
    min_repeat_threshold: int = 2,
) -> BehaviorObservationSchema | None:
    """Detect if same track has repeatedly crossed boundaries.
    
    Args:
        track: TrackRecord from track history
        intrusion_count: Number of intrusion events for this track
        min_repeat_threshold: Minimum count to classify as repeated
        
    Returns:
        BehaviorObservationSchema if repeated intrusion detected, None otherwise
    """
    if intrusion_count >= min_repeat_threshold:
        severity = get_behavior_severity("REPEATED_INTRUSION", 0.9)
        
        return BehaviorObservationSchema(
            behavior_type="REPEATED_INTRUSION",
            severity=severity,
            confidence=0.9,
            evidence={
                "intrusion_count": intrusion_count,
                "min_threshold": min_repeat_threshold,
            },
            reason=(
                f"Track {track.track_id} has crossed boundary {intrusion_count} times "
                f"(>= {min_repeat_threshold} threshold)"
            ),
            detected_at=datetime.now(timezone.utc),
        )
    
    return None


def detect_abnormal_movement(
    observations: list[BehaviorObservationSchema],
) -> BehaviorObservationSchema | None:
    """Detect abnormal movement as combination of unusual behaviors.
    
    Args:
        observations: List of other detected behavior observations
        
    Returns:
        BehaviorObservationSchema if abnormal movement pattern detected, None otherwise
    """
    if not observations:
        return None
    
    # Count behavior types
    behavior_types = [obs.behavior_type for obs in observations]
    
    # Abnormal patterns:
    # - Multiple direction reversals
    # - Rapid movement + direction reversals
    # - Repeated rapid stops and starts
    
    direction_reversals = behavior_types.count("DIRECTION_REVERSAL")
    rapid_movements = behavior_types.count("RAPID_MOVEMENT")
    reversals_and_movement = direction_reversals > 0 and rapid_movements > 0
    
    is_abnormal = (
        direction_reversals >= 2 or
        reversals_and_movement or
        (direction_reversals > 0 and rapid_movements > 1)
    )
    
    if is_abnormal:
        contributing_behaviors = ", ".join(
            str(obs.behavior_type) for obs in observations 
            if obs.behavior_type in ("DIRECTION_REVERSAL", "RAPID_MOVEMENT")
        )
        
        severity = get_behavior_severity("ABNORMAL_MOVEMENT", 0.8)
        
        return BehaviorObservationSchema(
            behavior_type="ABNORMAL_MOVEMENT",
            severity=severity,
            confidence=0.8,
            evidence={
                "direction_reversals": float(direction_reversals),
                "rapid_movements": float(rapid_movements),
                "contributing_count": float(len(contributing_behaviors.split(", ")) if contributing_behaviors else 0),
            },
            reason=(
                f"Abnormal movement pattern detected: {direction_reversals} direction reversals, "
                f"{rapid_movements} rapid movements. Contributing behaviors: {contributing_behaviors or 'none'}"
            ),
            detected_at=datetime.now(timezone.utc),
        )
    
    return None


class BehaviorEngine:
    """Analyzes track history and produces behavior assessments."""
    
    def __init__(
        self,
        loitering_min_duration_seconds: float = DEFAULT_LOITERING_MIN_DURATION_SECONDS,
        loitering_max_displacement_pixels: float = DEFAULT_LOITERING_MAX_DISPLACEMENT_PIXELS,
        stationary_max_displacement_pixels: float = DEFAULT_STATIONARY_MAX_DISPLACEMENT_PIXELS,
        rapid_movement_threshold_pixels_per_second: float = DEFAULT_RAPID_MOVEMENT_THRESHOLD_PIXELS_PER_SECOND,
        direction_reversal_angle_threshold_degrees: float = DEFAULT_DIRECTION_REVERSAL_ANGLE_THRESHOLD_DEGREES,
        fps: float = 30.0,
    ) -> None:
        """Initialize behavior engine with configurable thresholds.
        
        Args:
            loitering_min_duration_seconds: Minimum duration for loitering detection
            loitering_max_displacement_pixels: Max movement radius for loitering
            stationary_max_displacement_pixels: Max movement for stationary
            rapid_movement_threshold_pixels_per_second: Speed threshold for rapid movement
            direction_reversal_angle_threshold_degrees: Angle threshold for direction reversal
            fps: Assumed frames per second (used for timestamps)
        """
        self.loitering_min_duration_seconds = loitering_min_duration_seconds
        self.loitering_max_displacement_pixels = loitering_max_displacement_pixels
        self.stationary_max_displacement_pixels = stationary_max_displacement_pixels
        self.rapid_movement_threshold_pixels_per_second = rapid_movement_threshold_pixels_per_second
        self.direction_reversal_angle_threshold_degrees = direction_reversal_angle_threshold_degrees
        self.fps = fps
    
    def analyze_track(
        self,
        camera_id: str,
        track: TrackRecord,
        intrusion_count: int = 1,
    ) -> BehaviorAssessment | None:
        """Analyze a single track and produce behavior assessment.
        
        Args:
            camera_id: Camera ID where track was observed
            track: TrackRecord from track history
            intrusion_count: Number of intrusions for this track
            
        Returns:
            BehaviorAssessment if behaviors detected, None if insufficient data
        """
        if not track.position_log or len(track.position_log) < DEFAULT_MIN_HISTORY_FRAMES:
            return None
        
        # Detect individual behaviors
        observations: list[BehaviorObservationSchema] = []
        
        # Order matters: detect specific behaviors first, then composite ones
        loitering = detect_loitering(
            track,
            self.loitering_min_duration_seconds,
            self.loitering_max_displacement_pixels,
            self.fps,
        )
        if loitering:
            observations.append(loitering)
        
        stationary = detect_stationary(
            track,
            self.stationary_max_displacement_pixels,
            fps=self.fps,
        )
        if stationary:
            observations.append(stationary)
        
        rapid = detect_rapid_movement(
            track,
            self.rapid_movement_threshold_pixels_per_second,
            self.fps,
        )
        if rapid:
            observations.append(rapid)
        
        direction = detect_direction_reversal(
            track,
            self.direction_reversal_angle_threshold_degrees,
            self.fps,
        )
        if direction:
            observations.append(direction)
        
        repeated_intrusion = detect_repeated_intrusion(track, intrusion_count)
        if repeated_intrusion:
            observations.append(repeated_intrusion)
        
        # Detect abnormal movement based on other observations
        abnormal = detect_abnormal_movement(observations)
        if abnormal:
            observations.append(abnormal)
        
        # If no behaviors detected, return None
        if not observations:
            return None
        
        # Calculate composite behavior score
        behavior_score = 0
        for obs in observations:
            contribution = BEHAVIOR_CONTRIBUTIONS.get(obs.behavior_type, 0)
            behavior_score += contribution
        
        # Clamp to [0, 100]
        behavior_score = min(100, max(0, behavior_score))
        
        # Identify primary behavior (highest contribution)
        primary_behavior = max(
            observations,
            key=lambda obs: BEHAVIOR_CONTRIBUTIONS.get(obs.behavior_type, 0),
        ).behavior_type if observations else None
        
        # Calculate duration window
        frames_span = max(track.last_seen_frame - track.first_seen_frame, 1)
        duration_seconds = frames_span / self.fps
        
        return BehaviorAssessment(
            id=f"BEH-{camera_id}-{track.track_id}-{int(datetime.now(timezone.utc).timestamp() * 1000)}",
            camera_id=camera_id,
            track_id=track.track_id,
            observations=observations,
            behavior_score=behavior_score,
            primary_behavior=primary_behavior,
            assessed_at=datetime.now(timezone.utc),
            duration_window_seconds=duration_seconds,
            created_at=datetime.now(timezone.utc),
        )


# Global behavior engine instance
behavior_engine = BehaviorEngine()
