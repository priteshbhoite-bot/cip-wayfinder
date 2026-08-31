# Offline Evaluation Report

Run date: 2026-08-28  
Mode: deterministic local-only; fake providers; no external tracing or model calls.

| # | Evaluation | Result | Proof |
|---:|---|---|---|
| 1 | Valid intake shape | PASS | Typed synthetic state accepts the scoped case. |
| 2 | Unsupported version | PASS | Unknown version returns no local requirement. |
| 3 | Requirement retrieval | PASS | Version-scoped fake retrieval returned the expected ID. |
| 4 | Missing requirement | PASS | Absent requirement returns an empty result. |
| 5 | Draft-control labeling | PASS | Generated control retains its draft label. |
| 6 | Evidence insight | PASS | Incomplete synthetic evidence identifies missing fields. |
| 7 | Baseline variance | PASS | Changed synthetic account is a bounded review observation. |
| 8 | Risk rubric | PASS | Known missing-evidence fixture maps to Medium. |
| 9 | Remediation completeness | PASS | Each ordered draft step includes action, owner, decision, and end state. |
| 10 | Bounded tool retry | PASS | Graph retry limit remains two. |
| 11 | Approval interrupt | PASS | Pending decision pauses before export. |
| 12 | Rejection safety | PASS | Rejected decision cannot enter an export route. |
| 13 | Approved workflow boundary | PASS | A pending state cannot satisfy the existing export guard. |
| 14 | Checkpoint-style resume | PASS | Approved local save resumes the same typed case and thread ID. |
| 15 | Citation and data guardrail | PASS | Requirement metadata is present and evidence remains synthetic/local. |

Command: `uv run python -m nerc_compliance_intelligence.evaluations`.

The report is test evidence for the MVP behavior, not evidence of NERC compliance.
