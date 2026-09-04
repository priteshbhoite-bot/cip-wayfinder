"""Typed, local-only case intake for the Streamlit learning demonstration.

This module collects scope; it does not decide applicability, retrieve source
material, call a model, persist a case, or make an operational change.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from nerc_compliance_intelligence.agent_contracts import (
    ApplicabilityAgentInput,
    ApplicabilityAgentOutput,
    run_applicability_agent,
)
from nerc_compliance_intelligence.schemas import StandardVersion


class CaseIntake(BaseModel):
    """The learner-entered scope for one local draft review."""

    model_config = ConfigDict(frozen=True)

    functional_entity: list[str] = Field(default_factory=list)
    jurisdiction: list[str] = Field(default_factory=list)
    asset_scope: list[str] = Field(default_factory=list)
    review_objective: str | None = Field(default=None, max_length=300)

    @field_validator("functional_entity", "jurisdiction", "asset_scope", mode="before")
    @classmethod
    def normalize_scope_selections(cls, value: object) -> list[str]:
        """Turn blank selections into an empty list and remove duplicate choices."""
        if value is None:
            return []
        raw_values = value if isinstance(value, list) else [value]
        selections: list[str] = []
        for raw_value in raw_values:
            normalized = str(raw_value).strip()
            if normalized and normalized not in selections:
                selections.append(normalized)
        return selections

    @field_validator("review_objective", mode="before")
    @classmethod
    def normalize_optional_text(cls, value: object) -> str | None:
        """Turn a blank objective into missing text so the app asks clearly."""
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized or None


class CaseIntakeAssessment(BaseModel):
    """A safe, UI-ready readiness result for the selected standard version."""

    intake: CaseIntake
    standard: StandardVersion
    applicability: ApplicabilityAgentOutput

    @property
    def ready_for_review(self) -> bool:
        """Require a clear analyst objective in addition to the agent's scope check."""
        return self.applicability.ready_for_retrieval and self.intake.review_objective is not None

    @property
    def questions(self) -> list[str]:
        """Include the objective question when the user has not supplied one."""
        questions = list(self.applicability.questions)
        if self.intake.review_objective is None:
            questions.append("What review objective should this local draft package support?")
        return questions


def assess_case_intake(intake: CaseIntake, standard: StandardVersion) -> CaseIntakeAssessment:
    """Ask the existing Applicability Agent for missing scope without guessing."""
    applicability = run_applicability_agent(
        ApplicabilityAgentInput(
            functional_entity=format_scope_selections(intake.functional_entity) or None,
            jurisdiction=format_scope_selections(intake.jurisdiction) or None,
            standard_id=standard.standard_id,
            version=standard.version,
            asset_scope=format_scope_selections(intake.asset_scope) or None,
        )
    )
    return CaseIntakeAssessment(intake=intake, standard=standard, applicability=applicability)


def format_scope_selections(selections: list[str]) -> str:
    """Format multiple local scope choices for the existing string-based agent contract."""
    return "; ".join(selections)
