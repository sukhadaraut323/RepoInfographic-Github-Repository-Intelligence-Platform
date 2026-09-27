"""Unit tests for app.services.language_distribution_formatter.LanguageDistributionFormatter."""

from app.schemas.static_analysis import LanguageDistributionEntry
from app.services.language_distribution_formatter import LanguageDistributionFormatter
from app.tests.factories import make_static_analysis_result

FORMATTER = LanguageDistributionFormatter()


def test_formats_language_entries_to_chart_slices() -> None:
    result = make_static_analysis_result(
        language_distribution=[
            LanguageDistributionEntry(language="Python", file_count=8, percentage=80.0),
            LanguageDistributionEntry(language="JavaScript", file_count=2, percentage=20.0),
        ]
    )

    slices = FORMATTER.format(result)

    assert len(slices) == 2
    assert slices[0].name == "Python"
    assert slices[0].value == 8
    assert slices[0].percentage == 80.0
    assert slices[1].name == "JavaScript"


def test_empty_language_distribution_returns_empty_list() -> None:
    result = make_static_analysis_result()
    # Module 5's factory uses `x or default`, so passing [] directly would
    # silently fall back to its non-empty default. Force true emptiness here.
    result = result.model_copy(update={"language_distribution": []})

    slices = FORMATTER.format(result)

    assert slices == []
