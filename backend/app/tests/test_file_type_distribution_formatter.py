"""Unit tests for app.services.file_type_distribution_formatter.FileTypeDistributionFormatter."""

from app.services.file_type_distribution_formatter import FileTypeDistributionFormatter
from app.tests.factories import make_static_analysis_result

FORMATTER = FileTypeDistributionFormatter()


def test_splits_source_and_other_files() -> None:
    result = make_static_analysis_result(total_files=10, supported_source_files=7)

    slices = FORMATTER.format(result)

    slices_by_name = {s.name: s for s in slices}
    assert slices_by_name["Source Files"].value == 7
    assert slices_by_name["Source Files"].percentage == 70.0
    assert slices_by_name["Other Files"].value == 3
    assert slices_by_name["Other Files"].percentage == 30.0


def test_all_files_are_source() -> None:
    result = make_static_analysis_result(total_files=5, supported_source_files=5)

    slices = FORMATTER.format(result)

    slices_by_name = {s.name: s for s in slices}
    assert slices_by_name["Source Files"].percentage == 100.0
    assert slices_by_name["Other Files"].value == 0


def test_empty_repository_returns_empty_list() -> None:
    result = make_static_analysis_result(total_files=0, supported_source_files=0)

    slices = FORMATTER.format(result)

    assert slices == []
