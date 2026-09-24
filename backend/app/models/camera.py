"""Camera request and response schemas."""

from datetime import datetime, timezone
from typing import Any, Literal
from urllib.parse import urlparse

from pydantic import BaseModel, Field, model_validator


class CameraBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    sector: str = Field(min_length=1, max_length=120)
    location: str = Field(min_length=1, max_length=255)
    status: Literal["ONLINE", "OFFLINE", "MAINTENANCE"] = "ONLINE"
    source_type: Literal["FILE", "RTSP", "MJPEG", "DEVICE"] = "FILE"
    stream_url: str | None = Field(default=None, max_length=500)
    storage_key: str | None = Field(default=None, max_length=255)
    storage_metadata: dict[str, Any] | None = Field(default=None)

    @model_validator(mode="after")
    def validate_source(self) -> "CameraBase":
        if self.source_type in {"RTSP", "MJPEG"}:
            if not self.stream_url or not self.stream_url.strip():
                raise ValueError(f"{self.source_type} cameras require a stream URL")
            raw = self.stream_url.strip()
            parsed = urlparse(raw)
            scheme = parsed.scheme.lower()
            allowed = {"rtsp", "rtsps"} if self.source_type == "RTSP" else {"http", "https"}
            if scheme not in allowed:
                raise ValueError(f"{self.source_type} cameras require a {', '.join(sorted(allowed))} URL")
            if not parsed.netloc and not parsed.hostname:
                raise ValueError(f"{self.source_type} camera URL must include a host")
        elif self.source_type == "FILE" and self.stream_url:
            raw = self.stream_url.strip()
            if "://" in raw:
                parsed = urlparse(raw)
                scheme = parsed.scheme.lower()
                if scheme not in {"http", "https"}:
                    raise ValueError(f"FILE camera remote URLs must use http or https, got '{scheme}'")
                if not parsed.netloc and not parsed.hostname:
                    raise ValueError("FILE camera remote URL must include a host")
        return self


class CameraCreate(CameraBase):
    pass


class CameraUpdate(CameraBase):
    pass


class Camera(CameraBase):
    id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PresignedUploadRequest(BaseModel):
    filename: str = Field(min_length=1, max_length=255, description="Original filename of the MP4 video file")
    content_type: str = Field(default="video/mp4", max_length=100)
    camera_id: str | None = Field(default=None, max_length=80, description="Optional existing camera ID to update")


class PresignedUploadResponse(BaseModel):
    upload_url: str = Field(description="Presigned PUT URL for direct browser S3 upload, or dev fallback URL")
    object_key: str = Field(description="Unique object key for S3 object storage")
    method: str = Field(default="PUT")
    headers: dict[str, str] = Field(default_factory=dict)
    storage_type: Literal["S3", "LOCAL_DEV_FALLBACK"] = Field(description="S3 in production, or LOCAL_DEV_FALLBACK in dev")


class ConfirmUploadRequest(BaseModel):
    object_key: str = Field(min_length=1, max_length=255)
    camera_id: str | None = Field(default=None, max_length=80)
    name: str | None = Field(default=None, max_length=120)
    sector: str | None = Field(default=None, max_length=120)
    location: str | None = Field(default=None, max_length=255)
    file_size_bytes: int | None = Field(default=None, ge=0)


class CameraTestRequest(BaseModel):
    source_type: Literal["FILE", "RTSP", "MJPEG", "DEVICE"] = "FILE"
    stream_url: str = Field(min_length=1, max_length=500)


class CameraTestResponse(BaseModel):
    is_reachable: bool
    status: Literal[
        "REACHABLE",
        "PRIVATE_NETWORK_NOT_REACHABLE",
        "UNREACHABLE",
        "INVALID_URL",
        "DEVICE_AVAILABLE",
        "DEVICE_UNAVAILABLE",
    ]
    message: str
    details: dict[str, Any] | None = Field(default=None)
