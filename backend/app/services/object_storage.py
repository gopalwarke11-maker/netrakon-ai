"""S3-compatible Object Storage Service for direct browser MP4 video uploads."""

from datetime import datetime, timezone
import logging
import os
from pathlib import Path
import re
from typing import Any
import uuid

from app.core.config import settings
from app.models.camera import PresignedUploadResponse

logger = logging.getLogger(__name__)

try:
    import boto3
    from botocore.config import Config
    BOTO3_AVAILABLE = True
except ImportError:
    boto3 = None
    Config = None
    BOTO3_AVAILABLE = False


def sanitize_filename(filename: str) -> str:
    """Sanitize original filename to prevent path traversal or invalid character issues."""
    base = os.path.basename(filename)
    clean = re.sub(r"[^a-zA-Z0-9_\-\.]", "_", base)
    if not clean.lower().endswith((".mp4", ".webm", ".mov", ".avi", ".mkv")):
        clean += ".mp4"
    return clean


class ObjectStorageService:
    def is_s3_configured(self) -> bool:
        """Return True if S3 access key and secret key are configured."""
        return bool(
            BOTO3_AVAILABLE
            and settings.s3_access_key_id
            and settings.s3_secret_access_key
            and settings.s3_bucket_name
        )

    def _get_s3_client(self):
        if not self.is_s3_configured():
            raise RuntimeError("S3 object storage credentials are not configured.")
        client_kwargs: dict[str, Any] = {
            "service_name": "s3",
            "aws_access_key_id": settings.s3_access_key_id,
            "aws_secret_access_key": settings.s3_secret_access_key,
            "region_name": settings.s3_region,
            "config": Config(signature_version="s3v4"),
        }
        if settings.s3_endpoint_url:
            client_kwargs["endpoint_url"] = settings.s3_endpoint_url
        return boto3.client(**client_kwargs)

    def generate_object_key(self, filename: str) -> str:
        """Generate a unique S3 object key for a video upload."""
        date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
        clean_name = sanitize_filename(filename)
        unique_id = uuid.uuid4().hex[:10]
        return f"uploads/{date_str}/{unique_id}_{clean_name}"

    def create_presigned_upload_url(
        self,
        filename: str,
        content_type: str = "video/mp4",
        camera_id: str | None = None,
    ) -> PresignedUploadResponse:
        """Generate a presigned PUT URL for direct browser S3 upload, or dev fallback URL."""
        object_key = self.generate_object_key(filename)

        if self.is_s3_configured():
            try:
                s3_client = self._get_s3_client()
                upload_url = s3_client.generate_presigned_url(
                    "put_object",
                    Params={
                        "Bucket": settings.s3_bucket_name,
                        "Key": object_key,
                        "ContentType": content_type,
                    },
                    ExpiresIn=settings.s3_presigned_expiration_seconds,
                )
                logger.info("Generated S3 presigned upload URL for key: %s", object_key)
                return PresignedUploadResponse(
                    upload_url=upload_url,
                    object_key=object_key,
                    method="PUT",
                    headers={"Content-Type": content_type},
                    storage_type="S3",
                )
            except Exception as exc:
                logger.error("Failed to generate S3 presigned URL: %s", exc)
                raise RuntimeError(f"Could not generate S3 presigned URL: {exc}") from exc

        # Development Fallback Mode (when S3 is not configured)
        fallback_url = f"/api/cameras/upload-fallback/{object_key}"
        logger.info("Generated development fallback upload URL for key: %s", object_key)
        return PresignedUploadResponse(
            upload_url=fallback_url,
            object_key=object_key,
            method="PUT",
            headers={"Content-Type": content_type},
            storage_type="LOCAL_DEV_FALLBACK",
        )

    def verify_and_get_stream_url(self, object_key: str) -> tuple[bool, str, dict[str, Any]]:
        """Verify uploaded object existence and return the stream URL and metadata.

        Returns: (exists, stream_url, metadata_dict)
        """
        metadata: dict[str, Any] = {
            "object_key": object_key,
            "verified_at": datetime.now(timezone.utc).isoformat(),
        }

        if self.is_s3_configured():
            try:
                s3_client = self._get_s3_client()
                head = s3_client.head_object(Bucket=settings.s3_bucket_name, Key=object_key)
                metadata["storage_type"] = "S3"
                metadata["content_length"] = head.get("ContentLength")
                metadata["content_type"] = head.get("ContentType")

                if settings.s3_public_url_prefix:
                    prefix = settings.s3_public_url_prefix.rstrip("/")
                    stream_url = f"{prefix}/{object_key}"
                else:
                    stream_url = s3_client.generate_presigned_url(
                        "get_object",
                        Params={"Bucket": settings.s3_bucket_name, "Key": object_key},
                        ExpiresIn=86400,
                    )
                return True, stream_url, metadata
            except Exception as exc:
                logger.warning("S3 object key '%s' verification failed: %s", object_key, exc)
                return False, "", metadata

        # Development Fallback Mode
        fallback_path = Path(settings.storage_dev_fallback_dir) / object_key
        if fallback_path.is_file():
            metadata["storage_type"] = "LOCAL_DEV_FALLBACK"
            metadata["content_length"] = fallback_path.stat().st_size
            return True, str(fallback_path.resolve()), metadata
        return False, "", metadata


object_storage_service = ObjectStorageService()
