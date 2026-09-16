# Prompt and Model-Behavior Log

This project does not store raw prompts, model transcripts, credentials, or source-document text in the repository.

| Component | Current behavior | Guardrail | Status |
|---|---|---|---|
| Standards Agent | Strict structured output from retrieved local chunks | Rejects citations/mappings not identical to supplied retrieval | Fake default |
| Applicability Agent | Requests missing scope fields | May not guess scope or decide applicability | Fake default |
| Control Drafting | Deterministic draft text; a requirement-specific, source-grounded provider seam is available | One selected retrieved mapping only; every text field must cite that exact requirement ID; separate approval is required before external transmission | Fake default |
| Review Package Agent | Deterministically assembles validated knowledge, mappings, controls, remediation, and sources | Cannot alter grounded inputs, approve, render, email, or perform operational actions | Local only |
| Evidence Analyst | Deterministic label extraction | Treats text as untrusted and ignores instruction-like lines | Local only |
| Provider abstraction | Fake default plus Nebius AI Studio / Token Factory OpenAI-compatible structured-output adapter | Token Factory uses its documented JSON-schema `response_format`; Nebius requires `NCI_NEBIUS_API_KEY`, an account-selected `NCI_MODEL_NAME`, exact preview review, and explicit approval before any request | Fake default; Nebius adapter installed but disconnected |
| LangSmith tracing | Configuration preview | No key read, client creation, or trace transmission | Disabled by default |

For a future paid provider smoke test, show the selected model, exact small request shape, credential variable name, and cost-sensitive scope; then wait for explicit approval.

## Representative coding prompts and iterations

These safe excerpts describe development requests, not runtime prompts, credentials, or model transcripts:

- "Implement Milestone 3 only. Define StandardVersion, RequirementMapping, ControlDesign, EvidenceArtifact, EvidenceObservation, BaselineObservation, PotentialFinding, ProcessStep, ValidationResult, HumanDecision, and AgentState." This established typed contracts before UI or model logic.
- "Implement Milestone 6 only. Build the graph from docs/architecture.md using fake agents and fake tools." The request also required bounded recovery, checkpointing, and a human interrupt before export.
- "Please go ahead and make all the necessary changes to the code base and files to implement the hybrid upload-and-chat interface." Later iterations simplified this into the current upload-first package.
- "Please implement that local requirement-aware drafter next" addressed repetitive controls while keeping the product deterministic and source-linked.
- "Do one final assignment-readiness check, fix only submission blockers, and submit." The final pass verified existing behavior rather than adding Excel automation or paid calls.

Codex assisted with beginner explanations, implementation and test generation. Iterations addressed navigation/session-state errors, version-aware parsing, repetitive drafts, simpler intake, and source-text readability. Learnings: build contracts before orchestration; distinguish fixture tests from live-model quality; test failure and approval routes; and distinguish the product UI from the synthetic LangGraph demonstration. No real-user success rate was measured.
