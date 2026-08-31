"""Deterministic, local package validation for Milestone 13A.

The Quality Reviewer checks structural safety and traceability only. It does
not interpret NERC requirements, declare compliance, reveal prompt content, or
write data anywhere.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from nerc_compliance_intelligence.baseline_analysis import BaselineReviewObservation
from nerc_compliance_intelligence.control_remediation import (
    ControlGenerationOutput,
    DraftControl,
    DraftRemediationPlan,
    validate_traceability,
)
from nerc_compliance_intelligence.evidence_analysis import EvidenceAnalysisOutput
from nerc_compliance_intelligence.schemas import RequirementMapping


class QualitySeverity(str, Enum):
    """The two local validation levels used by the MVP."""

    ERROR = "error"
    WARNING = "warning"


class QualityIssue(BaseModel):
    """A safe, concise validation message with no data dump or stack trace."""

    code: str
    severity: QualitySeverity
    message: str


class ReviewPackage(BaseModel):
    """The local artifacts checked together before an approval handoff."""

    requirement_mappings: list[RequirementMapping] = Field(min_length=1)
    control: DraftControl
    remediation_plan: DraftRemediationPlan
    evidence_analysis: EvidenceAnalysisOutput
    baseline_observation: BaselineReviewObservation


class QualityReviewResult(BaseModel):
    """A deterministic package-validation result, not an approval decision."""

    model_config = ConfigDict(frozen=True)

    is_valid: bool
    issues: list[QualityIssue]
    checked_components: list[str]
    safety_note: str = "Package validation is local and deterministic; it is not a compliance conclusion or human approval."


def review_package(review_package: ReviewPackage) -> QualityReviewResult:
    """Validate trace links and cross-artifact references without exposing inputs."""
    issues: list[QualityIssue] = []
    try:
        validate_traceability(
            ControlGenerationOutput(
                control=review_package.control,
                remediation_plan=review_package.remediation_plan,
            ),
            review_package.requirement_mappings,
        )
    except ValueError:
        issues.append(QualityIssue(code="traceability.invalid", severity=QualitySeverity.ERROR, message="One or more draft fields reference a requirement ID absent from this local retrieval package."))

    if review_package.remediation_plan.control_id != review_package.control.control_id:
        issues.append(QualityIssue(code="remediation.control_link_missing", severity=QualitySeverity.ERROR, message="The remediation draft is not linked to the supplied draft control."))
    if review_package.baseline_observation.control_id != review_package.control.control_id:
        issues.append(QualityIssue(code="baseline.control_link_missing", severity=QualitySeverity.ERROR, message="The baseline observation is not linked to the supplied draft control."))
    if review_package.evidence_analysis.ignored_instruction_lines:
        issues.append(QualityIssue(code="evidence.untrusted_text_ignored", severity=QualitySeverity.WARNING, message="Instruction-like document text was ignored; an SME should confirm the extracted facts."))
    if review_package.evidence_analysis.missing_fields:
        issues.append(QualityIssue(code="evidence.incomplete", severity=QualitySeverity.WARNING, message="Synthetic evidence has missing fields that require SME follow-up."))

    return QualityReviewResult(
        is_valid=not any(issue.severity is QualitySeverity.ERROR for issue in issues),
        issues=issues,
        checked_components=["retrieved requirements", "draft control", "draft remediation", "evidence analysis", "baseline observation"],
    )
