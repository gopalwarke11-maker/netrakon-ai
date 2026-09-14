"""Pydantic schemas for risk assessment API and persistence."""

from datetime import datetime
from pydantic import BaseModel, Field


class RiskFactorSchema(BaseModel):
    """A single factor contributing to the risk score."""
    
    factor: str = Field(description="Factor name (e.g., intrusion_severity, object_type)")
    value: str = Field(description="The actual value (e.g., HIGH, person, 0.85)")
    contribution: int = Field(description="Points added to risk score", ge=0, le=100)
    reason: str = Field(description="Human-readable explanation")


class RiskAssessmentBase(BaseModel):
    """Base schema for risk assessment."""
    
    risk_score: int = Field(description="Risk score 0-100", ge=0, le=100)
    risk_level: str = Field(description="Risk level: LOW, MEDIUM, HIGH, CRITICAL")
    factors: list[RiskFactorSchema] = Field(description="Contributing risk factors")


class RiskAssessmentCreate(RiskAssessmentBase):
    """Risk assessment data for persistence."""
    
    assessed_at: datetime = Field(description="When the assessment was calculated")
    intrusion_event_id: str = Field(description="Reference to intrusion event")
    camera_id: str | None = Field(default=None)
    boundary_id: str | None = Field(default=None)
    track_id: int = Field(description="Track ID of intruding object")


class RiskAssessment(RiskAssessmentCreate):
    """Complete risk assessment response."""
    
    pass


class RiskTestRequest(BaseModel):
    """Request for POST /api/ai/risk-test endpoint."""
    
    severity: str = Field(description="Intrusion severity: LOW, MEDIUM, HIGH, CRITICAL")
    object_class: str = Field(default="person", description="COCO object class")
    confidence: float | None = Field(default=0.85, ge=0.0, le=1.0, description="Detection confidence")
    direction: str = Field(
        default="UNRESTRICTED_TO_RESTRICTED",
        description="Crossing direction"
    )
    repeat_count: int = Field(default=1, ge=1, description="Number of repeated intrusions")


class RiskTestResponse(RiskAssessmentBase):
    """Response for POST /api/ai/risk-test endpoint."""
    
    test_mode: bool = Field(default=True, description="True for synthetic test")
    input_params: dict = Field(description="The test parameters used")
