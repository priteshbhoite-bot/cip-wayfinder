"""Deterministic comparison of synthetic expected and observed asset snapshots.

This module reports bounded draft observations. It never changes an asset,
accepts a change automatically, or writes to an operational system.
"""

from __future__ import annotations

import csv
import json
from datetime import date
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


COMPARISON_FIELDS = ("software", "ports_services", "patches", "accounts", "baseline_version")


class BaselineStatus(str, Enum):
    """The limited outcomes for a demonstration baseline review."""

    NO_CHANGE = "no_change"
    APPROVED_CHANGE = "approved_change"
    UNEXPLAINED_CHANGE = "unexplained_change"
    STALE_OBSERVATION = "stale_observation"
    MISSING_ASSET = "missing_asset"


class AssetSnapshot(BaseModel):
    """One synthetic expected or observed asset record."""

    model_config = ConfigDict(frozen=True)

    asset_id: str = Field(min_length=1)
    software: str = Field(min_length=1)
    ports_services: list[str]
    patches: list[str]
    accounts: list[str]
    baseline_version: str = Field(min_length=1)
    observation_date: date
    approved_change_fields: list[str] = Field(default_factory=list)


class BaselineException(BaseModel):
    """One difference between a synthetic expected and observed snapshot."""

    field_name: str
    expected_value: str
    observed_value: str
    approved: bool


class BaselineComparison(BaseModel):
    """The low-level deterministic comparison result."""

    asset_id: str
    exceptions: list[BaselineException]
    observation_age_days: int | None
    is_stale: bool
    asset_found: bool


class BaselineReviewObservation(BaseModel):
    """A bounded draft observation linked to a generated draft control."""

    model_config = ConfigDict(frozen=True)

    observation_id: str
    asset_id: str
    control_id: str
    status: BaselineStatus
    summary: str
    exceptions: list[BaselineException] = Field(default_factory=list)
    requires_sme_review: bool = True
    safety_note: str = "Synthetic baseline review observation only; not a compliance conclusion or operational action."


def _decode_list(value: str) -> list[str]:
    """Decode a JSON list stored in one small CSV cell."""
    decoded = json.loads(value)
    if not isinstance(decoded, list) or not all(isinstance(item, str) for item in decoded):
        raise ValueError("snapshot list fields must be JSON arrays of strings")
    return decoded


def load_expected_snapshots(csv_path: Path) -> list[AssetSnapshot]:
    """Read explicitly supplied local synthetic expected snapshots from CSV."""
    with csv_path.open(newline="", encoding="utf-8") as source:
        return [
            AssetSnapshot(
                asset_id=row["asset_id"], software=row["software"],
                ports_services=_decode_list(row["ports_services"]), patches=_decode_list(row["patches"]),
                accounts=_decode_list(row["accounts"]), baseline_version=row["baseline_version"],
                observation_date=date.fromisoformat(row["observation_date"]),
            )
            for row in csv.DictReader(source)
        ]


def load_observed_snapshots(json_path: Path) -> list[AssetSnapshot]:
    """Read explicitly supplied local synthetic observed snapshots from JSON."""
    return [AssetSnapshot.model_validate(item) for item in json.loads(json_path.read_text(encoding="utf-8"))]


def compare_snapshots(
    expected: AssetSnapshot,
    observed: AssetSnapshot | None,
    as_of_date: date,
    stale_after_days: int = 30,
) -> BaselineComparison:
    """Compare five named fields without inferring cause or changing either snapshot."""
    if observed is None:
        return BaselineComparison(asset_id=expected.asset_id, exceptions=[], observation_age_days=None, is_stale=False, asset_found=False)
    age_days = (as_of_date - observed.observation_date).days
    exceptions = [
        BaselineException(
            field_name=field_name,
            expected_value=json.dumps(getattr(expected, field_name), sort_keys=True),
            observed_value=json.dumps(getattr(observed, field_name), sort_keys=True),
            approved=field_name in observed.approved_change_fields,
        )
        for field_name in COMPARISON_FIELDS
        if getattr(expected, field_name) != getattr(observed, field_name)
    ]
    return BaselineComparison(
        asset_id=expected.asset_id,
        exceptions=exceptions,
        observation_age_days=age_days,
        is_stale=age_days > stale_after_days,
        asset_found=True,
    )


def analyze_baseline(
    expected: AssetSnapshot,
    observed: AssetSnapshot | None,
    control_id: str,
    as_of_date: date,
    stale_after_days: int = 30,
) -> BaselineReviewObservation:
    """Convert comparison output into one small control-linked review observation."""
    comparison = compare_snapshots(expected, observed, as_of_date, stale_after_days)
    if not comparison.asset_found:
        status, summary = BaselineStatus.MISSING_ASSET, "No synthetic observed snapshot was supplied for the expected asset."
    elif comparison.is_stale:
        status, summary = BaselineStatus.STALE_OBSERVATION, "The synthetic observation is older than the configured review window."
    elif not comparison.exceptions:
        status, summary = BaselineStatus.NO_CHANGE, "No difference was found between the synthetic expected and observed snapshots."
    elif all(exception.approved for exception in comparison.exceptions):
        status, summary = BaselineStatus.APPROVED_CHANGE, "All observed synthetic differences are marked as approved changes and still require SME review."
    else:
        status, summary = BaselineStatus.UNEXPLAINED_CHANGE, "One or more synthetic differences lack an approved-change marker and require SME review."
    return BaselineReviewObservation(
        observation_id=f"baseline-review-{expected.asset_id}", asset_id=expected.asset_id,
        control_id=control_id, status=status, summary=summary, exceptions=comparison.exceptions,
    )
