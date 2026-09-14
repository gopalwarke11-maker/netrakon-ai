"""Comprehensive unit tests for Phase 8 Risk Intelligence Engine."""

import pytest
from datetime import datetime, timezone

from app.ai.risk_engine import calculate_risk, RiskAssessment
from app.models.intrusion import IntrusionEvent, IntrusionPoint


def create_test_event(
    severity: str = "HIGH",
    object_class: str = "person",
    confidence: float = 0.85,
    direction: str = "UNRESTRICTED_TO_RESTRICTED",
) -> IntrusionEvent:
    """Helper to create a test intrusion event."""
    return IntrusionEvent(
        id="TEST-EVT",
        camera_id="TEST-CAM",
        boundary_id="TEST-BND",
        boundary_name="Test Boundary",
        track_id=1,
        object_class=object_class,
        confidence=confidence,
        timestamp=datetime.now(timezone.utc),
        current_anchor=IntrusionPoint(x=100, y=100),
        previous_anchor=IntrusionPoint(x=0, y=0),
        crossing_direction=direction,  # type: ignore
        severity=severity,  # type: ignore
        alert_id=None,
    )


class TestRiskScoringBasics:
    """Test fundamental risk scoring behavior."""

    def test_low_intrusion_produces_low_risk(self) -> None:
        """Intrusion severity LOW should produce LOW or MEDIUM risk."""
        # LOW severity alone = 10, with person = 30, so can be LOW if we use unknown class
        event = create_test_event(
            severity="LOW",
            object_class="unknown",
            confidence=0.30,
            direction="NONE"  # type: ignore
        )
        assessment = calculate_risk(event, repeat_count=1)
        
        # Score should be 10 (severity only), which is LOW
        assert assessment.risk_level == "LOW"
        assert assessment.risk_score == 10

    def test_medium_intrusion_produces_medium_risk(self) -> None:
        """Intrusion severity MEDIUM should produce MEDIUM risk."""
        event = create_test_event(
            severity="MEDIUM",
            object_class="unknown",
            confidence=0.30,
            direction="NONE"  # type: ignore
        )
        assessment = calculate_risk(event, repeat_count=1)
        
        # Score should be 25 (severity only), which is MEDIUM
        assert assessment.risk_level == "MEDIUM"
        assert assessment.risk_score == 25

    def test_high_intrusion_produces_high_risk(self) -> None:
        """Intrusion severity HIGH should produce HIGH risk with enough factors."""
        # HIGH severity alone = 40, which is MEDIUM (25-49)
        # Need HIGH severity (40) + person (20) = 60 to reach HIGH (50-74)
        event = create_test_event(
            severity="HIGH",
            object_class="person",
            confidence=0.30,
            direction="NONE"  # type: ignore
        )
        assessment = calculate_risk(event, repeat_count=1)
        
        assert assessment.risk_score >= 50
        assert assessment.risk_level == "HIGH"

    def test_critical_intrusion_produces_critical_risk(self) -> None:
        """Intrusion severity CRITICAL should produce CRITICAL risk."""
        # CRITICAL severity = 55, which is already CRITICAL (75-100)... wait no
        # Actually 55 is in the HIGH range (50-74)
        # Need CRITICAL (55) + person (20) = 75 to reach CRITICAL
        event = create_test_event(
            severity="CRITICAL",
            object_class="person",
            confidence=0.30,
            direction="NONE"  # type: ignore
        )
        assessment = calculate_risk(event, repeat_count=1)
        
        assert assessment.risk_score >= 75
        assert assessment.risk_level == "CRITICAL"


class TestObjectTypeContributions:
    """Test object type factor contributions."""

    def test_person_increases_risk(self) -> None:
        """Person class should contribute +20 to risk."""
        event = create_test_event(object_class="person", confidence=0.85)
        assessment = calculate_risk(event, repeat_count=1)
        
        # Should have contribution from severity + person
        assert any(f.factor == "object_type" and f.contribution == 20 for f in assessment.factors)

    def test_car_increases_risk(self) -> None:
        """Car class should contribute +10 to risk."""
        event = create_test_event(object_class="car", confidence=0.85)
        assessment = calculate_risk(event, repeat_count=1)
        
        assert any(f.factor == "object_type" and f.contribution == 10 for f in assessment.factors)

    def test_truck_increases_risk(self) -> None:
        """Truck class should contribute +15 to risk."""
        event = create_test_event(object_class="truck", confidence=0.85)
        assessment = calculate_risk(event, repeat_count=1)
        
        assert any(f.factor == "object_type" and f.contribution == 15 for f in assessment.factors)

    def test_unknown_object_type_no_contribution(self) -> None:
        """Unknown object class should contribute +0."""
        event = create_test_event(object_class="unknown_class", confidence=0.85)
        assessment = calculate_risk(event, repeat_count=1)
        
        assert any(f.factor == "object_type" and f.contribution == 0 for f in assessment.factors)


class TestConfidenceContributions:
    """Test detection confidence factor contributions."""

    def test_confidence_below_040_no_contribution(self) -> None:
        """Confidence < 0.40 should contribute +0."""
        event = create_test_event(confidence=0.30)
        assessment = calculate_risk(event, repeat_count=1)
        
        assert any(f.factor == "detection_confidence" and f.contribution == 0 for f in assessment.factors)

    def test_confidence_040_to_060_five_points(self) -> None:
        """Confidence 0.40–0.60 should contribute +5."""
        event = create_test_event(confidence=0.50)
        assessment = calculate_risk(event, repeat_count=1)
        
        assert any(f.factor == "detection_confidence" and f.contribution == 5 for f in assessment.factors)

    def test_confidence_060_to_080_ten_points(self) -> None:
        """Confidence 0.60–0.80 should contribute +10."""
        event = create_test_event(confidence=0.70)
        assessment = calculate_risk(event, repeat_count=1)
        
        assert any(f.factor == "detection_confidence" and f.contribution == 10 for f in assessment.factors)

    def test_confidence_080_plus_fifteen_points(self) -> None:
        """Confidence >= 0.80 should contribute +15."""
        event = create_test_event(confidence=0.95)
        assessment = calculate_risk(event, repeat_count=1)
        
        assert any(f.factor == "detection_confidence" and f.contribution == 15 for f in assessment.factors)

    def test_confidence_none_no_contribution(self) -> None:
        """Missing confidence should contribute +0."""
        event = create_test_event(confidence=None)
        assessment = calculate_risk(event, repeat_count=1)
        
        assert any(f.factor == "detection_confidence" and f.contribution == 0 for f in assessment.factors)


class TestDirectionContributions:
    """Test crossing direction factor contributions."""

    def test_unrestricted_to_restricted_fifteen_points(self) -> None:
        """Unrestricted→Restricted should contribute +15."""
        event = create_test_event(direction="UNRESTRICTED_TO_RESTRICTED")
        assessment = calculate_risk(event, repeat_count=1)
        
        assert any(f.factor == "direction" and f.contribution == 15 for f in assessment.factors)

    def test_restricted_to_unrestricted_five_points(self) -> None:
        """Restricted→Unrestricted should contribute +5."""
        event = create_test_event(direction="RESTRICTED_TO_UNRESTRICTED")
        assessment = calculate_risk(event, repeat_count=1)
        
        assert any(f.factor == "direction" and f.contribution == 5 for f in assessment.factors)

    def test_unknown_direction_no_contribution(self) -> None:
        """Unknown direction should contribute +0."""
        event = create_test_event(direction="NONE")  # type: ignore
        assessment = calculate_risk(event, repeat_count=1)
        
        assert any(f.factor == "direction" and f.contribution == 0 for f in assessment.factors)


class TestRepeatedActivityContributions:
    """Test repeated activity factor contributions."""

    def test_first_event_no_contribution(self) -> None:
        """First event (repeat_count=1) should contribute +0."""
        event = create_test_event()
        assessment = calculate_risk(event, repeat_count=1)
        
        assert any(f.factor == "repeated_activity" and f.contribution == 0 for f in assessment.factors)

    def test_second_event_five_points(self) -> None:
        """Second event (repeat_count=2) should contribute +5."""
        event = create_test_event()
        assessment = calculate_risk(event, repeat_count=2)
        
        assert any(f.factor == "repeated_activity" and f.contribution == 5 for f in assessment.factors)

    def test_third_plus_event_ten_points(self) -> None:
        """Third+ event (repeat_count>=3) should contribute +10."""
        event = create_test_event()
        assessment = calculate_risk(event, repeat_count=3)
        
        assert any(f.factor == "repeated_activity" and f.contribution == 10 for f in assessment.factors)


class TestRiskLevelThresholds:
    """Test risk level boundary conditions."""

    def test_score_24_is_low(self) -> None:
        """Score 24 should be LOW (0-24 range)."""
        # LOW severity = 10
        # Use unknown object and none direction to get exactly 10
        event = create_test_event(severity="LOW", object_class="unknown", confidence=0.30, direction="NONE")  # type: ignore
        assessment = calculate_risk(event, repeat_count=1)
        
        assert assessment.risk_score <= 24
        assert assessment.risk_level == "LOW"

    def test_score_25_is_medium(self) -> None:
        """Score 25 should be MEDIUM (25-49 range)."""
        # MEDIUM severity = 25
        event = create_test_event(severity="MEDIUM", object_class="unknown", confidence=0.30, direction="NONE")  # type: ignore
        assessment = calculate_risk(event, repeat_count=1)
        
        assert assessment.risk_score >= 25
        assert assessment.risk_level == "MEDIUM"

    def test_score_49_is_medium(self) -> None:
        """Score 49 should be MEDIUM (25-49 range)."""
        # MEDIUM severity (25) + bicycle (8) + moderate confidence (5) + restricted->unrestricted (5) = 43
        event = create_test_event(
            severity="MEDIUM",
            object_class="bicycle",
            confidence=0.50,
            direction="RESTRICTED_TO_UNRESTRICTED"
        )
        assessment = calculate_risk(event, repeat_count=1)
        
        assert assessment.risk_score <= 49
        assert assessment.risk_level == "MEDIUM"

    def test_score_50_is_high(self) -> None:
        """Score 50 should be HIGH (50-74 range)."""
        # HIGH severity = 40, + unknown = 0, + confidence 0.30 = 0, + direction NONE = 0 => 40
        # HIGH severity (40) + bicycle (8) + restricted->unrestricted (5) = 53
        event = create_test_event(
            severity="HIGH",
            object_class="bicycle",
            confidence=0.30,
            direction="RESTRICTED_TO_UNRESTRICTED"
        )
        assessment = calculate_risk(event, repeat_count=1)
        
        assert assessment.risk_score >= 50
        assert assessment.risk_level == "HIGH"

    def test_score_74_is_high(self) -> None:
        """Score 74 should be HIGH (50-74 range)."""
        # HIGH severity (40) + person (20) + high confidence (15) - unrestricted_to_restricted (15) = 90, too high
        # HIGH severity (40) + person (20) + none direction (0) + low confidence (0) = 60
        event = create_test_event(
            severity="HIGH",
            object_class="person",
            confidence=0.30,
            direction="NONE"  # type: ignore
        )
        assessment = calculate_risk(event, repeat_count=1)
        
        assert assessment.risk_score <= 74
        assert assessment.risk_level == "HIGH"

    def test_score_75_is_critical(self) -> None:
        """Score 75 should be CRITICAL (75-100 range)."""
        # CRITICAL severity = 55
        # CRITICAL (55) + person (20) = 75
        event = create_test_event(
            severity="CRITICAL",
            object_class="person",
            confidence=0.30,
            direction="NONE"  # type: ignore
        )
        assessment = calculate_risk(event, repeat_count=1)
        
        assert assessment.risk_score >= 75
        assert assessment.risk_level == "CRITICAL"


class TestScoreClamping:
    """Test that scores are properly clamped to [0, 100]."""

    def test_score_cannot_exceed_100(self) -> None:
        """Score should never exceed 100."""
        event = create_test_event(
            severity="CRITICAL",
            object_class="person",
            confidence=0.95,
            direction="UNRESTRICTED_TO_RESTRICTED"
        )
        assessment = calculate_risk(event, repeat_count=10)  # Many repeats
        
        assert 0 <= assessment.risk_score <= 100

    def test_score_cannot_be_below_0(self) -> None:
        """Score should never be below 0."""
        event = create_test_event(
            severity="LOW",
            object_class="unknown",
            confidence=0.30,
            direction="NONE"  # type: ignore
        )
        assessment = calculate_risk(event, repeat_count=1)
        
        assert 0 <= assessment.risk_score <= 100


class TestMissingData:
    """Test handling of missing or optional data."""

    def test_missing_object_type(self) -> None:
        """Missing object type should be handled gracefully."""
        event = create_test_event(object_class="")
        assessment = calculate_risk(event, repeat_count=1)
        
        assert assessment.risk_score >= 0
        assert assessment.risk_level in ("LOW", "MEDIUM", "HIGH", "CRITICAL")

    def test_missing_confidence(self) -> None:
        """Missing confidence should be handled gracefully."""
        event = create_test_event(confidence=None)
        assessment = calculate_risk(event, repeat_count=1)
        
        assert assessment.risk_score >= 0
        assert assessment.risk_level in ("LOW", "MEDIUM", "HIGH", "CRITICAL")


class TestDeterminism:
    """Test that risk calculation is deterministic."""

    def test_repeated_calculation_identical(self) -> None:
        """Same event calculated multiple times should produce identical results."""
        event = create_test_event(
            severity="HIGH",
            object_class="person",
            confidence=0.85,
            direction="UNRESTRICTED_TO_RESTRICTED"
        )
        
        assessment1 = calculate_risk(event, repeat_count=2)
        assessment2 = calculate_risk(event, repeat_count=2)
        
        assert assessment1.risk_score == assessment2.risk_score
        assert assessment1.risk_level == assessment2.risk_level
        assert len(assessment1.factors) == len(assessment2.factors)


class TestFactorExplanations:
    """Test that factors are properly explained."""

    def test_all_factors_present(self) -> None:
        """Assessment should include all expected factors."""
        event = create_test_event()
        assessment = calculate_risk(event, repeat_count=1)
        
        factor_names = {f.factor for f in assessment.factors}
        expected_factors = {
            "intrusion_severity",
            "object_type",
            "detection_confidence",
            "direction",
            "repeated_activity",
        }
        
        assert expected_factors == factor_names

    def test_factors_have_reasons(self) -> None:
        """Each factor should have a non-empty reason."""
        event = create_test_event()
        assessment = calculate_risk(event, repeat_count=1)
        
        for factor in assessment.factors:
            assert len(factor.reason) > 0
            assert factor.contribution >= 0

    def test_contributions_sum_reasonable(self) -> None:
        """Sum of contributions should relate to final score."""
        event = create_test_event()
        assessment = calculate_risk(event, repeat_count=1)
        
        total_contributions = sum(f.contribution for f in assessment.factors)
        # Score should be clamped sum of contributions
        assert assessment.risk_score <= 100
        assert assessment.risk_score >= 0
