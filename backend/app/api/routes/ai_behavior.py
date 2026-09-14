"""Behavior analysis API endpoints.

Provides access to behavior observations and deterministic test endpoint.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, status

from app.ai.behavior_engine import behavior_engine
from app.ai.behavior_schemas import (
    BehaviorAssessment,
    BehaviorTestRequest,
    BehaviorTestResponse,
)
from app.services.behavior_service import behavior_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["Behavior Analysis"])


@router.get(
    "/behavior/{behavior_id}",
    response_model=BehaviorAssessment,
    summary="Get behavior observation",
    description="Retrieve a stored behavior analysis observation.",
)
def get_behavior(behavior_id: str) -> BehaviorAssessment:
    """Retrieve a specific behavior observation.
    
    Args:
        behavior_id: The behavior observation ID
        
    Returns:
        BehaviorAssessment with observations and score
        
    Raises:
        404: Behavior observation not found
    """
    behavior = behavior_service.get_behavior(behavior_id)
    if not behavior:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Behavior observation not found: {behavior_id}",
        )
    return behavior


@router.get(
    "/behavior/track/{camera_id}/{track_id}",
    response_model=list[BehaviorAssessment],
    summary="Get track behaviors",
    description="Retrieve all behavior observations for a track.",
)
def get_track_behaviors(camera_id: str, track_id: int) -> list[BehaviorAssessment]:
    """Retrieve behavior observations for a specific track.
    
    Args:
        camera_id: Camera ID
        track_id: Track ID
        
    Returns:
        List of BehaviorAssessment records, ordered by recency
    """
    behaviors = behavior_service.get_track_behaviors(camera_id, track_id)
    return behaviors


@router.get(
    "/behavior/camera/{camera_id}",
    response_model=list[BehaviorAssessment],
    summary="Get camera behaviors",
    description="Retrieve recent behavior observations for a camera.",
)
def get_camera_behaviors(
    camera_id: str,
    limit: int = 100,
) -> list[BehaviorAssessment]:
    """Retrieve recent behavior observations for a camera.
    
    Args:
        camera_id: Camera ID
        limit: Maximum number of records (default 100, max 1000)
        
    Returns:
        List of recent BehaviorAssessment records
    """
    limit = min(limit, 1000)
    behaviors = behavior_service.get_camera_behaviors(camera_id, limit=limit)
    return behaviors


@router.post(
    "/behavior-test",
    response_model=BehaviorTestResponse,
    summary="Test behavior detection",
    description="Deterministic test endpoint for behavior detection validation.",
)
def test_behavior(request: BehaviorTestRequest) -> BehaviorTestResponse:
    """Test behavior detection with synthetic input.
    
    This is a development/testing endpoint. Results are deterministic based on input.
    Does not create actual behavior records or broadcast events.
    
    Args:
        request: BehaviorTestRequest with test parameters
        
    Returns:
        BehaviorTestResponse with test results and explanation
    """
    # Provide deterministic test responses
    behavior_type = request.behavior_type
    severity = request.severity
    confidence = request.confidence
    
    # Get the contribution for this behavior
    from app.ai.behavior_schemas import BEHAVIOR_CONTRIBUTIONS
    
    contribution = BEHAVIOR_CONTRIBUTIONS.get(behavior_type, 0)
    
    reason = (
        f"Test: {behavior_type} with {severity} severity and {confidence:.2f} confidence. "
        f"Contribution: +{contribution} points to behavior score."
    )
    
    return BehaviorTestResponse(
        test_mode=True,
        behavior_type=behavior_type,
        severity=severity,
        behavior_score=contribution,
        reason=reason,
        input_params={
            "camera_id": request.camera_id,
            "track_id": request.track_id,
            "behavior_type": behavior_type,
            "severity": severity,
            "duration_seconds": request.duration_seconds,
            "displacement_pixels": request.displacement_pixels,
            "confidence": confidence,
        },
    )
