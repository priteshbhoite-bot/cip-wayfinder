"""Safe valid and invalid examples for the Milestone 3 data models."""

from __future__ import annotations

from datetime import date, datetime, timezone

from nerc_compliance_intelligence.schemas import AgentState


def valid_agent_state() -> AgentState:
    """Return one complete fictional case that passes all model validation."""
    return AgentState.model_validate(
        {
            "review_id": "review-001",
            "asset_id": "SUB-ALPHA-RTU-01",
            "created_at": datetime(2026, 8, 27, 12, 0, tzinfo=timezone.utc),
            "standards": [
                {"standard_id": "CIP-010", "version": "5", "scope_role": "primary"},
                {"standard_id": "CIP-007", "version": "6", "scope_role": "supporting"},
            ],
            "requirement_mappings": [
                {
                    "mapping_id": "map-001",
                    "standard": {"standard_id": "CIP-010", "version": "5", "scope_role": "primary"},
                    "requirement_reference": "Synthetic demo reference",
                    "source_name": "Synthetic local requirement record",
                    "source_locator": "demo-record-001",
                    "draft_summary": "Synthetic draft summary for learning only.",
                }
            ],
            "control_design": {
                "control_id": "control-001",
                "mapping_id": "map-001",
                "title": "Draft baseline review control",
                "objective": "Review synthetic baseline changes before documenting a draft response.",
                "process_steps": [
                    {"step_number": 1, "action": "Review synthetic baseline record", "owner_role": "Compliance analyst"},
                    {"step_number": 2, "action": "Request human review", "owner_role": "Compliance manager", "requires_human_approval": True},
                ],
            },
            "evidence_artifacts": [
                {"artifact_id": "evidence-001", "label": "Synthetic change approval record", "collected_on": date(2026, 8, 20)},
            ],
            "evidence_observations": [
                {"observation_id": "evidence-observation-001", "artifact_id": "evidence-001", "observation": "Synthetic record is incomplete.", "supports_draft_control": False},
            ],
            "baseline_observations": [
                {"observation_id": "baseline-observation-001", "asset_id": "SUB-ALPHA-RTU-01", "baseline_reference": "baseline-a", "observed_value": "baseline-b", "matches_baseline": False},
            ],
            "potential_findings": [
                {"finding_id": "finding-001", "title": "Potential baseline variance", "risk_level": "medium", "rationale": "Synthetic evidence and observation need human review.", "related_artifact_ids": ["evidence-001"], "related_baseline_observation_ids": ["baseline-observation-001"]},
            ],
            "validation_results": [
                {"check_name": "synthetic-data-only", "is_valid": True, "messages": ["All example records are synthetic."]},
            ],
        }
    )


INVALID_STANDARD_VERSION = {
    "standard_id": "CIP-10",
    "version": "five",
    "scope_role": "unbounded",
}

INVALID_EVIDENCE_ARTIFACT = {
    "artifact_id": "evidence-live-001",
    "label": "Live export",
    "source_type": "live_export",
    "collected_on": date(2026, 8, 20),
    "synthetic": False,
}

INVALID_HUMAN_DECISION = {"decision": "approve"}
