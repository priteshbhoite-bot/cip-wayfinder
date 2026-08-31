# Milestone 13B — Approved local case persistence

`case_persistence.py` stores a typed synthetic `AgentState` and its graph `thread_id` in local SQLite so a reviewer can resume the same case later.

Saving is intentionally separate from creating a workflow. The caller must provide `LocalSaveApproval(approved=True, reviewer_role="...")`; without it, no database file is created. This is an explicit local-save confirmation, not an automatic approval of any finding or remediation plan.

`resume_case(case_id)` only reads. If the database or case does not exist, it returns `None` without creating anything. Errors use safe messages rather than exposing database internals or stack traces.
