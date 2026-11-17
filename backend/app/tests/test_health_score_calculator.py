"""Unit tests for app.services.health_score_calculator.HealthScoreCalculator."""

from app.schemas.metrics import SubScore
from app.services.health_score_calculator import HealthScoreCalculator


def _calculator() -> HealthScoreCalculator:
    return HealthScoreCalculator(
        weight_documentation=0.15,
        weight_codebase=0.20,
        weight_activity=0.20,
        weight_community=0.15,
        weight_maintainability=0.15,
        weight_best_practices=0.15,
    )


def test_all_perfect_scores_yield_100() -> None:
    perfect = SubScore(score=100.0, evidence=[], reasons=[])
    calculator = _calculator()

    overall = calculator.calculate_overall_score(
        documentation_score=perfect,
        codebase_score=perfect,
        activity_score=perfect,
        community_score=perfect,
        maintainability_score=perfect,
        best_practices_score=perfect,
    )

    assert overall.score == 100.0


def test_all_zero_scores_yield_zero() -> None:
    zero = SubScore(score=0.0, evidence=[], reasons=[])
    calculator = _calculator()

    overall = calculator.calculate_overall_score(
        documentation_score=zero,
        codebase_score=zero,
        activity_score=zero,
        community_score=zero,
        maintainability_score=zero,
        best_practices_score=zero,
    )

    assert overall.score == 0.0


def test_weighted_average_is_computed_correctly() -> None:
    calculator = HealthScoreCalculator(
        weight_documentation=0.5,
        weight_codebase=0.5,
        weight_activity=0.0,
        weight_community=0.0,
        weight_maintainability=0.0,
        weight_best_practices=0.0,
    )
    doc = SubScore(score=80.0, evidence=[], reasons=[])
    code = SubScore(score=40.0, evidence=[], reasons=[])
    zero = SubScore(score=0.0, evidence=[], reasons=[])

    overall = calculator.calculate_overall_score(
        documentation_score=doc,
        codebase_score=code,
        activity_score=zero,
        community_score=zero,
        maintainability_score=zero,
        best_practices_score=zero,
    )

    assert overall.score == 60.0  # (80*0.5 + 40*0.5)


def test_low_subscore_produces_a_reason() -> None:
    low = SubScore(score=20.0, evidence=[], reasons=[])
    high = SubScore(score=90.0, evidence=[], reasons=[])
    calculator = _calculator()

    overall = calculator.calculate_overall_score(
        documentation_score=low,
        codebase_score=high,
        activity_score=high,
        community_score=high,
        maintainability_score=high,
        best_practices_score=high,
    )

    assert any("Documentation" in reason and "low" in reason for reason in overall.reasons)
    assert any("Codebase" in reason and "strong" in reason for reason in overall.reasons)


def test_evidence_lists_all_six_subscores() -> None:
    mid = SubScore(score=50.0, evidence=[], reasons=[])
    calculator = _calculator()

    overall = calculator.calculate_overall_score(
        documentation_score=mid,
        codebase_score=mid,
        activity_score=mid,
        community_score=mid,
        maintainability_score=mid,
        best_practices_score=mid,
    )

    assert len(overall.evidence) == 6
