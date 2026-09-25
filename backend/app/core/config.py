"""Centralized backend settings loaded from environment variables."""

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "NETRAKON AI"
    app_version: str = "0.1.0"
    environment: str = "development"
    debug: bool = True
    host: str = "127.0.0.1"
    port: int = 8000
    api_prefix: str = "/api"
    frontend_url: str = (
        "https://netrakon-ai.netlify.app,"
        "http://localhost:5173,"
        "http://localhost:5174,"
        "http://localhost:5175,"
        "http://127.0.0.1:5173,"
        "http://127.0.0.1:5174,"
        "http://127.0.0.1:5175"
    )
    database_url: str | None = None

    # ── Phase 3: AI inference ──────────────────────────────────────────────
    # ONNX model name or path. Nano variant (~12 MB ONNX) is the default;
    # ONNX Runtime CPU engine provides < 200 MB RSS execution memory.
    yolo_model_name: str = "yolov8n.onnx"
    # Minimum detection confidence [0, 1].  Requests may override this per-call.
    yolo_conf_threshold: float = 0.25

    # ── Phase 4: Object tracking ────────────────────────────────────────────
    # ByteTrack config bundled with ultralytics.  BoT-SORT: "botsort.yaml".
    yolo_tracker: str = "bytetrack.yaml"
    # Default confidence for tracking (can be overridden per request).
    track_conf_threshold: float = 0.25
    # Maximum number of (center_x, center_y) positions stored per track.
    # Prevents unbounded memory growth for long videos.
    track_position_history_limit: int = 50
    # Maximum video file size accepted by POST /api/ai/track (megabytes).
    track_max_video_size_mb: int = 200

    # ── Phase 10: Night Surveillance & Low-Light Enhancement ────────────────
    # Enable low-light detection and enhancement preprocessing.
    low_light_enabled: bool = True
    # Mean grayscale luminance threshold below which a frame is considered low-light.
    # Typical range: 50-100. Lower → stricter low-light detection.
    low_light_threshold: float = 70.0
    # CLAHE clip limit for contrast enhancement. Higher → more aggressive enhancement.
    # Typical range: 1.0-4.0. Preserves texture; avoid values > 5.0 to prevent artifacts.
    clahe_clip_limit: float = 2.0
    # CLAHE tile grid size as "HxW" (e.g., "8x8").
    # Larger tiles → smoother enhancement; smaller → more localized contrast.
    clahe_tile_grid_size: str = "8x8"

    # ── Phase 14: S3 Object Storage & Video Upload ─────────────────────────
    s3_endpoint_url: str | None = None
    s3_bucket_name: str = "netrakon-videos"
    s3_access_key_id: str | None = None
    s3_secret_access_key: str | None = None
    s3_region: str = "us-east-1"
    s3_public_url_prefix: str | None = None
    s3_presigned_expiration_seconds: int = 3600
    storage_dev_fallback_dir: str = "videos"

    @field_validator("debug", mode="before")
    @classmethod
    def normalize_debug(cls, value: object) -> object:
        """Accept common deployment labels in addition to boolean env values.

        Some launch profiles set ``DEBUG=release`` rather than a literal
        boolean.  Treat production/release labels as false while preserving
        Pydantic's normal validation for malformed values.
        """
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"release", "production", "prod"}:
                return False
            if normalized in {"development", "dev"}:
                return True
        return value

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def cors_origins(self) -> list[str]:
        """Return configured frontend origins, accepting comma-separated values and stripping trailing slashes."""
        raw_origins = [origin.strip().rstrip("/") for origin in self.frontend_url.split(",") if origin.strip()]
        production_origin = "https://netrakon-ai.netlify.app"
        if production_origin not in raw_origins:
            raw_origins.append(production_origin)

        seen: set[str] = set()
        origins: list[str] = []
        for origin in raw_origins:
            if origin and origin not in seen:
                seen.add(origin)
                origins.append(origin)
        return origins


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
