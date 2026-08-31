"""Milestone 6: a checkpointed, fake-only LangGraph review workflow.

This module follows docs/architecture.md. The graph is deliberately small and
deterministic so learners can inspect every route before real integrations exist.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt
from pydantic import ValidationError
from typing_extensions import TypedDict

from nerc_compliance_intelligence.fake_tools import (
    ApprovalGateInput,
    BaselineReadInput,
    ControlDraftInput,
    EvidenceInsightInput,
    EvidenceRetrieveInput,
    FakeToolError,
    GapRiskInput,
    RemediationPlanInput,
    RequirementLookupInput,
    WorkflowStoreInput,
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
from nerc_compliance_intelligence.schemas import (
    AgentState,
    DecisionType,
    EvidenceObservation,
    HumanDecision,
    StandardVersion,
)


MAX_TOOL_RETRIES = 2
MAX_VALIDATION_REPAIRS = 1


class ReviewGraphState(TypedDict, total=False):
    """JSON-friendly state carried and checkpointed by the LangGraph workflow."""

    review_id: str
    thread_id: str
    asset_id: str
    standard_id: str
    standard_version: str
    scope_role: str
    requirement_reference: str
    created_at: str
    requirement_mapping: dict[str, Any]
    control_design: dict[str, Any]
    evidence_artifacts: list[dict[str, Any]]
    evidence_observations: list[dict[str, Any]]
    baseline_observations: list[dict[str, Any]]
    evidence_insight: dict[str, Any]
    potential_findings: list[dict[str, Any]]
    remediation_plan: dict[str, Any]
    human_decision: dict[str, Any]
    workflow_export_path: str
    status: str
    stop_reason: str
    last_error: str
    last_failed_tool: str
    empty_retrieval_target: str
    repair_route: str
    retry_counts: dict[str, int]
    repair_count: int
    plan_revision_count: int
    route_history: list[str]


def initial_review_state(
    *,
    review_id: str = "review-graph-001",
    thread_id: str = "thread-graph-001",
    asset_id: str = "SUB-ALPHA-RTU-01",
    standard_id: str = "CIP-010",
    standard_version: str = "5",
    scope_role: str = "primary",
    requirement_reference: str = "Synthetic demo reference",
) -> ReviewGraphState:
    """Create a safe, deterministic starting state for one synthetic review."""
    return {
        "review_id": review_id,
        "thread_id": thread_id,
        "asset_id": asset_id,
        "standard_id": standard_id,
        "standard_version": standard_version,
        "scope_role": scope_role,
        "requirement_reference": requirement_reference,
        "created_at": datetime(2026, 8, 27, 12, 0, tzinfo=timezone.utc).isoformat(),
        "retry_counts": {},
        "repair_count": 0,
        "plan_revision_count": 0,
        "route_history": [],
        "status": "new",
    }


def graph_config(thread_id: str) -> dict[str, dict[str, str]]:
    """Return the LangGraph configuration that selects one checkpoint thread."""
    return {"configurable": {"thread_id": thread_id}}


def _history(state: ReviewGraphState, node_name: str) -> list[str]:
    return [*state.get("route_history", []), node_name]


def _scope_from_state(state: ReviewGraphState) -> StandardVersion:
    return StandardVersion(
        standard_id=state["standard_id"],
        version=state["standard_version"],
        scope_role=state["scope_role"],
    )


def intake_agent(state: ReviewGraphState) -> dict[str, Any]:
    """Validate that the minimum review scope exists before any tool call."""
    required = ("asset_id", "standard_id", "standard_version", "scope_role")
    missing = [field for field in required if not state.get(field)]
    return {
        "status": "scope_valid" if not missing else "missing_scope",
        "stop_reason": f"missing scope: {', '.join(missing)}" if missing else "",
        "route_history": _history(state, "intake_agent"),
    }


def requirement_agent(state: ReviewGraphState) -> dict[str, Any]:
    """Call the fake requirement lookup tool and retain its typed result as JSON data."""
    try:
        result = requirement_lookup(
            RequirementLookupInput(
                standard=_scope_from_state(state),
                requirement_reference=state["requirement_reference"],
            )
        )
    except (FakeToolError, ValidationError) as error:
        return _tool_error_update(state, "requirement_lookup", error)
    if result.mapping is None:
        return {
            "status": "empty_retrieval",
            "empty_retrieval_target": "requirement_lookup",
            "last_error": "",
            "route_history": _history(state, "requirement_agent:empty"),
        }
    return {
        "status": "requirement_ready",
        "requirement_mapping": result.mapping.model_dump(mode="json"),
        "last_error": "",
        "empty_retrieval_target": "",
        "route_history": _history(state, "requirement_agent:success"),
    }


def control_agent(state: ReviewGraphState) -> dict[str, Any]:
    """Use the fake control drafter to create a clearly labeled draft control."""
    try:
        result = control_drafter(ControlDraftInput(mapping=state.get("requirement_mapping")))
    except (FakeToolError, ValidationError) as error:
        return _tool_error_update(state, "control_drafter", error)
    if result.control_design is None:
        return {
            "status": "empty_retrieval",
            "empty_retrieval_target": "control_drafter",
            "route_history": _history(state, "control_agent:empty"),
        }
    return {
        "status": "control_ready",
        "control_design": result.control_design.model_dump(mode="json"),
        "last_error": "",
        "route_history": _history(state, "control_agent:success"),
    }


def evidence_agent(state: ReviewGraphState) -> dict[str, Any]:
    """Read synthetic evidence and create a synthetic observation for analysis."""
    try:
        result = evidence_retriever(EvidenceRetrieveInput(asset_id=state["asset_id"]))
    except (FakeToolError, ValidationError) as error:
        return _tool_error_update(state, "evidence_retriever", error)
    if not result.artifacts:
        return {
            "status": "empty_retrieval",
            "empty_retrieval_target": "evidence_retriever",
            "route_history": _history(state, "evidence_agent:empty"),
        }
    observations = [
        EvidenceObservation(
            observation_id="graph-evidence-observation-001",
            artifact_id=item.artifact_id,
            observation="Synthetic approval record is incomplete.",
            supports_draft_control=False,
        )
        for item in result.artifacts
    ]
    return {
        "status": "evidence_ready",
        "evidence_artifacts": [item.model_dump(mode="json") for item in result.artifacts],
        "evidence_observations": [item.model_dump(mode="json") for item in observations],
        "last_error": "",
        "route_history": _history(state, "evidence_agent:success"),
    }


def baseline_agent(state: ReviewGraphState) -> dict[str, Any]:
    """Read the deterministic synthetic baseline observation."""
    try:
        result = asset_baseline_reader(BaselineReadInput(asset_id=state["asset_id"]))
    except (FakeToolError, ValidationError) as error:
        return _tool_error_update(state, "asset_baseline_reader", error)
    if not result.observations:
        return {
            "status": "empty_retrieval",
            "empty_retrieval_target": "asset_baseline_reader",
            "route_history": _history(state, "baseline_agent:empty"),
        }
    return {
        "status": "baseline_ready",
        "baseline_observations": [item.model_dump(mode="json") for item in result.observations],
        "last_error": "",
        "route_history": _history(state, "baseline_agent:success"),
    }


def insight_agent(state: ReviewGraphState) -> dict[str, Any]:
    """Analyze the already-loaded synthetic evidence without an LLM."""
    try:
        result = evidence_insight_analyzer(
            EvidenceInsightInput(
                artifacts=state.get("evidence_artifacts", []),
                observations=state.get("evidence_observations", []),
            )
        )
    except (FakeToolError, ValidationError) as error:
        return _tool_error_update(state, "evidence_insight_analyzer", error)
    return {
        "status": "insight_ready",
        "evidence_insight": result.model_dump(mode="json"),
        "last_error": "",
        "route_history": _history(state, "insight_agent"),
    }


def risk_agent(state: ReviewGraphState) -> dict[str, Any]:
    """Use the fake assessor to produce potential findings, never compliance claims."""
    try:
        result = gap_and_risk_assessor(
            GapRiskInput(
                asset_id=state["asset_id"],
                mapping=state["requirement_mapping"],
                control_design=state["control_design"],
                evidence_insight=state["evidence_insight"],
                baseline_observations=state.get("baseline_observations", []),
            )
        )
    except (FakeToolError, ValidationError) as error:
        return _tool_error_update(state, "gap_and_risk_assessor", error)
    return {
        "status": "findings_ready" if result.findings else "no_findings",
        "potential_findings": [item.model_dump(mode="json") for item in result.findings],
        "last_error": "",
        "route_history": _history(state, "risk_agent"),
    }


def remediation_agent(state: ReviewGraphState) -> dict[str, Any]:
    """Create a fake draft plan from potential findings."""
    try:
        result = remediation_planner(
            RemediationPlanInput(asset_id=state["asset_id"], findings=state.get("potential_findings", []))
        )
    except (FakeToolError, ValidationError) as error:
        return _tool_error_update(state, "remediation_planner", error)
    return {
        "status": "plan_ready" if result.plan else "no_plan",
        "remediation_plan": result.plan.model_dump(mode="json") if result.plan else {},
        "last_error": "",
        "route_history": _history(state, "remediation_agent"),
    }


def approval_interrupt(state: ReviewGraphState) -> dict[str, Any]:
    """Pause before export and wait for an explicit structured human decision."""
    response = interrupt(
        {
            "review_id": state["review_id"],
            "instruction": "Approve, edit, or reject this synthetic draft before local export.",
            "allowed_decisions": ["approve", "edit", "reject"],
            "draft_plan": state.get("remediation_plan", {}),
        }
    )
    try:
        decision_data = dict(response)
        if decision_data.get("decision") == "edit":
            decision_data["decision"] = "revise"
        decision = HumanDecision.model_validate(decision_data)
    except (TypeError, ValidationError) as error:
        return {
            "status": "invalid_human_decision",
            "last_error": f"invalid human decision: {error}",
            "route_history": _history(state, "approval_interrupt:invalid"),
        }
    return {
        "status": "human_decision_recorded",
        "human_decision": decision.model_dump(mode="json"),
        "last_error": "",
        "route_history": _history(state, "approval_interrupt:resumed"),
    }


def edit_plan(state: ReviewGraphState) -> dict[str, Any]:
    """Apply a visible synthetic revision, then return to the human approval pause."""
    plan = dict(state["remediation_plan"])
    plan["revision_note"] = "Synthetic human-requested edit recorded for another review."
    return {
        "remediation_plan": plan,
        "plan_revision_count": state.get("plan_revision_count", 0) + 1,
        "status": "plan_edited",
        "route_history": _history(state, "edit_plan"),
    }


def export_agent(state: ReviewGraphState) -> dict[str, Any]:
    """Construct approved AgentState and call the guarded local export tool."""
    try:
        agent_state = AgentState.model_validate(
            {
                "review_id": state["review_id"],
                "asset_id": state["asset_id"],
                "created_at": state["created_at"],
                "standards": [
                    {
                        "standard_id": state["standard_id"],
                        "version": state["standard_version"],
                        "scope_role": state["scope_role"],
                    }
                ],
                "requirement_mappings": [state["requirement_mapping"]],
                "control_design": state["control_design"],
                "evidence_artifacts": state.get("evidence_artifacts", []),
                "evidence_observations": state.get("evidence_observations", []),
                "baseline_observations": state.get("baseline_observations", []),
                "potential_findings": state.get("potential_findings", []),
                "human_decision": state["human_decision"],
                "status": "approved_for_synthetic_export",
            }
        )
        result = simulated_workflow_store(WorkflowStoreInput(state=agent_state))
    except (FakeToolError, ValidationError) as error:
        return _tool_error_update(state, "simulated_workflow_store", error)
    return {
        "status": "exported",
        "workflow_export_path": result.export_path,
        "last_error": "",
        "route_history": _history(state, "export_agent"),
    }


def retry_tool(state: ReviewGraphState) -> dict[str, Any]:
    """Increment one bounded retry counter before routing back to the failed tool."""
    tool_name = state["last_failed_tool"]
    counters = dict(state.get("retry_counts", {}))
    counters[tool_name] = counters.get(tool_name, 0) + 1
    return {
        "retry_counts": counters,
        "route_history": _history(state, f"retry_tool:{tool_name}"),
    }


def validation_repair(state: ReviewGraphState) -> dict[str, Any]:
    """Make one deterministic repair attempt; never loop indefinitely."""
    target = state["empty_retrieval_target"]
    repairs = state.get("repair_count", 0) + 1
    updates: dict[str, Any] = {
        "repair_count": repairs,
        "repair_route": target,
        "route_history": _history(state, f"validation_repair:{target}"),
    }
    if target == "requirement_lookup":
        updates["requirement_reference"] = "Synthetic demo reference"
        updates["status"] = "requirement_repaired"
    else:
        updates["status"] = "unrepairable_empty_retrieval"
        updates["stop_reason"] = f"no synthetic data available for {target}"
    return updates


def safe_stop(state: ReviewGraphState) -> dict[str, Any]:
    """End safely without an export when a route cannot continue."""
    current_status = state.get("status", "stopped")
    return {
        "status": "completed" if current_status == "exported" else "stopped",
        "stop_reason": state.get("stop_reason") or current_status,
        "route_history": _history(state, "safe_stop"),
    }


def _tool_error_update(state: ReviewGraphState, tool_name: str, error: Exception) -> dict[str, Any]:
    return {
        "status": "tool_error",
        "last_failed_tool": tool_name,
        "last_error": str(error),
        "route_history": _history(state, f"{tool_name}:error"),
    }


def _route_after_intake(state: ReviewGraphState) -> Literal["requirement_agent", "safe_stop"]:
    return "safe_stop" if state["status"] == "missing_scope" else "requirement_agent"


def _route_after_tool(state: ReviewGraphState, success: str, empty: bool = False) -> str:
    if state.get("last_error"):
        retries = state.get("retry_counts", {}).get(state["last_failed_tool"], 0)
        return "retry_tool" if retries < MAX_TOOL_RETRIES else "safe_stop"
    if empty:
        return "validation_repair" if state.get("repair_count", 0) < MAX_VALIDATION_REPAIRS else "safe_stop"
    return success


def _route_requirement(state: ReviewGraphState) -> str:
    return _route_after_tool(state, "control_agent", state.get("status") == "empty_retrieval")


def _route_control(state: ReviewGraphState) -> str:
    return _route_after_tool(state, "evidence_agent", state.get("status") == "empty_retrieval")


def _route_evidence(state: ReviewGraphState) -> str:
    return _route_after_tool(state, "baseline_agent", state.get("status") == "empty_retrieval")


def _route_baseline(state: ReviewGraphState) -> str:
    return _route_after_tool(state, "insight_agent", state.get("status") == "empty_retrieval")


def _route_insight(state: ReviewGraphState) -> str:
    return _route_after_tool(state, "risk_agent")


def _route_risk(state: ReviewGraphState) -> str:
    if state.get("last_error"):
        return _route_after_tool(state, "remediation_agent")
    return "remediation_agent" if state.get("potential_findings") else "safe_stop"


def _route_remediation(state: ReviewGraphState) -> str:
    if state.get("last_error"):
        return _route_after_tool(state, "approval_interrupt")
    return "approval_interrupt" if state.get("remediation_plan") else "safe_stop"


def _route_retry(state: ReviewGraphState) -> str:
    return {
        "requirement_lookup": "requirement_agent",
        "control_drafter": "control_agent",
        "evidence_retriever": "evidence_agent",
        "asset_baseline_reader": "baseline_agent",
        "evidence_insight_analyzer": "insight_agent",
        "gap_and_risk_assessor": "risk_agent",
        "remediation_planner": "remediation_agent",
        "simulated_workflow_store": "safe_stop",
    }.get(state["last_failed_tool"], "safe_stop")


def _route_repair(state: ReviewGraphState) -> str:
    return "requirement_agent" if state.get("repair_route") == "requirement_lookup" else "safe_stop"


def _route_after_decision(state: ReviewGraphState) -> Literal["export_agent", "edit_plan", "safe_stop"]:
    if state.get("last_error"):
        return "safe_stop"
    decision = state["human_decision"]["decision"]
    if decision == DecisionType.APPROVE.value:
        return "export_agent"
    if decision == DecisionType.REVISE.value:
        return "edit_plan"
    return "safe_stop"


def _route_export(state: ReviewGraphState) -> str:
    return "safe_stop"


def build_review_graph(checkpointer: InMemorySaver | None = None):
    """Compile the documented graph with a local in-memory checkpointer."""
    builder = StateGraph(ReviewGraphState)
    builder.add_node("intake_agent", intake_agent)
    builder.add_node("requirement_agent", requirement_agent)
    builder.add_node("control_agent", control_agent)
    builder.add_node("evidence_agent", evidence_agent)
    builder.add_node("baseline_agent", baseline_agent)
    builder.add_node("insight_agent", insight_agent)
    builder.add_node("risk_agent", risk_agent)
    builder.add_node("remediation_agent", remediation_agent)
    builder.add_node("approval_interrupt", approval_interrupt)
    builder.add_node("edit_plan", edit_plan)
    builder.add_node("export_agent", export_agent)
    builder.add_node("retry_tool", retry_tool)
    builder.add_node("validation_repair", validation_repair)
    builder.add_node("safe_stop", safe_stop)

    builder.add_edge(START, "intake_agent")
    builder.add_conditional_edges("intake_agent", _route_after_intake)
    builder.add_conditional_edges("requirement_agent", _route_requirement)
    builder.add_conditional_edges("control_agent", _route_control)
    builder.add_conditional_edges("evidence_agent", _route_evidence)
    builder.add_conditional_edges("baseline_agent", _route_baseline)
    builder.add_conditional_edges("insight_agent", _route_insight)
    builder.add_conditional_edges("risk_agent", _route_risk)
    builder.add_conditional_edges("remediation_agent", _route_remediation)
    builder.add_conditional_edges("approval_interrupt", _route_after_decision)
    builder.add_edge("edit_plan", "approval_interrupt")
    builder.add_conditional_edges("export_agent", _route_export)
    builder.add_conditional_edges("retry_tool", _route_retry)
    builder.add_conditional_edges("validation_repair", _route_repair)
    builder.add_edge("safe_stop", END)
    return builder.compile(checkpointer=checkpointer or InMemorySaver())


def compact_graph_summary() -> str:
    """Return a compact one-line summary suitable for a terminal demonstration."""
    return (
        "Milestone 6 graph | 14 nodes | thread_id + InMemorySaver | "
        "tool retries<=2 | validation repairs<=1 | interrupt before approved local export"
    )


if __name__ == "__main__":
    print(compact_graph_summary())
