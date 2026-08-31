# AI-Native NERC Compliance Intelligence — Learning-First Rules

## Build incrementally

- Make small, independently testable changes. Explain every meaningful change in beginner-friendly language: what changed, why it matters, and how it was checked.
- Use Python type hints throughout application code. Use Pydantic models for structured application configuration and later graph state.
- Run targeted tests after each meaningful change and the full test suite before handoff.
- Update `README.md` and `docs/decision-log.md` whenever behavior, architecture, data contracts, or safety boundaries change.

## Keep data and providers safe

- Never put secrets in source files, logs, tests, screenshots, documentation, or Git. Keep future local credentials only in ignored environment files.
- Use synthetic requirements, evidence, assets, remediation records, fake retrieval, and fake model providers by default.
- Never use confidential evidence, real operational records, or live IT/OT asset exports in this application.
- Cite source name, standard/version, and section or page reference for every material NERC claim retrieved from an approved local source.

## Respect compliance and operational boundaries

- This is a fictional, local application using Northstar Grid Services and `SUB-ALPHA-RTU-01` as safe example data; it is not legal advice or an authoritative NERC compliance determination.
- Never make a compliance declaration. Generated controls, findings, and remediation plans are drafts requiring organization-specific review and tailoring.
- Do not deploy, activate, modify, or otherwise write to an operational control, live IT/OT system, or production workflow.
- All application write actions, exports, external connections, and GitHub publication require explicit human approval. The MVP may read and analyze local synthetic data only.
