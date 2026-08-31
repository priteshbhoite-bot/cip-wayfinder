# Final Local MVP Architecture

## Purpose

This is a local, deterministic graph for a fictional review. It uses fake agents and the nine tools from Milestone 4. The current dashboard and tests use synthetic data by default. When an explicitly supplied, approved local NERC corpus is used, retrieval preserves local provenance metadata; it does not crawl the web. The MVP does not declare compliance, provide legal advice, connect to external systems, or change operational controls.

## Components and boundaries

![CIP Wayfinder architecture diagram](../assets/cip-wayfinder-architecture.svg)

**How to read the diagram:** solid arrows are the normal review path. Dashed arrows are bounded recovery or safe-stop paths. The Streamlit interface currently presents a deterministic, source-grounded package and decision preview; the LangGraph path above is separately implemented and branch-tested. The interface does not yet invoke a paid model, external service, or write-capable graph run.

```text
Streamlit review screens (display + in-memory decision preview)
  → typed local state and local SQLite case store (explicit save consent)
  → LangGraph review workflow + in-memory checkpointer/thread_id
  → local read/compute tools and deterministic analysts
  → human approval interrupt
  → approved-only synthetic local export below outputs/
```

The only write-classified workflow action is the existing synthetic local export. A local case save also requires an explicit local-save confirmation. Neither action changes an IT/OT asset, external ticket, or operational control.

## Optional source-grounded model seam

The control-drafting step has an optional structured-provider seam. It accepts exactly one retrieved requirement mapping and constructs a request containing only its standard/version, requirement reference, source name, source locator, and retrieved excerpt. The response must remain draft-only and every meaningful field must cite exactly that requirement ID. The deterministic fake provider is still the default. The Nebius adapter is deliberately disconnected from the Streamlit UI and graph until a user selects an account-available model and explicitly approves the exact bounded request; no source text is transmitted before that approval.

The Streamlit Review package now exposes that boundary as **Review and send a source-grounded draft**. It chooses one matched requirement-level local source, shows its bounded request summary, requires a checked approval statement and a separate send click, then calls Token Factory only for that one request. The returned draft is traceability-validated and held in session memory; it cannot export, save a case, create a workflow, or change an operational control.

The upload-first interface validates one user-supplied, authorized public CIP-010-5 or CIP-007-6 PDF in browser-session memory. An optional local four-step tour explains the process before upload. The UI has two workspaces: **Start a review** provides deterministic chat-style analysis choices, and **Review package** presents the related draft results in progressive expandable sections. The package opens the existing approved local SQLite corpus in read-only mode and matches the standard/version and extracted requirement labels. A match displays a short local excerpt plus page, section, source URL, and retrieval-date provenance. The app does not persist or transmit the upload; a separate future local-save action would require explicit confirmation.

## Happy path

```text
intake agent
  → requirement lookup tool
  → control drafting agent
  → evidence retrieval tool
  → baseline retrieval tool
  → evidence insight agent
  → gap and risk agent
  → remediation planning agent
  → human approval interrupt
  → approved local export tool
  → completed safe stop
```

## Conditional routes

| Condition | Route | Limit / result |
|---|---|---|
| Missing standard, version, or asset scope | `safe_stop` | Stop without calling a tool. |
| Tool error | `retry_tool` → failed tool | At most two retries after the initial attempt; then safe stop. |
| Empty requirement/evidence/baseline retrieval | `validation_repair` | Repair once. Requirement lookup retries with the known synthetic fixture; other empty retrievals stop after recording the repair. |
| Validation still fails after repair | `safe_stop` | No second repair. |
| No potential finding / remediation plan | `safe_stop` | Stop without export. |
| Pending human decision | `approval_interrupt` | Pause using LangGraph interrupt and checkpoint state. |
| Approve | `simulated_workflow_store` → `safe_stop` | Export only approved synthetic state below `outputs/`. |
| Edit | `edit_plan` → `approval_interrupt` | Return a draft plan to human review. |
| Reject | `safe_stop` | Record rejection and do not export. |

## State and persistence

- A `thread_id` is supplied in LangGraph configuration for every run.
- `InMemorySaver` is the local Milestone 6 checkpointer. It preserves graph state through an interrupt for the life of the running process.
- `LocalCaseStore` can persist typed synthetic `AgentState` plus `thread_id` in ignored local SQLite after an explicit local-save approval. It is used for later resume, not as a workflow system.
- State records review scope, tool retry counters, validation repair counter, synthetic data, draft plan, human decision, route history, status, and any error message.
- Tool retries and validation repair are bounded counters; they are never reset inside a run.

## Safety boundary

- Only the approved route calls the write-classified `simulated_workflow_store` tool.
- The store tool independently checks for an approved `HumanDecision` and enforces the local `outputs/` directory.
- `safe_stop` is terminal and never exports data.
- Evidence document text is untrusted data. The Evidence Analyst extracts only an allowlist of factual labels and ignores instruction-like text.
- Draft controls and remediation text include retrieved requirement IDs; the Quality Reviewer rejects untraceable IDs or mismatched control links.
- Optional LangSmith tracing is configuration-preview only. It reads no key, creates no client, and makes no network call.
