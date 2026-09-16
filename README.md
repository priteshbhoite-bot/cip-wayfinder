# CIP Wayfinder

**CIP Wayfinder** helps utility teams understand authorized NERC standards-related PDFs and turn source-grounded knowledge into draft control and remediation starting points without using confidential evidence, live asset data, or production systems.

## Final review guide

Requirement summaries retain complete Key parts paragraphs, without character-limit ellipses. After updating from an older version, upload the PDF again to rebuild any shortened session data.

Review package source text wraps to the available width. Remediation steps appear as full-text Action, Owner, Decision, and End state fields instead of clipped table cells; expand a requirement or control to read its details.

The [v4 connected system architecture](assets/cip-wayfinder-system-v4.svg) shows the current product workflow and a separate synthetic LangGraph panel. It supersedes the older combined-flow diagram for submission use.

For the v4 document refresh, see the [updated demo script](docs/demo-script.md) and [submission link verification](docs/submission-links.md). The existing Drive video is accessible, but its duration and alignment with the current app still need review.

Latest verified submission status: [final readiness check](docs/final-readiness-check.md). The 2026-09-16 check passed 167 tests and 15 offline evaluations. Submission still requires the final Google Doc, live app-demo video, current GitHub code, and submission form. The Excel walkthrough is not the required live app demo.

Start here for product review and local use:

- [Architecture](docs/architecture.md), [agent framework](docs/agent-framework.md), and [project brief](docs/project-brief.md)
- [Agent communication diagram](assets/cip-wayfinder-agent-communication.svg), showing the six-agent handoffs and validation loop
- [Review and delivery flow](assets/cip-wayfinder-review-delivery-flow.svg), showing package approval followed by direct download or separately authorized email
- [Data notes](docs/data-notes.md), [prompt/model-behavior log](docs/prompt-log.md), and [limitations](docs/limitations.md)
- [Offline evaluation report](docs/evaluation-report.md), [sample approved case](docs/sample-approved-case.md), [submission outline](docs/submission-outline.md), and [under-five-minute demo script](docs/demo-script.md)
- [Week 3 assignment alignment check](docs/assignment-alignment-check.md), including completion evidence and remaining delivery items
- [ElevenLabs video production brief](docs/elevenlabs-video-production-brief.md) for an optional synthetic-data-only narrated video

The MVP is local-first and fake-provider-first. It does not declare NERC compliance, provide legal advice, use confidential or live IT/OT data, or make operational changes. Every generated control and remediation plan is a draft requiring organization-specific SME review.

## Visual theme

The local Streamlit page uses a SigmaFlow-inspired light theme in [`.streamlit/config.toml`](.streamlit/config.toml): dark blue text, blue primary actions, green success accents, and accessible blue/violet/green badge tints. It is a local visual adaptation based on SigmaFlow’s public logo treatment, not an official or endorsed brand configuration.

The selected local app name is **CIP Wayfinder**, with a compass/waypoint logo asset at [`assets/cip-wayfinder-logo.png`](assets/cip-wayfinder-logo.png). A single 120px version appears at the top left of the main page beside the app name, and the same asset is used for the browser tab icon. The landing page uses text-and-badge safety cues, rather than repeating the logo, followed by three color-coded review waypoints. An optional native Streamlit status tour animates the four review steps only when the learner presses Play. The page subtitle preserves the learning-only, draft-guidance boundary. The name and logo are project concepts only and need separate trademark and brand review before any public use.

At the top of every app view, a short description explains that CIP Wayfinder reviews one authorized NERC standards-related PDF at a time, builds a local document profile, and organizes source-grounded knowledge into draft materials for human review.

## Hybrid upload-and-chat interface

The Streamlit app places the authorized public-PDF upload first. Its optional **How this local review works** expander contains a generated four-step infographic and a short guided tour, so the explanation is available without blocking the first task. It accepts one searchable PDF at a time and requires the user to attest that it is an authorized public document published or shared by NERC. Content validation requires a recognized NERC standard reference plus multiple NERC identity signals; a filename by itself is never sufficient. The document remains in browser-session memory. The **Review package** workspace keeps the existing layout for source knowledge, draft controls and remediation, and approval-gated Word delivery through direct download or optional email.

The local parser recognizes the NERC BAL, CIP, COM, EOP, FAC, INT, IRO, MOD, NUC, PER, PRC, TOP, TPL, and VAR families, including decimal or letter versions and regional suffixes. It classifies common standards-related materials, discovers every referenced standard version, extracts requirement labels when present, and otherwise creates one knowledge topic per referenced standard. Multi-standard documents keep repeated labels such as `R1` distinct by prefixing the relevant standard. Unicode dash variants from PDF extraction are normalized before matching.

The upload path first attempts to match each standard/version and requirement label against the approved local SQLite index in **read-only** mode. A corpus match uses its preserved provenance. Each requirement displays both a plain-language synopsis and the official requirement block extracted from section B; the extracted layout may differ from the published PDF. When no corpus entry exists, the app uses the bounded requirement block retained from the content-validated upload. Content-based identity checks are a local safety gate, not cryptographic proof of publication authenticity.

The Review package has no requirement-picker. It generates one draft control and one ordered draft remediation plan for each extracted requirement or document knowledge item, then displays all items with their source locator and standard context. Supporting guidance is explicitly identified as non-binding material; every output still needs organization-specific SME tailoring.

## Demonstration flow

The local Streamlit application keeps the workflow focused: upload and scope one public NERC standards-related document, review extracted knowledge and draft controls, then make a human export decision. Assignment diagnostics, graph-animation controls, and optional external-model enhancement are not shown as product features.

The local Streamlit application makes the review workflow visible without requiring an external model call:

1. **Case intake** — The analyst supplies one or more Functional Entity, Regional Entity, and asset-scope choices. The existing Applicability Agent asks direct questions for missing scope; it does not guess or decide applicability. The product objective is fixed: prepare a source-grounded draft package for SME tailoring.
2. **Source-grounded package** — The uploaded PDF is content-validated, classified, and converted into a typed profile of its title, document type, referenced standards, requirement labels, bounded source blocks, page locations, and plain-language summaries. Approved local corpus matches take precedence; otherwise the content-validated uploaded requirement block supplies the local source text.
3. **Human decision and deliverable** — The reviewer chooses Approve package, Needs editing, or Reject and supplies a role and rationale. Approval prepares an in-memory Word package containing the review scope, requirements and sources, draft controls, and remediation. The approved package can be downloaded directly. A separate form requires the recipient, destination preview, and explicit send authorization before SMTP is called.

Every landing-page field has built-in hover help. The tooltips explain what the analyst should provide and restate the no-confidential-data boundary for document upload and organization-specific scope values.

For the actual checkpoint/resume, bounded retries, validation repair, interrupt, and guarded approved-only export demonstration, use the existing LangGraph tests and the demo script. No GitHub publication, external tracing, model request, or operational write is part of the local UI flow. SMTP remains a separate, explicitly approved external action.

The app does not send an uploaded PDF to a provider or external service, persist the upload, accept confidential evidence, read live assets, or bypass human approval for export. Content-validated public source summaries and approved-corpus excerpts are visible to the reviewer and can be included in the explicitly approved local Word package.

## Intake reference options and provider learning code

The landing page has a bundled, offline catalog of Functional Entity and Regional Entity choices collected once from public NERC material on 2026-08-31. It does not browse NERC at runtime and the options do not determine applicability. Both fields use straightforward multi-select dropdowns and accept multiple selections or typed values because a utility can have more than one relevant role or region. Asset-specific tailoring is intentionally deferred to the generated control questions rather than collected as a required intake field.

The deterministic **Review Package Agent** receives only validated document knowledge, source mappings, draft controls, remediation plans, and any approved local-corpus matches. It preserves those objects in a strict typed package, flags items without an approved corpus match for source verification, and passes the package to quality review and human approval. It cannot retrieve new material, rewrite grounded content, approve, render, email, or take an operational action.

The repository retains a source-grounded structured-provider seam as learning and test code. It accepts exactly one retrieved requirement mapping and constructs a bounded request containing only that record's standard/version, requirement ID, source metadata, and retrieved excerpt. The fake provider remains the default for tests. This seam is not connected to the Streamlit Review package, so normal product use makes no Token Factory call and needs no model credential.

## Milestone 1: Python foundation

`learning/lesson_01_case.py` is a beginner exercise. It introduces variables, strings, lists, dictionaries, functions, imports, and the main guard using a fictional Northstar Grid Services case.

Run the exercise after the local environment is installed:

```powershell
uv run python learning/lesson_01_case.py
```

Run the tests:

```powershell
uv run pytest
```

The exercise uses simple Python dictionaries rather than Pydantic because this lesson is intentionally introducing basic built-in data types first. Later milestones will use Pydantic for structured application and graph state.

## Milestone 2: local application shell

The application package lives in `src/nerc_compliance_intelligence/`. It contains:

- `config.py`: a small Pydantic settings model that reads only non-secret display configuration.
- `app.py`: a minimal Streamlit page that confirms fake providers, local-only data, and disabled operational writes.
- `app.py` at the repository root: the Streamlit entry point.

Start the local page from the repository root:

```powershell
uv run streamlit run app.py
```

The initial page has no model calls, retrieval calls, SQLite database, or workflow writes. It is intentionally a safe visual starting point.

## Milestone 3: typed data models

`src/nerc_compliance_intelligence/schemas.py` defines the synthetic, typed records for the future agent state. `learning/milestone_03_examples.py` contains valid and deliberately invalid examples. No model, UI, tool, database, or workflow behavior was added in this milestone.

Run the schema tests:

```powershell
uv run pytest tests/test_schemas.py
```

## Milestone 4: deterministic fake tools

`src/nerc_compliance_intelligence/fake_tools.py` contains the nine tools from the project brief. Each has typed input/output models, a read/write classification, and success/empty/error fixtures. The only write-capable tool exports an approved synthetic workflow JSON file below `outputs/workflows/`; it rejects every non-approved decision.

Run the tool tests:

```powershell
uv run pytest tests/test_fake_tools.py
```

## Milestone 6: checkpointed fake graph

`docs/architecture.md` explains the local review graph. `src/nerc_compliance_intelligence/review_graph.py` implements that graph with fake agents, fake tools, an in-memory LangGraph checkpointer, a `thread_id`, bounded retries/repair, and a human interrupt before approved local export.

Run the graph tests and print its compact summary:

```powershell
uv run pytest tests/test_review_graph.py
uv run python -m nerc_compliance_intelligence.review_graph
```

## Milestone 7: local corpus ingestion

`src/nerc_compliance_intelligence/local_corpus.py` ingests only explicitly supplied local corpus files into a local SQLite index. The test suite retains a two-chunk synthetic JSON fixture, while `data/corpus_manifests/approved_cip_manifest.json` allowlists the 24 distinct approved CIP standard-version PDFs currently supplied in `../approved-nerc-corpus`. The shared parser creates one searchable source block per top-level requirement strictly within section B, stopping before measures and section C. The current corpus contains 84 bounded requirement chunks with provenance and idempotent content hashes; the adapter never ingests unlisted files or follows source URLs.

Build or refresh the local approved CIP index:

```powershell
uv run python learning/ingest_approved_corpus.py
```

The generated `data/approved_nerc_corpus.sqlite` remains ignored by Git. In this MVP, “RAG tokens” means locally extracted, metadata-rich retrieval chunks; no embedding API or external tokenizer is called.

Run the corpus tests:

```powershell
uv run pytest tests/test_local_corpus.py
```

## Milestone 8: strict fake-agent contracts

`src/nerc_compliance_intelligence/agent_contracts.py` adds Standards and Applicability Agent prompts, strict schemas, and fake-model defaults. The Standards Agent rejects claims not backed by retrieved chunks; the Applicability Agent asks for missing scope rather than guessing.

## Milestone 9: fake-first model providers

`src/nerc_compliance_intelligence/providers.py` adds structured provider contracts, fake defaults, environment-variable settings, timeouts, and a maximum of two retries. It also includes a Nebius AI Studio OpenAI-compatible structured-output adapter, but the adapter is not connected to the UI or graph. A future paid smoke test must first display `build_live_smoke_preview()` and receive explicit approval.

## Milestone 10: traceable draft controls and remediation

`src/nerc_compliance_intelligence/control_remediation.py` creates deterministic draft controls and ordered remediation steps from already retrieved requirement IDs. Each text-bearing field carries its supporting `requirement_ids`, and validation rejects an ID not present in local retrieval. It creates no workflow and does not bypass the graph's existing human-approval interrupt.

Run the contract and validation tests:

```powershell
uv run pytest tests/test_control_remediation.py
```

## Milestone 11: safe synthetic evidence analysis

`src/nerc_compliance_intelligence/evidence_analysis.py` extracts an allowlist of observable facts from synthetic evidence text. It ignores embedded instruction-like text and returns draft support signals, missing fields, age, inconsistencies, confidence, and SME questions. The three fixtures cover strong, incomplete, and unrelated evidence.

```powershell
uv run pytest tests/test_evidence_analysis.py
```

## Milestone 12: synthetic baseline analysis

`data/synthetic_assets/` holds tiny expected CSV and observed JSON snapshots. `src/nerc_compliance_intelligence/baseline_analysis.py` compares the allowed asset fields and creates one control-linked, draft review observation for no change, approved change, unexplained change, stale data, or a missing asset.

```powershell
uv run pytest tests/test_baseline_analysis.py
```

## Milestone 13A: local quality review

`src/nerc_compliance_intelligence/quality_review.py` validates a local package before handoff: requirement traceability plus control links from remediation and baseline observations. It returns concise errors/warnings and never exposes source text, prompts, secrets, or stack traces.

```powershell
uv run pytest tests/test_quality_review.py
```

## Milestone 13B: approved local case persistence

`src/nerc_compliance_intelligence/case_persistence.py` saves and resumes typed synthetic cases with their LangGraph `thread_id` in local SQLite. Each save requires an explicit local-save approval and reviewer role; reads never create a database. The local SQLite file is ignored by Git.

```powershell
uv run pytest tests/test_case_persistence.py
```

## Milestone 13C: local review screens

The Streamlit page uses two safe local workspaces: **Start a review** and **Review package**. The optional click-triggered tour explains upload, review, and human decision before intake. The review package uses expandable sections for cited sources, draft controls/remediation, and an approve/edit/reject decision. Approval creates a genuine `.docx` in memory for direct download or optional email delivery; it does not save a case, create a workflow, declare compliance, or write to an operational system.

## Approval-gated Word download and email delivery

Package approval has one narrow meaning: **the reviewer authorizes creation of a draft-review document from the exact content they reviewed**. The user can download that approved document directly. Downloading does not send a message. The separate email form shows the recipient, attachment name and size, and standard; the user must explicitly authorize that external send.

The Word package contains:

- review scope and the fixed Review Package Agent objective;
- requirement identifiers and approved-local source excerpts with provenance;
- draft control objectives, activities, owners, frequency, procedures, evidence expectations, testing, assumptions, and tailoring questions;
- ordered remediation actions, decisions, owners, and expected end states;
- reviewer role, rationale, timestamp, and safety boundaries.

Choosing **Needs editing** or **Reject** creates no document. If the underlying package or intake changes after approval, both download and email delivery are blocked until the reviewer makes a new decision. Tests use an injected fake transport and never send real email.

Configure SMTP only in the ignored `.env` file (or deployment environment): `NCI_SMTP_HOST`, `NCI_SMTP_PORT`, `NCI_SMTP_USERNAME`, `NCI_SMTP_PASSWORD`, and `NCI_SMTP_FROM_ADDRESS`. Optional values are `NCI_SMTP_USE_STARTTLS` and `NCI_SMTP_TIMEOUT_SECONDS`. Never commit credentials.

```powershell
uv run streamlit run app.py
uv run pytest tests/test_dashboard.py
```

## Milestone 13D: offline evaluations and tracing preview

`src/nerc_compliance_intelligence/evaluations.py` runs 15 deterministic, offline checks and prints a Markdown results table. `src/nerc_compliance_intelligence/tracing.py` provides an optional LangSmith configuration preview without reading a credential, initializing a client, or making a network call.

```powershell
uv run python -m nerc_compliance_intelligence.evaluations
uv run pytest tests/test_evaluations.py
```

## Dynamic NERC document knowledge and local drafting

The ingestion layer is offline and deterministic. It dynamically creates a typed knowledge profile from the searchable uploaded PDF rather than relying on a fixed standards allowlist or filename. For known approved-corpus requirement areas, the drafter creates more specific activities, owners, timing, retained records, escalation, and remediation. For newly encountered standards or supporting documents, it creates conservative generic drafts from the locally extracted knowledge item and page locator. Every draft remains source-cited, organization-tailored guidance—not a compliance determination.

## MVP caching policy

CIP Wayfinder uses two intentionally different caching layers:

1. The approved local NERC SQLite corpus is the persistent source layer. It is opened read-only by the Streamlit review screen and is not a model-response cache.
2. Public-source-derived review packages use a bounded Streamlit data cache (maximum 32 entries). The key changes when the uploaded public document hash, document profile, referenced standards, extracted knowledge items, local corpus file revision, or cache-policy version changes.
Raw uploaded PDF bytes, credentials, approval state, confidential evidence, and operational data are never placed in the shared cache. Semantic or approximate matching is intentionally excluded from this MVP because a similar-looking compliance question may require a different answer. LangGraph checkpoints are workflow state, not a substitute for these caches.

Caching is intentionally transparent in the product UI. Automated tests verify package-key invalidation.
