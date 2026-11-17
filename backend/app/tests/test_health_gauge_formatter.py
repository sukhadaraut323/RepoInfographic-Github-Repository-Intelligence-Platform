"""Unit tests for app.services.health_gauge_formatter.HealthGaugeFormatter."""

import pytest

from app.services.health_gauge_formatter import HealthGaugeFormatter
from app.tests.analytics_factories import make_repository_metrics_result


@pytest.fixture
def formatter() -> HealthGaugeFormatter:
    return HealthGaugeFormatter(excellent_threshold=85.0, good_threshold=70.0, fair_threshold=50.0)


def test_excellent_status(formatter) -> None:
    result = make_repository_metrics_result(overall_health_score=90.0)
    gauge = formatter.format(result)
    assert gauge.value == 90.0
    assert gauge.status == "Excellent"
    assert gauge.min == 0
    assert gauge.max == 100


def test_good_status(formatter) -> None:
    result = make_repository_metrics_result(overall_health_score=75.0)
    gauge = formatter.format(result)
    assert gauge.status == "Good"


def test_fair_status(formatter) -> None:
    result = make_repository_metrics_result(overall_health_score=55.0)
    gauge = formatter.format(result)
    assert gauge.status == "Fair"


def test_poor_status(formatter) -> None:
    result = make_repository_metrics_result(overall_health_score=20.0)
    gauge = formatter.format(result)
    assert gauge.status == "Poor"


def test_boundary_values_are_inclusive(formatter) -> None:
    assert formatter.format(make_repository_metrics_result(overall_health_score=85.0)).status == "Excellent"
    assert formatter.format(make_repository_metrics_result(overall_health_score=70.0)).status == "Good"
    assert formatter.format(make_repository_metrics_result(overall_health_score=50.0)).status == "Fair"
