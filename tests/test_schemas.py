"""Serialization and validation tests for the Milestone 3 data layer."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from learning.milestone_03_examples import (
    INVALID_EVIDENCE_ARTIFACT,
    INVALID_HUMAN_DECISION,
    INVALID_STANDARD_VERSION,
    valid_agent_state,
)
from nerc_compliance_intelligence.schemas import (
    AgentState,
    EvidenceArtifact,
    HumanDecision,
    StandardVersion,
)


def test_valid_synthetic_agent_state_serializes_and_round_trips() -> None:
    state = valid_agent_state()

    serialized = state.model_dump(mode="json")
    restored = AgentState.model_validate(serialized)

    assert serialized["asset_id"] == "SUB-ALPHA-RTU-01"
    assert serialized["potential_findings"][0]["risk_level"] == "medium"
    assert restored == state


@pytest.mark.parametrize(
    ("standard_id", "version"),
    [
        ("BAL-003", "2"),
        ("CIP-002", "5.1a"),
        ("PRC-006-NPCC", "2"),
        ("TOP-003", "8"),
    ],
)
def test_standard_version_accepts_nerc_families_and_version_shapes(
    standard_id: str, version: str
) -> None:
    standard = StandardVersion(
        standard_id=standard_id,
        version=version,
        scope_role="primary",
    )

    assert standard.standard_id == standard_id
    assert standard.version == version


@pytest.mark.parametrize(
    ("model", "example"),
    [
        (StandardVersion, INVALID_STANDARD_VERSION),
        (EvidenceArtifact, INVALID_EVIDENCE_ARTIFACT),
        (HumanDecision, INVALID_HUMAN_DECISION),
    ],
)
def test_invalid_examples_are_rejected(model: type[object], example: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        model.model_validate(example)  # type: ignore[attr-defined]


def test_agent_state_rejects_a_baseline_for_a_different_asset() -> None:
    state_data = valid_agent_state().model_dump(mode="python")
    state_data["baseline_observations"][0]["asset_id"] = "SUB-BRAVO-RTU-02"

    with pytest.raises(ValidationError, match="state asset_id"):
        AgentState.model_validate(state_data)
