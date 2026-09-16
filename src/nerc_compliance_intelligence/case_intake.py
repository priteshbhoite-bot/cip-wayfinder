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

    @field_validator("functional_entity", "jurisdiction", mode="before")
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

class CaseIntakeAssessment(BaseModel):
    """A safe, UI-ready readiness result for the selected standard version."""

    intake: CaseIntake
    standard: StandardVersion
    applicability: ApplicabilityAgentOutput

    @property
    def ready_for_review(self) -> bool:
        """Begin only after the Applicability Agent has every required scope group."""
        return self.applicability.ready_for_retrieval

    @property
    def questions(self) -> list[str]:
        """Return the Applicability Agent's direct questions for missing scope."""
        return list(self.applicability.questions)


def assess_case_intake(intake: CaseIntake, standard: StandardVersion) -> CaseIntakeAssessment:
    """Ask the existing Applicability Agent for missing scope without guessing."""
    applicability = run_applicability_agent(
        ApplicabilityAgentInput(
            functional_entity=format_scope_selections(intake.functional_entity) or None,
            jurisdiction=format_scope_selections(intake.jurisdiction) or None,
            standard_id=standard.standard_id,
            version=standard.version,
        )
    )
    return CaseIntakeAssessment(intake=intake, standard=standard, applicability=applicability)


def format_scope_selections(selections: list[str]) -> str:
    """Format multiple local scope choices for the existing string-based agent contract."""
    return "; ".join(selections)
