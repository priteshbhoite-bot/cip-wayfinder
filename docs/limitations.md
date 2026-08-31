# Limitations

- This is a fictional local application, not a NERC compliance determination, legal opinion, audit conclusion, or engineering approval.
- Applicability is not determined automatically. Missing Functional Entity, jurisdiction, standard/version, or asset scope must be supplied by an SME.
- Draft controls, findings, risk labels, and remediation plans require organization-specific tailoring and human review.
- Evidence and asset records are synthetic. The MVP must not receive confidential evidence or live IT/OT exports.
- Local corpus extraction preserves source metadata but does not replace a qualified review of the authoritative document and organization context.
- Case persistence is local SQLite only. Checkpoint persistence is in-memory for the running process.
- The current dashboard’s decision buttons are an in-memory preview; they do not save or export.
- Optional providers and LangSmith tracing are not connected. Any future external call needs separate explicit approval.
- No operational control, configuration, ticket, or external workflow is deployed, activated, modified, or closed by this MVP.
