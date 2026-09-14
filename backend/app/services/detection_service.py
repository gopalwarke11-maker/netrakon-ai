"""In-memory detection business logic."""

from itertools import count

from app.models.detection import Detection, DetectionCreate


class DetectionService:
    def __init__(self) -> None:
        self._detections: dict[str, Detection] = {}
        self._next_id = count(1)

    def list(self) -> list[Detection]:
        return list(self._detections.values())

    def get(self, detection_id: str) -> Detection | None:
        return self._detections.get(detection_id)

    def create(self, payload: DetectionCreate) -> Detection:
        detection_id = f"DET-{next(self._next_id):04d}"
        detection = Detection(id=detection_id, **payload.model_dump())
        self._detections[detection_id] = detection
        return detection


detection_service = DetectionService()