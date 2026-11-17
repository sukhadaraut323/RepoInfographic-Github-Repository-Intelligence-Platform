"""Unit tests for AIInsightsService and the prompt builder (mocked Ollama client)."""

import json

import pytest

from app.core.exceptions import AIInvalidResponseError, OllamaUnavailableError
from app.schemas.ai import AIStatus
from app.services.ai_insights_service import AIInsightsService
from app.services.ai_prompt_builder import SECTION_KEYS, build_ai_input
from app.tests.analytics_factories import make_repository_metrics_result
from app.tests.factories import (
    make_git_history_result,
    make_marker_files,
    make_repository_metadata,
    make_static_analysis_result,
)
from app.tests.test_repository_orchestrator_service import make_analytics_dashboard_result

LOCAL_PATH = "/secret/internal/workspace/path"


def valid_ai_payload() -> dict:
    section = {
        "available": True,
        "summary": "A summary.",
        "observations": [{"statement": "Has commits.", "evidence": ["total_commits=2"]}],
        "recommendations": ["Add tests."],
        "stages": [],
        "missing_information": ["README text was not provided."],
    }
    return {key: dict(section) for key in SECTION_KEYS}


class FakeClient:
    model = "fake-model"

    def __init__(self, reply=None, error=None) -> None:
        self.reply, self.error, self.calls = reply, error, []

    async def chat_json(self, system_prompt, user_prompt):
        self.calls.append((system_prompt, user_prompt))
        if self.error:
            raise self.error
        return self.reply


def inputs():
    return dict(
        repository_metadata=make_repository_metadata(full_name="octo/demo"),
        static_analysis_result=make_static_analysis_result(local_path=LOCAL_PATH),
        git_history_result=make_git_history_result(local_path=LOCAL_PATH),
        repository_metrics_result=make_repository_metrics_result(),
        analytics_result=make_analytics_dashboard_result(),
    )


async def run(reply=None, error=None, **overrides):
    client = FakeClient(reply=reply, error=error)
    data = {**inputs(), **overrides}
    return client, await AIInsightsService(client).generate_insights(**data)


@pytest.mark.asyncio
async def test_valid_structured_input_produces_structured_output() -> None:
    client, result = await run(json.dumps(valid_ai_payload()))
    assert result.status == AIStatus.COMPLETED and result.model == "fake-model"
    section = result.insights.repository_summary
    assert section.summary == "A summary."
    assert section.observations[0].evidence == ["total_commits=2"]  # evidence separated from recommendations
    assert section.recommendations == ["Add tests."]
    assert all(getattr(result.insights, k).available for k in SECTION_KEYS)


@pytest.mark.asyncio
async def test_prompt_carries_structured_evidence_and_no_local_paths() -> None:
    client, _ = await run(json.dumps(valid_ai_payload()))
    system_prompt, user_prompt = client.calls[0]
    assert "octo/demo" in user_prompt
    assert '"git_history"' in user_prompt and '"engineering_metrics"' in user_prompt
    assert LOCAL_PATH not in user_prompt
    assert "Never invent repository facts" in system_prompt
    # Things never given to the model regardless of README availability.
    assert "source code contents" in user_prompt
    assert "commit messages" in user_prompt


@pytest.mark.asyncio
async def test_prompt_excludes_the_bulky_raw_monthly_commit_timeline() -> None:
    """The raw month-by-month array is intentionally omitted (see ai_prompt_builder docstring);
    the summary statistics (total_commits, dates, cadence) are included instead."""
    client, _ = await run(json.dumps(valid_ai_payload()))
    payload = build_ai_input(**inputs())
    assert "monthly_commit_timeline" not in payload["git_history"]
    assert "total_commits" in payload["git_history"]


@pytest.mark.asyncio
async def test_readme_content_is_included_when_present_and_not_listed_as_missing() -> None:
    with_readme = dict(
        static_analysis_result=make_static_analysis_result(
            local_path=LOCAL_PATH,
            marker_files=make_marker_files(readme="README.md"),
            readme_content="# Demo\n\nThis project does X.",
        )
    )
    client, _ = await run(json.dumps(valid_ai_payload()), **with_readme)
    _, user_prompt = client.calls[0]
    assert "This project does X." in user_prompt
    assert '"readme_available":true' in user_prompt
    # Only listed as not-provided when genuinely absent - here it was supplied.
    payload = build_ai_input(**{**inputs(), **with_readme})
    assert "README text" not in payload["not_provided"]


@pytest.mark.asyncio
async def test_readme_absence_is_reported_plainly_not_guessed() -> None:
    client, _ = await run(json.dumps(valid_ai_payload()))  # default factory: no README
    payload = build_ai_input(**inputs())
    assert payload["readme_available"] is False
    assert payload["readme_content"] is None
    assert "README text" in payload["not_provided"]


@pytest.mark.asyncio
async def test_code_fenced_json_is_accepted() -> None:
    _, result = await run("```json\n" + json.dumps(valid_ai_payload()) + "\n```")
    assert result.status == AIStatus.COMPLETED


@pytest.mark.asyncio
async def test_plain_string_observations_are_coerced() -> None:
    payload = valid_ai_payload()
    payload["repository_summary"]["observations"] = ["Just a string"]
    _, result = await run(json.dumps(payload))
    assert result.insights.repository_summary.observations[0].statement == "Just a string"


@pytest.mark.asyncio
async def test_missing_section_is_marked_unavailable_not_invented() -> None:
    payload = valid_ai_payload()
    del payload["readme_review"]
    _, result = await run(json.dumps(payload))
    assert result.insights.readme_review.available is False
    assert result.insights.readme_review.missing_information


@pytest.mark.asyncio
async def test_malformed_section_degrades_only_that_section() -> None:
    payload = valid_ai_payload()
    payload["learning_roadmap"] = {"observations": 42}
    _, result = await run(json.dumps(payload))
    assert result.insights.learning_roadmap.available is False
    assert result.insights.repository_summary.available is True


@pytest.mark.asyncio
@pytest.mark.parametrize("reply", ["this is not json", "[1, 2, 3]", '{"unrelated": 1}', "", '{"repository_summary": {"observations": 5}}'])
async def test_invalid_ai_output_raises(reply) -> None:
    with pytest.raises(AIInvalidResponseError):
        await run(reply)


@pytest.mark.asyncio
async def test_ollama_failure_propagates_as_ai_error() -> None:
    with pytest.raises(OllamaUnavailableError):
        await run(error=OllamaUnavailableError("down"))


@pytest.mark.asyncio
async def test_incomplete_analysis_data_still_builds_valid_input() -> None:
    sparse = dict(
        repository_metadata=make_repository_metadata().model_copy(
            update={"languages": {}, "primary_language": None, "description": None, "topics": []}
        ),
        git_history_result=make_git_history_result(local_path=LOCAL_PATH).model_copy(
            update={"total_commits": 0, "monthly_commit_timeline": [], "first_commit_date": None}
        ),
    )
    client, result = await run(json.dumps(valid_ai_payload()), **sparse)
    assert result.status == AIStatus.COMPLETED
    payload = build_ai_input(**{**inputs(), **sparse})
    assert payload["git_history"]["total_commits"] == 0
    assert "monthly_commit_timeline" not in payload["git_history"]
    assert "not_provided" in client.calls[0][1]
