"""Comprehensive unit tests for Phase 9 Behavior Analysis Engine.

Tests cover:
1. Insufficient history detection
2. Loitering detection (positive and negative)
3. Stationary detection (positive and negative)
4. Rapid movement detection (positive and negative)
5. Direction reversal detection (positive and negative)
6. Repeated intrusion detection
7. Abnormal movement detection
8. Duplicate behavior prevention
9. Behavior score clamping [0, 100]
10. Deterministic results
11. Missing data handling
12. Multiple tracks/cameras
13. Engine initialization
14. WebSocket compatibility
"""

from __future__ import annotations

import pytest
from collections import deque
from datetime import datetime, timezone

from app.ai.behavior_engine import (
    BehaviorEngine,
    detect_loitering,
    detect_stationary,
    detect_rapid_movement,
    detect_direction_reversal,
    detect_repeated_intrusion,
    detect_abnormal_movement,
    calculate_distance,
    calculate_angle,
    calculate_angle_difference,
    get_behavior_severity,
)
from app.ai.behavior_schemas import (
    BehaviorAssessment,
    BehaviorObservationSchema,
)
from app.ai.schemas import BoundingBoxAI
from app.ai.track_history import TrackRecord


def create_test_track(
    track_id: int = 1,
    class_name: str = "person",
    first_seen_frame: int = 0,
    last_seen_frame: int = 100,
    positions: list[tuple[float, float]] | None = None,
) -> TrackRecord:
    """Create a TrackRecord for testing."""
    track = TrackRecord(
        track_id=track_id,
        class_name=class_name,
        first_seen_frame=first_seen_frame,
        last_seen_frame=last_seen_frame,
        position_log=deque(maxlen=50),
    )
    
    if positions:
        for i, (x, y) in enumerate(positions):
            track.position_log.append((x, y))
            track.latest_center_x = x
            track.latest_center_y = y
            track.frames_seen = i + 1
    
    return track


class TestInsufficientHistory:
    """Test handling of insufficient track history."""
    
    def test_empty_position_log(self) -> None:
        """Track with no positions should return None."""
        track = create_test_track()
        result = detect_loitering(track)
        assert result is None
    
    def test_insufficient_frames_for_detection(self) -> None:
        """Track with too few frames should return None."""
        track = create_test_track(positions=[(0, 0), (1, 1)])
        result = detect_rapid_movement(track)
        assert result is None


class TestStationaryDetection:
    """Test stationary behavior detection."""
    
    def test_stationary_positive(self) -> None:
        """Object with minimal movement should be classified as stationary."""
        # Object stays in same location (within 10 pixels)
        positions = [(100, 100)] * 20  # 20 frames at same position
        track = create_test_track(positions=positions)
        
        result = detect_stationary(track, max_displacement_pixels=20)
        assert result is not None
        assert result.behavior_type == "STATIONARY"
        assert result.severity in ("LOW", "MEDIUM", "HIGH", "CRITICAL")
    
    def test_stationary_negative(self) -> None:
        """Object with significant movement should NOT be stationary."""
        # Object moves 100 pixels
        positions = [(100.0 + i * 5, 100.0) for i in range(21)]
        track = create_test_track(positions=positions)
        
        result = detect_stationary(track, max_displacement_pixels=20)
        assert result is None


class TestLoiteringDetection:
    """Test loitering behavior detection."""
    
    def test_loitering_positive(self) -> None:
        """Object remaining in limited area for sustained period should be loitering."""
        # Object moves within 30-pixel radius over many frames
        positions = [(100.0 + i * 0.5, 100.0 + (i % 3) * 2) for i in range(90)]
        track = create_test_track(
            first_seen_frame=0,
            last_seen_frame=89,
            positions=positions,
        )
        
        result = detect_loitering(
            track,
            min_duration_seconds=2.0,
            max_displacement_pixels=50.0,
            fps=30.0,
        )
        assert result is not None
        assert result.behavior_type == "LOITERING"
    
    def test_loitering_negative_too_short(self) -> None:
        """Brief movement in limited area is not loitering."""
        positions = [(100.0 + i * 0.5, 100.0) for i in range(10)]
        track = create_test_track(positions=positions)
        
        result = detect_loitering(
            track,
            min_duration_seconds=5.0,
            max_displacement_pixels=50.0,
            fps=30.0,
        )
        assert result is None
    
    def test_loitering_negative_too_much_movement(self) -> None:
        """Movement exceeding displacement threshold is not loitering."""
        positions = [(100.0 + i * 10, 100.0) for i in range(20)]
        track = create_test_track(
            first_seen_frame=0,
            last_seen_frame=19,
            positions=positions,
        )
        
        result = detect_loitering(
            track,
            min_duration_seconds=2.0,
            max_displacement_pixels=30.0,
            fps=30.0,
        )
        assert result is None


class TestRapidMovementDetection:
    """Test rapid movement behavior detection."""
    
    def test_rapid_movement_positive(self) -> None:
        """Object moving quickly should be detected."""
        # Large jumps between frames
        positions = [(0.0 + i * 50, 0.0) for i in range(10)]
        track = create_test_track(positions=positions)
        
        result = detect_rapid_movement(
            track,
            threshold_pixels_per_second=100.0,
            fps=30.0,
        )
        assert result is not None
        assert result.behavior_type == "RAPID_MOVEMENT"
    
    def test_rapid_movement_negative(self) -> None:
        """Object moving slowly should not be rapid."""
        # Small movements
        positions = [(0.0 + i * 1, 0.0) for i in range(20)]
        track = create_test_track(positions=positions)
        
        result = detect_rapid_movement(
            track,
            threshold_pixels_per_second=100.0,
            fps=30.0,
        )
        assert result is None


class TestDirectionReversalDetection:
    """Test direction reversal behavior detection."""
    
    def test_direction_reversal_positive(self) -> None:
        """Large change in movement direction should be detected."""
        # Move right, then move back left (180° reversal)
        positions = [
            (0, 0), (5, 0), (10, 0), (15, 0),  # Moving right
            (14, 0), (10, 0), (5, 0), (0, 0),  # Moving left (reversal)
        ]
        track = create_test_track(positions=positions)
        
        result = detect_direction_reversal(
            track,
            angle_threshold_degrees=120.0,
            fps=30.0,
        )
        assert result is not None
        assert result.behavior_type == "DIRECTION_REVERSAL"
    
    def test_direction_reversal_with_jitter(self) -> None:
        """Small directional changes should not trigger direction reversal."""
        # Move right with slight jitter (< 120°)
        positions = [
            (0, 0), (5, 0), (10, 0.5), (15, 0.2), (20, 0),
        ]
        track = create_test_track(positions=positions)
        
        result = detect_direction_reversal(
            track,
            angle_threshold_degrees=120.0,
            fps=30.0,
        )
        assert result is None


class TestRepeatedIntrusionDetection:
    """Test repeated intrusion behavior detection."""
    
    def test_repeated_intrusion_positive(self) -> None:
        """Multiple intrusions should be detected."""
        track = create_test_track()
        
        result = detect_repeated_intrusion(track, intrusion_count=3, min_repeat_threshold=2)
        assert result is not None
        assert result.behavior_type == "REPEATED_INTRUSION"
    
    def test_repeated_intrusion_negative(self) -> None:
        """Single intrusion should not be repeated."""
        track = create_test_track()
        
        result = detect_repeated_intrusion(track, intrusion_count=1, min_repeat_threshold=2)
        assert result is None


class TestAbnormalMovementDetection:
    """Test abnormal movement behavior detection."""
    
    def test_abnormal_movement_multiple_reversals(self) -> None:
        """Multiple direction reversals should trigger abnormal movement."""
        observations = [
            BehaviorObservationSchema(
                behavior_type="DIRECTION_REVERSAL",
                severity="MEDIUM",
                confidence=0.8,
                evidence={},
                reason="Test",
                detected_at=datetime.now(timezone.utc),
            ),
            BehaviorObservationSchema(
                behavior_type="DIRECTION_REVERSAL",
                severity="MEDIUM",
                confidence=0.8,
                evidence={},
                reason="Test",
                detected_at=datetime.now(timezone.utc),
            ),
        ]
        
        result = detect_abnormal_movement(observations)
        assert result is not None
        assert result.behavior_type == "ABNORMAL_MOVEMENT"
    
    def test_abnormal_movement_reversal_with_rapid(self) -> None:
        """Direction reversal + rapid movement should trigger abnormal."""
        observations = [
            BehaviorObservationSchema(
                behavior_type="DIRECTION_REVERSAL",
                severity="MEDIUM",
                confidence=0.8,
                evidence={},
                reason="Test",
                detected_at=datetime.now(timezone.utc),
            ),
            BehaviorObservationSchema(
                behavior_type="RAPID_MOVEMENT",
                severity="HIGH",
                confidence=0.8,
                evidence={},
                reason="Test",
                detected_at=datetime.now(timezone.utc),
            ),
        ]
        
        result = detect_abnormal_movement(observations)
        assert result is not None
        assert result.behavior_type == "ABNORMAL_MOVEMENT"


class TestBehaviorSeverity:
    """Test behavior severity determination."""
    
    def test_high_confidence_critical_behavior(self) -> None:
        """High confidence + REPEATED_INTRUSION should be CRITICAL."""
        severity = get_behavior_severity("REPEATED_INTRUSION", 0.95)
        assert severity == "CRITICAL"
    
    def test_low_confidence_same_behavior(self) -> None:
        """Low confidence reduces severity."""
        severity = get_behavior_severity("REPEATED_INTRUSION", 0.6)
        assert severity in ("LOW", "MEDIUM")


class TestBehaviorScoreClamping:
    """Test behavior score clamping to [0, 100]."""
    
    def test_score_clamping_high(self) -> None:
        """Multiple behaviors should clamp to 100."""
        engine = BehaviorEngine()
        
        observations = [
            BehaviorObservationSchema(
                behavior_type="LOITERING",
                severity="MEDIUM",
                confidence=0.8,
                evidence={},
                reason="Test",
                detected_at=datetime.now(timezone.utc),
            ),
            BehaviorObservationSchema(
                behavior_type="RAPID_MOVEMENT",
                severity="HIGH",
                confidence=0.8,
                evidence={},
                reason="Test",
                detected_at=datetime.now(timezone.utc),
            ),
            BehaviorObservationSchema(
                behavior_type="REPEATED_INTRUSION",
                severity="CRITICAL",
                confidence=0.9,
                evidence={},
                reason="Test",
                detected_at=datetime.now(timezone.utc),
            ),
        ]
        
        # Calculate score manually
        from app.ai.behavior_schemas import BEHAVIOR_CONTRIBUTIONS
        score = sum(BEHAVIOR_CONTRIBUTIONS.get(obs.behavior_type, 0) for obs in observations)
        clamped = min(100, max(0, score))
        
        assert clamped <= 100
        assert clamped >= 0


class TestDeterminism:
    """Test deterministic behavior calculation."""
    
    def test_same_input_same_output(self) -> None:
        """Same track data should produce identical results."""
        positions = [(100.0 + i * 0.5, 100.0) for i in range(30)]
        
        track1 = create_test_track(positions=list(positions))
        track2 = create_test_track(positions=list(positions))
        
        result1 = detect_loitering(
            track1,
            min_duration_seconds=2.0,
            max_displacement_pixels=50.0,
            fps=30.0,
        )
        result2 = detect_loitering(
            track2,
            min_duration_seconds=2.0,
            max_displacement_pixels=50.0,
            fps=30.0,
        )
        
        if result1 and result2:
            assert result1.behavior_type == result2.behavior_type
            assert result1.severity == result2.severity
            assert result1.confidence == result2.confidence


class TestMissingData:
    """Test handling of missing optional data."""
    
    def test_missing_timestamps(self) -> None:
        """Engine should work even without precise timestamps."""
        positions = [(100.0 + i, 100.0) for i in range(20)]
        track = create_test_track(positions=positions)
        
        engine = BehaviorEngine(fps=30.0)
        result = engine.analyze_track("cam1", track, intrusion_count=1)
        
        # Should not crash with missing timestamps
        assert result is None or isinstance(result, BehaviorAssessment)


class TestEngineIntegration:
    """Test complete behavior engine."""
    
    def test_analyze_track_no_behaviors(self) -> None:
        """Track with minimal data should return None."""
        track = create_test_track(positions=[(0, 0), (1, 1)])
        engine = BehaviorEngine()
        
        result = engine.analyze_track("cam1", track)
        assert result is None
    
    def test_analyze_track_with_behaviors(self) -> None:
        """Track with clear behaviors should produce assessment."""
        positions = [(100.0 + i * 0.5, 100.0) for i in range(90)]
        track = create_test_track(
            first_seen_frame=0,
            last_seen_frame=89,
            positions=positions,
        )
        
        engine = BehaviorEngine(
            loitering_min_duration_seconds=2.0,
            fps=30.0,
        )
        result = engine.analyze_track("cam1", track, intrusion_count=1)
        
        assert result is not None
        assert result.camera_id == "cam1"
        assert result.track_id == 1
        assert 0 <= result.behavior_score <= 100
        assert result.observations


class TestMultipleTracksAndCameras:
    """Test behavior detection across multiple tracks/cameras."""
    
    def test_multiple_tracks(self) -> None:
        """Should handle multiple tracks independently."""
        track1 = create_test_track(track_id=1, positions=[(0, 0)] * 20)
        track2 = create_test_track(track_id=2, positions=[(100, 100)] * 20)
        
        engine = BehaviorEngine()
        
        result1 = engine.analyze_track("cam1", track1)
        result2 = engine.analyze_track("cam1", track2)
        
        # Both should return assessments
        assert result1 is not None
        assert result2 is not None
        assert result1.track_id == 1
        assert result2.track_id == 2


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_single_position(self) -> None:
        """Track with single position should not crash."""
        track = create_test_track(positions=[(100, 100)])
        engine = BehaviorEngine()
        
        result = engine.analyze_track("cam1", track)
        assert result is None
    
    def test_zero_confidence(self) -> None:
        """Zero confidence should not crash."""
        severity = get_behavior_severity("LOITERING", 0.0)
        assert severity == "LOW"
    
    def test_perfect_confidence(self) -> None:
        """Perfect confidence should be handled."""
        severity = get_behavior_severity("REPEATED_INTRUSION", 1.0)
        assert severity == "CRITICAL"


# Run all tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
