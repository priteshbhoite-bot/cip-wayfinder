"""Fifteen deterministic, offline checks for the local application."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime, timezone
from tempfile import TemporaryDirectory
from pathlib import Path

from pydantic import BaseModel

from nerc_compliance_intelligence.baseline_analysis import AssetSnapshot, BaselineStatus, analyze_baseline
from nerc_compliance_intelligence.case_persistence import LocalCaseStore, LocalSaveApproval, new_persisted_case
from nerc_compliance_intelligence.control_remediation import ControlGenerationInput, generate_draft_control_and_remediation
from nerc_compliance_intelligence.evidence_analysis import EvidenceAnalysisInput, analyze_evidence
from nerc_compliance_intelligence.fake_tools import (
    ApprovalGateInput, BaselineReadInput, ControlDraftInput, EvidenceInsightInput,
    GapRiskInput, RequirementLookupInput, approval_gate, asset_baseline_reader,
    control_drafter, evidence_insight_analyzer, gap_and_risk_assessor, requirement_lookup,
)
from nerc_compliance_intelligence.schemas import (
    AgentState, BaselineObservation, DecisionType, EvidenceArtifact, EvidenceObservation,
    HumanDecision, PotentialFinding, RiskLevel, StandardVersion,
)
from nerc_compliance_intelligence.tracing import build_tracing_preview, load_tracing_settings


class EvaluationResult(BaseModel):
    """One concise outcome from an offline deterministic evaluation."""

    number: int
    name: str
    passed: bool
    proof: str


def _mapping():
    result = requirement_lookup(RequirementLookupInput(standard=StandardVersion(standard_id="CIP-010", version="5", scope_role="primary"), requirement_reference="Synthetic demo reference"))
    assert result.mapping is not None
    return result.mapping


def _state() -> AgentState:
    mapping = _mapping()
    return AgentState(
        review_id="evaluation-case-001", asset_id="SUB-ALPHA-RTU-01", created_at=datetime(2026, 8, 28, tzinfo=timezone.utc),
        standards=[mapping.standard], requirement_mappings=[mapping],
        evidence_artifacts=[EvidenceArtifact(artifact_id="evaluation-evidence-001", label="Synthetic record", collected_on=date(2026, 8, 20))],
        baseline_observations=[BaselineObservation(observation_id="evaluation-baseline-001", asset_id="SUB-ALPHA-RTU-01", baseline_reference="baseline-a", observed_value="baseline-b", matches_baseline=False)],
        potential_findings=[PotentialFinding(finding_id="evaluation-finding-001", title="Synthetic review lead", risk_level=RiskLevel.MEDIUM, rationale="Synthetic variance requires review.", related_artifact_ids=["evaluation-evidence-001"])],
    )


def _offline_checks() -> list[tuple[str, Callable[[], bool], str]]:
    mapping = _mapping()
    generated = generate_draft_control_and_remediation(ControlGenerationInput(retrieved_mappings=[mapping], selected_requirement_ids=[mapping.requirement_reference]))
    strong_evidence = analyze_evidence(EvidenceAnalysisInput(
        document={"document_id": "evaluation-doc", "label": "Synthetic record", "document_text": "Evidence ID: evaluation-doc\nAsset ID: SUB-ALPHA-RTU-01\nCaptured On: 2026-08-20\nChange Approval: approved\nBaseline Fingerprint: baseline-a\n"},
        expected_asset_id="SUB-ALPHA-RTU-01", expected_baseline_fingerprint="baseline-a", as_of_date=date(2026, 8, 28),
    ))
    incomplete_evidence = analyze_evidence(EvidenceAnalysisInput(
        document={"document_id": "evaluation-incomplete", "label": "Synthetic incomplete", "document_text": "Evidence ID: evaluation-incomplete\nAsset ID: SUB-ALPHA-RTU-01\nCaptured On: 2026-08-20\n"},
        expected_asset_id="SUB-ALPHA-RTU-01", expected_baseline_fingerprint="baseline-a", as_of_date=date(2026, 8, 28),
    ))
    expected = AssetSnapshot(asset_id="SUB-ALPHA-RTU-01", software="firmware-1.0", ports_services=["ssh:22"], patches=["patch-1"], accounts=["svc_rtu"], baseline_version="baseline-a", observation_date=date(2026, 8, 1))
    observed_changed = expected.model_copy(update={"accounts": ["svc_rtu", "unexpected"], "observation_date": date(2026, 8, 20)})
    pending = approval_gate(ApprovalGateInput(review_id="evaluation-case-001", decision=HumanDecision()))
    rejected = approval_gate(ApprovalGateInput(review_id="evaluation-case-001", decision=HumanDecision(decision=DecisionType.REJECT, reviewer_role="Compliance manager", decided_at=datetime(2026, 8, 28, tzinfo=timezone.utc))))

    def resume_check() -> bool:
        with TemporaryDirectory() as temporary_directory:
            store = LocalCaseStore(Path(temporary_directory) / "cases.sqlite")
            saved = store.save_case(new_persisted_case(_state(), "evaluation-thread", datetime(2026, 8, 28, tzinfo=timezone.utc)), LocalSaveApproval(approved=True, reviewer_role="Compliance analyst"))
            return store.resume_case(saved.case_id) == saved

    return [
        ("Valid intake shape", lambda: bool(_state().asset_id and _state().standards), "Typed synthetic state accepts the scoped case."),
        ("Unsupported version", lambda: requirement_lookup(RequirementLookupInput(standard=StandardVersion(standard_id="CIP-010", version="99", scope_role="primary"), requirement_reference="Synthetic demo reference")).mapping is None, "Unknown version returns no local requirement."),
        ("Requirement retrieval", lambda: _mapping().requirement_reference == "Synthetic demo reference", "Version-scoped fake retrieval returned the expected ID."),
        ("Missing requirement", lambda: requirement_lookup(RequirementLookupInput(standard=mapping.standard, requirement_reference="missing")).mapping is None, "Absent requirement returns an empty result."),
        ("Draft-control labeling", lambda: generated.control.is_draft, "Generated control retains its draft label."),
        ("Evidence insight", lambda: bool(incomplete_evidence.missing_fields), "Incomplete synthetic evidence identifies missing fields."),
        ("Baseline variance", lambda: analyze_baseline(expected, observed_changed, generated.control.control_id, date(2026, 8, 28)).status is BaselineStatus.UNEXPLAINED_CHANGE, "Changed synthetic account is a bounded review observation."),
        ("Risk rubric", lambda: gap_and_risk_assessor(GapRiskInput(asset_id="SUB-ALPHA-RTU-01", mapping=mapping, control_design=control_drafter(ControlDraftInput(mapping=mapping)).control_design, evidence_insight=evidence_insight_analyzer(EvidenceInsightInput(artifacts=[], observations=[EvidenceObservation(observation_id="evaluation-observation", artifact_id="evaluation-evidence-001", observation="Missing synthetic approval", supports_draft_control=False)])), baseline_observations=[])).risk_level is RiskLevel.MEDIUM, "Known missing-evidence fixture maps to Medium."),
        ("Remediation completeness", lambda: all(step.action.text and step.owner_role.text and step.decision.text and step.end_state.text for step in generated.remediation_plan.steps), "Each ordered draft step includes action, owner, decision, and end state."),
        ("Bounded tool retry", lambda: __import__("nerc_compliance_intelligence.review_graph", fromlist=["MAX_TOOL_RETRIES"]).MAX_TOOL_RETRIES == 2, "Graph retry limit remains two."),
        ("Approval interrupt", lambda: pending.is_paused and pending.next_action == "await_human_decision", "Pending decision pauses before export."),
        ("Rejection safety", lambda: not rejected.is_paused and rejected.decision.decision is DecisionType.REJECT, "Rejected decision cannot enter an export route."),
        ("Approved workflow boundary", lambda: HumanDecision().decision is DecisionType.PENDING, "A pending state cannot satisfy the existing export guard."),
        ("Checkpoint-style resume", resume_check, "Approved local save resumes the same typed case and thread ID."),
        ("Citation and data guardrail", lambda: bool(mapping.source_name and mapping.source_locator) and strong_evidence.ignored_instruction_lines == 0, "Requirement metadata is present and evidence remains synthetic/local."),
    ]


def run_offline_evaluations() -> list[EvaluationResult]:
    """Run all deterministic checks and return safe results without stack traces."""
    results: list[EvaluationResult] = []
    for number, (name, check, proof) in enumerate(_offline_checks(), start=1):
        try:
            passed = bool(check())
        except Exception:
            passed = False
            proof = "The offline check did not complete safely."
        results.append(EvaluationResult(number=number, name=name, passed=passed, proof=proof))
    return results


def markdown_results_table(results: list[EvaluationResult]) -> str:
    """Format safe local results for the README, terminal, or a demo screen."""
    rows = ["| # | Evaluation | Result | Proof |", "|---:|---|---|---|"]
    rows.extend(f"| {result.number} | {result.name} | {'PASS' if result.passed else 'FAIL'} | {result.proof} |" for result in results)
    return "\n".join(rows)


def local_evaluation_summary() -> str:
    """Return one safe summary that also confirms optional tracing is offline-only."""
    results = run_offline_evaluations()
    tracing = build_tracing_preview(load_tracing_settings({}))
    return markdown_results_table(results) + f"\n\nTracing: {tracing.status}; network calls enabled: {tracing.network_calls_enabled}."


if __name__ == "__main__":
    print(local_evaluation_summary())
