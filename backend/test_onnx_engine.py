"""Focused unit tests for ONNX inference engine (backend/app/ai/onnx_engine.py)."""

import sys
from pathlib import Path

import cv2
import numpy as np
import pytest

from app.ai.onnx_engine import (
    COCO_CLASSES,
    ONNXDetection,
    decode_output,
    detect_objects,
    get_onnx_session,
    letterbox,
)


def test_onnx_engine_does_not_import_torch_or_ultralytics():
    """Verify that importing app.ai.onnx_engine does NOT pull in torch or ultralytics."""
    assert "torch" not in sys.modules, "onnx_engine MUST NOT import torch!"
    assert "ultralytics" not in sys.modules, "onnx_engine MUST NOT import ultralytics!"


def test_letterbox_preprocessing_dimensions():
    """Verify aspect-ratio letterbox padding produces exactly 640x640 output."""
    frame_1080p = np.zeros((1080, 1920, 3), dtype=np.uint8)
    padded, ratio, (pad_w, pad_h) = letterbox(frame_1080p, (640, 640))

    assert padded.shape == (640, 640, 3)
    assert round(ratio, 4) == round(640 / 1920, 4)  # ~0.3333
    assert pad_w == 0.0
    assert pad_h == 140.0  # (640 - (1080 * (640/1920))) / 2 = (640 - 360) / 2 = 140


def test_decode_output_and_coordinate_restoration():
    """Verify raw tensor decoding, confidence filtering, and coordinate restoration."""
    # Synthetic output tensor (1, 84, 8400)
    tensor = np.zeros((1, 84, 8400), dtype=np.float32)

    # Set 1st anchor: cx=320, cy=320, w=100, h=200, class_0 (person) conf=0.85
    tensor[0, 0, 0] = 320.0  # cx
    tensor[0, 1, 0] = 320.0  # cy
    tensor[0, 2, 0] = 100.0  # w
    tensor[0, 3, 0] = 200.0  # h
    tensor[0, 4, 0] = 0.85   # class 0 score

    # Set 2nd anchor: low confidence (below 0.25 threshold)
    tensor[0, 0, 1] = 100.0
    tensor[0, 1, 1] = 100.0
    tensor[0, 2, 1] = 50.0
    tensor[0, 3, 1] = 50.0
    tensor[0, 4, 1] = 0.10   # class 0 score = 0.10

    # 1920x1080 original image with ratio=0.333333, pad_w=0, pad_h=140
    ratio = 640.0 / 1920.0
    pad_w = 0.0
    pad_h = 140.0

    detections = decode_output(
        tensor,
        image_width=1920,
        image_height=1080,
        ratio=ratio,
        pad_w=pad_w,
        pad_h=pad_h,
        conf_threshold=0.25,
        nms_threshold=0.45,
    )

    assert len(detections) == 1
    det = detections[0]
    assert isinstance(det, ONNXDetection)
    assert det.class_id == 0
    assert det.class_name == "person"
    assert det.confidence == 0.85

    # Check restored coordinates:
    # x1_pad = 320 - 50 = 270 -> x1_orig = (270 - 0) / (640/1920) = 810.0
    # y1_pad = 320 - 100 = 220 -> y1_orig = (220 - 140) / (640/1920) = 80 / (1/3) = 240.0
    assert abs(det.x1 - 810.0) < 1.0
    assert abs(det.y1 - 240.0) < 1.0
    assert abs(det.bounding_box.width - 300.0) < 1.0
    assert abs(det.bounding_box.height - 600.0) < 1.0


def test_nms_suppression_of_overlapping_boxes():
    """Verify Non-Maximum Suppression removes duplicate overlapping bounding boxes."""
    tensor = np.zeros((1, 84, 8400), dtype=np.float32)

    # Box 1: high confidence (0.90)
    tensor[0, 0, 0] = 320.0
    tensor[0, 1, 0] = 320.0
    tensor[0, 2, 0] = 100.0
    tensor[0, 3, 0] = 100.0
    tensor[0, 4, 0] = 0.90

    # Box 2: overlapping box (IoU > 0.45) with lower confidence (0.75)
    tensor[0, 0, 1] = 322.0
    tensor[0, 1, 1] = 322.0
    tensor[0, 2, 1] = 100.0
    tensor[0, 3, 1] = 100.0
    tensor[0, 4, 1] = 0.75

    detections = decode_output(
        tensor,
        image_width=640,
        image_height=640,
        ratio=1.0,
        pad_w=0.0,
        pad_h=0.0,
        conf_threshold=0.25,
        nms_threshold=0.45,
    )

    assert len(detections) == 1
    assert detections[0].confidence == 0.90


def test_detect_objects_with_onnx_model():
    """Integration test running detect_objects with actual yolov8n.onnx model."""
    onnx_file = Path(__file__).parent / "yolov8n.onnx"
    assert onnx_file.exists(), f"yolov8n.onnx not found at {onnx_file}"

    asset_path = Path(r"C:\Users\gopal\AppData\Local\Programs\Python\Python314\Lib\site-packages\ultralytics\assets\bus.jpg")
    if not asset_path.exists():
        frame = np.full((720, 1280, 3), 128, dtype=np.uint8)
    else:
        frame = cv2.imread(str(asset_path))

    session = get_onnx_session(onnx_file)
    detections, proc_time = detect_objects(frame, conf_threshold=0.25, session=session)

    assert proc_time > 0
    assert isinstance(detections, list)
    if asset_path.exists():
        assert len(detections) > 0
        classes_found = {d.class_name for d in detections}
        assert "bus" in classes_found or "person" in classes_found
