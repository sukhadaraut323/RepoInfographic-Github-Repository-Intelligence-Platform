"""
Additional test-fixture factories for Module 6 tests.

Builds a minimal-but-valid `RepositoryMetricsResult` (Module 5's output
schema), which Module 5's own `factories.py` does not provide. Reuses
Module 5's existing factories for Modules 1/3/4 outputs unchanged.
"""

from datetime import datetime, timezone

from app.schemas.metrics import RepositoryMetricsResult, SubScore


def make_sub_score(score: float = 70.0) -> SubScore:
    return SubScore(score=score, evidence=[f"evidence at {score}"], reasons=[])


def make_repository_metrics_result(
    *,
    documentation_score: float = 70.0,
    codebase_score: float = 70.0,
    activity_score: float = 70.0,
    community_score: float = 70.0,
    maintainability_score: float = 70.0,
    best_practices_score: float = 70.0,
    overall_health_score: float = 70.0,
) -> RepositoryMetricsResult:
    return RepositoryMetricsResult(
        documentation_score=make_sub_score(documentation_score),
        codebase_score=make_sub_score(codebase_score),
        activity_score=make_sub_score(activity_score),
        community_score=make_sub_score(community_score),
        maintainability_score=make_sub_score(maintainability_score),
        best_practices_score=make_sub_score(best_practices_score),
        overall_health_score=make_sub_score(overall_health_score),
        calculated_at=datetime.now(timezone.utc),
    )
