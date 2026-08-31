"""Unit tests for the deterministic Milestone 4 fake tools."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

import pytest

from nerc_compliance_intelligence.fake_tools import (
    TOOL_METADATA,
    ApprovalGateOutput,
    BaselineReadOutput,
    EvidenceInsightOutput,
    EvidenceRetrieveOutput,
    FakeToolError,
    GapRiskOutput,
    RemediationPlanOutput,
    ToolClassification,
    approval_gate,
    asset_baseline_reader,
    control_drafter,
    evidence_insight_analyzer,
    evidence_retriever,
    gap_and_risk_assessor,
    remediation_planner,
    requirement_lookup,
    simulated_workflow_store,
)
from tests.fixtures.fake_tool_fixtures import EMPTY_FIXTURES, ERROR_FIXTURES, SUCCESS_FIXTURES


TOOL_CALLS: dict[str, Callable] = {
    "requirement_lookup": requirement_lookup,
    "control_drafter": control_drafter,
    "evidence_retriever": evidence_retriever,
    "asset_baseline_reader": asset_baseline_reader,
    "evidence_insight_analyzer": evidence_insight_analyzer,
    "gap_and_risk_assessor": gap_and_risk_assessor,
    "remediation_planner": remediation_planner,
    "approval_gate": approval_gate,
    "simulated_workflow_store": simulated_workflow_store,
}


def test_nine_tools_have_explicit_read_write_classification() -> None:
    assert set(TOOL_METADATA) == set(TOOL_CALLS)
    assert TOOL_METADATA["simulated_workflow_store"].classification is ToolClassification.WRITE
    assert TOOL_METADATA["approval_gate"].classification is ToolClassification.INTERRUPT
    assert all(item.classification in ToolClassification for item in TOOL_METADATA.values())


@pytest.mark.parametrize("tool_name", list(TOOL_CALLS))
def test_success_fixtures_return_typed_outputs(tool_name: str) -> None:
    output = TOOL_CALLS[tool_name](SUCCESS_FIXTURES[tool_name])

    assert output is not None


def test_empty_result_fixtures_return_empty_or_paused_outputs() -> None:
    assert requirement_lookup(EMPTY_FIXTURES["requirement_lookup"]).mapping is None
    assert control_drafter(EMPTY_FIXTURES["control_drafter"]).control_design is None
    assert evidence_retriever(EMPTY_FIXTURES["evidence_retriever"]) == EvidenceRetrieveOutput()
    assert asset_baseline_reader(EMPTY_FIXTURES["asset_baseline_reader"]) == BaselineReadOutput()
    assert evidence_insight_analyzer(EMPTY_FIXTURES["evidence_insight_analyzer"]) == EvidenceInsightOutput()
    assert gap_and_risk_assessor(EMPTY_FIXTURES["gap_and_risk_assessor"]) == GapRiskOutput()
    assert remediation_planner(EMPTY_FIXTURES["remediation_planner"]) == RemediationPlanOutput(plan=None)
    assert approval_gate(EMPTY_FIXTURES["approval_gate"]).is_paused is True


def test_unapproved_workflow_export_is_rejected() -> None:
    with pytest.raises(FakeToolError, match="approved human decision"):
        simulated_workflow_store(EMPTY_FIXTURES["simulated_workflow_store"])


def test_approved_workflow_export_cannot_escape_the_safe_outputs_directory() -> None:
    approved_input = SUCCESS_FIXTURES["simulated_workflow_store"].model_copy(
        update={"output_subdirectory": "../outside-outputs"}
    )

    with pytest.raises(FakeToolError, match="inside the local outputs directory"):
        simulated_workflow_store(approved_input)


@pytest.mark.parametrize("tool_name", list(TOOL_CALLS))
def test_error_fixtures_raise_fake_tool_error(tool_name: str) -> None:
    with pytest.raises(FakeToolError, match="simulated fake-tool failure"):
        TOOL_CALLS[tool_name](ERROR_FIXTURES[tool_name])


def test_approved_export_writes_json_only_below_safe_outputs_directory() -> None:
    output = simulated_workflow_store(SUCCESS_FIXTURES["simulated_workflow_store"])
    exported_data = json.loads(Path(output.export_path).read_text(encoding="utf-8"))

    assert "outputs" in output.export_path
    assert output.validation.is_valid is True
    assert exported_data["human_decision"]["decision"] == "approve"
