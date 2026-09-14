"""Database-backed Virtual Security Boundary business logic."""

from sqlalchemy import select

from app.models.boundary import (
    Point2D,
    VirtualBoundary,
    VirtualBoundaryCreate,
    VirtualBoundaryUpdate,
)
from app.db.models import BoundaryRecord, CameraRecord
from app.db.session import SessionLocal


def _boundary(row: BoundaryRecord) -> VirtualBoundary:
    return VirtualBoundary(id=row.id, camera_id=row.camera_id, name=row.name, enabled=row.enabled,
        point_a=Point2D.model_validate(row.point_a), point_b=Point2D.model_validate(row.point_b),
        restricted_side=row.restricted_side, severity=row.severity, tolerance=row.tolerance,
        created_at=row.created_at, updated_at=row.updated_at)


class BoundaryService:

    def list(
        self,
        camera_id: str | None = None,
        enabled: bool | None = None,
    ) -> list[VirtualBoundary]:
        """List boundaries with optional camera and enabled filtering."""
        with SessionLocal() as db:
            query = select(BoundaryRecord).order_by(BoundaryRecord.id)
            if camera_id is not None: query = query.where(BoundaryRecord.camera_id == camera_id)
            if enabled is not None: query = query.where(BoundaryRecord.enabled == enabled)
            return [_boundary(row) for row in db.scalars(query).all()]

    def get(self, boundary_id: str) -> VirtualBoundary | None:
        """Get a boundary by its ID."""
        with SessionLocal() as db:
            row = db.get(BoundaryRecord, boundary_id)
            return _boundary(row) if row else None

    def get_by_camera(self, camera_id: str) -> list[VirtualBoundary]:
        """Get all boundaries registered for a specific camera."""
        return self.list(camera_id=camera_id)

    def create(self, payload: VirtualBoundaryCreate) -> VirtualBoundary:
        """Create a new boundary after validating camera existence and ID uniqueness.

        Raises:
            ValueError: If camera does not exist or duplicate boundary_id.
        """
        with SessionLocal.begin() as db:
            if db.get(CameraRecord, payload.camera_id) is None: raise ValueError(f"Camera '{payload.camera_id}' does not exist.")
            if payload.id and db.get(BoundaryRecord, payload.id): raise ValueError(f"Boundary with ID '{payload.id}' already exists.")
            if payload.id: bnd_id = payload.id
            else:
                ids = set(db.scalars(select(BoundaryRecord.id)).all()); number = 1
                while f"BND-{number:04d}" in ids: number += 1
                bnd_id = f"BND-{number:04d}"
            data = payload.model_dump(exclude={"id", "point_a", "point_b"})
            row = BoundaryRecord(id=bnd_id, **data, point_a=payload.point_a.model_dump(), point_b=payload.point_b.model_dump())
            db.add(row); db.flush(); return _boundary(row)

    def update(
        self,
        boundary_id: str,
        payload: VirtualBoundaryUpdate,
    ) -> VirtualBoundary | None:
        """Update an existing boundary.

        Raises:
            ValueError: If updated camera_id does not exist.
        """
        with SessionLocal.begin() as db:
            row = db.get(BoundaryRecord, boundary_id)
            if row is None: return None
            merged = VirtualBoundary.model_validate({**_boundary(row).model_dump(), **payload.model_dump(exclude_unset=True)})
            if merged.camera_id != row.camera_id and db.get(CameraRecord, merged.camera_id) is None: raise ValueError(f"Camera '{merged.camera_id}' does not exist.")
            for name, value in merged.model_dump(exclude={"id", "created_at", "updated_at"}).items():
                setattr(row, name, value if isinstance(value, dict) else value)
            db.flush(); return _boundary(row)

    def delete(self, boundary_id: str) -> bool:
        """Delete a boundary by ID."""
        with SessionLocal.begin() as db:
            row = db.get(BoundaryRecord, boundary_id)
            if row is None: return False
            db.delete(row)
        return True


boundary_service = BoundaryService()
