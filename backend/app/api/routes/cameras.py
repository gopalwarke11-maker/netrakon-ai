"""Camera API routes."""

from pathlib import Path

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.models.boundary import VirtualBoundary
from app.models.camera import Camera, CameraCreate, CameraUpdate
from app.services.camera_service import camera_service
from app.services.camera_processor import camera_manager
import time


router = APIRouter(prefix="/cameras", tags=["cameras"])

_BROWSER_VIDEO_SUFFIXES = {".mp4", ".webm", ".ogg", ".mov", ".avi", ".mkv"}


@router.get("/{camera_id}/stream", response_class=FileResponse, summary="Stream a configured local camera file")
def stream_camera_file(camera_id: str) -> FileResponse:
    """Serve only the local video file configured for this camera."""
    camera = camera_service.get(camera_id)
    if camera is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camera not found")
    source = camera.stream_url
    if not source or source.lower().startswith(("rtsp://", "rtsps://", "http://", "https://")):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camera has no browser-playable local file")
    file_path = Path(source)
    if file_path.suffix.lower() not in _BROWSER_VIDEO_SUFFIXES or not file_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Configured camera file is unavailable")
    return FileResponse(
        file_path,
        media_type="video/mp4",
        headers={"Content-Disposition": f'inline; filename="{file_path.name}"'},
    )


@router.get("/{camera_id}/processed-stream", summary="Stream synchronized processed camera frames")
def processed_camera_stream(camera_id: str) -> StreamingResponse:
    camera = camera_service.get(camera_id)
    if camera is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camera not found")
    processor = camera_manager.get(camera_id)
    if processor is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Camera processor is not running")

    def frames():
        while processor.is_running:
            jpeg = processor.latest_processed_frame()
            if jpeg:
                yield b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: " + str(len(jpeg)).encode() + b"\r\n\r\n" + jpeg + b"\r\n"
            time.sleep(0.05)

    return StreamingResponse(frames(), media_type="multipart/x-mixed-replace; boundary=frame")


@router.get("", response_model=list[Camera], summary="List cameras")
def list_cameras() -> list[Camera]:
    return camera_service.list()


@router.get("/{camera_id}", response_model=Camera, summary="Get a camera")
def get_camera(camera_id: str) -> Camera:
    camera = camera_service.get(camera_id)
    if camera is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camera not found")
    return camera


@router.post("", response_model=Camera, status_code=status.HTTP_201_CREATED, summary="Create a camera")
def create_camera(payload: CameraCreate) -> Camera:
    try:
        return camera_service.create(payload)
    except IntegrityError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Camera could not be created.") from exc
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable.") from exc


@router.put("/{camera_id}", response_model=Camera, summary="Replace a camera")
def update_camera(camera_id: str, payload: CameraUpdate) -> Camera:
    try:
        camera = camera_service.update(camera_id, payload)
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable.") from exc
    if camera is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camera not found")
    return camera


@router.delete("/{camera_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a camera")
def delete_camera(camera_id: str) -> None:
    try:
        deleted = camera_service.delete(camera_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camera not found")


@router.get(
    "/{camera_id}/boundaries",
    response_model=list[VirtualBoundary],
    summary="Get boundaries for a camera",
)
def get_camera_boundaries(camera_id: str) -> list[VirtualBoundary]:
    """Retrieve all virtual boundaries configured for the specified camera."""
    if camera_service.get(camera_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Camera '{camera_id}' not found.",
        )
    from app.services.boundary_service import boundary_service
    return boundary_service.get_by_camera(camera_id)
