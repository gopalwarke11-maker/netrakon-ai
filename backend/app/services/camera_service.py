"""Database-backed camera business logic."""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.db.models import CameraRecord
from app.db.session import SessionLocal
from app.models.camera import Camera, CameraCreate, CameraUpdate


def _camera(row: CameraRecord) -> Camera:
    return Camera.model_validate(row, from_attributes=True)


class CameraService:
    def list(self) -> list[Camera]:
        with SessionLocal() as db:
            return [_camera(row) for row in db.scalars(select(CameraRecord).order_by(CameraRecord.id)).all()]

    def get(self, camera_id: str) -> Camera | None:
        with SessionLocal() as db:
            row = db.get(CameraRecord, camera_id)
            return _camera(row) if row else None

    def create(self, payload: CameraCreate) -> Camera:
        with SessionLocal.begin() as db:
            ids = set(db.scalars(select(CameraRecord.id)).all())
            number = 1
            while f"CAM-{number:02d}" in ids:
                number += 1
            row = CameraRecord(id=f"CAM-{number:02d}", **payload.model_dump())
            db.add(row)
            db.flush()
            return _camera(row)

    def update(self, camera_id: str, payload: CameraUpdate) -> Camera | None:
        with SessionLocal.begin() as db:
            row = db.get(CameraRecord, camera_id)
            if row is None:
                return None
            for field, value in payload.model_dump().items():
                setattr(row, field, value)
            db.flush()
            return _camera(row)

    def delete(self, camera_id: str) -> bool:
        try:
            with SessionLocal.begin() as db:
                row = db.get(CameraRecord, camera_id)
                if row is None:
                    return False
                db.delete(row)
            return True
        except IntegrityError as exc:
            raise ValueError("Camera cannot be deleted while boundaries reference it.") from exc


camera_service = CameraService()
