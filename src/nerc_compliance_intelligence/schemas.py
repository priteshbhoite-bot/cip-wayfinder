"""Typed, synthetic-data records for the Milestone 3 data layer.

These models describe draft review information. They do not interpret standards,
declare compliance, invoke tools, or perform write actions.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class RiskLevel(str, Enum):
    """The intentionally simple risk labels used by the demonstration MVP."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class DecisionType(str, Enum):
    """The choices available at a future human approval boundary."""

    PENDING = "pending"
    APPROVE = "approve"
    REJECT = "reject"
    REVISE = "revise"


class StandardVersion(BaseModel):
    """Identifies one version-bounded standard used in the synthetic demo."""

    model_config = ConfigDict(frozen=True)

    standard_id: str = Field(pattern=r"^CIP-\d{3}$")
    version: str = Field(pattern=r"^\d+$")
    scope_role: str = Field(pattern=r"^(primary|supporting)$")


class RequirementMapping(BaseModel):
    """Links a synthetic requirement record to its future source citation fields."""

    mapping_id: str = Field(min_length=1)
    standard: StandardVersion
    requirement_reference: str = Field(min_length=1)
    source_name: str = Field(min_length=1)
    source_locator: str = Field(min_length=1)
    draft_summary: str = Field(min_length=1)


class ProcessStep(BaseModel):
    """Describes one draft action within a control process."""

    step_number: int = Field(ge=1)
    action: str = Field(min_length=1)
    owner_role: str = Field(min_length=1)
    requires_human_approval: bool = False


class ControlDesign(BaseModel):
    """A draft organization-specific control, never a compliance conclusion."""

    control_id: str = Field(min_length=1)
    mapping_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    objective: str = Field(min_length=1)
    process_steps: list[ProcessStep] = Field(min_length=1)
    is_draft: bool = True

    @model_validator(mode="after")
    def require_a_draft_label(self) -> "ControlDesign":
        """Prevent this application from representing a control as final."""
        if not self.is_draft:
            raise ValueError("control designs must remain drafts")
        return self


class EvidenceArtifact(BaseModel):
    """A synthetic evidence item that can be inspected in a review."""

    artifact_id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    source_type: str = "synthetic"
    collected_on: date
    synthetic: bool = True

    @model_validator(mode="after")
    def require_synthetic_evidence(self) -> "EvidenceArtifact":
        """Block real or confidential evidence from this synthetic data model."""
        if self.source_type != "synthetic" or not self.synthetic:
            raise ValueError("this application accepts synthetic evidence only")
        return self


class EvidenceObservation(BaseModel):
    """A draft observation about a synthetic evidence artifact."""

    observation_id: str = Field(min_length=1)
    artifact_id: str = Field(min_length=1)
    observation: str = Field(min_length=1)
    supports_draft_control: bool | None = None


class BaselineObservation(BaseModel):
    """A synthetic comparison of a documented and observed asset baseline value."""

    observation_id: str = Field(min_length=1)
    asset_id: str = Field(min_length=1)
    baseline_reference: str = Field(min_length=1)
    observed_value: str = Field(min_length=1)
    matches_baseline: bool
    synthetic: bool = True

    @model_validator(mode="after")
    def require_synthetic_baseline(self) -> "BaselineObservation":
        """Keep live IT/OT asset exports out of the MVP."""
        if not self.synthetic:
            raise ValueError("this application accepts synthetic baseline observations only")
        return self


class PotentialFinding(BaseModel):
    """A review lead that requires human analysis; it is not a compliance finding."""

    finding_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    risk_level: RiskLevel
    rationale: str = Field(min_length=1)
    related_artifact_ids: list[str] = Field(min_length=1)
    related_baseline_observation_ids: list[str] = Field(default_factory=list)
    requires_human_review: bool = True

    @model_validator(mode="after")
    def require_human_review(self) -> "PotentialFinding":
        """Ensure the model cannot represent a finding as auto-approved."""
        if not self.requires_human_review:
            raise ValueError("potential findings require human review")
        return self


class ValidationResult(BaseModel):
    """Records whether a local validation check passed and what it checked."""

    check_name: str = Field(min_length=1)
    is_valid: bool
    messages: list[str] = Field(default_factory=list)


class HumanDecision(BaseModel):
    """Represents a future human decision without performing a write action."""

    decision: DecisionType = DecisionType.PENDING
    reviewer_role: str | None = None
    decided_at: datetime | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def require_reviewer_details_after_a_decision(self) -> "HumanDecision":
        """Require a reviewer and time when the decision is no longer pending."""
        if self.decision is not DecisionType.PENDING:
            if not self.reviewer_role or self.decided_at is None:
                raise ValueError("a completed decision requires reviewer_role and decided_at")
        return self


class AgentState(BaseModel):
    """The complete in-memory state shape planned for a future review graph."""

    review_id: str = Field(min_length=1)
    asset_id: str = Field(min_length=1)
    created_at: datetime
    standards: list[StandardVersion] = Field(min_length=1)
    requirement_mappings: list[RequirementMapping] = Field(min_length=1)
    control_design: ControlDesign | None = None
    evidence_artifacts: list[EvidenceArtifact] = Field(default_factory=list)
    evidence_observations: list[EvidenceObservation] = Field(default_factory=list)
    baseline_observations: list[BaselineObservation] = Field(default_factory=list)
    potential_findings: list[PotentialFinding] = Field(default_factory=list)
    validation_results: list[ValidationResult] = Field(default_factory=list)
    human_decision: HumanDecision = Field(default_factory=HumanDecision)
    status: str = "draft"

    @model_validator(mode="after")
    def keep_review_assets_consistent(self) -> "AgentState":
        """Reject baseline observations that belong to a different synthetic asset."""
        if any(item.asset_id != self.asset_id for item in self.baseline_observations):
            raise ValueError("baseline observations must use the state asset_id")
        return self
