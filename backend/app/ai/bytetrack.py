"""Lightweight pure-NumPy ByteTrack algorithm for persistent object tracking.

Provides high-accuracy object tracking and persistent ID assignment across video frames
without importing PyTorch or Ultralytics.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Any

import numpy as np

# Assert torch and ultralytics are NOT imported
assert "torch" not in sys.modules, "bytetrack.py MUST NOT import torch!"
assert "ultralytics" not in sys.modules, "bytetrack.py MUST NOT import ultralytics!"


def compute_iou_matrix(boxes1: np.ndarray, boxes2: np.ndarray) -> np.ndarray:
    """Compute IoU matrix between N boxes1 and M boxes2.
    boxes shape: (N, 4) in [x1, y1, x2, y2] format.
    """
    if len(boxes1) == 0 or len(boxes2) == 0:
        return np.zeros((len(boxes1), len(boxes2)), dtype=np.float32)

    b1_x1, b1_y1, b1_x2, b1_y2 = boxes1[:, 0:1], boxes1[:, 1:2], boxes1[:, 2:3], boxes1[:, 3:4]
    b2_x1, b2_y1, b2_x2, b2_y2 = boxes2[:, 0], boxes2[:, 1], boxes2[:, 2], boxes2[:, 3]

    inter_x1 = np.maximum(b1_x1, b2_x1)
    inter_y1 = np.maximum(b1_y1, b2_y1)
    inter_x2 = np.minimum(b1_x2, b2_x2)
    inter_y2 = np.minimum(b1_y2, b2_y2)

    inter_w = np.maximum(0.0, inter_x2 - inter_x1)
    inter_h = np.maximum(0.0, inter_y2 - inter_y1)
    inter_area = inter_w * inter_h

    b1_area = (b1_x2 - b1_x1) * (b1_y2 - b1_y1)
    b2_area = (b2_x2 - b2_x1) * (b2_y2 - b2_y1)

    union = b1_area + b2_area - inter_area
    return inter_area / np.maximum(union, 1e-6)


@dataclass
class STrack:
    """Represents a single tracked target across frames."""

    track_id: int
    x1: float
    y1: float
    x2: float
    y2: float
    confidence: float
    class_id: int
    class_name: str
    frame_id: int
    state: str = "Tracked"  # "Tracked", "Lost", "Removed"
    tracklet_len: int = 0
    lost_frames: int = 0

    @property
    def bbox(self) -> np.ndarray:
        return np.array([self.x1, self.y1, self.x2, self.y2], dtype=np.float32)


class ByteTracker:
    """Pure-NumPy ByteTrack tracker session."""

    def __init__(
        self,
        high_thresh: float = 0.25,
        low_thresh: float = 0.10,
        match_thresh: float = 0.20,
        max_lost_frames: int = 30,
    ) -> None:
        self.high_thresh = high_thresh
        self.low_thresh = low_thresh
        self.match_thresh = match_thresh
        self.max_lost_frames = max_lost_frames
        self.tracked_stracks: list[STrack] = []
        self.lost_stracks: list[STrack] = []
        self.frame_id = 0
        self._next_id = 1

    def _get_next_id(self) -> int:
        tid = self._next_id
        self._next_id += 1
        return tid

    def update(self, detections: list[Any], frame_id: int) -> list[STrack]:
        """Update tracker state with new frame detections.

        Args:
            detections: Objects having x1, y1, x2, y2, confidence, class_id, class_name
            frame_id: 1-based frame index

        Returns:
            List of active STrack instances for the current frame.
        """
        self.frame_id = frame_id

        # Normalize detection inputs
        parsed_dets: list[dict[str, Any]] = []
        for det in detections:
            if hasattr(det, "x1"):
                x1, y1, x2, y2 = float(det.x1), float(det.y1), float(det.x2), float(det.y2)
                conf = float(det.confidence)
                cls_id = int(det.class_id)
                cls_name = str(det.class_name)
            elif isinstance(det, dict):
                x1, y1, x2, y2 = float(det["x1"]), float(det["y1"]), float(det["x2"]), float(det["y2"])
                conf = float(det["confidence"])
                cls_id = int(det["class_id"])
                cls_name = str(det["class_name"])
            else:
                continue

            parsed_dets.append({
                "bbox": np.array([x1, y1, x2, y2], dtype=np.float32),
                "score": conf,
                "class_id": cls_id,
                "class_name": cls_name,
            })

        if not parsed_dets:
            # Mark all tracked stracks as lost
            new_lost: list[STrack] = []
            for track in self.tracked_stracks:
                track.state = "Lost"
                track.lost_frames += 1
                if track.lost_frames <= self.max_lost_frames:
                    new_lost.append(track)
            for track in self.lost_stracks:
                track.lost_frames += 1
            self.lost_stracks = [t for t in (self.lost_stracks + new_lost) if t.lost_frames <= self.max_lost_frames]
            self.tracked_stracks = []
            return []

        scores = np.array([d["score"] for d in parsed_dets], dtype=np.float32)
        bboxes = np.array([d["bbox"] for d in parsed_dets], dtype=np.float32)
        class_ids = np.array([d["class_id"] for d in parsed_dets], dtype=np.int32)
        class_names = [d["class_name"] for d in parsed_dets]

        # Partition detections into High and Low confidence pools
        high_mask = scores >= self.high_thresh
        low_mask = (scores >= self.low_thresh) & (scores < self.high_thresh)

        high_dets = [
            STrack(-1, bboxes[i][0], bboxes[i][1], bboxes[i][2], bboxes[i][3], scores[i], class_ids[i], class_names[i], self.frame_id)
            for i in range(len(scores)) if high_mask[i]
        ]
        low_dets = [
            STrack(-1, bboxes[i][0], bboxes[i][1], bboxes[i][2], bboxes[i][3], scores[i], class_ids[i], class_names[i], self.frame_id)
            for i in range(len(scores)) if low_mask[i]
        ]

        activated_stracks: list[STrack] = []
        unmatched_tracks: list[STrack] = []
        unmatched_high_dets: list[STrack] = list(high_dets)

        # Candidate tracks for Stage 1 = active tracked stracks + lost stracks
        pool_tracks = self.tracked_stracks + self.lost_stracks

        # ── STAGE 1: Match active & lost tracks with high confidence detections ──
        if pool_tracks and high_dets:
            track_boxes = np.array([t.bbox for t in pool_tracks])
            det_boxes = np.array([d.bbox for d in high_dets])
            iou_mat = compute_iou_matrix(track_boxes, det_boxes)

            # Mask out class mismatches (don't match 'person' track with 'car' detection)
            for i, t in enumerate(pool_tracks):
                for j, d in enumerate(high_dets):
                    if t.class_id != d.class_id:
                        iou_mat[i, j] = -1.0

            matched_t_indices: set[int] = set()
            matched_d_indices: set[int] = set()

            for _ in range(min(len(pool_tracks), len(high_dets))):
                if iou_mat.max() < self.match_thresh:
                    break
                t_idx, d_idx = np.unravel_index(np.argmax(iou_mat), iou_mat.shape)
                if iou_mat[t_idx, d_idx] < self.match_thresh:
                    break

                track = pool_tracks[t_idx]
                det = high_dets[d_idx]
                track.x1, track.y1, track.x2, track.y2 = det.x1, det.y1, det.x2, det.y2
                track.confidence = det.confidence
                track.frame_id = self.frame_id
                track.tracklet_len += 1
                track.lost_frames = 0
                track.state = "Tracked"
                activated_stracks.append(track)

                matched_t_indices.add(t_idx)
                matched_d_indices.add(d_idx)
                iou_mat[t_idx, :] = -1.0
                iou_mat[:, d_idx] = -1.0

            unmatched_tracks = [pool_tracks[i] for i in range(len(pool_tracks)) if i not in matched_t_indices]
            unmatched_high_dets = [high_dets[i] for i in range(len(high_dets)) if i not in matched_d_indices]

        # ── STAGE 2: Match remaining tracks with low confidence detections ─────
        if unmatched_tracks and low_dets:
            track_boxes = np.array([t.bbox for t in unmatched_tracks])
            det_boxes = np.array([d.bbox for d in low_dets])
            iou_mat = compute_iou_matrix(track_boxes, det_boxes)

            for i, t in enumerate(unmatched_tracks):
                for j, d in enumerate(low_dets):
                    if t.class_id != d.class_id:
                        iou_mat[i, j] = -1.0

            matched_u_indices: set[int] = set()

            for _ in range(min(len(unmatched_tracks), len(low_dets))):
                if iou_mat.max() < self.match_thresh:
                    break
                t_idx, d_idx = np.unravel_index(np.argmax(iou_mat), iou_mat.shape)
                if iou_mat[t_idx, d_idx] < self.match_thresh:
                    break

                track = unmatched_tracks[t_idx]
                det = low_dets[d_idx]
                track.x1, track.y1, track.x2, track.y2 = det.x1, det.y1, det.x2, det.y2
                track.confidence = det.confidence
                track.frame_id = self.frame_id
                track.tracklet_len += 1
                track.lost_frames = 0
                track.state = "Tracked"
                activated_stracks.append(track)

                matched_u_indices.add(t_idx)
                iou_mat[t_idx, :] = -1.0
                iou_mat[:, d_idx] = -1.0

            unmatched_tracks = [unmatched_tracks[i] for i in range(len(unmatched_tracks)) if i not in matched_u_indices]

        # ── STAGE 3: New track creation & lost track maintenance ────────────────
        for det in unmatched_high_dets:
            det.track_id = self._get_next_id()
            det.state = "Tracked"
            det.tracklet_len = 1
            det.lost_frames = 0
            activated_stracks.append(det)

        # Update lost tracks
        new_lost: list[STrack] = []
        for track in unmatched_tracks:
            track.state = "Lost"
            track.lost_frames += 1
            if track.lost_frames <= self.max_lost_frames:
                new_lost.append(track)

        self.tracked_stracks = activated_stracks
        self.lost_stracks = [t for t in new_lost if t.lost_frames <= self.max_lost_frames]
        return self.tracked_stracks
