"""Camera request and response schemas."""

from datetime import datetime, timezone
from typing import Literal
from urllib.parse import urlparse

from pydantic import BaseModel, Field, model_validator


class CameraBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    sector: str = Field(min_length=1, max_length=120)
    location: str = Field(min_length=1, max_length=255)
    status: Literal["ONLINE", "OFFLINE", "MAINTENANCE"] = "ONLINE"
    source_type: Literal["FILE", "RTSP", "MJPEG", "DEVICE"] = "FILE"
    stream_url: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def validate_source(self) -> "CameraBase":
        if self.source_type in {"RTSP", "MJPEG"}:
            if not self.stream_url:
                raise ValueError(f"{self.source_type} cameras require a stream URL")
            scheme = urlparse(self.stream_url).scheme.lower()
            allowed = {"rtsp", "rtsps"} if self.source_type == "RTSP" else {"http", "https"}
            if scheme not in allowed:
                raise ValueError(f"{self.source_type} cameras require a {', '.join(sorted(allowed))} URL")
        return self


class CameraCreate(CameraBase):
    pass


class CameraUpdate(CameraBase):
    pass


class Camera(CameraBase):
    id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
