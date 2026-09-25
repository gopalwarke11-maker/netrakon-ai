"""ONNX Runtime inference engine for YOLOv8 object detection.

Provides high-performance, low-memory ONNX inference without importing PyTorch or Ultralytics.
"""

from __future__ import annotations

import logging
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
import onnxruntime as ort

from app.ai.schemas import BoundingBoxAI
from app.core.config import settings

# Explicit safety checks: Guarantee torch and ultralytics are NOT imported
assert "torch" not in sys.modules, "onnx_engine.py MUST NOT import torch!"
assert "ultralytics" not in sys.modules, "onnx_engine.py MUST NOT import ultralytics!"

logger = logging.getLogger(__name__)

COCO_CLASSES: list[str] = [
    "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train", "truck", "boat",
    "traffic light", "fire hydrant", "stop sign", "parking meter", "bench", "bird", "cat",
    "dog", "horse", "sheep", "cow", "elephant", "bear", "zebra", "giraffe", "backpack",
    "umbrella", "handbag", "tie", "suitcase", "frisbee", "skis", "snowboard", "sports ball",
    "kite", "baseball bat", "baseball glove", "skateboard", "surfboard", "tennis racket",
    "bottle", "wine glass", "cup", "fork", "knife", "spoon", "bowl", "banana", "apple",
    "sandwich", "orange", "broccoli", "carrot", "hot dog", "pizza", "donut", "cake",
    "chair", "couch", "potted plant", "bed", "dining table", "toilet", "tv", "laptop",
    "mouse", "remote", "keyboard", "cell phone", "microwave", "oven", "toaster", "sink",
    "refrigerator", "book", "clock", "vase", "scissors", "teddy bear", "hair drier", "toothbrush"
]


@dataclass
class ONNXDetection:
    """Internal structured representation of a single detected object."""

    x1: float
    y1: float
    x2: float
    y2: float
    confidence: float
    class_id: int
    class_name: str
    bounding_box: BoundingBoxAI


_onnx_session: ort.InferenceSession | None = None
_onnx_session_lock = threading.Lock()


def get_onnx_session(model_path: str | Path | None = None) -> ort.InferenceSession:
    """Get or lazily initialize the singleton ONNX Runtime InferenceSession."""
    global _onnx_session  # noqa: PLW0603

    with _onnx_session_lock:
        if _onnx_session is not None:
            return _onnx_session

        if model_path is None:
            # Default to yolov8n.onnx in project root/backend directory
            possible_paths = [
                Path(settings.yolo_model_name),
                Path(__file__).resolve().parent.parent.parent / "yolov8n.onnx",
                Path(__file__).resolve().parent.parent.parent.parent / "yolov8n.onnx",
            ]
            for p in possible_paths:
                if p.exists() and p.suffix.lower() == ".onnx":
                    model_path = p
                    break

            if model_path is None or not Path(model_path).exists():
                # Fall back to configured model_path if string provided
                model_path = Path(settings.yolo_model_name)

        model_path = Path(model_path)
        if not model_path.exists():
            raise RuntimeError(f"ONNX model file not found at: {model_path}")

        logger.info("[ONNX Engine] Initializing ONNX Runtime session: %s", model_path)
        _onnx_session = ort.InferenceSession(str(model_path), providers=["CPUExecutionProvider"])
        return _onnx_session


def letterbox(
    img: np.ndarray,
    target_shape: tuple[int, int] = (640, 640),
    color: tuple[int, int, int] = (114, 114, 114),
) -> tuple[np.ndarray, float, tuple[float, float]]:
    """Resize image and pad to target_shape maintaining aspect ratio.

    Returns:
        (padded_img, scale_ratio, (pad_w, pad_h))
    """
    shape = img.shape[:2]  # [height, width]
    ratio = min(target_shape[0] / shape[0], target_shape[1] / shape[1])

    new_unpad = (int(round(shape[1] * ratio)), int(round(shape[0] * ratio)))
    dw = (target_shape[1] - new_unpad[0]) / 2.0
    dh = (target_shape[0] - new_unpad[1]) / 2.0

    if shape[::-1] != new_unpad:
        img = cv2.resize(img, new_unpad, interpolation=cv2.INTER_LINEAR)

    top, bottom = int(round(dh - 0.1)), int(round(dh + 0.1))
    left, right = int(round(dw - 0.1)), int(round(dw + 0.1))
    padded_img = cv2.copyMakeBorder(img, top, bottom, left, right, cv2.BORDER_CONSTANT, value=color)
    return padded_img, ratio, (dw, dh)


def decode_output(
    output_tensor: np.ndarray,
    image_width: int,
    image_height: int,
    ratio: float,
    pad_w: float,
    pad_h: float,
    conf_threshold: float = 0.25,
    nms_threshold: float = 0.45,
) -> list[ONNXDetection]:
    """Decode raw ONNX output tensor (1, 84, 8400) to ONNXDetection objects."""
    if output_tensor.ndim == 3 and output_tensor.shape[0] == 1:
        output = output_tensor[0].T  # (8400, 84)
    else:
        output = output_tensor.T

    boxes_cxcywh = output[:, 0:4]
    scores = output[:, 4:]

    class_ids = np.argmax(scores, axis=1)
    confidences = np.max(scores, axis=1)

    mask = confidences >= conf_threshold
    if not np.any(mask):
        return []

    filtered_boxes = boxes_cxcywh[mask]
    filtered_confs = confidences[mask]
    filtered_classes = class_ids[mask]

    boxes_xywh: list[list[int]] = []
    for box in filtered_boxes:
        cx, cy, w, h = box
        x1 = cx - w / 2.0
        y1 = cy - h / 2.0
        boxes_xywh.append([int(x1), int(y1), int(w), int(h)])

    indices = cv2.dnn.NMSBoxes(boxes_xywh, filtered_confs.tolist(), conf_threshold, nms_threshold)

    detections: list[ONNXDetection] = []
    if len(indices) > 0:
        indices = indices.flatten()
        for idx in indices:
            cx, cy, w, h = filtered_boxes[idx]
            conf = float(filtered_confs[idx])
            cls_id = int(filtered_classes[idx])
            cls_name = COCO_CLASSES[cls_id] if cls_id < len(COCO_CLASSES) else str(cls_id)

            x1_pad = cx - w / 2.0
            y1_pad = cy - h / 2.0
            x2_pad = cx + w / 2.0
            y2_pad = cy + h / 2.0

            x1 = max(0.0, min(float(image_width), (x1_pad - pad_w) / ratio))
            y1 = max(0.0, min(float(image_height), (y1_pad - pad_h) / ratio))
            x2 = max(0.0, min(float(image_width), (x2_pad - pad_w) / ratio))
            y2 = max(0.0, min(float(image_height), (y2_pad - pad_h) / ratio))

            bbox = BoundingBoxAI(
                x1=round(x1, 2),
                y1=round(y1, 2),
                x2=round(x2, 2),
                y2=round(y2, 2),
                width=round(x2 - x1, 2),
                height=round(y2 - y1, 2),
            )

            detections.append(
                ONNXDetection(
                    x1=round(x1, 2),
                    y1=round(y1, 2),
                    x2=round(x2, 2),
                    y2=round(y2, 2),
                    confidence=round(conf, 4),
                    class_id=cls_id,
                    class_name=cls_name,
                    bounding_box=bbox,
                )
            )

    return detections


def detect_objects(
    frame: np.ndarray,
    conf_threshold: float | None = None,
    nms_threshold: float = 0.45,
    session: ort.InferenceSession | None = None,
) -> tuple[list[ONNXDetection], float]:
    """Run ONNX object detection on a single BGR frame.

    Args:
        frame: OpenCV BGR image array (H, W, 3).
        conf_threshold: Minimum confidence score [0, 1].
        nms_threshold: Non-Maximum Suppression IoU threshold.
        session: Optional custom InferenceSession instance.

    Returns:
        (detections, processing_time_ms)
    """
    if frame is None or frame.size == 0:
        raise ValueError("Received an empty or invalid frame.")

    if conf_threshold is None:
        conf_threshold = settings.yolo_conf_threshold

    session = session or get_onnx_session()
    image_height, image_width = frame.shape[:2]

    t0 = time.perf_counter()

    # Preprocess
    img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    img_padded, ratio, (pad_w, pad_h) = letterbox(img_rgb, (640, 640))
    blob = img_padded.transpose((2, 0, 1))[np.newaxis, :, :, :].astype(np.float32) / 255.0

    # Run ONNX inference
    input_name = session.get_inputs()[0].name
    raw_out = session.run(None, {input_name: blob})[0]

    # Decode and NMS
    detections = decode_output(
        raw_out,
        image_width=image_width,
        image_height=image_height,
        ratio=ratio,
        pad_w=pad_w,
        pad_h=pad_h,
        conf_threshold=conf_threshold,
        nms_threshold=nms_threshold,
    )

    processing_time_ms = (time.perf_counter() - t0) * 1000
    return detections, round(processing_time_ms, 2)
