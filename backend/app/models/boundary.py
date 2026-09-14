"""Virtual Security Boundary schemas."""

from datetime import datetime, timezone
from typing import Literal
from pydantic import BaseModel, Field, model_validator

from app.models.alert import AlertSeverity


class Point2D(BaseModel):
    """2D point in image pixel coordinates.
    
    Origin (0, 0) is at the top-left corner of the image.
    x increases rightwards, y increases downwards.
    """
    x: float = Field(ge=0.0, description="X coordinate in pixels (>= 0)")
    y: float = Field(ge=0.0, description="Y coordinate in pixels (>= 0)")


class VirtualBoundaryBase(BaseModel):
    """Base schema for a virtual security boundary line."""
    name: str = Field(min_length=1, max_length=120, description="Human-readable boundary name")
    camera_id: str = Field(min_length=1, max_length=80, description="Camera this boundary belongs to")
    enabled: bool = Field(default=True, description="Whether this boundary is actively monitored")
    point_a: Point2D = Field(description="First point (x1, y1) defining the boundary line segment")
    point_b: Point2D = Field(description="Second point (x2, y2) defining the boundary line segment")
    restricted_side: Literal["positive", "negative"] = Field(
        default="positive",
        description=(
            "Which side of the vector AB is considered the restricted/intrusion zone. "
            "'positive' = orientation > 0 (to the right of vector AB in standard image coords); "
            "'negative' = orientation < 0 (to the left of vector AB)."
        ),
    )
    severity: AlertSeverity = Field(
        default="HIGH",
        description="Default alert severity triggered when this boundary is crossed",
    )
    tolerance: float = Field(
        default=5.0,
        ge=0.0,
        le=200.0,
        description="Dead-zone tolerance in pixels to absorb detector bounding-box jitter",
    )

    @model_validator(mode="after")
    def validate_distinct_points(self) -> "VirtualBoundaryBase":
        """Ensure point_a and point_b are not identical."""
        if (
            abs(self.point_a.x - self.point_b.x) < 1e-4
            and abs(self.point_a.y - self.point_b.y) < 1e-4
        ):
            raise ValueError("Boundary points A and B cannot be identical.")
        return self


class VirtualBoundaryCreate(VirtualBoundaryBase):
    """Request payload to create a new boundary. Optional custom ID can be supplied."""
    id: str | None = Field(
        default=None,
        min_length=1,
        max_length=80,
        description="Optional custom boundary ID (e.g. BND-0001). Auto-generated if omitted.",
    )


class VirtualBoundaryUpdate(BaseModel):
    """Request payload to update an existing boundary (full or partial)."""
    name: str | None = Field(default=None, min_length=1, max_length=120)
    camera_id: str | None = Field(default=None, min_length=1, max_length=80)
    enabled: bool | None = None
    point_a: Point2D | None = None
    point_b: Point2D | None = None
    restricted_side: Literal["positive", "negative"] | None = None
    severity: AlertSeverity | None = None
    tolerance: float | None = Field(default=None, ge=0.0, le=200.0)

    @model_validator(mode="after")
    def validate_points_if_both_set(self) -> "VirtualBoundaryUpdate":
        if self.point_a is not None and self.point_b is not None:
            if (
                abs(self.point_a.x - self.point_b.x) < 1e-4
                and abs(self.point_a.y - self.point_b.y) < 1e-4
            ):
                raise ValueError("Boundary points A and B cannot be identical.")
        return self


class VirtualBoundary(VirtualBoundaryBase):
    """Complete virtual boundary entity."""
    id: str = Field(description="Unique boundary identifier (e.g. BND-0001)")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
