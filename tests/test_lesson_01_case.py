"""Tests for the first beginner exercise."""

import pytest

from learning.lesson_01_case import build_case_summary


def test_build_case_summary_returns_expected_synthetic_values() -> None:
    summary = build_case_summary("SUB-ALPHA-RTU-01", ["baseline", "approval"])

    assert summary["utility"] == "Northstar Grid Services"
    assert summary["standard"] == "CIP-010-5"
    assert summary["evidence_count"] == 2
    assert summary["review_status"] == "draft"


def test_build_case_summary_rejects_a_blank_asset_id() -> None:
    with pytest.raises(ValueError, match="asset_id must not be blank"):
        build_case_summary("   ", ["baseline"])
