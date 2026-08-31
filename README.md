# CIP Wayfinder

**CIP Wayfinder** helps utility teams explore a source-grounded starting point for Low-to-Medium Impact CIP readiness without using confidential evidence, live asset data, or production systems.

## Final review guide

Start here for product review and local use:

- [Architecture](docs/architecture.md), [agent framework](docs/agent-framework.md), and [project brief](docs/project-brief.md)
- [Agent communication diagram](assets/cip-wayfinder-agent-communication.svg), showing the six-agent handoffs and validation loop
- [Data notes](docs/data-notes.md), [prompt/model-behavior log](docs/prompt-log.md), and [limitations](docs/limitations.md)
- [Offline evaluation report](docs/evaluation-report.md), [sample approved case](docs/sample-approved-case.md), [submission outline](docs/submission-outline.md), and [under-five-minute demo script](docs/demo-script.md)
- [Week 3 assignment alignment check](docs/assignment-alignment-check.md), including completion evidence and remaining delivery items
- [ElevenLabs video production brief](docs/elevenlabs-video-production-brief.md) for an optional synthetic-data-only narrated video

The MVP is local-first and fake-provider-first. It does not declare NERC compliance, provide legal advice, use confidential or live IT/OT data, or make operational changes. Every generated control and remediation plan is a draft requiring organization-specific SME review.

## Visual theme

The local Streamlit page uses a SigmaFlow-inspired light theme in [`.streamlit/config.toml`](.streamlit/config.toml): dark blue text, blue primary actions, green success accents, and accessible blue/violet/green badge tints. It is a local visual adaptation based on SigmaFlow’s public logo treatment, not an official or endorsed brand configuration.

The selected local app name is **CIP Wayfinder**, with a compass/waypoint logo asset at [`assets/cip-wayfinder-logo.png`](assets/cip-wayfinder-logo.png). A single 120px version appears at the top left of the main page beside the app name, and the same asset is used for the browser tab icon. The landing page uses text-and-badge safety cues, rather than repeating the logo, followed by three color-coded review waypoints. An optional native Streamlit status tour animates the four review steps only when the learner presses Play. The page subtitle preserves the learning-only, draft-guidance boundary. The name and logo are project concepts only and need separate trademark and brand review before any public use.

At the top of every app view, a short description explains that CIP Wayfinder reviews one approved local NERC CIP standard at a time and organizes cited sources into draft materials for human review.

## Hybrid upload-and-chat interface

The Streamlit app now places the authorized public-PDF upload first. Its optional **How this local review works** expander contains a generated four-step infographic and a short guided tour, so the explanation is available without blocking the first task. It supports only one CIP-010-5 or CIP-007-6 document at a time, validates it locally, and keeps it in browser-session memory. After upload, the **Start a review** workspace offers four plain-language chat choices. The **Review package** workspace organizes the source, draft controls, fictional evidence/baseline examples, findings/remediation, traceability, and human decision into expandable sections instead of nine tabs.

The supplied public CIP PDFs are approved local source documents. The upload path matches their standard/version and extracted requirement labels against the approved local SQLite index in **read-only** mode. When a matching chunk is found, the Review package shows a short local source excerpt with standard/version, page, section, source URL, and retrieval-date provenance. Evidence and asset examples remain intentionally fictional for safety. The result is a source-grounded draft demonstration, not a real operational assessment or compliance conclusion.

The Review package has no requirement-picker. It generates one draft control and one ordered draft remediation plan for every requirement label extracted from the uploaded standard, then displays all of them with their individual requirement IDs. Each matching local-source requirement now appears with citation metadata; every draft still needs organization-specific SME tailoring.

## Demonstration flow

The local Streamlit demonstration makes the review workflow visible without calling a paid model or an external service:

1. **Case intake** — The analyst supplies Functional Entity, jurisdiction, asset scope, and review objective. The existing Applicability Agent asks direct questions for missing scope; it does not guess or decide applicability.
2. **Source-grounded package** — The uploaded CIP standard/version and requirement labels are matched against the approved local corpus index in read-only mode. Matching chunks show short, cited local excerpts.
3. **Graph progress** — The Review package shows requirement/source/control counts and has an optional animation of the tested graph path: intake, retrieval, drafting, synthetic evidence/baseline, findings/remediation, and the human approval interrupt.
4. **Human decision** — The in-memory preview now requires a selected decision, reviewer role, and rationale. It explains the safe outcome for edit, reject, or approve, but cannot create an export.

Every landing-page field has built-in hover help. The tooltips explain what the analyst should provide, include a fictional example where useful, and restate the no-confidential-data boundary for asset scope and document upload.

For the actual checkpoint/resume, bounded retries, validation repair, interrupt, and guarded approved-only export demonstration, use the existing LangGraph tests and the demo script. No GitHub publication, external tracing, model call, or operational write is part of the local UI flow.

The app does not send an uploaded PDF to a provider or external service, show raw source text, persist the upload, accept confidential evidence, read live assets, or bypass human approval for export.

## Intake reference options and future model drafting

The landing page has a bundled, offline catalog of Functional Entity and Regional Entity choices collected once from public NERC material on 2026-08-31. It does not browse NERC at runtime and the options do not determine applicability. Asset scope and review objective choices are safe local suggestions because NERC does not publish a universal list for those organization-specific fields; each dropdown also permits a typed value.

The source-grounded control-drafting seam accepts exactly one retrieved requirement mapping and sends only that record's standard/version, requirement ID, source metadata, and retrieved excerpt to a structured provider. The fake provider remains the default. The Nebius adapter supports AI Studio's guided JSON and Token Factory's documented JSON-schema response format, but is not connected to the UI or graph: before a paid call, the user must select an account-available model and explicitly approve the exact bounded request. A small connectivity smoke check is capped at 700 output tokens; a full control-plus-remediation schema is capped at 2,000 completion tokens, including Token Factory reasoning tokens, with low reasoning effort requested.

When a matched approved-local requirement is available, the Review package provides a **Review and send a source-grounded draft** expander. It uses the locally validated `moonshotai/Kimi-K3` model and previews one requirement's standard/version, citation locator, excerpt-character count, model, completion limit, and retry boundary. The analyst must check a plain-language approval statement and press the send button before the app reads the ignored local `.env` file and calls Token Factory. A validated draft remains in browser-session memory only; it is not persisted, exported, or treated as a compliance decision.

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

`src/nerc_compliance_intelligence/local_corpus.py` ingests only explicitly supplied local JSON corpus files into a local SQLite index. It preserves provenance metadata and is idempotent. The current two-chunk corpus is a synthetic test fixture because no approved local NERC corpus was present in the repository.

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

The Streamlit page now uses two safe local workspaces: **Start a review** and **Review package**. The optional click-triggered tour explains upload, choice, review, and human decision before intake. The review package uses expandable sections for source, controls, evidence/baseline, findings/remediation, traceability, and an approve/edit/reject preview. The preview is in memory only and cannot save, export, or create a workflow.

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
