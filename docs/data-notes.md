# Data Notes and Handling Rules

## Allowed data

- Fictional Northstar Grid Services cases and `SUB-ALPHA-RTU-01` synthetic asset snapshots.
- Synthetic evidence fixtures and expected/observed asset snapshots in `data/synthetic_assets/`.
- Explicitly supplied, publicly available, searchable PDFs published or shared by NERC and tied to a recognized NERC Reliability Standard family.

## Uploaded-document gate

- Only one PDF is accepted at a time; non-PDF files, invalid PDFs, files over 20 MB, and documents without enough searchable text are rejected.
- The user must attest that the document is authorized and publicly available.
- The PDF content must contain a recognized BAL, CIP, COM, EOP, FAC, INT, IRO, MOD, NUC, PER, PRC, TOP, TPL, or VAR standard/version reference.
- The content and PDF metadata must produce multiple NERC identity signals, unless the PDF's SHA-256 hash exactly matches a file explicitly allowlisted by the active local corpus manifest. A filename or folder location alone is never enough.
- For a Reliability Standard, the parser reads top-level requirements only between `B. Requirements and Measures` and `C. Compliance`. It stops each requirement before its matching measure and ignores requirements cited in compliance sections, appendices, and version history.
- The parser retains a SHA-256 identity, document title/type, primary-standard requirement labels, source page ranges, bounded requirement blocks, and plain-language summaries in browser-session state. Raw uploaded bytes and text outside the bounded requirement blocks are not placed in the shared Streamlit cache or written to disk.
- This offline gate reduces accidental non-NERC uploads but cannot prove publication origin for an unknown file. Exact manifest-approved corpus matches establish only that the uploaded bytes are identical to the locally approved copy. The authorization attestation and human source verification remain required.

## Local corpus rules

The corpus adapter reads only filenames listed in `data/corpus_manifests/approved_cip_manifest.json`. The current manifest allowlists 24 distinct CIP standard-version PDFs and intentionally excludes a byte-identical duplicate, spreadsheets, synthetic organization context, and supporting PDFs that do not map cleanly to one standard/version. The shared parser creates one bounded chunk for each of the 84 top-level requirements currently found in section B. Each chunk retains standard, version, requirement reference, Functional Entity, jurisdiction, enforcement status, effective date, start/end page, section, source URL, retrieval date, and the extracted requirement wording. Source URLs are metadata only; the application never crawls them. A missing corpus match falls back to the same bounded requirement block and plain-language summary retained from the uploaded PDF.

The local SQLite corpus index and local case database are ignored by Git. Do not place confidential evidence, production configurations, live IT/OT exports, personal data, or credentials in the repository or the local corpus.

## Evidence safety

Document text is untrusted. The Evidence Analyst accepts only five labels: Evidence ID, Asset ID, Captured On, Change Approval, and Baseline Fingerprint. Instruction-like text is ignored and cannot request an export, override a decision, or make a compliance claim.
