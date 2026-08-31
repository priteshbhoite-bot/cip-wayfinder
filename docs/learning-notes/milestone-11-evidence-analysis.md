# Milestone 11 — Synthetic evidence analysis

`src/nerc_compliance_intelligence/evidence_analysis.py` reads three fictional document fixtures. It treats each document's text as untrusted data, not as instructions for the program.

The extractor accepts only five exact labels: `Evidence ID`, `Asset ID`, `Captured On`, `Change Approval`, and `Baseline Fingerprint`. Lines containing instruction-like words are counted and ignored. No document can change the rules, cause an export, or make a compliance declaration.

The analyst then reports observable facts, possible (not conclusive) control support, missing fields, age in days, inconsistencies, a High/Medium/Low confidence label, and direct questions for an SME. These are draft observations based only on synthetic test data.
