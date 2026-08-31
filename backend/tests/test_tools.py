"""Unit tests for Quantitative Calculation & Sensitivity Analysis Engine."""

import pytest
from core.tools import recalculate_matrix, sensitivity_analysis, compute_confidence_bucket


def test_recalculate_matrix_scoring(sample_criteria_options):
    """Test normalized weighted scoring calculations."""
    criteria, options = sample_criteria_options
    recalculated = recalculate_matrix(criteria, options)

    assert len(recalculated) == 2
    # Cloud Run: 9*0.4 + 8*0.35 + 10*0.25 = 3.6 + 2.8 + 2.5 = 8.90
    assert recalculated[0]["name"] == "Cloud Run"
    assert recalculated[0]["total_weighted"] == 8.90
    assert recalculated[0]["rank"] == 1

    # GKE: 6*0.4 + 10*0.35 + 5*0.25 = 2.4 + 3.5 + 1.25 = 7.15
    assert recalculated[1]["name"] == "GKE Standard"
    assert recalculated[1]["total_weighted"] == 7.15
    assert recalculated[1]["rank"] == 2


def test_recalculate_matrix_zero_weights():
    """Test recalculation resilience when criteria have 0 weight."""
    criteria = [{"name": "Price", "weight": 0}]
    options = [{"name": "Product A", "scores": {"Price": 8}}]
    recalculated = recalculate_matrix(criteria, options)
    assert len(recalculated) == 1
    assert recalculated[0]["total_weighted"] == 0.0


def test_sensitivity_analysis_scenarios(sample_criteria_options):
    """Test sensitivity analysis produces optimistic, base, and pessimistic sweeps."""
    criteria, options = sample_criteria_options
    result = sensitivity_analysis(criteria, options, target_criterion="Cost", swing_pct=15)

    assert "scenarios" in result
    assert "optimistic" in result["scenarios"]
    assert "base" in result["scenarios"]
    assert "pessimistic" in result["scenarios"]

    # Base weight for Cost is 40
    assert result["scenarios"]["base"]["weight_used"] == 40
    assert result["scenarios"]["optimistic"]["weight_used"] == 55
    assert result["scenarios"]["pessimistic"]["weight_used"] == 25


def test_sensitivity_analysis_invalid_criterion(sample_criteria_options):
    """Test sensitivity analysis gracefully handles missing criteria."""
    criteria, options = sample_criteria_options
    result = sensitivity_analysis(criteria, options, target_criterion="NonExistentCriterion")
    assert "error" in result


def test_compute_confidence_bucket():
    """Test confidence scoring boundary conversions."""
    assert compute_confidence_bucket(95) == "Very High"
    assert compute_confidence_bucket(80) == "High"
    assert compute_confidence_bucket(65) == "Moderate"
    assert compute_confidence_bucket(45) == "Low"
    assert compute_confidence_bucket(20) == "Very Low"
