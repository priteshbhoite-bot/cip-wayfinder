# Limitations

- This is a fictional local application, not a NERC compliance determination, legal opinion, audit conclusion, or engineering approval.
- Applicability is not determined automatically. The upload flow requires Functional Entity and Regional Entity context, while standard/version comes from the validated document. Asset-specific applicability and tailoring remain questions for an SME.
- Draft controls, findings, risk labels, and remediation plans require organization-specific tailoring and human review.
- Evidence and asset records are synthetic. The MVP must not receive confidential evidence or live IT/OT exports.
- Local corpus extraction preserves source metadata but does not replace a qualified review of the authoritative document and organization context.
- Case persistence is local SQLite only. Checkpoint persistence is in-memory for the running process.
- The dashboard can create an in-memory Word draft package after explicit approval. It does not persist the file, create a workflow, or make a compliance determination. Direct download is local; optional email is a separate, explicitly authorized external action that requires configured SMTP credentials.
- Optional providers and LangSmith tracing are not connected. Any future external call needs separate explicit approval.
- No operational control, configuration, ticket, or external workflow is deployed, activated, modified, or closed by this MVP.
