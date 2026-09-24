"""Camera API routes."""

from pathlib import Path
import time

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import FileResponse, RedirectResponse, StreamingResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.core.config import settings
from app.models.boundary import VirtualBoundary
from app.models.camera import (
    Camera,
    CameraCreate,
    CameraTestRequest,
    CameraTestResponse,
    CameraUpdate,
    ConfirmUploadRequest,
    PresignedUploadRequest,
    PresignedUploadResponse,
)
from app.services.camera_connectivity import test_camera_stream_connectivity
from app.services.camera_processor import camera_manager, is_remote_url
from app.services.camera_service import camera_service
from app.services.object_storage import object_storage_service

router = APIRouter(prefix="/cameras", tags=["cameras"])

_BROWSER_VIDEO_SUFFIXES = {".mp4", ".webm", ".ogg", ".mov", ".avi", ".mkv"}


@router.post(
    "/presigned-upload-url",
    response_model=PresignedUploadResponse,
    summary="Create a presigned S3 upload URL for direct browser video upload",
)
def create_presigned_upload_url(payload: PresignedUploadRequest) -> PresignedUploadResponse:
    """Generate a presigned S3 PUT URL for uploading video directly to object storage."""
    try:
        return object_storage_service.create_presigned_upload_url(
            filename=payload.filename,
            content_type=payload.content_type,
            camera_id=payload.camera_id,
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


@router.post(
    "/confirm-upload",
    response_model=Camera,
    summary="Confirm completed S3 video upload and associate object key with PostgreSQL camera record",
)
def confirm_upload(payload: ConfirmUploadRequest) -> Camera:
    """Confirm object storage upload completion and save video object metadata to PostgreSQL."""
    verified, stream_url, metadata = object_storage_service.verify_and_get_stream_url(payload.object_key)
    if not verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Object key '{payload.object_key}' was not found in object storage.",
        )

    if payload.file_size_bytes is not None:
        metadata["file_size_bytes"] = payload.file_size_bytes

    if payload.camera_id:
        existing = camera_service.get(payload.camera_id)
        if existing is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Specified camera not found")
        update_payload = CameraUpdate(
            name=payload.name or existing.name,
            sector=payload.sector or existing.sector,
            location=payload.location or existing.location,
            status=existing.status,
            source_type="FILE",
            stream_url=stream_url,
            storage_key=payload.object_key,
            storage_metadata=metadata,
        )
        updated = camera_service.update(payload.camera_id, update_payload)
        if updated is None:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update camera")
        return updated

    create_payload = CameraCreate(
        name=payload.name or f"Camera {Path(payload.object_key).name[:20]}",
        sector=payload.sector or "Default Sector",
        location=payload.location or "Uploaded Video",
        status="ONLINE",
        source_type="FILE",
        stream_url=stream_url,
        storage_key=payload.object_key,
        storage_metadata=metadata,
    )
    return camera_service.create(create_payload)


@router.post(
    "/test-connection",
    response_model=CameraTestResponse,
    summary="Test camera stream reachability and report private LAN status",
)
def test_camera_connection(payload: CameraTestRequest) -> CameraTestResponse:
    """Test camera stream reachability, validate format, and report private LAN / timeout status."""
    return test_camera_stream_connectivity(payload.source_type, payload.stream_url)


@router.put(
    "/upload-fallback/{object_key:path}",
    summary="Development fallback upload endpoint for local storage (Dev Only)",
)
async def dev_upload_fallback(object_key: str, request: Request):
    """Local development fallback endpoint when S3 credentials are not configured."""
    target_path = Path(settings.storage_dev_fallback_dir) / object_key
    target_path.parent.mkdir(parents=True, exist_ok=True)
    body = await request.body()
    with open(target_path, "wb") as f:
        f.write(body)
    return {"status": "success", "object_key": object_key, "bytes_written": len(body)}


@router.get("", response_model=list[Camera], summary="List cameras")
def list_cameras() -> list[Camera]:
    return camera_service.list()


@router.post("", response_model=Camera, status_code=status.HTTP_201_CREATED, summary="Create a camera")
def create_camera(payload: CameraCreate) -> Camera:
    try:
        return camera_service.create(payload)
    except IntegrityError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Camera could not be created.") from exc
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable.") from exc


@router.get("/{camera_id}", response_model=Camera, summary="Get a camera")
def get_camera(camera_id: str) -> Camera:
    camera = camera_service.get(camera_id)
    if camera is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camera not found")
    return camera


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


@router.get("/{camera_id}/stream", summary="Stream a configured local camera file or redirect to remote video")
def stream_camera_file(camera_id: str):
    """Serve the local video file or redirect to remote video URL configured for this camera."""
    camera = camera_service.get(camera_id)
    if camera is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camera not found")
    if camera.storage_key:
        fresh_url = object_storage_service.get_presigned_download_url(camera.storage_key)
        if fresh_url.startswith("/"):
            # Local dev fallback mode
            file_path = Path(settings.storage_dev_fallback_dir) / camera.storage_key
            if file_path.is_file():
                return FileResponse(
                    file_path,
                    media_type="video/mp4",
                    headers={"Content-Disposition": f'inline; filename="{file_path.name}"'},
                )
        return RedirectResponse(url=fresh_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)
    source = camera.stream_url
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camera has no configured stream source")
    if camera.source_type == "FILE" and is_remote_url(source):
        return RedirectResponse(url=source, status_code=status.HTTP_307_TEMPORARY_REDIRECT)
    if source.lower().startswith(("rtsp://", "rtsps://", "http://", "https://")):
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
