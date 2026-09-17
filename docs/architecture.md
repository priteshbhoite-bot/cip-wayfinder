# Final Local MVP Architecture

## Product draft revisions

The Streamlit product has a separate session-only SME editor. Needs editing blocks delivery, opens a requirement/field selector and requires an explained save. Only existing draft control/remediation text can change; sources, IDs, date metadata and step ordering remain protected. Pydantic validation and structural quality review run after each save. Finish editing returns to review without granting approval.

Private revised package JSON and before/after history are overlaid on, never written into, cached generated data. New upload, scope or base content resets the overlay. Attachment approval is bound to the complete package and intake; edits clear the attachment, receipt and separate email consent. Session history is temporary, not a durable audit trail. The synthetic graph's own edit/interrupt route is unchanged.

## Purpose

This is a local, deterministic graph for a fictional review. It uses fake agents and the nine tools from Milestone 4. The current dashboard and tests use synthetic data by default. When an explicitly supplied, approved local NERC corpus is used, retrieval preserves local provenance metadata; it does not crawl the web. The MVP does not declare compliance, provide legal advice, connect to external systems, or change operational controls.

## Components and boundaries

![CIP Wayfinder architecture diagram](../assets/cip-wayfinder-architecture.svg)

**How to read the diagram:** solid arrows are the normal review path. Dashed arrows are bounded recovery or safe-stop paths. The Streamlit interface presents a deterministic, source-grounded package and approval-gated Word delivery through direct download or configured SMTP. Package approval and email-send authorization are separate gates. The LangGraph path above remains separately implemented and branch-tested.

```text
Streamlit review screens (display + approval-gated in-memory Word export)
  → typed local state and local SQLite case store (explicit save consent)
  → LangGraph review workflow + in-memory checkpointer/thread_id
  → local read/compute tools and deterministic analysts
  → human approval interrupt
  → approved-only synthetic local export below outputs/
```

The only write-classified workflow action is the existing synthetic local export. A local case save also requires an explicit local-save confirmation. Neither action changes an IT/OT asset, external ticket, or operational control.

## Structured-provider learning seam

The codebase retains an optional structured-provider seam for learning and automated testing. It accepts exactly one retrieved requirement mapping and constructs a bounded request containing only its standard/version, requirement reference, source name, source locator, and retrieved excerpt. The response must remain draft-only and every meaningful field must cite exactly that requirement ID. The deterministic fake provider remains the test default. This seam is disconnected from the Streamlit Review package, so product use makes no external model request.

The upload-first interface accepts one user-supplied, authorized public, searchable PDF in browser-session memory. The content must contain a recognized BAL, CIP, COM, EOP, FAC, INT, IRO, MOD, NUC, PER, PRC, TOP, TPL, or VAR standard reference plus enough independent NERC identity signals, or exactly match a manifest-approved corpus file by SHA-256. A filename alone cannot pass validation. For a Reliability Standard, the shared parser extracts only top-level requirements between `B. Requirements and Measures` and `C. Compliance`, ends each source block before its matching measure, and ignores appendix and version-history references. Supporting documents without that section retain standard-specific topic summaries. Raw PDF bytes are not placed in the shared cache.

The UI still has two workspaces: **Start a review** and **Review package**. The loading form collects scope but no longer asks the user to choose a review objective. The fixed Review Package Agent objective is to prepare a source-grounded draft package for SME tailoring. Approved read-only corpus matches take precedence. Requirements display as simple `R1`, `R2`, and similar labels beneath one primary-standard heading. Each collapsed item shows a source-derived plain-language synopsis, the official requirement wording extracted from its bounded section-B block, and its page citation when opened. Literal text rendering prevents untrusted PDF wording from being interpreted as Markdown, and no fixed-height text area is used. If the corpus has no match, the content-validated uploaded requirement block supplies the same source text, summary, and page citation. The typed Review Package Agent preserves the document profile, mappings, controls, remediation, and source links; it also flags missing approved-corpus support without inventing replacements. After reviewing sources and drafts, a user may approve the exact package for download or email delivery with a reviewer role and rationale. The deterministic renderer creates the `.docx` in memory. A separate form revalidates the package context, recipient, and explicit send authorization before calling SMTP. The app retains only a masked delivery receipt in session state and does not persist the document.

Content validation is a best-effort offline identity gate, not cryptographic proof that NERC published a file. The user authorization attestation and SME source verification remain required. Image-only scans are rejected because the app cannot safely identify or explain them without searchable text.

![CIP Wayfinder review and delivery flow](../assets/cip-wayfinder-review-delivery-flow.svg)

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
| Missing standard, version, or selected synthetic asset ID in the separate LangGraph demonstration | `safe_stop` | Stop without calling a tool. The Streamlit upload form does not collect asset scope. |
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
