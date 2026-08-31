"""Success, empty-result, and error fixtures for each Milestone 4 tool."""

from __future__ import annotations

from datetime import datetime, timezone

from learning.milestone_03_examples import valid_agent_state
from nerc_compliance_intelligence.fake_tools import (
    ApprovalGateInput,
    BaselineReadInput,
    ControlDraftInput,
    EvidenceInsightInput,
    EvidenceInsightOutput,
    EvidenceRetrieveInput,
    GapRiskInput,
    RemediationPlanInput,
    RequirementLookupInput,
    WorkflowStoreInput,
    _SYNTHETIC_MAPPING,
    control_drafter,
)
from nerc_compliance_intelligence.schemas import (
    BaselineObservation,
    DecisionType,
    EvidenceArtifact,
    EvidenceObservation,
    HumanDecision,
)


def approved_state():
    """Return the shared valid state with a recorded synthetic approval."""
    state = valid_agent_state()
    return state.model_copy(
        update={
            "human_decision": HumanDecision(
                decision=DecisionType.APPROVE,
                reviewer_role="Compliance manager",
                decided_at=datetime(2026, 8, 27, 13, 0, tzinfo=timezone.utc),
                notes="Synthetic approval for a local test export.",
            )
        }
    )


SYNTHETIC_CONTROL = control_drafter(ControlDraftInput(mapping=_SYNTHETIC_MAPPING)).control_design
MISSING_EVIDENCE_INSIGHT = EvidenceInsightOutput(missing_evidence=["Synthetic evidence is incomplete."])


SUCCESS_FIXTURES = {
    "requirement_lookup": RequirementLookupInput(standard=_SYNTHETIC_MAPPING.standard, requirement_reference="Synthetic demo reference"),
    "control_drafter": ControlDraftInput(mapping=_SYNTHETIC_MAPPING),
    "evidence_retriever": EvidenceRetrieveInput(asset_id="SUB-ALPHA-RTU-01"),
    "asset_baseline_reader": BaselineReadInput(asset_id="SUB-ALPHA-RTU-01"),
    "evidence_insight_analyzer": EvidenceInsightInput(artifacts=[EvidenceArtifact(artifact_id="evidence-001", label="Synthetic approval", collected_on=datetime(2026, 8, 20).date())], observations=[EvidenceObservation(observation_id="observation-001", artifact_id="evidence-001", observation="Synthetic evidence is present.", supports_draft_control=True)]),
    "gap_and_risk_assessor": GapRiskInput(asset_id="SUB-ALPHA-RTU-01", mapping=_SYNTHETIC_MAPPING, control_design=SYNTHETIC_CONTROL, evidence_insight=MISSING_EVIDENCE_INSIGHT, baseline_observations=[BaselineObservation(observation_id="baseline-observation-001", asset_id="SUB-ALPHA-RTU-01", baseline_reference="baseline-a", observed_value="baseline-b", matches_baseline=False)]),
    "remediation_planner": RemediationPlanInput(asset_id="SUB-ALPHA-RTU-01", findings=valid_agent_state().potential_findings),
    "approval_gate": ApprovalGateInput(review_id="review-001", decision=HumanDecision()),
    "simulated_workflow_store": WorkflowStoreInput(state=approved_state()),
}

EMPTY_FIXTURES = {
    "requirement_lookup": RequirementLookupInput(standard=_SYNTHETIC_MAPPING.standard, requirement_reference="No synthetic match"),
    "control_drafter": ControlDraftInput(mapping=None),
    "evidence_retriever": EvidenceRetrieveInput(asset_id="SUB-BRAVO-RTU-02"),
    "asset_baseline_reader": BaselineReadInput(asset_id="SUB-BRAVO-RTU-02"),
    "evidence_insight_analyzer": EvidenceInsightInput(artifacts=[], observations=[]),
    "gap_and_risk_assessor": GapRiskInput(asset_id="SUB-ALPHA-RTU-01", mapping=_SYNTHETIC_MAPPING, control_design=SYNTHETIC_CONTROL, evidence_insight=EvidenceInsightOutput(), baseline_observations=[]),
    "remediation_planner": RemediationPlanInput(asset_id="SUB-ALPHA-RTU-01", findings=[]),
    "approval_gate": ApprovalGateInput(review_id="review-001", decision=HumanDecision()),
    "simulated_workflow_store": WorkflowStoreInput(state=valid_agent_state()),
}

ERROR_FIXTURES = {
    "requirement_lookup": RequirementLookupInput(standard=_SYNTHETIC_MAPPING.standard, requirement_reference="raise-error"),
    "control_drafter": ControlDraftInput(mapping=_SYNTHETIC_MAPPING.model_copy(update={"mapping_id": "raise-error"})),
    "evidence_retriever": EvidenceRetrieveInput(asset_id="raise-error"),
    "asset_baseline_reader": BaselineReadInput(asset_id="raise-error"),
    "evidence_insight_analyzer": EvidenceInsightInput(artifacts=[EvidenceArtifact(artifact_id="raise-error", label="Synthetic error record", collected_on=datetime(2026, 8, 20).date())], observations=[]),
    "gap_and_risk_assessor": GapRiskInput(asset_id="raise-error", mapping=_SYNTHETIC_MAPPING, control_design=SYNTHETIC_CONTROL, evidence_insight=EvidenceInsightOutput(), baseline_observations=[]),
    "remediation_planner": RemediationPlanInput(asset_id="raise-error", findings=[]),
    "approval_gate": ApprovalGateInput(review_id="raise-error", decision=HumanDecision()),
    "simulated_workflow_store": WorkflowStoreInput(state=valid_agent_state().model_copy(update={"review_id": "raise-error"})),
}
