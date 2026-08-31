"""Tests for the deterministic Milestone 12 synthetic baseline analyst."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from nerc_compliance_intelligence.baseline_analysis import (
    AssetSnapshot,
    BaselineStatus,
    analyze_baseline,
    load_expected_snapshots,
    load_observed_snapshots,
)


DATA_DIRECTORY = Path(__file__).resolve().parents[1] / "data" / "synthetic_assets"
EXPECTED = load_expected_snapshots(DATA_DIRECTORY / "expected_assets.csv")[0]
OBSERVED = load_observed_snapshots(DATA_DIRECTORY / "observed_assets.json")[0]
AS_OF = date(2026, 8, 27)


def _analyze(observed: AssetSnapshot | None):
    return analyze_baseline(EXPECTED, observed, "draft-control-traceable-001", AS_OF)


def test_snapshot_files_load_expected_asset_fields() -> None:
    assert EXPECTED.software == "firmware-1.0"
    assert OBSERVED.ports_services == ["ssh:22", "https:443"]
    assert EXPECTED.patches == ["patch-2026-07"]
    assert EXPECTED.accounts == ["svc_rtu", "ops_viewer"]


def test_no_change_creates_a_control_linked_review_observation() -> None:
    observation = _analyze(OBSERVED)

    assert observation.status is BaselineStatus.NO_CHANGE
    assert observation.control_id == "draft-control-traceable-001"
    assert observation.exceptions == []


def test_approved_change_is_not_treated_as_an_unexplained_change() -> None:
    approved = OBSERVED.model_copy(update={"software": "firmware-1.1", "approved_change_fields": ["software"]})

    observation = _analyze(approved)

    assert observation.status is BaselineStatus.APPROVED_CHANGE
    assert observation.exceptions[0].approved is True


def test_unexplained_change_requires_sme_review() -> None:
    changed = OBSERVED.model_copy(update={"accounts": ["svc_rtu", "ops_viewer", "temp_account"]})

    observation = _analyze(changed)

    assert observation.status is BaselineStatus.UNEXPLAINED_CHANGE
    assert observation.exceptions[0].field_name == "accounts"
    assert observation.requires_sme_review is True


def test_stale_observation_is_bounded_even_when_values_match() -> None:
    stale = OBSERVED.model_copy(update={"observation_date": date(2026, 6, 1)})

    assert _analyze(stale).status is BaselineStatus.STALE_OBSERVATION


def test_missing_asset_creates_no_exceptions() -> None:
    observation = _analyze(None)

    assert observation.status is BaselineStatus.MISSING_ASSET
    assert observation.exceptions == []
