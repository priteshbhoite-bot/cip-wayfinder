"""Deterministic local implementations of the nine Milestone 4 tools.

Every function uses synthetic fixtures. No function calls an LLM, queries a
network, reads a real standard, or interacts with a live system.
"""

from __future__ import annotations

import json
from datetime import datetime
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field

from nerc_compliance_intelligence.schemas import (
    AgentState,
    BaselineObservation,
    ControlDesign,
    DecisionType,
    EvidenceArtifact,
    EvidenceObservation,
    HumanDecision,
    PotentialFinding,
    ProcessStep,
    RequirementMapping,
    RiskLevel,
    StandardVersion,
    ValidationResult,
)
from nerc_compliance_intelligence.local_corpus import LocalCorpusStore, RequirementChunk, RetrievalQuery, chunk_to_mapping


class ToolClassification(str, Enum):
    """A tool's safety category."""

    READ = "read"
    COMPUTE = "read/compute"
    INTERRUPT = "interrupt"
    WRITE = "write"


class ToolMetadata(BaseModel):
    """Human-readable metadata for one available fake tool."""

    name: str
    classification: ToolClassification
    description: str


class FakeToolError(RuntimeError):
    """Expected error from an intentionally simulated tool failure."""


TOOL_METADATA: dict[str, ToolMetadata] = {
    "requirement_lookup": ToolMetadata(name="requirement_lookup", classification=ToolClassification.READ, description="Reads a version-scoped synthetic requirement record."),
    "control_drafter": ToolMetadata(name="control_drafter", classification=ToolClassification.COMPUTE, description="Creates a labeled draft control from a mapping."),
    "evidence_retriever": ToolMetadata(name="evidence_retriever", classification=ToolClassification.READ, description="Reads synthetic evidence artifacts."),
    "asset_baseline_reader": ToolMetadata(name="asset_baseline_reader", classification=ToolClassification.READ, description="Reads synthetic asset baseline observations."),
    "evidence_insight_analyzer": ToolMetadata(name="evidence_insight_analyzer", classification=ToolClassification.COMPUTE, description="Summarizes synthetic evidence observations."),
    "gap_and_risk_assessor": ToolMetadata(name="gap_and_risk_assessor", classification=ToolClassification.COMPUTE, description="Produces potential findings and a simple risk label."),
    "remediation_planner": ToolMetadata(name="remediation_planner", classification=ToolClassification.COMPUTE, description="Produces a draft remediation plan."),
    "approval_gate": ToolMetadata(name="approval_gate", classification=ToolClassification.INTERRUPT, description="Represents a future human approval pause."),
    "simulated_workflow_store": ToolMetadata(name="simulated_workflow_store", classification=ToolClassification.WRITE, description="Exports an approved synthetic workflow record to a local safe directory."),
}


class RequirementLookupInput(BaseModel):
    standard: StandardVersion
    requirement_reference: str = Field(min_length=1)


class RequirementLookupOutput(BaseModel):
    mapping: RequirementMapping | None
    chunk: RequirementChunk | None = None


class ControlDraftInput(BaseModel):
    mapping: RequirementMapping | None


class ControlDraftOutput(BaseModel):
    control_design: ControlDesign | None


class EvidenceRetrieveInput(BaseModel):
    asset_id: str = Field(min_length=1)


class EvidenceRetrieveOutput(BaseModel):
    artifacts: list[EvidenceArtifact] = Field(default_factory=list)


class BaselineReadInput(BaseModel):
    asset_id: str = Field(min_length=1)


class BaselineReadOutput(BaseModel):
    observations: list[BaselineObservation] = Field(default_factory=list)


class EvidenceInsightInput(BaseModel):
    artifacts: list[EvidenceArtifact]
    observations: list[EvidenceObservation]


class EvidenceInsightOutput(BaseModel):
    strengths: list[str] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)


class GapRiskInput(BaseModel):
    asset_id: str = Field(min_length=1)
    mapping: RequirementMapping
    control_design: ControlDesign
    evidence_insight: EvidenceInsightOutput
    baseline_observations: list[BaselineObservation]


class GapRiskOutput(BaseModel):
    findings: list[PotentialFinding] = Field(default_factory=list)
    risk_level: RiskLevel | None = None


class RemediationPlan(BaseModel):
    """A synthetic draft plan; it cannot be treated as an approved workflow."""

    plan_id: str
    asset_id: str
    actions: list[ProcessStep]
    related_finding_ids: list[str]
    is_draft: bool = True


class RemediationPlanInput(BaseModel):
    asset_id: str = Field(min_length=1)
    findings: list[PotentialFinding]


class RemediationPlanOutput(BaseModel):
    plan: RemediationPlan | None


class ApprovalGateInput(BaseModel):
    review_id: str = Field(min_length=1)
    decision: HumanDecision


class ApprovalGateOutput(BaseModel):
    is_paused: bool
    next_action: str
    decision: HumanDecision


class WorkflowStoreInput(BaseModel):
    state: AgentState
    output_subdirectory: str = "workflows"


class WorkflowStoreOutput(BaseModel):
    workflow_id: str
    export_path: str
    validation: ValidationResult


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SAFE_OUTPUTS_ROOT = PROJECT_ROOT / "outputs"


_SYNTHETIC_MAPPING = RequirementMapping(
    mapping_id="map-001",
    standard=StandardVersion(standard_id="CIP-010", version="5", scope_role="primary"),
    requirement_reference="Synthetic demo reference",
    source_name="Synthetic local requirement record",
    source_locator="demo-record-001",
    draft_summary="Synthetic draft summary for learning only.",
)


def _raise_for_error_fixture(value: str) -> None:
    if value == "raise-error":
        raise FakeToolError("simulated fake-tool failure")


def requirement_lookup(
    tool_input: RequirementLookupInput,
    corpus_store: LocalCorpusStore | None = None,
) -> RequirementLookupOutput:
    """Read a matching fixture or locally ingested chunk through one stable interface."""
    _raise_for_error_fixture(tool_input.requirement_reference)
    if corpus_store is not None:
        chunks = corpus_store.retrieve(
            RetrievalQuery(
                standard=tool_input.standard,
                requirement_reference=tool_input.requirement_reference,
            )
        )
        if not chunks:
            return RequirementLookupOutput(mapping=None, chunk=None)
        chunk = chunks[0]
        return RequirementLookupOutput(
            mapping=chunk_to_mapping(chunk, tool_input.standard.scope_role),
            chunk=chunk,
        )
    if tool_input.standard == _SYNTHETIC_MAPPING.standard and tool_input.requirement_reference == "Synthetic demo reference":
        return RequirementLookupOutput(mapping=_SYNTHETIC_MAPPING)
    return RequirementLookupOutput(mapping=None)


def control_drafter(tool_input: ControlDraftInput) -> ControlDraftOutput:
    """Create a draft control from a synthetic mapping."""
    if tool_input.mapping is None:
        return ControlDraftOutput(control_design=None)
    _raise_for_error_fixture(tool_input.mapping.mapping_id)
    return ControlDraftOutput(
        control_design=ControlDesign(
            control_id=f"draft-control-{tool_input.mapping.mapping_id}",
            mapping_id=tool_input.mapping.mapping_id,
            title="Draft synthetic review control",
            objective="Review synthetic records and request human approval before any local export.",
            process_steps=[
                ProcessStep(step_number=1, action="Review synthetic inputs", owner_role="Compliance analyst"),
                ProcessStep(step_number=2, action="Request a human decision", owner_role="Compliance manager", requires_human_approval=True),
            ],
        )
    )


def evidence_retriever(tool_input: EvidenceRetrieveInput) -> EvidenceRetrieveOutput:
    """Read synthetic evidence for the known demo asset, or return no records."""
    _raise_for_error_fixture(tool_input.asset_id)
    if tool_input.asset_id != "SUB-ALPHA-RTU-01":
        return EvidenceRetrieveOutput()
    return EvidenceRetrieveOutput(
        artifacts=[EvidenceArtifact(artifact_id="evidence-001", label="Synthetic change approval record", collected_on=datetime(2026, 8, 20).date())]
    )


def asset_baseline_reader(tool_input: BaselineReadInput) -> BaselineReadOutput:
    """Read a synthetic baseline observation for the known demo asset."""
    _raise_for_error_fixture(tool_input.asset_id)
    if tool_input.asset_id != "SUB-ALPHA-RTU-01":
        return BaselineReadOutput()
    return BaselineReadOutput(
        observations=[BaselineObservation(observation_id="baseline-observation-001", asset_id=tool_input.asset_id, baseline_reference="baseline-a", observed_value="baseline-b", matches_baseline=False)]
    )


def evidence_insight_analyzer(tool_input: EvidenceInsightInput) -> EvidenceInsightOutput:
    """Compute simple, explainable insights from synthetic evidence observations."""
    if any(item.artifact_id == "raise-error" for item in tool_input.artifacts):
        raise FakeToolError("simulated fake-tool failure")
    if not tool_input.artifacts and not tool_input.observations:
        return EvidenceInsightOutput()
    missing = [item.observation for item in tool_input.observations if item.supports_draft_control is False]
    strengths = [item.observation for item in tool_input.observations if item.supports_draft_control is True]
    return EvidenceInsightOutput(strengths=strengths, missing_evidence=missing)


def gap_and_risk_assessor(tool_input: GapRiskInput) -> GapRiskOutput:
    """Create a potential finding only when synthetic inputs show a variance or gap."""
    _raise_for_error_fixture(tool_input.asset_id)
    has_variance = any(not item.matches_baseline for item in tool_input.baseline_observations)
    has_missing_evidence = bool(tool_input.evidence_insight.missing_evidence)
    if not has_variance and not has_missing_evidence:
        return GapRiskOutput()
    return GapRiskOutput(
        risk_level=RiskLevel.MEDIUM,
        findings=[
            PotentialFinding(
                finding_id="finding-001",
                title="Potential synthetic review gap",
                risk_level=RiskLevel.MEDIUM,
                rationale="Synthetic baseline variance or incomplete synthetic evidence requires human review.",
                related_artifact_ids=["evidence-001"],
                related_baseline_observation_ids=[item.observation_id for item in tool_input.baseline_observations],
            )
        ],
    )


def remediation_planner(tool_input: RemediationPlanInput) -> RemediationPlanOutput:
    """Create a draft remediation plan for synthetic potential findings."""
    _raise_for_error_fixture(tool_input.asset_id)
    if not tool_input.findings:
        return RemediationPlanOutput(plan=None)
    return RemediationPlanOutput(
        plan=RemediationPlan(
            plan_id="plan-001",
            asset_id=tool_input.asset_id,
            related_finding_ids=[item.finding_id for item in tool_input.findings],
            actions=[ProcessStep(step_number=1, action="Validate synthetic review inputs", owner_role="Compliance analyst"), ProcessStep(step_number=2, action="Request human approval before export", owner_role="Compliance manager", requires_human_approval=True)],
        )
    )


def approval_gate(tool_input: ApprovalGateInput) -> ApprovalGateOutput:
    """Represent an approval interrupt without changing state or writing data."""
    _raise_for_error_fixture(tool_input.review_id)
    if tool_input.decision.decision is DecisionType.PENDING:
        return ApprovalGateOutput(is_paused=True, next_action="await_human_decision", decision=tool_input.decision)
    return ApprovalGateOutput(is_paused=False, next_action="continue_after_human_decision", decision=tool_input.decision)


def _safe_export_directory(subdirectory: str) -> Path:
    """Return a directory only when it resolves below the repository's outputs folder."""
    candidate = (SAFE_OUTPUTS_ROOT / subdirectory).resolve()
    safe_root = SAFE_OUTPUTS_ROOT.resolve()
    if not candidate.is_relative_to(safe_root):
        raise FakeToolError("exports must stay inside the local outputs directory")
    candidate.mkdir(parents=True, exist_ok=True)
    return candidate


def simulated_workflow_store(tool_input: WorkflowStoreInput) -> WorkflowStoreOutput:
    """Export an approved synthetic workflow record to the safe local outputs folder."""
    state = tool_input.state
    if state.review_id == "raise-error":
        raise FakeToolError("simulated fake-tool failure")
    if state.human_decision.decision is not DecisionType.APPROVE:
        raise FakeToolError("export requires an approved human decision")

    export_directory = _safe_export_directory(tool_input.output_subdirectory)
    workflow_id = f"workflow-{state.review_id}"
    export_path = export_directory / f"{workflow_id}.json"
    export_path.write_text(json.dumps(state.model_dump(mode="json"), indent=2), encoding="utf-8")
    return WorkflowStoreOutput(
        workflow_id=workflow_id,
        export_path=str(export_path),
        validation=ValidationResult(check_name="approved-local-export", is_valid=True, messages=["Synthetic workflow exported after an approved human decision."]),
    )
