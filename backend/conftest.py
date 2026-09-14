"""Pytest configuration and shared fixtures for regression suite."""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import SessionLocal
from app.db.models import CameraRecord, BoundaryRecord, IntrusionEventRecord, AlertRecord
from datetime import datetime, timezone
from sqlalchemy import delete


@pytest.fixture(scope="session", autouse=True)
def setup_test_data():
    """Populate test database with required test cameras and boundaries before any tests run."""
    with SessionLocal.begin() as db:
        # Create test cameras if they don't exist
        existing_cameras = db.query(CameraRecord).filter(CameraRecord.id.in_(["CAM-01", "CAM-02"])).first()
        
        if not existing_cameras:
            cameras = [
                CameraRecord(
                    id="CAM-01",
                    name="Test Camera 1",
                    sector="SECTOR 1",
                    location="Test Location 1",
                    status="ONLINE",
                    stream_url=None,
                    created_at=datetime.now(timezone.utc),
                ),
                CameraRecord(
                    id="CAM-02",
                    name="Test Camera 2",
                    sector="SECTOR 2",
                    location="Test Location 2",
                    status="ONLINE",
                    stream_url=None,
                    created_at=datetime.now(timezone.utc),
                ),
            ]
            for camera in cameras:
                db.add(camera)
            db.flush()
        
        # Create test boundaries that will be used by unit tests
        # These need to exist because intrusion_detector.process_tracks() calls
        # intrusion_service.create_with_alert() which has FK constraint to boundaries
        test_boundaries = [
            {"id": "BND-TEST-01", "camera_id": "CAM-01", "name": "Test Line"},
            {"id": "BND-MULTI", "camera_id": "CAM-01", "name": "Multi-track line"},
            {"id": "BND-C1", "camera_id": "CAM-01", "name": "Cam1 Boundary"},
            {"id": "BND-C2", "camera_id": "CAM-02", "name": "Cam2 Boundary"},
            {"id": "BND-A", "camera_id": "CAM-01", "name": "Boundary A"},
            {"id": "BND-B", "camera_id": "CAM-01", "name": "Boundary B"},
            {"id": "BND-DISABLED", "camera_id": "CAM-01", "name": "Disabled Boundary"},
            {"id": "BND-POS", "camera_id": "CAM-01", "name": "Positive Side"},
            {"id": "BND-NEG", "camera_id": "CAM-01", "name": "Negative Side"},
            {"id": "BND-DISAPP", "camera_id": "CAM-01", "name": "Disappear Boundary"},
            {"id": "BND-NEWID", "camera_id": "CAM-01", "name": "New ID Boundary"},
            {"id": "BND-0001", "camera_id": "CAM-01", "name": "Boundary for validation testing"},
        ]
        
        for bnd in test_boundaries:
            existing = db.query(BoundaryRecord).filter(BoundaryRecord.id == bnd["id"]).first()
            if not existing:
                boundary = BoundaryRecord(
                    id=bnd["id"],
                    camera_id=bnd["camera_id"],
                    name=bnd["name"],
                    enabled=True,
                    point_a={"x": 100.0, "y": 300.0},
                    point_b={"x": 800.0, "y": 300.0},
                    restricted_side="positive",
                    severity="HIGH",
                    tolerance=5.0,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                )
                db.add(boundary)
        db.flush()
    
    yield
    
    # Cleanup is not performed - keep test data for subsequent test runs


@pytest.fixture(autouse=True)
def cleanup_test_data_after_each_test():
    """Clean up intrusion events and alerts after each test (but keep boundaries and cameras)."""
    yield
    
    # Delete all test data created by unit tests
    with SessionLocal.begin() as db:
        # Delete in correct order to respect FK constraints
        db.execute(delete(AlertRecord).where(AlertRecord.id.like("ALT-%")))
        db.execute(delete(IntrusionEventRecord).where(IntrusionEventRecord.id.like("EVT-%")))
        db.flush()


@pytest.fixture(scope="module", autouse=True)
def setup_lifespan():
    """Ensure YOLO model is loaded for inference during tests."""
    with TestClient(app) as test_client:
        yield test_client


