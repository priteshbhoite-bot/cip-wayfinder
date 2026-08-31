# Prompt and Model-Behavior Log

This project does not store raw prompts, model transcripts, credentials, or source-document text in the repository.

| Component | Current behavior | Guardrail | Status |
|---|---|---|---|
| Standards Agent | Strict structured output from retrieved local chunks | Rejects citations/mappings not identical to supplied retrieval | Fake default |
| Applicability Agent | Requests missing scope fields | May not guess scope or decide applicability | Fake default |
| Control Drafting | Deterministic draft text; a requirement-specific, source-grounded provider seam is available | One selected retrieved mapping only; every text field must cite that exact requirement ID; separate approval is required before external transmission | Fake default |
| Evidence Analyst | Deterministic label extraction | Treats text as untrusted and ignores instruction-like lines | Local only |
| Provider abstraction | Fake default plus Nebius AI Studio / Token Factory OpenAI-compatible structured-output adapter | Token Factory uses its documented JSON-schema `response_format`; Nebius requires `NCI_NEBIUS_API_KEY`, an account-selected `NCI_MODEL_NAME`, exact preview review, and explicit approval before any request | Fake default; Nebius adapter installed but disconnected |
| LangSmith tracing | Configuration preview | No key read, client creation, or trace transmission | Disabled by default |

For a future paid provider smoke test, show the selected model, exact small request shape, credential variable name, and cost-sensitive scope; then wait for explicit approval.
