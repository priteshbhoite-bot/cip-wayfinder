# Milestone 12 — Synthetic baseline comparison

The folder `data/synthetic_assets/` contains a tiny expected CSV snapshot and observed JSON snapshot. Both are fictional learning data. Each asset record includes software, ports/services, patches, accounts, baseline version, and observation date.

`baseline_analysis.py` first compares exactly those five baseline fields. A change is only tagged as an approved synthetic change when its observed record explicitly names the changed field in `approved_change_fields`; the program never assumes approval. The Baseline Analyst turns that result into one bounded, draft review observation linked to a provided control ID.

The possible statuses are no change, approved change, unexplained change, stale observation, and missing asset. Every status requires SME review and is not a compliance conclusion or an action on an asset.
