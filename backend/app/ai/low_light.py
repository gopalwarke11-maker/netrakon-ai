"""Low-light detection and enhancement for night surveillance.

This module provides deterministic methods to:
1. Detect whether a frame is low-light (based on mean luminance)
2. Enhance low-light frames using CLAHE (Contrast Limited Adaptive Histogram Equalization)
3. Optionally apply gamma correction

These methods operate on raw numpy arrays (BGR frames from OpenCV).
"""

from __future__ import annotations

import logging

import cv2
import numpy as np

from app.core.config import settings

logger = logging.getLogger(__name__)


class LowLightAnalysis:
    """Result of low-light analysis for a frame."""

    def __init__(
        self,
        low_light: bool,
        mean_luminance: float,
        threshold: float,
    ):
        self.low_light = low_light
        self.mean_luminance = mean_luminance
        self.threshold = threshold

    def __repr__(self) -> str:
        return (
            f"LowLightAnalysis(low_light={self.low_light}, "
            f"mean_luminance={self.mean_luminance:.2f}, "
            f"threshold={self.threshold})"
        )


class LowLightProcessor:
    """Deterministic low-light detection and enhancement."""

    def __init__(
        self,
        low_light_threshold: float | None = None,
        clahe_clip_limit: float | None = None,
        clahe_tile_grid_size: tuple[int, int] | None = None,
    ):
        """Initialize the low-light processor.

        Args:
            low_light_threshold: Mean luminance threshold below which a frame is
                considered low-light. Defaults to settings.LOW_LIGHT_THRESHOLD.
            clahe_clip_limit: Clip limit for CLAHE enhancement. Higher values
                preserve more texture but risk over-contrast. Defaults to
                settings.CLAHE_CLIP_LIMIT.
            clahe_tile_grid_size: Size of grid tiles for CLAHE (height, width).
                Defaults to settings.CLAHE_TILE_GRID_SIZE.
        """
        self.low_light_threshold = (
            low_light_threshold
            if low_light_threshold is not None
            else settings.low_light_threshold
        )
        self.clahe_clip_limit = (
            clahe_clip_limit
            if clahe_clip_limit is not None
            else settings.clahe_clip_limit
        )
        
        tile_size = (
            clahe_tile_grid_size
            if clahe_tile_grid_size is not None
            else settings.clahe_tile_grid_size
        )
        # Parse tuple if it's a string from config
        if isinstance(tile_size, str):
            h, w = map(int, tile_size.split("x"))
            tile_size = (h, w)
        
        self.clahe_tile_grid_size = tile_size

        # Initialize CLAHE object (reuse across calls for efficiency)
        self.clahe = cv2.createCLAHE(
            clipLimit=self.clahe_clip_limit,
            tileGridSize=self.clahe_tile_grid_size,
        )

    def analyze_frame(self, frame: np.ndarray) -> LowLightAnalysis:
        """Analyze frame brightness and determine if it's low-light.

        Args:
            frame: BGR frame as numpy array (H, W, 3).

        Returns:
            LowLightAnalysis with low_light flag and mean_luminance.

        Raises:
            ValueError: If frame is not a valid BGR image.
        """
        if not isinstance(frame, np.ndarray):
            raise ValueError(f"Frame must be numpy array, got {type(frame)}")
        
        if frame.ndim != 3 or frame.shape[2] != 3:
            raise ValueError(
                f"Frame must be BGR (H, W, 3), got shape {frame.shape}"
            )

        # Convert BGR to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        mean_luminance = float(gray.mean())

        low_light = mean_luminance < self.low_light_threshold

        logger.debug(
            "Low-light analysis: mean_luminance=%.2f, threshold=%.2f, low_light=%s",
            mean_luminance,
            self.low_light_threshold,
            low_light,
        )

        return LowLightAnalysis(
            low_light=low_light,
            mean_luminance=mean_luminance,
            threshold=self.low_light_threshold,
        )

    def enhance_clahe(self, frame: np.ndarray) -> np.ndarray:
        """Enhance frame using CLAHE (Contrast Limited Adaptive Histogram Equalization).

        Converts BGR → LAB, applies CLAHE to L channel, merges back to BGR.

        Args:
            frame: BGR frame as numpy array (H, W, 3).

        Returns:
            Enhanced BGR frame with same shape and dtype.

        Raises:
            ValueError: If frame is not a valid BGR image.
        """
        if not isinstance(frame, np.ndarray):
            raise ValueError(f"Frame must be numpy array, got {type(frame)}")
        
        if frame.ndim != 3 or frame.shape[2] != 3:
            raise ValueError(
                f"Frame must be BGR (H, W, 3), got shape {frame.shape}"
            )

        original_dtype = frame.dtype

        # Ensure frame is uint8 for OpenCV processing
        if frame.dtype != np.uint8:
            frame_uint8 = cv2.convertScaleAbs(frame)
        else:
            frame_uint8 = frame.copy()

        # BGR → LAB
        lab = cv2.cvtColor(frame_uint8, cv2.COLOR_BGR2LAB)
        l_channel, a_channel, b_channel = cv2.split(lab)

        # Apply CLAHE to L channel
        l_enhanced = self.clahe.apply(l_channel)

        # Merge back
        lab_enhanced = cv2.merge([l_enhanced, a_channel, b_channel])

        # LAB → BGR
        enhanced = cv2.cvtColor(lab_enhanced, cv2.COLOR_LAB2BGR)

        # Convert back to original dtype if needed
        if original_dtype != np.uint8:
            enhanced = enhanced.astype(original_dtype)

        logger.debug("CLAHE enhancement applied")
        return enhanced

    def apply_gamma_correction(
        self, frame: np.ndarray, gamma: float
    ) -> np.ndarray:
        """Apply gamma correction to frame.

        gamma < 1: brightens image
        gamma = 1: no change
        gamma > 1: darkens image

        Args:
            frame: BGR frame as numpy array.
            gamma: Gamma exponent for correction.

        Returns:
            Gamma-corrected frame with same shape and dtype.

        Raises:
            ValueError: If frame is not valid or gamma <= 0.
        """
        if not isinstance(frame, np.ndarray):
            raise ValueError(f"Frame must be numpy array, got {type(frame)}")
        
        if gamma <= 0:
            raise ValueError(f"Gamma must be > 0, got {gamma}")

        if frame.ndim != 3 or frame.shape[2] != 3:
            raise ValueError(
                f"Frame must be BGR (H, W, 3), got shape {frame.shape}"
            )

        original_dtype = frame.dtype

        # Ensure frame is uint8
        if frame.dtype != np.uint8:
            frame_uint8 = cv2.convertScaleAbs(frame)
        else:
            frame_uint8 = frame.copy()

        # Build lookup table
        inv_gamma = 1.0 / gamma
        table = np.array([((i / 255.0) ** inv_gamma) * 255 for i in range(256)]).astype(
            np.uint8
        )

        # Apply gamma correction via lookup table
        corrected = cv2.LUT(frame_uint8, table)

        # Convert back to original dtype if needed
        if original_dtype != np.uint8:
            corrected = corrected.astype(original_dtype)

        logger.debug("Gamma correction applied (gamma=%.2f)", gamma)
        return corrected

    def process_frame(
        self,
        frame: np.ndarray,
        enable_enhancement: bool = True,
    ) -> tuple[np.ndarray, dict]:
        """Analyze and optionally enhance a frame for low-light conditions.

        Args:
            frame: BGR frame as numpy array.
            enable_enhancement: If True and frame is low-light, apply CLAHE.

        Returns:
            (processed_frame, metadata) where metadata contains:
            - low_light: bool
            - mean_luminance: float
            - enhancement_applied: bool
            - enhancement_method: str ("CLAHE", "NONE")
            - threshold: float

        Raises:
            ValueError: If frame is invalid.
        """
        # Analyze brightness
        analysis = self.analyze_frame(frame)

        metadata = {
            "low_light": analysis.low_light,
            "mean_luminance": round(analysis.mean_luminance, 2),
            "threshold": analysis.threshold,
            "enhancement_applied": False,
            "enhancement_method": "NONE",
        }

        # Apply enhancement if low-light and enabled
        if enable_enhancement and analysis.low_light:
            processed_frame = self.enhance_clahe(frame)
            metadata["enhancement_applied"] = True
            metadata["enhancement_method"] = "CLAHE"
        else:
            processed_frame = frame.copy()

        return processed_frame, metadata


# Global processor instance (lazy-initialized)
_processor: LowLightProcessor | None = None


def get_processor() -> LowLightProcessor:
    """Get or create the global low-light processor instance."""
    global _processor
    if _processor is None:
        _processor = LowLightProcessor()
    return _processor
