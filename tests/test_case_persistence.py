"""Offline SQLite save and resume tests for Milestone 13B."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from learning.milestone_03_examples import valid_agent_state
from nerc_compliance_intelligence.case_persistence import (
    CasePersistenceError,
    LocalCaseStore,
    LocalSaveApproval,
    new_persisted_case,
)


def _case():
    return new_persisted_case(
        valid_agent_state(),
        thread_id="thread-local-resume-001",
        saved_at=datetime(2026, 8, 27, 15, 0, tzinfo=timezone.utc),
    )


def _approval() -> LocalSaveApproval:
    return LocalSaveApproval(approved=True, reviewer_role="Compliance analyst")


def test_save_requires_explicit_human_approval(tmp_path) -> None:
    store = LocalCaseStore(tmp_path / "cases.sqlite")

    with pytest.raises(CasePersistenceError, match="explicit human approval"):
        store.save_case(_case(), LocalSaveApproval(approved=False))

    assert not (tmp_path / "cases.sqlite").exists()


def test_approved_save_resumes_same_case_state_and_thread_id(tmp_path) -> None:
    store = LocalCaseStore(tmp_path / "cases.sqlite")
    saved = store.save_case(_case(), _approval())

    resumed = store.resume_case(saved.case_id)

    assert resumed == saved
    assert resumed is not None
    assert resumed.thread_id == "thread-local-resume-001"
    assert resumed.state.review_id == saved.case_id


def test_approved_resave_updates_a_case_without_creating_a_second_record(tmp_path) -> None:
    store = LocalCaseStore(tmp_path / "cases.sqlite")
    first = store.save_case(_case(), _approval())
    updated = first.model_copy(update={"thread_id": "thread-local-resume-002"})

    store.save_case(updated, _approval())

    assert store.resume_case(first.case_id) == updated


def test_missing_case_or_database_returns_none_without_creating_anything(tmp_path) -> None:
    store = LocalCaseStore(tmp_path / "does-not-exist.sqlite")

    assert store.resume_case("missing-case") is None
    assert not (tmp_path / "does-not-exist.sqlite").exists()
