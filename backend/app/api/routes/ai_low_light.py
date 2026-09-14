"""Low-light detection and analysis route — POST /api/ai/low-light-test.

Development/testing endpoint for low-light frame analysis and enhancement.
"""

from __future__ import annotations

import logging

import cv2
import numpy as np
from fastapi import APIRouter, File, UploadFile, status
from pydantic import BaseModel, Field

from app.ai.low_light import get_processor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["Low-Light Enhancement"])

_MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB hard limit


class LowLightTestResponse(BaseModel):
    """Response from low-light analysis endpoint."""

    low_light: bool = Field(description="True if frame is detected as low-light")
    mean_luminance: float = Field(description="Mean grayscale intensity of the frame")
    threshold: float = Field(description="Luminance threshold used for classification")
    enhancement_applied: bool = Field(
        description="True if CLAHE enhancement was applied"
    )
    enhancement_method: str = Field(
        description="Enhancement method name (CLAHE, NONE)"
    )
    image_width: int = Field(description="Original image width in pixels")
    image_height: int = Field(description="Original image height in pixels")


@router.post(
    "/low-light-test",
    response_model=LowLightTestResponse,
    summary="Analyze frame for low-light conditions and apply enhancement",
    description=(
        "Upload an image to analyze its brightness and determine if low-light "
        "enhancement should be applied. Returns brightness metrics and metadata "
        "about any applied enhancement.\n\n"
        "This is a **development/testing endpoint** for understanding low-light "
        "preprocessing behavior."
    ),
    status_code=status.HTTP_200_OK,
)
async def analyze_low_light(
    file: UploadFile = File(
        ...,
        description="Image file to analyze (JPEG / PNG / BMP / WEBP)",
    ),
) -> LowLightTestResponse:
    """Analyze and optionally enhance an uploaded image for low-light conditions.

    The endpoint:
    1. Decodes the uploaded image
    2. Analyzes its mean luminance
    3. Determines if it's low-light
    4. Applies CLAHE enhancement if low-light is detected
    5. Returns metadata about the analysis and any enhancement

    Args:
        file: Image file to analyze.

    Returns:
        LowLightTestResponse with analysis results.

    Raises:
        HTTPException: If the file cannot be decoded or is corrupt.
    """
    if file.size and file.size > _MAX_FILE_SIZE:
        raise Exception(
            f"File is too large ({file.size} bytes > {_MAX_FILE_SIZE} byte limit)"
        )

    # Read and decode image
    contents = await file.read()

    arr = np.frombuffer(contents, dtype=np.uint8)
    frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)

    if frame is None:
        raise Exception(
            f"Could not decode '{file.filename}' as an image. "
            "Supported formats: JPEG, PNG, BMP, TIFF, WEBP."
        )

    image_height, image_width = frame.shape[:2]
    logger.debug("Image decoded: %d×%d px", image_width, image_height)

    # Analyze and process frame
    processor = get_processor()
    enhanced_frame, metadata = processor.process_frame(
        frame, enable_enhancement=True
    )

    logger.info(
        "Low-light analysis: low_light=%s, mean_luminance=%.2f, "
        "enhancement_applied=%s",
        metadata["low_light"],
        metadata["mean_luminance"],
        metadata["enhancement_applied"],
    )

    return LowLightTestResponse(
        low_light=metadata["low_light"],
        mean_luminance=metadata["mean_luminance"],
        threshold=metadata["threshold"],
        enhancement_applied=metadata["enhancement_applied"],
        enhancement_method=metadata["enhancement_method"],
        image_width=image_width,
        image_height=image_height,
    )
