# CIP Wayfinder assignment demonstration script

Aligned with Submission v4 and published application baseline `ce0f0c9`. Aim for 4:40 and leave a 20-second buffer. Existing video: https://drive.google.com/file/d/1LBrPT0LFz-n4r8UJg99BQxy7cHizHDAA/view (opens as ElevenLabs.mov; current-app coverage and duration still need review). Repository: https://github.com/priteshbhoite-bot/cip-wayfinder.

## Demo goal

Demonstrate, in five minutes or less, how CIP Wayfinder turns an authorized public NERC standards-related PDF into a dynamic, source-grounded draft review package while preserving human control, traceability, and safe failure behavior.

The presentation should make one distinction clear:

- The **Streamlit product path** content-validates a local public NERC PDF, dynamically identifies its document type, referenced standards, and knowledge items, prefers matching material from the approved local SQLite corpus, creates deterministic draft controls and remediation, and prepares an in-memory Word package after a human package decision. Download and email are separate delivery choices.
- The **LangGraph assignment path** uses synthetic data to demonstrate specialized agents, typed shared state, tools, bounded retries, one validation repair, checkpointed interruption, edit/reject/approve routing, and an approved-only local synthetic workflow export.

These layers support the same product direction, but the current Streamlit page does not claim that every LangGraph node runs behind each screen interaction.

## Before recording

1. Start the app from the repository root:

   ```powershell
   uv run streamlit run app.py
   ```

2. Have one authorized public, searchable NERC standards-related PDF ready. A `CIP-010-5` or `CIP-007-6` PDF still works well for the assignment walkthrough.
3. Use only the fictional organization and safe scope choices shown below. Do not enter real people, asset inventories, evidence, or operational information.
4. Open these two diagrams in separate tabs so they can be shown briefly:
   - `assets/cip-wayfinder-system-v4.svg` (current connected product flow and separate LangGraph panel)
   - `assets/cip-wayfinder-agent-communication.svg`
5. If demonstrating email, use a test mailbox. Keep `.env`, API keys, SMTP credentials, and terminal environment output off screen.
6. Keep a terminal open at the repository root with the verification commands near the end of this script ready to paste.

## Presenter-ready script

### 0:00–0:25 — Introduce the problem and safety boundary

**On screen:** Open CIP Wayfinder on **Start a review** and point to the three safety badges.

**Say:**

> CIP Wayfinder helps a utility compliance analyst understand an authorized NERC standards-related PDF and turn its source-grounded knowledge into draft controls and remediation guidance. It does not determine compliance, provide legal advice, or change an IT or operational-technology system. This demonstration uses local public sources and fictional scope information.

Briefly add: “I used Codex to learn Python, implement small milestones, and generate tests. I reviewed the results and simplified the interface through repeated testing.”

**Technical intention:** Establish the system's hard limits before showing automation. The local-first boundary is part of the design, not a disclaimer added after the fact.

### 0:25–0:55 — Explain the agent architecture

**On screen:** Show `assets/cip-wayfinder-agent-communication.svg`.

**Say:**

> The architecture uses narrow specialist roles rather than one agent doing everything. They are deterministic Python functions and LangGraph nodes, not six paid model calls. The roles validate scope, retrieve cited requirements, draft controls, analyze synthetic evidence, explain risk, propose remediation, and pause for a human decision. Supporting Applicability and Quality Reviewer components ask for missing scope and check traceability.

Use v4's updated diagram. Point out the Review Package Agent in the product path. The product Quality Reviewer is not a node in the synthetic graph. Do not describe each roster role as a separate LLM call.

**Technical intention:** Show separation of responsibilities, typed handoffs, and least-authority design. Each role receives only the information needed for its task.

### 0:55–1:35 — Demonstrate intake and the Applicability Agent

**On screen:** In **Start a review**, choose:

- Functional Entity: `Transmission Operator`
- Regional Entity: initially leave blank
- Point out the fixed product statement: `Prepare a source-grounded draft package for SME tailoring.` No objective selection is required.
- Upload the authorized public PDF and check the authorization statement

Select **Analyze locally** once with the Regional Entity missing.

**Say:**

> I left the Regional Entity blank, so the Applicability Agent asks a direct question and stops instead of inventing an answer or deciding applicability.

Now choose `Midwest Reliability Organization (MRO)` in Regional Entity and select **Analyze locally** again. There is no required Asset Scope field in the current interface.

**Say:**

> With complete scope, the app validates the PDF and authorization, then uses searchable content—not just the filename—to identify NERC signals, document type, and referenced standard versions. The document remains in this browser session and is not sent to an external model.

**Technical intention:** The form batches the related inputs into one submission. Pydantic models validate the data, and Streamlit session state holds the temporary review context for this browser tab.

### 1:35–2:15 — Demonstrate source-grounded retrieval

**On screen:** Select **Open review package**. Point to the knowledge-item, corpus-match, and draft-control measures plus the detected document profile. Open **Requirements and sources**, then turn on one requirement such as **R1**. Show the plain-language synopsis, the official requirement text extracted from the bounded section-B block, and the page citation.

**Say:**

> The Requirement and Citation Agent is designed for grounding, not interpretation from memory. The parser recognizes every NERC standard family and builds knowledge from the uploaded PDF. It then checks the standard and requirement ID against an approved local SQLite corpus opened read-only. It preserves page and standard context for verification.

> If the corpus has no match, the app displays the bounded requirement block and its plain-language summary extracted locally from the content-validated upload. PDF line wrapping may differ from the published layout, so the citation remains available for verification.

**Technical intention:** Retrieval is version-scoped and citation metadata travels with the knowledge item. Derived package data uses a bounded cache of at most 32 entries; a changed document profile, corpus revision, or cache-policy version produces a different cache key.

### 2:15–2:55 — Demonstrate control drafting and remediation

**On screen:** Collapse the source section and open **Draft controls and remediation**. Show one requirement card, its objective, owner, frequency, evidence expectation, tailoring question, remediation table, and traceability line.

**Say:**

> The Control Drafting Agent turns the retrieved mapping into an objective, owner, frequency, evidence expectation, and tailoring question. Every result remains draft guidance linked to its requirement ID.

> The Review Package Agent then assembles those grounded items into one strict package for SME tailoring. It preserves the document profile and citations, flags missing approved-corpus support, and cannot approve, render, email, or change operational systems.

> Remediation describes possible next steps; it does not create a ticket, close a finding, or implement a control. An SME must tailor it.

**Technical intention:** Strict Pydantic contracts prevent undeclared fields, and traceability identifiers connect the control and remediation records to their source requirement.

### 2:55–3:25 — Explain the evidence and risk agents honestly

**On screen:** Return briefly to the agent communication diagram and point to **Evidence Insight Agent**, **Risk and Remediation Agent**, and **Quality Reviewer**.

**Say:**

> The fuller LangGraph path demonstrates the next product stage with synthetic data. The Evidence Insight Agent extracts allowlisted facts, ignores embedded instructions, and compares a simulated baseline. The Risk and Remediation Agent turns those facts into an explainable potential finding, a demo risk rating, and a draft plan.

> These steps are verified in the graph and tests; the Streamlit page does not ingest live evidence or telemetry. The separately tested Quality Reviewer rejects broken traceability, but it is not a compliance judge.

**Technical intention:** Treat documents as untrusted data, keep analysis explainable, and avoid overstating what the current live interface executes.

### 3:25–4:15 — Demonstrate human control, download, and email

**On screen:** Open **Human decision**. First select **Needs editing**, enter `CIP compliance manager` as the reviewer role, add a short rationale, and apply the decision.

**Say:**

> A human decision is required before a deliverable exists. Returning it for editing creates no attachment and sends nothing.

Now select **Approve package**, enter a fresh rationale, and apply the decision. Show **Download approved Word package** and the separate email form.

Download and briefly open the Word result on screen. Do not send email during the submission demo; explain the second approval without making an external call. SMTP is configurable, not tied to Resend.

**Say:**

> Approval creates the Word package locally in memory; it is not compliance approval and sends no email. Download is immediate. Email is a second action with recipient validation, an attachment preview, and separate authorization before SMTP is called.

> If the package context changes, delivery is blocked until a new decision. After email delivery, only a masked session receipt remains.

**Technical intention:** The UI has two distinct gates: package approval and email-send authorization. Credentials remain in the ignored local `.env` file and are never placed in the package or repository.

### 4:15–4:45 — Demonstrate LangGraph recovery and interruption

**On screen:** In the terminal, run:

```powershell
uv run python -m nerc_compliance_intelligence.review_graph
uv run pytest tests/test_review_graph.py -q
```

**Say:**

> LangGraph carries typed state and a thread ID through an in-memory checkpointer. Empty requirement retrieval gets one deterministic repair, tool errors get at most two retries, and unresolved problems stop safely. A real interrupt pauses for the human: edit returns to approval, reject exports nothing, and only approve reaches the synthetic local workflow store.

Clarify: graph state is a TypedDict with Pydantic-validated records at boundaries. Graph tests include an actual approved synthetic export. They do not mean the Streamlit page executes every graph node.

**Technical intention:** Demonstrate conditional routing, bounded loops, checkpointed resume, and a human interrupt before the only write-classified graph tool.

### 4:45–5:00 — Show evaluation evidence and close

Keep the recording below five minutes. Mention that Codex helped implement small milestones, explain Python, and generate tests; human review and repeated local tests guided revisions. Do not substitute the Excel-evaluation tutorial for this live application demo.

**On screen:** Run:

```powershell
uv run python -m nerc_compliance_intelligence.evaluations
```

Point to the 15 passing evaluations.

Mention the final 2026-09-16 run: 167 tests and 15 offline evaluations passed. LangSmith is a disabled preview, not evidence of a live trace. These results do not measure real-model answer quality. Check `docs/submission-links.md` before filling the submission form.

**Say:**

> Fifteen offline evaluations verify retrieval, draft labeling, evidence safety, risk logic, bounded recovery, interruption, checkpoint resume, and guarded export. CIP Wayfinder shows that agentic compliance support can be useful, traceable, and human-controlled without replacing an SME.

## Agent intention reference

Use this table if the reviewer asks for more technical detail after the timed demo.

| Role | Main intention | Current proof | Explicit boundary |
|---|---|---|---|
| Applicability Agent | Collect complete scope by asking direct questions | Missing-field behavior in the Streamlit intake and contract tests | Does not determine applicability |
| Intake and Scope Agent | Validate the minimum graph state before tools run | `intake_agent` and missing-scope route tests | Missing scope goes directly to safe stop |
| Requirement and Citation Agent | Retrieve only the selected standard/version and preserve provenance | Read-only local corpus in the UI; `requirement_agent` and Standards Agent contract tests | Does not rely on unstated model knowledge |
| Control Drafting Agent | Turn a retrieved requirement into traceable draft control language | Draft-control package in the UI and `control_agent` tests | Does not label the control compliant |
| Review Package Agent | Assemble validated knowledge, mappings, controls, remediation, and sources for SME tailoring | Fixed objective and typed package visible in the UI; dedicated contract tests | Cannot retrieve, rewrite, approve, render, email, or act operationally |
| Evidence Insight Agent | Extract allowed facts and identify incomplete or conflicting synthetic evidence | `evidence_agent`, `baseline_agent`, `insight_agent`, and evidence tests | Does not obey instructions found inside evidence text |
| Risk and Remediation Agent | Explain potential gaps and create an ordered draft response plan | `risk_agent`, `remediation_agent`, and deterministic evaluations | No automatic finding closure or operational action |
| Human Handoff and Workflow Agent | Pause for approve, edit, or reject and guard the write boundary | LangGraph interrupt, checkpoint, and branch tests | Only explicit approval reaches synthetic export |
| Quality Reviewer | Validate traceability and links in a prepared package | Runs after package assembly in the Streamlit path; separate `quality_review.py` contract tests | Structural review only; not a compliance decision |

## Statements to avoid

Do not say that the app:

- determines or certifies NERC compliance;
- decides whether a standard applies to a real entity;
- currently analyzes live evidence, Beacon data, IT assets, or OT assets;
- sends the uploaded PDF to a model or to Resend;
- runs every LangGraph agent behind the visible Streamlit package page;
- automatically creates a production remediation workflow;
- uses the Quality Reviewer as a compliance authority;
- requires a model call to produce the Word package.

Instead, describe every control, finding, risk, and remediation item as **draft guidance for authorized SME review and tailoring**.
