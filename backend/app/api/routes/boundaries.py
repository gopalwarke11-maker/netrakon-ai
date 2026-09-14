"""Virtual Security Boundary API routes."""

import logging
from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.models.boundary import (
    VirtualBoundary,
    VirtualBoundaryCreate,
    VirtualBoundaryUpdate,
)
from app.services.boundary_service import boundary_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/boundaries", tags=["boundaries"])


@router.get("", response_model=list[VirtualBoundary], summary="List virtual boundaries")
def list_boundaries(
    camera_id: str | None = Query(default=None, description="Filter boundaries by camera ID"),
    enabled: bool | None = Query(default=None, description="Filter boundaries by enabled status"),
) -> list[VirtualBoundary]:
    """List all virtual security boundaries, optionally filtered by camera or status."""
    return boundary_service.list(camera_id=camera_id, enabled=enabled)


@router.get("/{boundary_id}", response_model=VirtualBoundary, summary="Get a virtual boundary")
def get_boundary(boundary_id: str) -> VirtualBoundary:
    """Retrieve details for a specific virtual security boundary."""
    boundary = boundary_service.get(boundary_id)
    if boundary is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Boundary '{boundary_id}' not found.",
        )
    return boundary


@router.post(
    "",
    response_model=VirtualBoundary,
    status_code=status.HTTP_201_CREATED,
    summary="Create a virtual boundary",
)
def create_boundary(payload: VirtualBoundaryCreate) -> VirtualBoundary:
    """Create a new virtual security boundary associated with a camera."""
    try:
        return boundary_service.create(payload)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except IntegrityError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Boundary conflicts with existing data.") from exc
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable.") from exc


@router.put("/{boundary_id}", response_model=VirtualBoundary, summary="Update a virtual boundary")
def update_boundary(boundary_id: str, payload: VirtualBoundaryUpdate) -> VirtualBoundary:
    """Update properties of an existing virtual security boundary."""
    try:
        updated = boundary_service.update(boundary_id, payload)
        if updated is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Boundary '{boundary_id}' not found.",
            )
        return updated
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable.") from exc


@router.delete("/{boundary_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a virtual boundary")
def delete_boundary(boundary_id: str) -> None:
    """Delete a virtual security boundary."""
    try:
        deleted = boundary_service.delete(boundary_id)
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable.") from exc
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Boundary '{boundary_id}' not found.",
        )
