"""Comprehensive unit tests for Phase 10: Low-Light Detection & Enhancement.

Tests cover:
- Low-light detection (bright/dark frames, thresholds)
- CLAHE enhancement (validity, dimensions, dtype preservation)
- Configuration and parameter handling
- Image validation and error handling
- Deterministic behavior
- Integration with existing detector
- Regression verification for Phases 1-9
"""

import time

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.ai.detector import run_detection
from app.ai.low_light import LowLightAnalysis, LowLightProcessor, get_processor
from app.core.config import settings
from app.main import app

client = TestClient(app)


# ─────────────────────────────────────────────────────────────────────────────
# Tests 1-5: Low-light detection basics
# ─────────────────────────────────────────────────────────────────────────────


def test_01_bright_frame_not_low_light():
    """Test that a bright frame (high luminance) is NOT classified as low-light."""
    processor = LowLightProcessor(low_light_threshold=70.0)
    
    # Create a very bright frame (white/light gray)
    frame = np.full((100, 100, 3), 220, dtype=np.uint8)  # Light gray
    
    analysis = processor.analyze_frame(frame)
    
    assert analysis.low_light is False
    assert analysis.mean_luminance > 200  # Very bright
    assert analysis.threshold == 70.0


def test_02_dark_frame_is_low_light():
    """Test that a dark frame (low luminance) IS classified as low-light."""
    processor = LowLightProcessor(low_light_threshold=70.0)
    
    # Create a very dark frame
    frame = np.full((100, 100, 3), 30, dtype=np.uint8)  # Dark gray
    
    analysis = processor.analyze_frame(frame)
    
    assert analysis.low_light is True
    assert analysis.mean_luminance < 50  # Very dark


def test_03_threshold_behavior_exact_boundary():
    """Test behavior at exact threshold boundary."""
    processor = LowLightProcessor(low_light_threshold=100.0)
    
    # Create frame with mean luminance just below threshold
    frame_dark = np.full((100, 100, 3), 99, dtype=np.uint8)
    analysis_dark = processor.analyze_frame(frame_dark)
    assert analysis_dark.low_light is True
    
    # Create frame with mean luminance just above threshold
    frame_bright = np.full((100, 100, 3), 101, dtype=np.uint8)
    analysis_bright = processor.analyze_frame(frame_bright)
    assert analysis_bright.low_light is False


def test_04_mean_luminance_calculation_accuracy():
    """Test that mean luminance is calculated correctly."""
    processor = LowLightProcessor()
    
    # Create frame with known mean value
    frame = np.zeros((10, 10, 3), dtype=np.uint8)
    frame[:5, :5, :] = 100  # Top-left quarter is 100
    # Rest is black (0)
    
    analysis = processor.analyze_frame(frame)
    
    # Mean should be 100 * 0.25 (25% of pixels are 100) = 25
    expected_mean = 25.0
    assert abs(analysis.mean_luminance - expected_mean) < 1.0


def test_05_custom_threshold_respected():
    """Test that custom thresholds are respected."""
    processor_strict = LowLightProcessor(low_light_threshold=50.0)
    processor_lenient = LowLightProcessor(low_light_threshold=150.0)
    
    # Medium-brightness frame
    frame = np.full((50, 50, 3), 80, dtype=np.uint8)
    
    analysis_strict = processor_strict.analyze_frame(frame)
    analysis_lenient = processor_lenient.analyze_frame(frame)
    
    # Same frame, different classifications based on threshold
    assert analysis_strict.low_light is False  # 80 >= 50
    assert analysis_lenient.low_light is True   # 80 < 150


# ─────────────────────────────────────────────────────────────────────────────
# Tests 6-9: CLAHE enhancement validity
# ─────────────────────────────────────────────────────────────────────────────


def test_06_clahe_enhancement_returns_valid_frame():
    """Test that CLAHE enhancement returns a valid numpy array."""
    processor = LowLightProcessor()
    frame = np.full((100, 100, 3), 40, dtype=np.uint8)
    
    enhanced = processor.enhance_clahe(frame)
    
    assert isinstance(enhanced, np.ndarray)
    assert enhanced.dtype == np.uint8
    assert enhanced.shape == frame.shape
    assert enhanced.size > 0


def test_07_enhancement_preserves_dimensions():
    """Test that enhancement preserves frame dimensions."""
    processor = LowLightProcessor()
    
    for height, width in [(480, 640), (720, 1280), (100, 100)]:
        frame = np.full((height, width, 3), 50, dtype=np.uint8)
        enhanced = processor.enhance_clahe(frame)
        assert enhanced.shape == (height, width, 3)


def test_08_enhancement_preserves_channels():
    """Test that enhancement preserves 3 color channels."""
    processor = LowLightProcessor()
    frame = np.full((100, 100, 3), 50, dtype=np.uint8)
    
    enhanced = processor.enhance_clahe(frame)
    
    assert enhanced.ndim == 3
    assert enhanced.shape[2] == 3


def test_09_enhancement_preserves_dtype():
    """Test that enhancement preserves data type."""
    processor = LowLightProcessor()
    frame = np.full((100, 100, 3), 50, dtype=np.uint8)
    
    enhanced = processor.enhance_clahe(frame)
    
    assert enhanced.dtype == frame.dtype


# ─────────────────────────────────────────────────────────────────────────────
# Tests 10-11: Normal frame handling
# ─────────────────────────────────────────────────────────────────────────────


def test_10_normal_bright_frame_remains_usable():
    """Test that a normal bright frame is not enhanced."""
    processor = LowLightProcessor(low_light_threshold=70.0)
    frame = np.full((100, 100, 3), 200, dtype=np.uint8)
    
    enhanced, metadata = processor.process_frame(frame, enable_enhancement=True)
    
    assert metadata["low_light"] is False
    assert metadata["enhancement_applied"] is False
    assert metadata["enhancement_method"] == "NONE"
    # Bright frames should be essentially unchanged
    np.testing.assert_array_equal(enhanced, frame)


def test_11_low_light_frame_gets_enhancement():
    """Test that low-light frames receive CLAHE enhancement."""
    processor = LowLightProcessor(low_light_threshold=70.0)
    frame = np.full((100, 100, 3), 30, dtype=np.uint8)
    
    enhanced, metadata = processor.process_frame(frame, enable_enhancement=True)
    
    assert metadata["low_light"] is True
    assert metadata["enhancement_applied"] is True
    assert metadata["enhancement_method"] == "CLAHE"
    # Enhanced frame should be different (brighter) than original
    assert enhanced.mean() > frame.mean()


# ─────────────────────────────────────────────────────────────────────────────
# Tests 12-13: Configuration and control
# ─────────────────────────────────────────────────────────────────────────────


def test_12_enhancement_can_be_disabled():
    """Test that enhancement can be explicitly disabled."""
    processor = LowLightProcessor(low_light_threshold=70.0)
    frame = np.full((100, 100, 3), 30, dtype=np.uint8)
    
    enhanced, metadata = processor.process_frame(frame, enable_enhancement=False)
    
    # Even though frame is low-light, enhancement should not be applied
    assert metadata["low_light"] is True
    assert metadata["enhancement_applied"] is False
    assert metadata["enhancement_method"] == "NONE"
    np.testing.assert_array_equal(enhanced, frame)


def test_13_configuration_values_respected():
    """Test that custom configuration values are respected."""
    custom_threshold = 50.0
    custom_clip = 3.0
    custom_tile = (16, 16)
    
    processor = LowLightProcessor(
        low_light_threshold=custom_threshold,
        clahe_clip_limit=custom_clip,
        clahe_tile_grid_size=custom_tile,
    )
    
    assert processor.low_light_threshold == custom_threshold
    assert processor.clahe_clip_limit == custom_clip
    assert processor.clahe_tile_grid_size == custom_tile


# ─────────────────────────────────────────────────────────────────────────────
# Tests 14-17: Error handling and edge cases
# ─────────────────────────────────────────────────────────────────────────────


def test_14_invalid_image_raises_error():
    """Test that invalid image data raises ValueError."""
    processor = LowLightProcessor()
    
    with pytest.raises(ValueError, match="must be numpy array"):
        processor.analyze_frame("not an array")


def test_15_wrong_shape_raises_error():
    """Test that wrong-shaped array raises ValueError."""
    processor = LowLightProcessor()
    
    # 2D grayscale instead of 3D BGR
    frame = np.zeros((100, 100), dtype=np.uint8)
    with pytest.raises(ValueError, match="H, W, 3"):
        processor.analyze_frame(frame)


def test_16_clahe_on_invalid_frame_raises_error():
    """Test that CLAHE on invalid frame raises ValueError."""
    processor = LowLightProcessor()
    frame = np.zeros((100, 100), dtype=np.uint8)
    
    with pytest.raises(ValueError):
        processor.enhance_clahe(frame)


def test_17_gamma_correction_with_zero_raises_error():
    """Test that gamma correction with invalid gamma raises error."""
    processor = LowLightProcessor()
    frame = np.full((100, 100, 3), 100, dtype=np.uint8)
    
    with pytest.raises(ValueError, match="Gamma must be > 0"):
        processor.apply_gamma_correction(frame, gamma=0.0)


# ─────────────────────────────────────────────────────────────────────────────
# Tests 18-20: Determinism and consistency
# ─────────────────────────────────────────────────────────────────────────────


def test_18_deterministic_low_light_classification():
    """Test that low-light classification is deterministic."""
    processor = LowLightProcessor(low_light_threshold=70.0)
    frame = np.full((100, 100, 3), 50, dtype=np.uint8)
    
    # Run analysis multiple times
    results = [processor.analyze_frame(frame) for _ in range(5)]
    
    # All should be identical
    assert all(r.low_light == results[0].low_light for r in results)
    assert all(r.mean_luminance == results[0].mean_luminance for r in results)


def test_19_repeated_processing_behaves_consistently():
    """Test that repeated processing gives consistent results."""
    processor = LowLightProcessor()
    frame = np.full((100, 100, 3), 40, dtype=np.uint8)
    
    results = [processor.process_frame(frame) for _ in range(3)]
    
    # All should have same metadata
    for enhanced, metadata in results:
        assert metadata["enhancement_applied"] is True
        assert metadata["enhancement_method"] == "CLAHE"


def test_20_normal_frame_remains_unchanged():
    """Test that bright frames are not modified."""
    processor = LowLightProcessor(low_light_threshold=70.0)
    frame = np.full((100, 100, 3), 200, dtype=np.uint8)
    
    enhanced, _ = processor.process_frame(frame, enable_enhancement=True)
    
    # Frames should be pixel-identical
    np.testing.assert_array_equal(enhanced, frame)


# ─────────────────────────────────────────────────────────────────────────────
# Tests 21-22: Detection integration
# ─────────────────────────────────────────────────────────────────────────────


def test_21_yolo_works_on_normal_frames():
    """Test that YOLO detection works on normal daylight frames."""
    # Create a simple synthetic frame with a bright rectangle (object)
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    cv2.rectangle(frame, (100, 100), (200, 200), (0, 255, 255), -1)  # Cyan square
    
    # Encode to JPEG
    success, buffer = cv2.imencode(".jpg", frame)
    assert success
    
    # Run detection (low-light enhancement should not apply)
    response = run_detection(buffer.tobytes(), enhance_low_light=True)
    
    # Should return valid response
    assert response.image_width == 640
    assert response.image_height == 480
    assert response.processing_time_ms > 0


def test_22_yolo_works_through_low_light_preprocessing():
    """Test that YOLO works on enhanced low-light frames."""
    # Create a dark frame with a bright rectangle
    frame = np.full((480, 640, 3), 30, dtype=np.uint8)  # Dark background
    cv2.rectangle(frame, (100, 100), (200, 200), (255, 255, 255), -1)  # White square
    
    success, buffer = cv2.imencode(".jpg", frame)
    assert success
    
    # Run detection with enhancement enabled
    response = run_detection(buffer.tobytes(), enhance_low_light=True)
    
    # Should return valid response
    assert response.image_width == 640
    assert response.image_height == 480
    assert isinstance(response.detections, list)


# ─────────────────────────────────────────────────────────────────────────────
# Tests 23-25: Regression verification
# ─────────────────────────────────────────────────────────────────────────────


def test_23_phase5_intrusion_regression():
    """Verify Phase 5 intrusion detection still works."""
    # This test just ensures the intrusion module can be imported
    # Full regression testing happens in test_phase5_intrusion.py
    try:
        from app.ai.intrusion_detector import IntrusionDetector
        detector = IntrusionDetector()
        assert detector is not None
    except ImportError:
        pytest.fail("Phase 5 intrusion detector import failed")


def test_24_phase8_risk_engine_regression():
    """Verify Phase 8 risk engine still works."""
    try:
        from app.services.alert_service import AlertService
        service = AlertService()
        assert service is not None
    except ImportError:
        pytest.fail("Phase 8 risk engine import failed")


def test_25_phase9_behavior_engine_regression():
    """Verify Phase 9 behavior engine still works."""
    try:
        from app.services.behavior_service import BehaviorService
        service = BehaviorService()
        assert service is not None
    except ImportError:
        pytest.fail("Phase 9 behavior service import failed")


# ─────────────────────────────────────────────────────────────────────────────
# Tests 26-28: REST API endpoint tests
# ─────────────────────────────────────────────────────────────────────────────


def test_26_low_light_api_endpoint_exists():
    """Test that the low-light API endpoint is accessible."""
    # Create a simple test image
    frame = np.full((100, 100, 3), 50, dtype=np.uint8)
    success, buffer = cv2.imencode(".jpg", frame)
    assert success
    
    # Upload to endpoint
    response = client.post(
        "/api/ai/low-light-test",
        files={"file": ("test.jpg", buffer.tobytes(), "image/jpeg")},
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "low_light" in data
    assert "mean_luminance" in data
    assert "enhancement_applied" in data


def test_27_low_light_api_reports_correct_metadata():
    """Test that the API reports correct metadata."""
    # Create a dark frame
    frame = np.full((200, 300, 3), 30, dtype=np.uint8)
    success, buffer = cv2.imencode(".jpg", frame)
    assert success
    
    response = client.post(
        "/api/ai/low-light-test",
        files={"file": ("dark.jpg", buffer.tobytes(), "image/jpeg")},
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["low_light"] is True  # Should be low-light
    assert data["enhancement_applied"] is True
    assert data["enhancement_method"] == "CLAHE"
    assert data["image_width"] == 300
    assert data["image_height"] == 200


def test_28_low_light_api_handles_bright_frame():
    """Test that the API handles bright frames correctly."""
    # Create a bright frame
    frame = np.full((150, 150, 3), 220, dtype=np.uint8)
    success, buffer = cv2.imencode(".jpg", frame)
    assert success
    
    response = client.post(
        "/api/ai/low-light-test",
        files={"file": ("bright.jpg", buffer.tobytes(), "image/jpeg")},
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["low_light"] is False  # Should NOT be low-light
    assert data["enhancement_applied"] is False
    assert data["enhancement_method"] == "NONE"
