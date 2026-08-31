# Data Notes and Handling Rules

## Allowed data

- Fictional Northstar Grid Services cases and `SUB-ALPHA-RTU-01` synthetic asset snapshots.
- Synthetic evidence fixtures and expected/observed asset snapshots in `data/synthetic_assets/`.
- Explicitly supplied, publicly available local copies of the two selected standard versions: CIP-010-5 and CIP-007-6.

## Local corpus rules

The corpus adapter reads only filenames listed in a local manifest. It retains standard, version, requirement reference, Functional Entity, jurisdiction, enforcement status, effective date, page/section, source URL, and retrieval date. Source URLs are metadata only; the application never crawls them.

The local SQLite corpus index and local case database are ignored by Git. Do not place confidential evidence, production configurations, live IT/OT exports, personal data, or credentials in the repository or the local corpus.

## Evidence safety

Document text is untrusted. The Evidence Analyst accepts only five labels: Evidence ID, Asset ID, Captured On, Change Approval, and Baseline Fingerprint. Instruction-like text is ignored and cannot request an export, override a decision, or make a compliance claim.
