"""Approved local SQLite persistence for synthetic Milestone 13B cases.

Saving a case is a local write, so the caller must supply an explicit save
approval. This is separate from the stricter approval needed for workflow export.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from nerc_compliance_intelligence.schemas import AgentState


class CasePersistenceError(RuntimeError):
    """Safe local persistence error; callers should show its message, not a stack trace."""


class LocalSaveApproval(BaseModel):
    """An explicit human confirmation for a local case-save action."""

    approved: bool
    reviewer_role: str | None = None
    action: str = "save_case"


class PersistedCase(BaseModel):
    """The minimal local record needed to resume one synthetic review."""

    model_config = ConfigDict(frozen=True)

    case_id: str = Field(min_length=1)
    thread_id: str = Field(min_length=1)
    state: AgentState
    saved_at: datetime


class LocalCaseStore:
    """A local SQLite store that only writes after an explicit save approval."""

    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize_for_approved_write(self) -> None:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        connection = self._connect()
        try:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS persisted_cases (
                    case_id TEXT PRIMARY KEY,
                    thread_id TEXT NOT NULL,
                    state_json TEXT NOT NULL,
                    saved_at TEXT NOT NULL
                )
                """
            )
            connection.commit()
        finally:
            connection.close()

    def save_case(self, persisted_case: PersistedCase, approval: LocalSaveApproval) -> PersistedCase:
        """Insert or update one local synthetic case only after a human saves it."""
        if not approval.approved or not approval.reviewer_role or approval.action != "save_case":
            raise CasePersistenceError("local case save requires explicit human approval, reviewer role, and save_case action")
        self._initialize_for_approved_write()
        connection = self._connect()
        try:
            connection.execute(
                """
                INSERT INTO persisted_cases (case_id, thread_id, state_json, saved_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(case_id) DO UPDATE SET
                    thread_id = excluded.thread_id,
                    state_json = excluded.state_json,
                    saved_at = excluded.saved_at
                """,
                (
                    persisted_case.case_id,
                    persisted_case.thread_id,
                    persisted_case.state.model_dump_json(),
                    persisted_case.saved_at.isoformat(),
                ),
            )
            connection.commit()
        finally:
            connection.close()
        return persisted_case

    def resume_case(self, case_id: str) -> PersistedCase | None:
        """Read a previously approved local save without creating a database or writing."""
        if not self.database_path.exists():
            return None
        try:
            connection = self._connect()
            try:
                row = connection.execute(
                    "SELECT case_id, thread_id, state_json, saved_at FROM persisted_cases WHERE case_id = ?",
                    (case_id,),
                ).fetchone()
            finally:
                connection.close()
        except sqlite3.Error as error:
            raise CasePersistenceError("local case store could not be read safely") from error
        if row is None:
            return None
        try:
            return PersistedCase(
                case_id=row["case_id"],
                thread_id=row["thread_id"],
                state=AgentState.model_validate_json(row["state_json"]),
                saved_at=datetime.fromisoformat(row["saved_at"]),
            )
        except (ValueError, TypeError) as error:
            raise CasePersistenceError("stored case cannot be resumed safely") from error


def new_persisted_case(state: AgentState, thread_id: str, saved_at: datetime | None = None) -> PersistedCase:
    """Create a typed case snapshot without writing it; saving remains a separate action."""
    return PersistedCase(
        case_id=state.review_id,
        thread_id=thread_id,
        state=state,
        saved_at=saved_at or datetime.now(timezone.utc),
    )
