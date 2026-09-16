# AI-Native NERC Compliance Intelligence MVP

## 1. MVP definition

The MVP is a local Streamlit application that helps a compliance analyst review a **synthetic** cyber-asset case. It combines a version-scoped NERC requirement record, draft controls, synthetic evidence insights, simulated asset-baseline observations, and a simulated remediation workflow.

The agent graph may read and analyze autonomously. Before it creates or updates a simulated remediation workflow or exports a document, it pauses for explicit human approval. All data, database records, model stubs, and automated tests remain local for the first release.

This is a local demonstration system, not a compliance determination, legal opinion, or operational-control system. Every generated control and finding is a draft requiring organization-specific review and tailoring.

## 2. Target subject-matter expert (SME)

**Primary user:** a compliance analyst who coordinates evidence reviews and drafts remediation plans for cyber-system compliance work.

**Supporting reviewers:** a cybersecurity/OT asset owner and a compliance manager who can approve, reject, or request revision of a proposed remediation workflow.

**Assumption:** Northstar Grid Services is a fictional registered entity. Its users, asset inventory, evidence process, ownership roles, risk thresholds, and remediation procedures are fictional for this project.

## 3. Standards and document boundary

`CIP-010-5` remains the primary assignment demonstration and `CIP-007-6` remains the supporting example, but the upload capability now recognizes all current NERC Reliability Standard families: BAL, CIP, COM, EOP, FAC, INT, IRO, MOD, NUC, PER, PRC, TOP, TPL, and VAR. It supports decimal or letter versions, regional suffixes, and NERC supporting materials that cite at least one recognized standard.

The application accepts one authorized public, searchable PDF at a time. It must display the source file, detected document type, referenced standard/version, and section or page reference for every material NERC claim retrieved from a local corpus or summarized from the upload.

Out of scope: non-PDF material, documents without searchable text, documents that cannot be content-identified as NERC-associated, enforcement interpretations, organization-specific applicability decisions, and any claim that this system establishes compliance.

**Assumption:** the user has an authorized, publicly available NERC-published or NERC-shared PDF. Local content validation reduces accidental misuse but is not cryptographic proof of publication origin.

## 4. Sample case

**Fictional utility:** Northstar Grid Services  
**Fictional asset:** `SUB-ALPHA-RTU-01`  
**Case:** A synthetic review identifies a mismatch between the documented baseline and the observed configuration fingerprint for the asset. Synthetic evidence also includes an incomplete approval record for a recent change. The agent retrieves the version-scoped requirement record, drafts a control, assesses the evidence and observation, assigns a demo risk level, and proposes a remediation workflow. A human reviewer must approve before the local workflow record is created.

**Assumption:** asset criticality, baseline fields, evidence items, owners, dates, and risk scores are invented solely for testing and demonstration.

## 5. Nine local tools

| # | Tool | Mode | Purpose |
|---|---|---|---|
| 1 | `requirement_lookup` | Read | Retrieves a version-scoped synthetic requirement record and citation metadata. |
| 2 | `control_drafter` | Read/compute | Produces a clearly labeled draft control from the requirement record. |
| 3 | `evidence_retriever` | Read | Returns synthetic evidence items for the selected asset and review. |
| 4 | `asset_baseline_reader` | Read | Returns simulated asset-baseline and observed-configuration data. |
| 5 | `evidence_insight_analyzer` | Read/compute | Extracts structured strengths, missing evidence, and conflicts. |
| 6 | `gap_and_risk_assessor` | Read/compute | Compares requirement, control, evidence, and observations; returns explainable gaps and High/Medium/Low risk. |
| 7 | `remediation_planner` | Read/compute | Produces a draft remediation plan with owner, due date, and rationale. |
| 8 | `approval_gate` | Interrupt | Pauses the graph for explicit approve, reject, or revise input. |
| 9 | `simulated_workflow_store` | Write | Creates or updates a local SQLite remediation workflow only after approval. |

Automated tests use deterministic fake implementations of tools 1–7. Tool 9 writes only to a disposable local test database during tests.

## 6. Seven agent roles

The MVP uses seven named specialist roles. They are deterministic components or graph nodes with narrow responsibilities; they do not need to be seven separate paid model calls.

1. **Intake and Scope Agent** — validates the synthetic review request, standard identifier, version, and asset ID.
2. **Requirement and Citation Agent** — retrieves the version-scoped requirement record and preserves citation metadata.
3. **Control Drafting Agent** — creates a draft, organization-tailored control statement; it never labels it as compliant.
4. **Review Package Agent** — assembles the validated document profile, citations, draft controls, and remediation into a strict source-grounded package for SME tailoring; it cannot approve or deliver the package.
5. **Evidence Insight Agent** — reads synthetic evidence and simulated baseline observations, then identifies missing or conflicting inputs.
6. **Risk and Remediation Agent** — produces explainable gap findings, a High/Medium/Low score, and a draft remediation plan.
7. **Human Handoff and Workflow Agent** — presents the plan, invokes the approval interrupt, and writes the simulated workflow only after approval.

## 7. State and control flow

The LangGraph state is persisted through a local checkpointer and includes:

- review ID, graph thread ID, status, and timestamps;
- standard ID, version, source citation metadata, and selected asset ID;
- requirement record, draft control, evidence items, baseline observation, and analysis notes;
- gaps, risk score, risk rationale, remediation draft, and reviewer decision;
- tool-call history, retry count, error details, and audit events;
- simulated workflow ID only after approved creation.

Control flow:

```text
validate intake → retrieve requirement → draft control → retrieve evidence + baseline
→ analyze insights → assess gaps/risk → draft remediation → approval interrupt
→ approved: create local workflow → summary
→ rejected: record decision and close without workflow write
→ revise: return to remediation drafting
```

Read-only tool failures retry once when safe, then produce a clear recoverable error state. Missing required inputs stop the review with an actionable message. The checkpointer allows an interrupted approval review to resume using the same local thread ID.

## 8. Read/write boundary

| Category | Allowed without approval | Requires explicit human approval | Prohibited |
|---|---|---|---|
| Local synthetic data | Read and analyze | Export a draft document | Using confidential or live operational data |
| Local SQLite | Read review/checkpoint state | Create/update a simulated remediation workflow | Writing to a production workflow system |
| External systems | None in MVP | Future connected-system write, separately authorized | Unapproved calls or data transfer |
| Operational controls | None | None | Deploying, activating, or changing an IT/OT or operational control |
| Source control | Local review only | GitHub publication | Committing secrets or sensitive data |

## 9. Non-goals

- Certifying, declaring, or guaranteeing NERC compliance.
- Providing legal, regulatory, audit, or engineering advice for a real entity.
- Ingesting confidential evidence, production configurations, or live IT/OT exports.
- Connecting to a real ticketing system, document repository, SIEM, CMDB, or operational technology environment.
- Automatically closing gaps, approving remediation, or applying configuration changes.
- Broad RAG across the full NERC corpus or interpretation of standards outside the defined versions.
- Replacing human SME, legal, security, or compliance review.

## 10. Success metrics

1. A new synthetic review reaches a human approval interrupt in under 60 seconds on a local laptop.
2. An approved review creates exactly one simulated local workflow with an auditable approval event.
3. A rejected review creates no workflow record.
4. Every material retrieved NERC claim in a real-document run includes source, version, and section/page citation metadata.
5. The graph resumes an interrupted approval review from its local checkpointer.
6. The automated evaluation suite passes 15 of 15 deterministic MVP evaluations.
7. A first-time viewer can follow the end-to-end demo, including an error path and approval decision, in under five minutes.

## 11. Fifteen evaluations

| # | Evaluation | Expected proof |
|---|---|---|
| 1 | Valid intake | Accepted request contains allowed asset, standard, and version. |
| 2 | Unsupported version | Clear stop message; no downstream tool call. |
| 3 | Requirement retrieval | Correct synthetic record and citation metadata are returned. |
| 4 | Missing requirement | Recoverable error state names the missing source. |
| 5 | Draft-control labeling | Output is labeled draft and includes no compliance declaration. |
| 6 | Evidence insight | Missing approval evidence is identified from the synthetic fixture. |
| 7 | Baseline variance | Configuration mismatch is identified from the synthetic fixture. |
| 8 | Risk rubric | Known fixture maps to expected High/Medium/Low result and rationale. |
| 9 | Remediation completeness | Draft includes action, owner, due date, and linked gaps. |
| 10 | Safe retry | Read-only tool failure retries once, then records a helpful error. |
| 11 | Approval interrupt | Graph pauses before any workflow-store call. |
| 12 | Rejection safety | Rejection records the decision and creates no workflow. |
| 13 | Approved workflow | Approval creates one local workflow with audit trail. |
| 14 | Checkpoint resume | Paused graph resumes with the same review state and thread ID. |
| 15 | Citation and data guardrail | Real-document fixture requires citation fields; test fixtures contain no confidential/live data markers. |

## 12. Delivery requirements → planned proof

| Delivery requirement | Planned proof |
|---|---|
| Agentic multi-step workflow | LangGraph graph and end-to-end review run. |
| Tools | Nine-tool registry with unit tests and tool-call history. |
| State across steps | Typed graph state plus local SQLite/checkpointer records. |
| Control flow | Conditional routing diagram and tests for approve/reject/revise/error paths. |
| Tool failure handling | Evaluation 10 and demo of a deterministic fake-tool failure. |
| Checkpointers | Evaluation 14 plus local resume demonstration. |
| Interrupts | `approval_gate` pauses before workflow creation. |
| Human approval | Evaluations 11–13 and visible reviewer action in Streamlit. |
| Tracing and evaluations | Local structured trace/audit log initially; optional LangSmith tracing after graph tests pass; 15 deterministic evaluations. |
| End-to-end demo | Under-five-minute script: intake, analysis, failure recovery, approval, workflow, summary. |
| Documentation | README, this project brief, decision log, datasets description, prompts/iterations, and learnings. |
| GitHub | Local repository is cleaned of secrets and synthetic-only before explicit approval to publish. |
| Video under five minutes | Recorded walkthrough of architecture, Codex-assisted development, live happy path, error path, and approval gate. |

## 13. Ready-to-build checklist

- [x] Demonstration scope selected: CIP-010-5 primary and CIP-007-6 supporting; dynamic upload supports all recognized NERC standard families.
- [x] Target user selected: compliance analyst.
- [x] Interface selected: Streamlit.
- [x] Persistence selected: local SQLite and local LangGraph checkpointer.
- [x] Approval rule selected: approval before simulated workflow creation; no automatic gap closure.
- [x] Data boundary selected: synthetic-only MVP.
- [x] Fictional utility and sample asset approved.
- [x] Initial model strategy selected: fake deterministic implementations until graph tests pass.
- [ ] Create the local project foundation, test runner, README, and decision log.
- [ ] Implement and test the fake read-only tools before using NERC documents or API keys.
- [ ] Add authorized public local standards documents only after graph tests pass.
- [ ] Obtain explicit approval before any export, external connection, GitHub publication, or credential use.
