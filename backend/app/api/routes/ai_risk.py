"""Risk assessment API endpoints.

Provides access to calculated risk assessments for intrusion events.
Includes a deterministic test endpoint for validation.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.ai.risk_engine import calculate_risk
from app.ai.risk_schemas import RiskTestRequest, RiskTestResponse, RiskAssessment
from app.models.intrusion import IntrusionEvent, IntrusionPoint, CrossingDirection
from app.services.risk_service import risk_service
from app.services.intrusion_service import intrusion_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["Risk Intelligence"])


@router.get(
    "/risk/{event_id}",
    response_model=RiskAssessment,
    summary="Get risk assessment for an intrusion event",
    description="Retrieve the calculated risk score, level, and contributing factors for a confirmed intrusion.",
)
def get_event_risk(event_id: str) -> RiskAssessment:
    """Retrieve the risk assessment for a specific intrusion event.
    
    Args:
        event_id: The intrusion event ID (e.g., EVT-0001)
        
    Returns:
        RiskAssessment with score (0-100), level, and factors
        
    Raises:
        404: Event not found or risk not calculated
    """
    risk = risk_service.get_risk(event_id)
    if not risk:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Risk assessment not found for event {event_id}"
        )
    return risk


@router.post(
    "/risk-test",
    response_model=RiskTestResponse,
    summary="Test risk scoring with synthetic parameters",
    description=(
        "Calculate risk score for arbitrary combinations of severity, object type, "
        "confidence, direction, and repeat count. "
        "**This is a deterministic test endpoint** for validation and debugging."
    ),
)
def test_risk_scoring(payload: RiskTestRequest) -> RiskTestResponse:
    """Test risk scoring with synthetic parameters.
    
    Allows validation of risk calculation without requiring real events.
    
    Args:
        payload: Test parameters including severity, object class, confidence, direction
        
    Returns:
        RiskTestResponse with calculated score, level, and factors
        
    Raises:
        422: Invalid input parameters
    """
    # Create a synthetic intrusion event for testing
    synthetic_event = IntrusionEvent(
        id="TEST-EVENT",
        camera_id="TEST-CAM",
        boundary_id="TEST-BND",
        boundary_name="Test Boundary",
        track_id=9999,
        object_class=payload.object_class,
        confidence=payload.confidence,
        timestamp=datetime.now(timezone.utc),
        current_anchor=IntrusionPoint(x=100, y=100),
        previous_anchor=IntrusionPoint(x=0, y=0),
        crossing_direction=payload.direction,  # type: ignore
        severity=payload.severity,  # type: ignore
        alert_id=None,
    )
    
    # Calculate risk
    assessment = calculate_risk(synthetic_event, repeat_count=payload.repeat_count)
    
    return RiskTestResponse(
        risk_score=assessment.risk_score,
        risk_level=assessment.risk_level,
        factors=[
            {
                "factor": f.factor,
                "value": f.value,
                "contribution": f.contribution,
                "reason": f.reason,
            }
            for f in assessment.factors
        ],
        test_mode=True,
        input_params={
            "severity": payload.severity,
            "object_class": payload.object_class,
            "confidence": payload.confidence,
            "direction": payload.direction,
            "repeat_count": payload.repeat_count,
        }
    )
