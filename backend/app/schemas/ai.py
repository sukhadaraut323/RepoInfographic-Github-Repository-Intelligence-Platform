"""
Pydantic schemas for the AI Layer.

Every AI section separates evidence-based OBSERVATIONS (each carrying the
supplied data points it rests on) from RECOMMENDATIONS (advice, not fact),
and lists any information the model says it lacked. All fields are tolerant
of omissions so one weak section never invalidates the whole result.
"""

from datetime import datetime
from enum import Enum
from typing import Any, List, Optional

from pydantic import BaseModel, Field, field_validator


class AIStatus(str, Enum):
    COMPLETED = "completed"
    UNAVAILABLE = "unavailable"


class AIEvidenceItem(BaseModel):
    """A claim about the repository together with the supplied data it rests on."""

    statement: str
    evidence: List[str] = Field(default_factory=list)


class AIStage(BaseModel):
    """One level of a roadmap (e.g. 'Beginner Developer')."""

    level: str
    description: str = ""
    items: List[str] = Field(default_factory=list)


class AIInsightSection(BaseModel):
    available: bool = True
    summary: str = ""
    observations: List[AIEvidenceItem] = Field(default_factory=list, description="Evidence-based statements.")
    recommendations: List[str] = Field(default_factory=list, description="Advice - not presented as fact.")
    stages: List[AIStage] = Field(default_factory=list, description="Used by roadmap sections only.")
    missing_information: List[str] = Field(default_factory=list)

    @field_validator("observations", mode="before")
    @classmethod
    def _coerce_observations(cls, value: Any) -> Any:
        # Small models often emit plain strings instead of objects.
        if isinstance(value, list):
            return [{"statement": v} if isinstance(v, str) else v for v in value]
        return value


def _unavailable_section() -> AIInsightSection:
    return AIInsightSection(available=False, missing_information=["The model did not return this section."])


class AIInsights(BaseModel):
    repository_summary: AIInsightSection = Field(default_factory=_unavailable_section)
    architecture_explanation: AIInsightSection = Field(default_factory=_unavailable_section)
    contribution_guide: AIInsightSection = Field(default_factory=_unavailable_section)
    project_evolution_roadmap: AIInsightSection = Field(default_factory=_unavailable_section)
    learning_roadmap: AIInsightSection = Field(default_factory=_unavailable_section)
    commit_suggestions: AIInsightSection = Field(default_factory=_unavailable_section)
    improvement_suggestions: AIInsightSection = Field(default_factory=_unavailable_section)
    readme_review: AIInsightSection = Field(default_factory=_unavailable_section)


class AIErrorDetail(BaseModel):
    code: str
    detail: str


class AIInsightsResult(BaseModel):
    """
    AI outcome embedded in the dashboard response.

    A failed AI stage is a structured partial result (status=unavailable),
    not a request failure: Modules 1-6 already succeeded and their data is
    still returned.
    """

    status: AIStatus
    model: Optional[str] = None
    generated_at: datetime
    insights: Optional[AIInsights] = None
    error: Optional[AIErrorDetail] = None
