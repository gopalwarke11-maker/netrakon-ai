import json
from pathlib import Path

import cv2
import numpy as np
import pytest

import validate_night_video as vnv


@pytest.fixture
def synthetic_video_path(tmp_path):
    path = tmp_path / "synthetic_night.mp4"
    writer = cv2.VideoWriter(
        str(path),
        cv2.VideoWriter_fourcc(*"mp4v"),
        10.0,
        (320, 240),
    )
    assert writer.isOpened()

    for idx in range(20):
        frame = np.full((240, 320, 3), 20 + idx * 2, dtype=np.uint8)
        if idx % 4 == 0:
            cv2.rectangle(frame, (50, 80), (120, 180), (200, 200, 200), -1)
        writer.write(frame)
    writer.release()
    return path


def test_missing_video_raises_clear_error(tmp_path):
    missing = tmp_path / "missing.mp4"
    with pytest.raises(FileNotFoundError, match="does not exist"):
        vnv.validate_video_file(missing)


def test_invalid_video_raises_clear_error(tmp_path):
    bad = tmp_path / "bad.txt"
    bad.write_text("not a video")
    with pytest.raises(ValueError, match="unsupported|video"):
        vnv.validate_video_file(bad)


def test_video_metadata_extraction(synthetic_video_path):
    metadata = vnv.extract_video_metadata(str(synthetic_video_path))
    assert metadata["filename"].endswith("synthetic_night.mp4")
    assert metadata["width"] == 320
    assert metadata["height"] == 240
    assert metadata["fps"] > 0
    assert metadata["frame_count"] >= 20


def test_frame_sampling_selects_expected_indices():
    indexes = vnv.sample_frame_indices(total_frames=30, sample_every=5, max_frames=10)
    assert indexes == [0, 5, 10, 15, 20, 25]


def test_low_light_analysis_integration(synthetic_video_path):
    metadata = vnv.extract_video_metadata(str(synthetic_video_path))
    processor = vnv.get_processor()
    cap = cv2.VideoCapture(str(synthetic_video_path))
    assert cap.isOpened()
    ok, frame = cap.read()
    cap.release()
    assert ok
    analysis = processor.analyze_frame(frame)
    assert isinstance(analysis.low_light, bool)
    assert isinstance(analysis.mean_luminance, float)


def test_original_detection_path_returns_detections(synthetic_video_path):
    cap = cv2.VideoCapture(str(synthetic_video_path))
    ok, frame = cap.read()
    cap.release()
    assert ok
    result = vnv.run_original_detection_path(frame)
    assert "detections" in result
    assert isinstance(result["detections"], list)
    assert isinstance(result["processing_time_ms"], float)


def test_enhanced_detection_path_returns_detections(synthetic_video_path):
    cap = cv2.VideoCapture(str(synthetic_video_path))
    ok, frame = cap.read()
    cap.release()
    assert ok
    result = vnv.run_enhanced_detection_path(frame)
    assert "detections" in result
    assert isinstance(result["detections"], list)
    assert isinstance(result["processing_time_ms"], float)


def test_detection_comparison_aggregates_results():
    original = {"detections": [
        {"class_name": "person", "confidence": 0.9},
        {"class_name": "person", "confidence": 0.7},
    ], "processing_time_ms": 10.0}
    enhanced = {"detections": [
        {"class_name": "person", "confidence": 0.95},
        {"class_name": "car", "confidence": 0.8},
    ], "processing_time_ms": 12.5}
    summary = vnv.compare_detection_results(original, enhanced)
    assert summary["original_detection_count"] == 2
    assert summary["enhanced_detection_count"] == 2
    assert summary["original_confidences"] == [0.9, 0.7]
    assert summary["enhanced_confidences"] == [0.95, 0.8]


def test_class_aggregation_counts_objects():
    detections = [
        {"class_name": "person", "confidence": 0.9},
        {"class_name": "car", "confidence": 0.8},
        {"class_name": "person", "confidence": 0.7},
    ]
    counts = vnv.aggregate_class_counts(detections)
    assert counts["person"] == 2
    assert counts["car"] == 1


def test_metric_calculation_computes_averages():
    frame_metrics = [
        {"original_detection_count": 1, "enhanced_detection_count": 2, "original_processing_ms": 20.0, "enhanced_processing_ms": 25.0},
        {"original_detection_count": 3, "enhanced_detection_count": 1, "original_processing_ms": 30.0, "enhanced_processing_ms": 35.0},
    ]
    metrics = vnv.calculate_aggregate_metrics(frame_metrics)
    assert metrics["total_sampled_frames"] == 2
    assert metrics["total_original_detections"] == 4
    assert metrics["total_enhanced_detections"] == 3
    assert metrics["average_detections_per_frame_original"] == pytest.approx(2.0)
    assert metrics["average_detections_per_frame_enhanced"] == pytest.approx(1.5)


def test_report_generation_creates_file(tmp_path):
    report_path = tmp_path / "PHASE10_NIGHT_VIDEO_VALIDATION.md"
    vnv.write_validation_report(report_path, {"video_filename": "demo.mp4", "validation_status": "D"})
    assert report_path.exists()
    text = report_path.read_text(encoding="utf-8")
    assert "Phase 10 Night Video Validation" in text
    assert "Final Verdict" in text


def test_output_directory_creation(tmp_path):
    output_dir = tmp_path / "validation_output"
    vnv.ensure_validation_output_dir(output_dir)
    assert output_dir.exists()
    assert output_dir.is_dir()


def test_cli_parsing_handles_required_video_argument(monkeypatch):
    argv = ["validate_night_video.py", "--video", "sample.mp4", "--sample-every", "10", "--max-frames", "50", "--confidence", "0.4", "--output-dir", "custom_out"]
    parsed = vnv.parse_args(argv)
    assert parsed.video == "sample.mp4"
    assert parsed.sample_every == 10
    assert parsed.max_frames == 50
    assert parsed.confidence == 0.4
    assert parsed.output_dir == "custom_out"


def test_graceful_error_handling_from_invalid_video_path(tmp_path, monkeypatch):
    bad_path = tmp_path / "ghost.mp4"
    with pytest.raises(FileNotFoundError):
        vnv.validate_video_file(bad_path)

    captured = vnv.handle_validation_error("bad path", "error")
    assert "bad path" in captured["message"]
    assert captured["status"] in {"error", "warning"}
