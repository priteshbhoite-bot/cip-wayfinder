"""Branch-focused tests for the Milestone 6 fake LangGraph workflow."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from nerc_compliance_intelligence.review_graph import (
    MAX_TOOL_RETRIES,
    build_review_graph,
    compact_graph_summary,
    graph_config,
    initial_review_state,
)


def _decision(decision: str) -> dict[str, str]:
    return {
        "decision": decision,
        "reviewer_role": "Compliance manager",
        "decided_at": datetime(2026, 8, 27, 14, 0, tzinfo=timezone.utc).isoformat(),
        "notes": "Synthetic graph-test decision.",
    }


def _paused_graph(thread_id: str = "thread-test-001"):
    checkpointer = InMemorySaver()
    graph = build_review_graph(checkpointer)
    config = graph_config(thread_id)
    paused = graph.invoke(initial_review_state(thread_id=thread_id), config=config)
    return graph, config, paused


def test_happy_path_pauses_before_export_then_approves_and_exports() -> None:
    graph, config, paused = _paused_graph()

    assert paused["__interrupt__"]
    checkpoint = graph.get_state(config)
    assert checkpoint.values["status"] == "plan_ready"
    assert "workflow_export_path" not in checkpoint.values

    completed = graph.invoke(Command(resume=_decision("approve")), config=config)

    assert completed["status"] == "completed"
    assert "outputs" in completed["workflow_export_path"]
    assert completed["human_decision"]["decision"] == "approve"


def test_missing_scope_routes_to_safe_stop_without_an_interrupt() -> None:
    graph = build_review_graph()
    result = graph.invoke(initial_review_state(asset_id=""), config=graph_config("thread-missing-scope"))

    assert result["status"] == "stopped"
    assert "missing scope" in result["stop_reason"]
    assert result["route_history"] == ["intake_agent", "safe_stop"]


def test_empty_requirement_is_repaired_once_then_reaches_approval() -> None:
    graph = build_review_graph()
    result = graph.invoke(
        initial_review_state(requirement_reference="No synthetic match"),
        config=graph_config("thread-repair-success"),
    )

    assert result["__interrupt__"]
    assert result["repair_count"] == 1
    assert "validation_repair:requirement_lookup" in result["route_history"]


def test_empty_evidence_uses_one_repair_then_safely_stops() -> None:
    graph = build_review_graph()
    result = graph.invoke(initial_review_state(asset_id="SUB-BRAVO-RTU-02"), config=graph_config("thread-empty-evidence"))

    assert result["status"] == "stopped"
    assert result["repair_count"] == 1
    assert "no synthetic data available for evidence_retriever" in result["stop_reason"]


def test_empty_retrieval_after_the_repair_limit_safely_stops() -> None:
    graph = build_review_graph()
    state = initial_review_state(requirement_reference="No synthetic match")
    state["repair_count"] = 1
    result = graph.invoke(state, config=graph_config("thread-repair-limit"))

    assert result["status"] == "stopped"
    assert "validation_repair" not in result["route_history"]


def test_tool_error_retries_at_most_twice_then_safely_stops() -> None:
    graph = build_review_graph()
    result = graph.invoke(
        initial_review_state(asset_id="raise-error"),
        config=graph_config("thread-tool-error"),
    )

    assert result["status"] == "stopped"
    assert result["retry_counts"]["evidence_retriever"] == MAX_TOOL_RETRIES
    assert result["route_history"].count("retry_tool:evidence_retriever") == MAX_TOOL_RETRIES


def test_edit_routes_back_to_the_approval_interrupt_before_export() -> None:
    graph, config, _ = _paused_graph("thread-edit")

    paused_again = graph.invoke(Command(resume=_decision("edit")), config=config)

    assert paused_again["__interrupt__"]
    state_after_edit = graph.get_state(config).values
    assert state_after_edit["plan_revision_count"] == 1
    assert state_after_edit["remediation_plan"]["revision_note"]


def test_reject_safely_stops_without_export() -> None:
    graph, config, _ = _paused_graph("thread-reject")

    rejected = graph.invoke(Command(resume=_decision("reject")), config=config)

    assert rejected["status"] == "stopped"
    assert rejected["human_decision"]["decision"] == "reject"
    assert "workflow_export_path" not in rejected


def test_invalid_human_decision_safely_stops() -> None:
    graph, config, _ = _paused_graph("thread-invalid-decision")

    stopped = graph.invoke(Command(resume={"decision": "approve"}), config=config)

    assert stopped["status"] == "stopped"
    assert "invalid human decision" in stopped["last_error"]


def test_compact_graph_summary_prints_the_key_guards(capsys: pytest.CaptureFixture[str]) -> None:
    print(compact_graph_summary())

    output = capsys.readouterr().out
    assert "thread_id" in output
    assert "retries<=2" in output
    assert "interrupt before approved local export" in output
