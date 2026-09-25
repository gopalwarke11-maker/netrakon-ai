"""REST lifecycle controls for camera-scoped processing."""

from fastapi import APIRouter, HTTPException, status

from app.models.camera_processing import CameraProcessingStatus, CameraRuntimeSummary, CameraSourceUpdate
from app.services.camera_processor import camera_manager
from app.services.camera_service import camera_service

router = APIRouter(prefix="/cameras", tags=["camera-processing"])


def _camera_or_404(camera_id: str):
    camera = camera_service.get(camera_id)
    if camera is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camera not found")
    return camera


def _ensure_registered(
    camera_id: str,
    source: str | int | None = None,
    source_type: str | None = None,
    loop: bool = False,
):
    camera = _camera_or_404(camera_id)
    processor = camera_manager.get(camera_id)
    if processor is not None:
        return processor
    selected_source = source if source is not None else camera.stream_url
    if selected_source is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Camera has no configured stream_url")
    selected_type = source_type or camera.source_type
    return camera_manager.register(
        camera_id,
        selected_source,
        selected_type,
        loop_enabled=loop,
        storage_key=camera.storage_key,
    )  # type: ignore[arg-type]


@router.get("/runtime/summaries", response_model=list[CameraRuntimeSummary])
def runtime_summaries() -> list[CameraRuntimeSummary]:
    return camera_manager.list_summaries()


@router.post("/{camera_id}/start", response_model=CameraProcessingStatus)
def start_camera(camera_id: str, payload: CameraSourceUpdate | None = None) -> CameraProcessingStatus:
    payload = payload or CameraSourceUpdate()
    processor = _ensure_registered(camera_id, payload.source, payload.source_type, payload.loop)
    if processor.is_running:
        if processor.loop_enabled == payload.loop:
            return processor.status
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Camera is already running with a different loop mode.",
        )
    processor.set_loop_enabled(payload.loop)
    try:
        return processor.start()
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post("/{camera_id}/stop", response_model=CameraProcessingStatus)
def stop_camera(camera_id: str) -> CameraProcessingStatus:
    _camera_or_404(camera_id)
    try:
        return camera_manager.stop(camera_id)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Camera is not running") from None


@router.post("/{camera_id}/restart", response_model=CameraProcessingStatus)
def restart_camera(camera_id: str) -> CameraProcessingStatus:
    _camera_or_404(camera_id)
    processor = camera_manager.get(camera_id)
    if processor is None:
        processor = _ensure_registered(camera_id)
    try:
        return processor.restart()
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.get("/{camera_id}/status", response_model=CameraProcessingStatus)
def camera_status(camera_id: str) -> CameraProcessingStatus:
    camera = _camera_or_404(camera_id)
    processor = camera_manager.get(camera_id)
    if processor is None:
        source_type = camera.source_type
        source = camera.stream_url or ""
        if source.lower().startswith(("rtsp://", "rtsps://")):
            source_type = "RTSP"
        elif source.isdigit():
            source_type = "DEVICE"
        return CameraProcessingStatus(camera_id=camera_id, status="OFFLINE", source_type=source_type)  # type: ignore[arg-type]
    return processor.status


@router.get("/{camera_id}/summary", response_model=CameraRuntimeSummary)
def camera_summary(camera_id: str) -> CameraRuntimeSummary:
    camera = _camera_or_404(camera_id)
    processor = camera_manager.get(camera_id)
    if processor is None:
        return CameraRuntimeSummary(camera_id=camera_id, status="OFFLINE", source_type=camera.source_type)
    return processor.summary()


@router.get("/runtime", response_model=list[CameraProcessingStatus])
def active_camera_statuses() -> list[CameraProcessingStatus]:
    return camera_manager.list_status()
