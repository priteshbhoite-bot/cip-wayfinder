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

    functional_entity: str | None = Field(default=None, max_length=160)
    jurisdiction: str | None = Field(default=None, max_length=160)
    asset_scope: str | None = Field(default=None, max_length=300)
    review_objective: str | None = Field(default=None, max_length=300)

    @field_validator("functional_entity", "jurisdiction", "asset_scope", "review_objective", mode="before")
    @classmethod
    def normalize_optional_text(cls, value: object) -> str | None:
        """Turn blank form fields into missing values so the agent asks clearly."""
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
            functional_entity=intake.functional_entity,
            jurisdiction=intake.jurisdiction,
            standard_id=standard.standard_id,
            version=standard.version,
            asset_scope=intake.asset_scope,
        )
    )
    return CaseIntakeAssessment(intake=intake, standard=standard, applicability=applicability)
