"""Deterministic, explainable Risk Intelligence Engine for intrusion events.

Evaluates confirmed intrusion events using explicit weighted factors to produce:
- risk_score (0-100, deterministic)
- risk_level (LOW, MEDIUM, HIGH, CRITICAL)
- risk_factors (list of contributing factors with explanations)
- confidence/metadata
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

from app.models.intrusion import IntrusionEvent, CrossingDirection

# Risk level thresholds
RISK_THRESHOLDS = {
    "LOW": (0, 24),
    "MEDIUM": (25, 49),
    "HIGH": (50, 74),
    "CRITICAL": (75, 100),
}

# Object type risk contributions (YOLO class names)
OBJECT_TYPE_CONTRIBUTIONS = {
    "person": 20,
    "car": 10,
    "truck": 15,
    "bus": 15,
    "motorcycle": 12,
    "bicycle": 8,
}

# Intrusion severity base contributions
SEVERITY_BASE_CONTRIBUTIONS = {
    "LOW": 10,
    "MEDIUM": 25,
    "HIGH": 40,
    "CRITICAL": 55,
}

# Confidence-based contributions
def get_confidence_contribution(confidence: float | None) -> tuple[int, str]:
    """Determine risk contribution based on detection confidence.
    
    Args:
        confidence: YOLO confidence [0, 1], or None
        
    Returns:
        (contribution_points, reason_text)
    """
    if confidence is None:
        return 0, "Confidence unavailable"
    
    if confidence < 0.40:
        return 0, f"Confidence {confidence:.2f} < 0.40 (low reliability)"
    elif confidence < 0.60:
        return 5, f"Confidence {confidence:.2f} (0.40–0.60, moderate reliability)"
    elif confidence < 0.80:
        return 10, f"Confidence {confidence:.2f} (0.60–0.80, good reliability)"
    else:
        return 15, f"Confidence {confidence:.2f} >= 0.80 (high reliability)"


@dataclass
class RiskFactor:
    """Represents one contributing factor to the overall risk score."""
    
    factor: str
    """Name of the factor (e.g., 'intrusion_severity', 'object_type')"""
    
    value: str
    """The actual value evaluated (e.g., 'HIGH', 'person', '0.85')"""
    
    contribution: int
    """Points added to risk score (0-100 clamped)"""
    
    reason: str
    """Human-readable explanation of why this contribution was assigned"""


@dataclass
class RiskAssessment:
    """Complete risk assessment for a confirmed intrusion event."""
    
    risk_score: int
    """Deterministic risk score [0, 100]"""
    
    risk_level: str
    """Risk classification: LOW, MEDIUM, HIGH, CRITICAL"""
    
    factors: list[RiskFactor]
    """Detailed breakdown of contributing factors"""
    
    assessed_at: datetime
    """Timestamp when assessment was calculated"""
    
    intrusion_event_id: str
    """Reference to the intrusion event"""
    
    camera_id: str | None
    """Camera where intrusion occurred"""
    
    boundary_id: str | None
    """Boundary that was crossed"""
    
    track_id: int
    """Track ID of the intruding object"""


def _get_direction_contribution(direction: CrossingDirection) -> tuple[int, str]:
    """Determine risk contribution based on crossing direction.
    
    Args:
        direction: Direction relative to restricted zone
        
    Returns:
        (contribution_points, reason_text)
    """
    if direction == "UNRESTRICTED_TO_RESTRICTED":
        return 15, "Crossing into restricted zone from unrestricted area"
    elif direction == "RESTRICTED_TO_UNRESTRICTED":
        return 5, "Crossing out of restricted zone"
    else:
        return 0, f"Unknown direction: {direction}"


def calculate_risk(
    event: IntrusionEvent,
    repeat_count: int = 1,
) -> RiskAssessment:
    """Calculate deterministic risk assessment for a confirmed intrusion.
    
    Args:
        event: Confirmed intrusion event with all detection context
        repeat_count: Number of times same track/camera/boundary has intruded (default 1)
        
    Returns:
        RiskAssessment with score (0-100), level, and contributing factors
    """
    factors: list[RiskFactor] = []
    total_score = 0
    
    # ── Factor 1: Intrusion Severity ──────────────────────────────────────
    severity_value = event.severity
    severity_contribution = SEVERITY_BASE_CONTRIBUTIONS.get(severity_value, 0)
    factors.append(RiskFactor(
        factor="intrusion_severity",
        value=severity_value,
        contribution=severity_contribution,
        reason=f"Confirmed {severity_value} severity intrusion"
    ))
    total_score += severity_contribution
    
    # ── Factor 2: Object Type ─────────────────────────────────────────────
    obj_class = event.object_class.lower()
    object_contribution = OBJECT_TYPE_CONTRIBUTIONS.get(obj_class, 0)
    factors.append(RiskFactor(
        factor="object_type",
        value=event.object_class,
        contribution=object_contribution,
        reason=f"Object class '{event.object_class}' identified" + (
            f" (+{object_contribution} risk)" if object_contribution > 0 else ""
        )
    ))
    total_score += object_contribution
    
    # ── Factor 3: Detection Confidence ────────────────────────────────────
    conf_contribution, conf_reason = get_confidence_contribution(event.confidence)
    factors.append(RiskFactor(
        factor="detection_confidence",
        value=f"{event.confidence:.2f}" if event.confidence is not None else "unknown",
        contribution=conf_contribution,
        reason=conf_reason
    ))
    total_score += conf_contribution
    
    # ── Factor 4: Crossing Direction ──────────────────────────────────────
    dir_contribution, dir_reason = _get_direction_contribution(event.crossing_direction)
    factors.append(RiskFactor(
        factor="direction",
        value=event.crossing_direction,
        contribution=dir_contribution,
        reason=dir_reason
    ))
    total_score += dir_contribution
    
    # ── Factor 5: Repeated Activity ───────────────────────────────────────
    repeat_contribution = 0
    if repeat_count >= 3:
        repeat_contribution = 10
        repeat_reason = f"3+ repeated intrusions on same camera/boundary/track"
    elif repeat_count == 2:
        repeat_contribution = 5
        repeat_reason = f"2nd intrusion on same camera/boundary/track"
    else:
        repeat_contribution = 0
        repeat_reason = f"First intrusion event for this track"
    
    factors.append(RiskFactor(
        factor="repeated_activity",
        value=str(repeat_count),
        contribution=repeat_contribution,
        reason=repeat_reason
    ))
    total_score += repeat_contribution
    
    # ── Clamp score to [0, 100] ──────────────────────────────────────────
    clamped_score = max(0, min(100, total_score))
    
    # ── Determine risk level ──────────────────────────────────────────────
    risk_level = "LOW"
    for level, (low, high) in RISK_THRESHOLDS.items():
        if low <= clamped_score <= high:
            risk_level = level
            break
    
    return RiskAssessment(
        risk_score=clamped_score,
        risk_level=risk_level,
        factors=factors,
        assessed_at=datetime.now(timezone.utc),
        intrusion_event_id=event.id,
        camera_id=event.camera_id,
        boundary_id=event.boundary_id,
        track_id=event.track_id,
    )
