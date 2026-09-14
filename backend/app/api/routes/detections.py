"""Detection API routes."""

from fastapi import APIRouter, HTTPException, status

from app.models.detection import Detection, DetectionCreate
from app.services.detection_service import detection_service

router = APIRouter(prefix="/detections", tags=["detections"])


@router.get("", response_model=list[Detection], summary="List detections")
def list_detections() -> list[Detection]:
    return detection_service.list()


@router.get("/{detection_id}", response_model=Detection, summary="Get a detection")
def get_detection(detection_id: str) -> Detection:
    detection = detection_service.get(detection_id)
    if detection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Detection not found")
    return detection


@router.post("", response_model=Detection, status_code=status.HTTP_201_CREATED, summary="Create a detection")
def create_detection(payload: DetectionCreate) -> Detection:
    return detection_service.create(payload)