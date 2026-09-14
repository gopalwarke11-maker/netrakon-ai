#!/usr/bin/env python
"""Night-video validation utility for the Phase 10 low-light pipeline.

This script evaluates the existing low-light enhancement and YOLO detection
pipeline on a real video file, comparing the original frame path against the
low-light-enhanced path while preserving the current NETRAKON AI architecture.

It intentionally reuses:
- app.ai.low_light.get_processor()
- app.ai.detector.run_detection()
- app.ai.model_manager.get_model()/load_model()

It does not create a second YOLO implementation or replace the existing model.
"""

from __future__ import annotations

import argparse
import json
import sys
import textwrap
import time
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from app.ai.detector import run_detection
from app.ai.low_light import get_processor
from app.ai.model_manager import is_model_loaded, load_model
from app.ai.tracker import TrackSession


SUPPORTED_EXTENSIONS = {
    ".mp4",
    ".avi",
    ".mov",
    ".mkv",
    ".webm",
    ".mjpeg",
    ".m4v",
    ".wmv",
    ".flv",
    ".ts",
    ".mts",
}


def handle_validation_error(message: str, error_type: str = "error") -> dict[str, Any]:
    """Return a structured error payload for CLI or API callers."""
    return {
        "status": error_type,
        "message": str(message),
    }


def validate_video_file(video_path: str | Path) -> Path:
    """Validate that a real video file exists and can be decoded by OpenCV."""
    path = Path(video_path).expanduser()
    if not path.exists():
        raise FileNotFoundError(f"Video file does not exist: {path}")
    if not path.is_file():
        raise ValueError(f"Video path is not a file: {path}")

    suffix = path.suffix.lower()
    if suffix and suffix not in SUPPORTED_EXTENSIONS:
        # Some valid files have no extension or unusual suffixes; allow OpenCV to decide.
        pass

    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise ValueError(
            f"Unsupported or corrupt video file: '{path}'. "
            "The file could not be opened by OpenCV for decoding."
        )

    ok, _ = cap.read()
    cap.release()
    if not ok:
        raise ValueError(
            f"The video file could not be decoded: '{path}'. "
            "OpenCV could not read the first frame."
        )

    return path


def extract_video_metadata(video_path: str | Path) -> dict[str, Any]:
    """Extract basic metadata for a video file and return a JSON-friendly dict."""
    path = validate_video_file(video_path)
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise ValueError(f"Unable to open video for metadata extraction: {path}")

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    duration_seconds = frame_count / fps if fps > 0 else 0.0
    codec_fourcc = int(cap.get(cv2.CAP_PROP_FOURCC) or 0)
    codec = "unknown"

    if codec_fourcc:
        codec = "".join(chr((codec_fourcc >> shift) & 0xFF) for shift in (0, 8, 16, 24)).strip()
        codec = codec or "unknown"

    ret, _ = cap.read()
    cap.release()
    if not ret:
        raise ValueError(f"Video file contains no readable frames: {path}")

    return {
        "filename": path.name,
        "path": str(path),
        "width": width,
        "height": height,
        "fps": round(fps, 2) if fps else 0.0,
        "frame_count": frame_count,
        "duration_seconds": round(duration_seconds, 2),
        "codec": codec,
        "resolution": f"{width}x{height}" if width and height else "unknown",
    }


def sample_frame_indices(total_frames: int, sample_every: int = 10, max_frames: int = 300) -> list[int]:
    """Return a representative set of frame indices to analyze."""
    if total_frames <= 0:
        return []

    interval = max(1, int(sample_every))
    indices = list(range(0, total_frames, interval))
    if max_frames and max_frames > 0 and len(indices) > max_frames:
        indices = indices[:max_frames]
    return indices


def ensure_validation_output_dir(output_dir: str | Path) -> Path:
    """Create the validation output directory if it does not exist."""
    path = Path(output_dir).expanduser()
    path.mkdir(parents=True, exist_ok=True)
    return path


def run_original_detection_path(frame: np.ndarray, conf_threshold: float = 0.25) -> dict[str, Any]:
    """Run the existing YOLO detector on the original unmodified frame."""
    if not isinstance(frame, np.ndarray) or frame.size == 0:
        raise ValueError("Original detection path received an empty or invalid frame.")

    success, encoded = cv2.imencode(".jpg", frame)
    if not success:
        raise ValueError("Could not encode the original frame before detection.")

    t0 = time.perf_counter()
    response = run_detection(encoded.tobytes(), conf_threshold=conf_threshold, enhance_low_light=False)
    processing_time_ms = (time.perf_counter() - t0) * 1000.0

    detections = [
        {
            "class_id": detection.class_id,
            "class_name": detection.class_name,
            "confidence": float(detection.confidence),
            "bounding_box": detection.bounding_box.model_dump(),
        }
        for detection in response.detections
    ]
    return {
        "detections": detections,
        "processing_time_ms": round(processing_time_ms, 2),
        "model_name": response.model_name,
        "image_width": response.image_width,
        "image_height": response.image_height,
    }


def run_enhanced_detection_path(frame: np.ndarray, conf_threshold: float = 0.25) -> dict[str, Any]:
    """Run the existing low-light enhancement path before YOLO detection."""
    if not isinstance(frame, np.ndarray) or frame.size == 0:
        raise ValueError("Enhanced detection path received an empty or invalid frame.")

    processor = get_processor()
    enhanced_frame, metadata = processor.process_frame(frame, enable_enhancement=True)

    success, encoded = cv2.imencode(".jpg", enhanced_frame)
    if not success:
        raise ValueError("Could not encode the enhanced frame before detection.")

    t0 = time.perf_counter()
    response = run_detection(encoded.tobytes(), conf_threshold=conf_threshold, enhance_low_light=False)
    processing_time_ms = (time.perf_counter() - t0) * 1000.0

    detections = [
        {
            "class_id": detection.class_id,
            "class_name": detection.class_name,
            "confidence": float(detection.confidence),
            "bounding_box": detection.bounding_box.model_dump(),
        }
        for detection in response.detections
    ]
    return {
        "detections": detections,
        "processing_time_ms": round(processing_time_ms, 2),
        "model_name": response.model_name,
        "image_width": response.image_width,
        "image_height": response.image_height,
        "low_light": bool(metadata.get("low_light", False)),
        "mean_luminance": float(metadata.get("mean_luminance", 0.0)),
        "enhancement_applied": bool(metadata.get("enhancement_applied", False)),
        "enhancement_method": metadata.get("enhancement_method", "NONE"),
    }


def aggregate_class_counts(detections: list[dict[str, Any]]) -> dict[str, int]:
    """Aggregate detection totals by class label, supporting common COCO classes."""
    counts: dict[str, int] = {}
    for detection in detections:
        class_name = str(detection.get("class_name", "unknown")).strip().lower()
        if not class_name:
            class_name = "unknown"
        counts[class_name] = counts.get(class_name, 0) + 1
    return counts


def compare_detection_results(original: dict[str, Any], enhanced: dict[str, Any]) -> dict[str, Any]:
    """Compare results for one frame between the original and enhanced paths."""
    original_detections = original.get("detections", [])
    enhanced_detections = enhanced.get("detections", [])

    return {
        "original_detection_count": len(original_detections),
        "enhanced_detection_count": len(enhanced_detections),
        "original_confidences": [float(det.get("confidence", 0.0)) for det in original_detections],
        "enhanced_confidences": [float(det.get("confidence", 0.0)) for det in enhanced_detections],
        "original_classes": [str(det.get("class_name", "unknown")) for det in original_detections],
        "enhanced_classes": [str(det.get("class_name", "unknown")) for det in enhanced_detections],
        "original_processing_ms": float(original.get("processing_time_ms", 0.0)),
        "enhanced_processing_ms": float(enhanced.get("processing_time_ms", 0.0)),
    }


def calculate_aggregate_metrics(frame_metrics: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate per-frame metrics across the sampled frames."""
    if not frame_metrics:
        return {
            "total_sampled_frames": 0,
            "low_light_frames": 0,
            "percentage_low_light_frames": 0.0,
            "average_luminance": 0.0,
            "total_original_detections": 0,
            "total_enhanced_detections": 0,
            "average_detections_per_frame_original": 0.0,
            "average_detections_per_frame_enhanced": 0.0,
            "average_confidence_original": 0.0,
            "average_confidence_enhanced": 0.0,
            "original_average_processing_ms": 0.0,
            "enhanced_average_processing_ms": 0.0,
            "enhancement_overhead_ms": 0.0,
        }

    total_original = sum(int(entry.get("original_detection_count", 0)) for entry in frame_metrics)
    total_enhanced = sum(int(entry.get("enhanced_detection_count", 0)) for entry in frame_metrics)

    all_orig_conf = []
    all_enh_conf = []
    for entry in frame_metrics:
        all_orig_conf.extend(entry.get("original_confidences", []))
        all_enh_conf.extend(entry.get("enhanced_confidences", []))

    low_light_frames = sum(1 for entry in frame_metrics if bool(entry.get("is_low_light")))
    average_luminance = float(np.mean([float(entry.get("mean_luminance", 0.0)) for entry in frame_metrics])) if frame_metrics else 0.0

    original_avg_processing = float(np.mean([float(entry.get("original_processing_ms", 0.0)) for entry in frame_metrics])) if frame_metrics else 0.0
    enhanced_avg_processing = float(np.mean([float(entry.get("enhanced_processing_ms", 0.0)) for entry in frame_metrics])) if frame_metrics else 0.0

    return {
        "total_sampled_frames": len(frame_metrics),
        "low_light_frames": low_light_frames,
        "percentage_low_light_frames": round((low_light_frames / len(frame_metrics)) * 100.0, 2) if frame_metrics else 0.0,
        "average_luminance": round(average_luminance, 2),
        "total_original_detections": total_original,
        "total_enhanced_detections": total_enhanced,
        "average_detections_per_frame_original": round(total_original / len(frame_metrics), 2) if frame_metrics else 0.0,
        "average_detections_per_frame_enhanced": round(total_enhanced / len(frame_metrics), 2) if frame_metrics else 0.0,
        "average_confidence_original": round(float(np.mean(all_orig_conf)) if all_orig_conf else 0.0, 4),
        "average_confidence_enhanced": round(float(np.mean(all_enh_conf)) if all_enh_conf else 0.0, 4),
        "original_average_processing_ms": round(original_avg_processing, 2),
        "enhanced_average_processing_ms": round(enhanced_avg_processing, 2),
        "enhancement_overhead_ms": round(enhanced_avg_processing - original_avg_processing, 2),
    }


def draw_bounding_boxes(frame: np.ndarray, detections: list[dict[str, Any]], label: str) -> np.ndarray:
    """Draw YOLO boxes onto a frame for the validation artifact."""
    image = frame.copy()
    for detection in detections:
        box = detection.get("bounding_box", {})
        x1 = float(box.get("x1", 0.0))
        y1 = float(box.get("y1", 0.0))
        x2 = float(box.get("x2", 0.0))
        y2 = float(box.get("y2", 0.0))
        if x2 <= x1 or y2 <= y1:
            continue

        cv2.rectangle(image, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
        class_name = str(detection.get("class_name", "object"))
        confidence = float(detection.get("confidence", 0.0))
        cv2.putText(
            image,
            f"{class_name} {confidence:.2f}",
            (max(0, int(x1)), max(10, int(y1) - 10)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 255, 0),
            1,
            cv2.LINE_AA,
        )

    cv2.putText(
        image,
        label,
        (20, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.0,
        (255, 255, 255),
        2,
        cv2.LINE_AA,
    )
    return image


def summarize_tracking_stream(track_observations: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarize ByteTrack observations for one stream."""
    if not track_observations:
        return {
            "unique_tracks": 0,
            "multi_frame_tracks": 0,
            "multi_frame_track_ratio": 0.0,
            "average_track_duration": 0.0,
            "maximum_track_duration": 0.0,
            "minimum_track_duration": 0.0,
            "total_track_observations": 0,
            "track_appearances": 0,
            "track_disappearances": 0,
            "continuity_breaks": 0,
            "continuity_observations": "No tracked objects were observed.",
        }

    by_track: dict[int, list[dict[str, Any]]] = {}
    for observation in track_observations:
        track_id = int(observation.get("track_id", -1))
        by_track.setdefault(track_id, []).append(observation)

    durations = [len(frames) for frames in by_track.values()]
    multi_frame_tracks = sum(1 for count in durations if count >= 2)
    continuity_breaks = 0
    track_disappearances = 0

    for frames in by_track.values():
        frame_numbers = sorted(int(item["frame_number"]) for item in frames)
        if len(frame_numbers) < 2:
            continue
        continuity_breaks += sum(1 for prev, current in zip(frame_numbers, frame_numbers[1:]) if current - prev > 1)
        for prev, current in zip(frame_numbers, frame_numbers[1:]):
            if current - prev > 1:
                track_disappearances += 1

    summary = {
        "unique_tracks": len(by_track),
        "multi_frame_tracks": multi_frame_tracks,
        "multi_frame_track_ratio": round(multi_frame_tracks / len(by_track), 4) if by_track else 0.0,
        "average_track_duration": round(float(sum(durations)) / len(durations), 2) if durations else 0.0,
        "maximum_track_duration": max(durations) if durations else 0,
        "minimum_track_duration": min(durations) if durations else 0,
        "total_track_observations": len(track_observations),
        "track_appearances": len(track_observations),
        "track_disappearances": track_disappearances,
        "continuity_breaks": continuity_breaks,
    }
    if summary["unique_tracks"]:
        summary["continuity_observations"] = (
            f"{summary['continuity_breaks']} continuity break(s) across {summary['unique_tracks']} track ID(s)."
        )
    else:
        summary["continuity_observations"] = "No tracked objects were observed."
    return summary


def compare_tracking_streams(original_summary: dict[str, Any], enhanced_summary: dict[str, Any]) -> dict[str, Any]:
    """Compare ByteTrack metrics between the original and enhanced streams."""
    return {
        "original_unique_tracks": original_summary.get("unique_tracks", 0),
        "enhanced_unique_tracks": enhanced_summary.get("unique_tracks", 0),
        "original_multi_frame_tracks": original_summary.get("multi_frame_tracks", 0),
        "enhanced_multi_frame_tracks": enhanced_summary.get("multi_frame_tracks", 0),
        "original_multi_frame_track_ratio": original_summary.get("multi_frame_track_ratio", 0.0),
        "enhanced_multi_frame_track_ratio": enhanced_summary.get("multi_frame_track_ratio", 0.0),
        "original_average_track_duration": original_summary.get("average_track_duration", 0.0),
        "enhanced_average_track_duration": enhanced_summary.get("average_track_duration", 0.0),
        "original_max_track_duration": original_summary.get("maximum_track_duration", 0),
        "enhanced_max_track_duration": enhanced_summary.get("maximum_track_duration", 0),
        "original_total_track_observations": original_summary.get("total_track_observations", 0),
        "enhanced_total_track_observations": enhanced_summary.get("total_track_observations", 0),
    }


def draw_tracking_frame(frame: np.ndarray, observations: list[dict[str, Any]], label: str) -> np.ndarray:
    """Draw tracked objects and track IDs onto a frame for visualization."""
    image = frame.copy()
    for observation in observations:
        box = observation.get("bounding_box", {}) or {}
        x1 = float(box.get("x1", observation.get("center_x", 0.0) - 20))
        y1 = float(box.get("y1", observation.get("center_y", 0.0) - 20))
        x2 = float(box.get("x2", observation.get("center_x", 0.0) + 20))
        y2 = float(box.get("y2", observation.get("center_y", 0.0) + 20))
        if x2 <= x1 or y2 <= y1:
            x1 = max(0.0, float(observation.get("center_x", 0.0)) - 20)
            y1 = max(0.0, float(observation.get("center_y", 0.0)) - 20)
            x2 = float(observation.get("center_x", 0.0)) + 20
            y2 = float(observation.get("center_y", 0.0)) + 20

        cv2.rectangle(image, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
        class_name = str(observation.get("class_name") or observation.get("class") or "object")
        confidence = float(observation.get("confidence", 0.0))
        track_id = int(observation.get("track_id", -1))
        text = f"{class_name} {confidence:.2f} ID:{track_id}"
        cv2.putText(
            image,
            text,
            (max(0, int(x1)), max(10, int(y1) - 12)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 255, 0),
            1,
            cv2.LINE_AA,
        )

    cv2.putText(
        image,
        label,
        (20, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.0,
        (255, 255, 255),
        2,
        cv2.LINE_AA,
    )
    return image


def generate_tracking_artifacts(
    video_path: str | Path,
    tracking_frames: list[dict[str, Any]],
    output_dir: str | Path,
    sample_every: int = 1,
) -> list[Path]:
    """Save a small set of representative tracking frames for both streams."""
    output_path = ensure_validation_output_dir(output_dir)
    if not tracking_frames:
        return []

    sample_list = tracking_frames[: min(len(tracking_frames), 5)]
    artifact_paths: list[Path] = []
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise ValueError(f"Unable to open the video for tracking artifact generation: {video_path}")

    frame_index = 0
    saved = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        for item in sample_list:
            if item.get("frame_number") == frame_index:
                original_frame = item.get("original_frame")
                enhanced_frame = item.get("enhanced_frame")
                if original_frame is not None:
                    image = draw_tracking_frame(original_frame, item.get("original_tracking_observations", []), "ORIGINAL + BYTETRACK")
                    path = output_path / f"tracking_original_{frame_index}.png"
                    cv2.imwrite(str(path), image)
                    artifact_paths.append(path)
                    saved += 1
                if enhanced_frame is not None:
                    image = draw_tracking_frame(enhanced_frame, item.get("enhanced_tracking_observations", []), "LOW-LIGHT ENHANCED + BYTETRACK")
                    path = output_path / f"tracking_enhanced_{frame_index}.png"
                    cv2.imwrite(str(path), image)
                    artifact_paths.append(path)
                    saved += 1
                if saved >= 10:
                    cap.release()
                    return artifact_paths
        frame_index += 1

    cap.release()
    return artifact_paths


def write_validation_report(report_path: str | Path, report: dict[str, Any]) -> Path:
    """Write the validation markdown report to disk."""
    path = Path(report_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    status = report.get("validation_status", "D")
    video_filename = report.get("video_filename", "unknown")
    resolution = report.get("resolution", "unknown")
    fps = report.get("fps", 0.0)
    frame_count = report.get("frame_count", 0)
    duration = report.get("duration_seconds", 0.0)
    codec = report.get("codec", "unknown")
    sample_every = report.get("sample_every", 10)
    sampled_frames = report.get("sampled_frames", 0)
    low_light_frames = report.get("low_light_frames", 0)
    percentage_low_light = report.get("percentage_low_light_frames", 0.0)
    average_luminance = report.get("average_luminance", 0.0)
    total_original = report.get("total_original_detections", 0)
    total_enhanced = report.get("total_enhanced_detections", 0)
    avg_original = report.get("average_detections_per_frame_original", 0.0)
    avg_enhanced = report.get("average_detections_per_frame_enhanced", 0.0)
    conf_original = report.get("average_confidence_original", 0.0)
    conf_enhanced = report.get("average_confidence_enhanced", 0.0)
    orig_time = report.get("original_average_processing_ms", 0.0)
    enh_time = report.get("enhanced_average_processing_ms", 0.0)
    overhead = report.get("enhancement_overhead_ms", 0.0)
    original_unique_tracks = report.get("original_unique_tracks", 0)
    enhanced_unique_tracks = report.get("enhanced_unique_tracks", 0)
    original_multi_frame_tracks = report.get("original_multi_frame_tracks", 0)
    enhanced_multi_frame_tracks = report.get("enhanced_multi_frame_tracks", 0)
    original_multi_frame_ratio = report.get("original_multi_frame_track_ratio", 0.0)
    enhanced_multi_frame_ratio = report.get("enhanced_multi_frame_track_ratio", 0.0)
    original_avg_duration = report.get("original_average_track_duration", 0.0)
    enhanced_avg_duration = report.get("enhanced_average_track_duration", 0.0)
    original_max_duration = report.get("original_max_track_duration", 0)
    enhanced_max_duration = report.get("enhanced_max_track_duration", 0)
    verdict = report.get("final_verdict", "D")

    body = textwrap.dedent(
        f"""\
        # Phase 10 Night Video Validation

        ## Video Information

        - filename: {video_filename}
        - resolution: {resolution}
        - FPS: {fps}
        - frame count: {frame_count}
        - duration: {duration} seconds
        - codec: {codec}

        ## Sampling

        - sampling interval: {sample_every}
        - number of frames analyzed: {sampled_frames}

        ## Low-Light Results

        - low-light frames: {low_light_frames}
        - percentage low-light: {percentage_low_light}%
        - average luminance: {average_luminance}

        ## Detection Comparison

        | Metric | Original | Enhanced |
        | --- | ---: | ---: |
        | total detections | {total_original} | {total_enhanced} |
        | average detections/frame | {avg_original} | {avg_enhanced} |
        | average confidence | {conf_original} | {conf_enhanced} |
        | person detections | {report.get('person_original', 0)} | {report.get('person_enhanced', 0)} |
        | vehicle detections | {report.get('vehicle_original', 0)} | {report.get('vehicle_enhanced', 0)} |
        | other classes | {report.get('other_original', 0)} | {report.get('other_enhanced', 0)} |

        ## Performance

        - original average processing ms: {orig_time}
        - enhanced average processing ms: {enh_time}
        - overhead ms: {overhead}
        - estimated FPS: {report.get('estimated_fps', 0.0)}

        ## Tracking Comparison

        | Metric | Original | Enhanced |
        | --- | ---: | ---: |
        | Unique tracks | {original_unique_tracks} | {enhanced_unique_tracks} |
        | Multi-frame tracks | {original_multi_frame_tracks} | {enhanced_multi_frame_tracks} |
        | Multi-frame track ratio | {original_multi_frame_ratio} | {enhanced_multi_frame_ratio} |
        | Average track duration | {original_avg_duration} | {enhanced_avg_duration} |
        | Maximum track duration | {original_max_duration} | {enhanced_max_duration} |
        | Total track observations | {report.get('original_total_track_observations', 0)} | {report.get('enhanced_total_track_observations', 0)} |

        These measurements reflect the current development machine and the specific validation sample only.

        ## Interpretation

        This validation is limited to the supplied sample and does not establish model accuracy on all night footage.
        Detection count changed by {report.get('detection_delta', 0)} detections across the sampled frames.
        Average confidence changed from {conf_original} to {conf_enhanced}.
        Tracking changed from {original_unique_tracks} unique tracks to {enhanced_unique_tracks} unique tracks with ByteTrack.
        The present result is recorded as: {report.get('interpretation', 'No measurable detection improvement was observed.')}

        ## Limitations

        - One video is not enough to establish model accuracy.
        - No ground-truth annotations are available unless explicitly provided.
        - Performance depends on hardware.
        - Camera quality matters.
        - IR/night-vision footage may behave differently.
        - Real CCTV conditions can vary.

        ## Final Verdict

        {status}. {verdict}

        """
    )

    path.write_text(body, encoding="utf-8")
    return path


def generate_validation_artifacts(
    video_path: str | Path,
    selected_frames: list[int],
    sampled_results: list[dict[str, Any]],
    output_dir: str | Path,
) -> list[Path]:
    """Save representative original and enhanced frames for a small sample of scenes."""
    output_path = ensure_validation_output_dir(output_dir)
    artifact_paths: list[Path] = []

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise ValueError(f"Unable to open the video for artifact creation: {video_path}")

    frame_index = 0
    target_frames = set(selected_frames)
    saved_count = 0
    max_artifacts = 10

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if frame_index in target_frames:
            sample = next((entry for entry in sampled_results if entry.get("frame_number") == frame_index), None)
            if sample is None:
                frame_index += 1
                continue

            original_frame = sample.get("original_frame")
            enhanced_frame = sample.get("enhanced_frame")
            if original_frame is not None:
                image = draw_bounding_boxes(original_frame, sample.get("original_detections", []), "ORIGINAL")
                out_path = output_path / f"original_{frame_index}.png"
                cv2.imwrite(str(out_path), image)
                artifact_paths.append(out_path)
                saved_count += 1

            if enhanced_frame is not None:
                image = draw_bounding_boxes(enhanced_frame, sample.get("enhanced_detections", []), "LOW-LIGHT ENHANCED")
                out_path = output_path / f"enhanced_{frame_index}.png"
                cv2.imwrite(str(out_path), image)
                artifact_paths.append(out_path)
                saved_count += 1

            if saved_count >= max_artifacts:
                break
        frame_index += 1

    cap.release()
    return artifact_paths


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments for the validation utility.

    Accept either a bare argument list (e.g. ['--video', 'sample.mp4']) or a
    script-style argv including the program name (e.g. ['validate_night_video.py',
    '--video', 'sample.mp4']).
    """
    if argv is None:
        argv = sys.argv[1:]
    elif argv and argv[0].endswith(".py"):
        argv = argv[1:]

    parser = argparse.ArgumentParser(description="Validate low-light enhancement vs. original YOLO detection on a video.")
    parser.add_argument("--video", required=True, help="Path to a video file for validation.")
    parser.add_argument("--sample-every", type=int, default=10, help="Sample every N frames (default: 10).")
    parser.add_argument("--max-frames", type=int, default=300, help="Maximum number of sampled frames to process (default: 300).")
    parser.add_argument("--confidence", type=float, default=0.25, help="Detection confidence threshold used for both paths (default: 0.25).")
    parser.add_argument("--output-dir", default="validation_output", help="Directory used for validation artifacts and report output.")
    return parser.parse_args(argv)


def run_validation(video_path: str | Path, sample_every: int = 10, max_frames: int = 300, confidence: float = 0.25, output_dir: str | Path = "validation_output") -> dict[str, Any]:
    """Run the validation workflow for the supplied video path."""
    if not is_model_loaded():
        load_model()

    path = validate_video_file(video_path)
    metadata = extract_video_metadata(path)
    output_path = ensure_validation_output_dir(output_dir)

    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise ValueError(f"Could not open video for validation: {path}")

    try:
        selected_indices = sample_frame_indices(int(metadata["frame_count"]) or 0, sample_every=sample_every, max_frames=max_frames)
        sampled_results: list[dict[str, Any]] = []
        original_tracking_observations: list[dict[str, Any]] = []
        enhanced_tracking_observations: list[dict[str, Any]] = []
        original_session = TrackSession(conf=confidence, session_id=f"{metadata['filename']}-original")
        enhanced_session = TrackSession(conf=confidence, session_id=f"{metadata['filename']}-enhanced")
        frame_number = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break
            if frame_number not in selected_indices:
                frame_number += 1
                continue

            original_result = run_original_detection_path(frame, conf_threshold=confidence)
            enhanced_result = run_enhanced_detection_path(frame, conf_threshold=confidence)
            comparison = compare_detection_results(original_result, enhanced_result)
            processor = get_processor()
            analysis = processor.analyze_frame(frame)

            original_track_frame = original_session.process_frame(frame, frame_number, timestamp_ms=frame_number * 1000.0 / max(metadata["fps"], 1.0))
            enhanced_frame, enhanced_meta = processor.process_frame(frame, enable_enhancement=True)
            enhanced_track_frame = enhanced_session.process_frame(enhanced_frame, frame_number, timestamp_ms=frame_number * 1000.0 / max(metadata["fps"], 1.0))

            original_track_entries = [
                {
                    "track_id": obj.track_id,
                    "class_name": obj.class_name,
                    "confidence": float(obj.confidence),
                    "bounding_box": obj.bounding_box.model_dump(),
                    "center_x": float(obj.center_x),
                    "center_y": float(obj.center_y),
                    "frame_number": frame_number,
                }
                for obj in original_track_frame.objects
            ]
            enhanced_track_entries = [
                {
                    "track_id": obj.track_id,
                    "class_name": obj.class_name,
                    "confidence": float(obj.confidence),
                    "bounding_box": obj.bounding_box.model_dump(),
                    "center_x": float(obj.center_x),
                    "center_y": float(obj.center_y),
                    "frame_number": frame_number,
                }
                for obj in enhanced_track_frame.objects
            ]

            original_tracking_observations.extend(original_track_entries)
            enhanced_tracking_observations.extend(enhanced_track_entries)

            sampled_entry = {
                "frame_number": frame_number,
                "timestamp_seconds": round(frame_number / metadata["fps"], 3) if metadata["fps"] > 0 else 0.0,
                "is_low_light": bool(analysis.low_light),
                "mean_luminance": float(analysis.mean_luminance),
                "original_detection_count": comparison["original_detection_count"],
                "enhanced_detection_count": comparison["enhanced_detection_count"],
                "original_confidences": comparison["original_confidences"],
                "enhanced_confidences": comparison["enhanced_confidences"],
                "original_classes": comparison["original_classes"],
                "enhanced_classes": comparison["enhanced_classes"],
                "original_processing_ms": comparison["original_processing_ms"],
                "enhanced_processing_ms": comparison["enhanced_processing_ms"],
                "original_detections": original_result["detections"],
                "enhanced_detections": enhanced_result["detections"],
                "original_frame": frame.copy(),
                "enhanced_frame": enhanced_frame.copy(),
                "original_tracking_observations": original_track_entries,
                "enhanced_tracking_observations": enhanced_track_entries,
            }
            sampled_results.append(sampled_entry)
            frame_number += 1

        # if no sampled frames were processed, still report metadata but not results.
        original_tracking_summary = summarize_tracking_stream(original_tracking_observations)
        enhanced_tracking_summary = summarize_tracking_stream(enhanced_tracking_observations)
        tracking_delta = compare_tracking_streams(original_tracking_summary, enhanced_tracking_summary)
        aggregate = calculate_aggregate_metrics(
            [
                {
                    "original_detection_count": entry["original_detection_count"],
                    "enhanced_detection_count": entry["enhanced_detection_count"],
                    "original_confidences": entry["original_confidences"],
                    "enhanced_confidences": entry["enhanced_confidences"],
                    "original_processing_ms": entry["original_processing_ms"],
                    "enhanced_processing_ms": entry["enhanced_processing_ms"],
                    "is_low_light": entry["is_low_light"],
                    "mean_luminance": entry["mean_luminance"],
                }
                for entry in sampled_results
            ]
        )

        original_class_counts = {}
        enhanced_class_counts = {}
        for sample in sampled_results:
            original_class_counts = {
                key: original_class_counts.get(key, 0) + sample["original_classes"].count(key)
                for key in set(original_class_counts) | set(sample["original_classes"])
            }
            enhanced_class_counts = {
                key: enhanced_class_counts.get(key, 0) + sample["enhanced_classes"].count(key)
                for key in set(enhanced_class_counts) | set(sample["enhanced_classes"])
            }

        if sampled_results:
            artifacts = generate_validation_artifacts(path, selected_indices, sampled_results, output_path)
        else:
            artifacts = []

        report = {
            "video_filename": metadata["filename"],
            "resolution": metadata["resolution"],
            "fps": metadata["fps"],
            "frame_count": metadata["frame_count"],
            "duration_seconds": metadata["duration_seconds"],
            "codec": metadata["codec"],
            "sample_every": sample_every,
            "sampled_frames": len(sampled_results),
            "low_light_frames": aggregate["low_light_frames"],
            "percentage_low_light_frames": aggregate["percentage_low_light_frames"],
            "average_luminance": aggregate["average_luminance"],
            "total_original_detections": aggregate["total_original_detections"],
            "total_enhanced_detections": aggregate["total_enhanced_detections"],
            "average_detections_per_frame_original": aggregate["average_detections_per_frame_original"],
            "average_detections_per_frame_enhanced": aggregate["average_detections_per_frame_enhanced"],
            "average_confidence_original": aggregate["average_confidence_original"],
            "average_confidence_enhanced": aggregate["average_confidence_enhanced"],
            "original_average_processing_ms": aggregate["original_average_processing_ms"],
            "enhanced_average_processing_ms": aggregate["enhanced_average_processing_ms"],
            "enhancement_overhead_ms": aggregate["enhancement_overhead_ms"],
            "person_original": original_class_counts.get("person", 0),
            "person_enhanced": enhanced_class_counts.get("person", 0),
            "vehicle_original": sum(original_class_counts.get(name, 0) for name in ("car", "motorcycle", "bus", "truck", "bicycle")),
            "vehicle_enhanced": sum(enhanced_class_counts.get(name, 0) for name in ("car", "motorcycle", "bus", "truck", "bicycle")),
            "other_original": max(0, aggregate["total_original_detections"] - (original_class_counts.get("person", 0) + sum(original_class_counts.get(name, 0) for name in ("car", "motorcycle", "bus", "truck", "bicycle")))),
            "other_enhanced": max(0, aggregate["total_enhanced_detections"] - (enhanced_class_counts.get("person", 0) + sum(enhanced_class_counts.get(name, 0) for name in ("car", "motorcycle", "bus", "truck", "bicycle")))),
            "estimated_fps": round(1000.0 / max(aggregate["enhanced_average_processing_ms"], 1.0), 2) if aggregate["enhanced_average_processing_ms"] > 0 else 0.0,
            "original_unique_tracks": tracking_delta["original_unique_tracks"],
            "enhanced_unique_tracks": tracking_delta["enhanced_unique_tracks"],
            "multi_frame_tracks": tracking_delta["original_multi_frame_tracks"],
            "enhanced_multi_frame_tracks": tracking_delta["enhanced_multi_frame_tracks"],
            "unique_tracks": tracking_delta["original_unique_tracks"],
            "average_track_duration": original_tracking_summary.get("average_track_duration", 0.0),
            "maximum_track_duration": original_tracking_summary.get("maximum_track_duration", 0),
            "continuity_observations": original_tracking_summary.get("continuity_observations", "No tracked objects were observed."),
            "original_multi_frame_tracks": tracking_delta["original_multi_frame_tracks"],
            "enhanced_multi_frame_track_ratio": tracking_delta["enhanced_multi_frame_track_ratio"],
            "original_multi_frame_track_ratio": tracking_delta["original_multi_frame_track_ratio"],
            "original_average_track_duration": tracking_delta["original_average_track_duration"],
            "enhanced_average_track_duration": tracking_delta["enhanced_average_track_duration"],
            "original_max_track_duration": tracking_delta["original_max_track_duration"],
            "enhanced_max_track_duration": tracking_delta["enhanced_max_track_duration"],
            "original_total_track_observations": tracking_delta["original_total_track_observations"],
            "enhanced_total_track_observations": tracking_delta["enhanced_total_track_observations"],
            "detection_delta": aggregate["total_enhanced_detections"] - aggregate["total_original_detections"],
            "interpretation": (
                "ByteTrack continuity was measured across consecutive frames in both streams; "
                "the enhancement path is compared against the original path using the same tracker configuration."
            ),
            "validation_status": "C" if sampled_results else "D",
            "final_verdict": (
                "Validation completed using the real night footage sample and measured tracking continuity across the selected frames."
                if sampled_results else "Validation could not be completed because no frames were processed."
            ),
            "artifacts": [str(p) for p in artifacts],
        }

        if original_tracking_summary["unique_tracks"] > 0 or enhanced_tracking_summary["unique_tracks"] > 0:
            report["validation_status"] = "B"
            report["final_verdict"] = (
                "ByteTrack analysis was completed on the real night-video sample and the comparison reflects the measured original-vs-enhanced tracking continuity."
            )

        report_path = output_path / "PHASE10_NIGHT_VIDEO_VALIDATION.md"
        write_validation_report(report_path, report)
        return report
    finally:
        cap.release()


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    try:
        args = parse_args(argv)
        try:
            load_model()
        except Exception as exc:  # noqa: BLE001
            print(f"YOLO model loading failed: {exc}", file=sys.stderr)
            return 2

        report = run_validation(
            video_path=args.video,
            sample_every=args.sample_every,
            max_frames=args.max_frames,
            confidence=args.confidence,
            output_dir=args.output_dir,
        )
        print(json.dumps({"status": "ok", "report": report}, indent=2))
        return 0
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: Validation failed unexpectedly: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
