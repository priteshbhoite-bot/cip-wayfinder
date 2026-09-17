# Decision Log

## 2026-09-17 — SME draft revision workflow

- Turn Needs editing into a session-only revision workflow: select requirement and existing draft field, explain the change, save, then finish editing and review before fresh approval.
- Allow only existing control/remediation text fields. Preserve official source wording, IDs, citations, metadata, draft flags and step ordering; validate the resulting package and rerun quality review.
- Keep before/after text and feedback in the private session, never the shared generated-data cache. Clear edits when the upload or scope changes; this is not durable case storage.
- Block delivery while editing. Invalidate old attachments and email consent; bind new approval to the complete revised package and intake.
- Retain the separate synthetic LangGraph edit branch unchanged. No model call, external write or GitHub publication is part of this change.

## 2026-09-17 — Connect the supplied requirement-date reference

- Extract only tables with named Effective Date of Requirement and Effective Date of Part columns from the supplied 121-page CIP reference export. Require all 596 declared row IDs exactly once; fail on unknown date syntax or malformed headers.
- Preserve requirement/part dates, inactive dates, statuses, source notes, page/row citations, U.S. scope, and source fingerprint. Do not use regulatory-order, filing, adoption, or retrieval dates as effective dates.
- Match schedules by exact standard/version to the 24 approved catalog entries, then attach them only to matching uploaded bytes. Do not substitute neighboring versions.
- Show one date only when the listed dates agree and are complete. Expose phased dates, missing dates, and DO NOT USE annotations explicitly. Regional Entity selection does not convert U.S. dates into another jurisdiction's applicability.
- Package metadata for cloud use without publishing the source PDF. Bump session/cache policy; no runtime network call, deployment, or GitHub publication.

## 2026-09-17 — Standard effective date summary card

- Replace the removed Corpus matches position with Standard effective date between the two existing counts.
- Carry optional reviewed date, jurisdiction, and source reference from the exact fingerprint-matched catalog record. Show Not verified when absent; never substitute a retrieval, publication, or approval date.
- Current catalog dates remain unpopulated pending source verification. Bump session/cache metadata version. This does not determine applicability or effective dates from Regional Entity selection.

## 2026-09-17 — Remove the Corpus matches display

- Remove the local retrieval counter from Review package and use two summary columns for Knowledge items and Draft controls.
- Keep retrieval, catalog verification, citations, and approval behavior unchanged. Verify rendered metric labels with the offline Streamlit test.

## 2026-09-17 — Portable CIP source verification

- Package SHA-256 fingerprints and official source URLs for all 24 PDFs already approved in the local manifest, covering CIP-002 through CIP-015. Do not publish PDF contents or the local database.
- Preserve exact standard/version and source URL when a fingerprint matches; reject content/catalog identity mismatch. Content-marker validation remains a separate, weaker path, never described as fingerprint verification.
- Direct retrieval of the 24 explicit official URLs was rejected by the remote server. Record the approval basis as the existing approved corpus, not fresh remote verification. Do not infer current enforcement or jurisdictional applicability.
- Unknown or altered low-signal uploads receive a source-verification instruction. New approvals require deliberate catalog maintenance, not user-controlled URLs or filenames.
- Bump the session/cache policy to regenerate source metadata. No model calls, email, operational writes, deployment, or GitHub publication are part of this change.

## 2026-09-16 — Preserve complete Key parts wording

- Remove 220-character part clipping and the 1,500-character overall requirement-summary clipping. Extraction remains bounded to the same requirement source block.
- Invalidate older dashboard/session data so re-uploading regenerates complete wording; source citations and human approval remain unchanged.
- Add a regression covering long nested parts and preservation of the final part.

## 2026-09-16 — Readable Review package text

- Replace non-wrapping requirement code blocks with native literal, width-fitting text so uploaded content is not interpreted as HTML or Markdown.
- Replace the wide remediation table with ordered, labeled full-text fields. Keep source content, drafting logic, and approval boundaries unchanged.
- Verify long text and all remediation fields through offline Streamlit rendering regression tests.

## 2026-08-26 — Milestone 1 foundation

- Use a minimal Python project with pytest for automated checks.
- Start with a standalone beginner exercise before adding LangGraph, SQLite, Streamlit, Pydantic, or model integrations.
- Keep the case data fictional and validate blank asset IDs locally to demonstrate safe failure handling.

## 2026-08-27 — Milestone 2 local application shell

- Use Python 3.11+ with Streamlit and Pydantic for the local application shell.
- Configuration reads only a non-secret application name and environment; provider mode is fixed to fake and operational writes are fixed to disabled.
- Keep the first Streamlit page informational so it can be smoke-tested without model credentials, local NERC documents, or a database.

## 2026-08-27 — Milestone 3 typed data layer

- Define the future review state with Pydantic models before implementing graph nodes, tools, persistence, or UI behavior.
- Keep requirements, controls, evidence, baseline observations, and findings explicitly synthetic; reject non-synthetic evidence and baseline records.
- Require human-review and draft labels in the model shape so future work cannot accidentally represent a generated result as a compliance conclusion or finalized control.

## 2026-08-27 — Milestone 4 deterministic fake tools

- Implement the nine project-brief tools as local, deterministic functions with Pydantic input and output contracts.
- Use explicit success, empty-result, and simulated-error fixtures so the next graph milestone can test normal and failure paths without an API, document source, or live system.
- Permit the simulated workflow store to export only approved synthetic state below the repository `outputs/` directory; reject all other decisions and paths outside that safe directory.

## 2026-08-27 — Milestone 6 checkpointed fake graph

- Use LangGraph with `InMemorySaver` and an explicit `thread_id` to demonstrate local checkpointing and resumption through a human approval interrupt.
- Bound fake-tool retries to two retries after an initial failure, and bound validation repair to one attempt.
- Route missing scope, unrecoverable empty retrieval, repeated tool errors, invalid human decisions, and rejection to a terminal safe stop that never exports.
- Route edit decisions back to the approval interrupt and allow local export only on an approved synthetic decision.

## 2026-08-27 — Milestone 7 local corpus ingestion

- No approved local NERC corpus was available in the repository, so use a clearly labeled synthetic two-chunk fixture only for ingestion and retrieval tests.
- Ingest only explicitly supplied local JSON files into SQLite using a source ID and SHA-256 content hash for idempotency.
- Preserve standard, version, requirement, Functional Entity, jurisdiction, enforcement status, effective date, page/section, source URL, and retrieval date with every chunk; treat source URLs as metadata and never crawl them.

## 2026-08-27 — Milestone 8 strict fake-agent contracts

- Use strict Pydantic schemas and deterministic fake models as the default for Standards and Applicability Agents.
- Reject Standards Agent output unless every mapping and citation exactly matches a retrieved local chunk.
- Require the Applicability Agent to ask for Functional Entity, jurisdiction, standard/version, and asset scope when any are absent; it may not guess or decide applicability.

## 2026-08-27 — Milestone 9 fake-first providers

- Add a provider abstraction with a deterministic fake default and strict Pydantic output parsing.
- Read provider name, model name, timeout, and retry limit from environment variables, never credential values.
- Bound retries to two and block every live request until an exact smoke-test preview is shown and the user explicitly approves it.

## 2026-08-27 — Milestone 10 traceable draft controls and remediation

- Create deterministic, draft-only control and remediation content from requirement IDs already returned by retrieval; the drafter may not invent an ID.
- Attach one or more retrieved requirement IDs to every meaningful control, decision, and end-state text field, then validate the links independently.
- Keep remediation steps consecutively ordered and require an action, owner role, decision, and end state for each one; this milestone adds no write or approval-bypass behavior.

## 2026-08-27 — Milestone 11 safe synthetic evidence analysis

- Keep exactly three fictional evidence fixtures: strong, incomplete, and unrelated to the selected asset.
- Treat document text as untrusted data: extract only an explicit label allowlist and ignore instruction-like lines.
- Produce draft observations and SME questions, not a compliance decision, automated approval, external connection, or write.

## 2026-08-27 — Milestone 12 synthetic baseline analyst

- Store only tiny fictional expected CSV and observed JSON snapshots in the repository for five named baseline fields.
- Compare fields deterministically; an approved-change marker must be explicit and never implies an approved workflow or operational action.
- Convert each comparison into one bounded, control-linked draft observation with a status that still requires SME review.

## 2026-08-27 — Milestone 13A local package quality review

- Add a deterministic Quality Reviewer that checks local traceability and cross-artifact control links before human handoff.
- Return short structured validation codes instead of exposing artifacts, prompts, secrets, or stack traces.
- Keep warnings non-blocking for incomplete synthetic evidence; preserve human approval as the only route toward the existing local export.

## 2026-08-27 — Milestone 13B approved local case persistence

- Persist only typed synthetic case state and its local graph thread ID in an ignored SQLite file.
- Require explicit human confirmation and reviewer role for every local case save; this confirmation does not approve a workflow or a compliance conclusion.
- Make resume read-only and return a safe empty result for a missing case or database.

## 2026-08-28 — Milestone 13C local Streamlit review screens

- Present existing synthetic typed data in nine local review tabs, including traceability and a human-decision preview.
- Do not display raw evidence text, model prompts, secrets, stack traces, or confidential data.
- Keep approve/edit/reject as an in-memory UI preview; no persistence, export, workflow creation, or operational action is connected in this substep.

## 2026-08-28 — Milestone 13D offline evaluation and optional tracing preview

- Run fifteen deterministic evaluations locally and report safe Markdown results without stack traces, prompts, tokens, or source-document text.
- Keep LangSmith configuration as a non-secret preview only; do not read credential values, create a client, or send a trace.
- Require explicit approval before any future external tracing connection, after displaying its project, credential-variable name, and data scope.

## 2026-08-28 — Optional ElevenLabs video production brief

- Provide a copy-ready scene plan and narration for an optional educational video that uses only fictional and synthetic material.
- Do not transmit the brief, screenshots, or narration to ElevenLabs automatically; an external paid generation still requires an exact request preview and explicit approval.

## 2026-08-28 — Hybrid upload-and-chat interface

- Replace the static-first dashboard entry point with one authorized public PDF upload at a time for CIP-010-5 or CIP-007-6.
- Keep uploaded PDF bytes only in browser-session memory; validate file type, size, scope boundary, and user attestation locally before any analysis.
- Use deterministic chat-style analysis choices and connected detail tabs; do not expose raw source text, transmit the file, persist it, accept confidential evidence, or bypass export approval.

## 2026-08-29 — Guided two-workspace interface

- Replace the nine peer detail tabs with two clear workspaces: **Start a review** for the guided upload/chat flow and **Review package** for expandable draft-review sections.
- Add a user-triggered four-step Streamlit status tour that explains upload, analysis choice, review, and the human decision. It is a short local visual aid, not a provider call, external animation, or data write.
- Keep all detailed views available as progressive expanders so the reduced navigation does not remove traceability, human-decision preview, or demonstration material.

## 2026-08-30 — Upload-first landing refinement

- Put the authorized-public-standard upload ahead of all explanatory content on the landing screen. Keep the process explanation, generated local infographic, and click-triggered tour in an optional expander.
- Replace the user-facing provider label `fake` with `local deterministic demo` to explain behavior without implying the supplied public standard itself is fabricated.
- State explicitly that the present upload flow uses document structure and metadata only; it has not yet been wired to the separate approved-local-corpus text retrieval path. Continue to label evidence and asset snapshots as fictional examples.

## 2026-08-30 — Whole-standard draft package

- Remove the requirement selector from the Review package. Generate one independently traceable draft-control/remediation pair for every requirement label extracted from the uploaded standard.
- Display all controls, remediation plans, and traceability links together. The user does not need to select a requirement to see the complete draft plan.
- Preserve the document-structure-only boundary: a requirement label and page location are not a verified interpretation of source text, and every generated item remains a draft for SME tailoring.

## 2026-08-30 — Read-only approved-local-source retrieval in the UI

- Open the existing approved local corpus index only in SQLite read-only mode when building a review package; the Streamlit display path cannot create, update, or ingest source records.
- Match uploaded standard/version and extracted requirement label to a local chunk. Show a short excerpt only alongside standard/version, page, section, source URL, and retrieval-date provenance.
- Use the matched local requirement mapping to make each draft-control title and objective specific to its cited standard/version and requirement ID. Continue to prohibit compliance conclusions, live evidence, operational writes, and uncited material claims.

## 2026-08-30 — Intake, graph progress, and decision preview

- Add typed in-memory case intake for Functional Entity, jurisdiction, asset scope, and review objective. Reuse the strict Applicability Agent to ask for missing scope rather than guessing; no case is saved or workflow started from intake.
- Add an optional Streamlit status animation showing the tested graph path through the human approval interrupt. It is visual guidance only and cannot call the write-classified export tool.
- Add a four-measure review summary and require an explicit decision, reviewer role, and rationale for the in-memory human-decision preview. Edit, reject, and approve previews explain their safe graph outcome but never create an export.

## 2026-08-30 — Beginner landing-field help

- Add native Streamlit hover help to every landing-page field: Functional Entity, jurisdiction, asset scope, review objective, authorized public-standard PDF, and public-use attestation.
- Make each tooltip explain the expected input in plain language, offer fictional examples where useful, and repeat the no-confidential-data boundary where it matters.

## 2026-08-30 — SigmaFlow-inspired Streamlit theme

- Add a native Streamlit light-theme configuration rather than custom CSS. Use a dark-blue, blue, and green palette inspired by SigmaFlow’s public NERC-platform logo treatment.
- Treat the palette as a local visual adaptation, not an official or endorsed SigmaFlow brand configuration. Preserve readable text/background contrast and distinct warning/error colors.

## 2026-08-30 — CIP Wayfinder app identity

- The user selected `CIP Wayfinder` as the local app name. Use it as the default configuration value, browser-page title, and visible Streamlit title.
- Display the existing compass/waypoint, grid-node, and forward-path mark once as a 120px main-page header logo and use the same asset as the browser-page icon. Do not repeat the mark in Streamlit app chrome or the landing content; use text-and-badge safety cues there instead. Keep the navy/blue/green local visual palette.
- Place a two-sentence plain-language description directly below the app name so a first-time user understands the one-standard-at-a-time, source-grounded draft-review purpose before seeing upload instructions.
- Do not represent the name or logo as trademark-cleared, affiliated with SigmaFlow, or an authoritative compliance product. Keep the local learning, draft-guidance, and no-compliance-determination subtitle visible.

## 2026-08-30 — Landing-page visual hierarchy and optional animation

- Add a larger in-page CIP Wayfinder logo, an upload-first headline, and three native Streamlit waypoint cards: Upload, Explore, and Decide. The cards use accessible theme-provided blue, violet, and green accents rather than custom CSS.
- Rename the optional walkthrough to make its animated four-step status tour clear. The animation runs only after the learner presses Play, so it does not distract from the first upload action or replay on normal reruns.
- Preserve the existing workflow boundary: the tour is visual guidance only and cannot start an export, create an operational change, or bypass human review.

## 2026-08-30 — Product-facing language

- Remove academic framing from the app, package metadata, prompts, documentation, video brief, and project guidance so CIP Wayfinder presents as a local product demonstration.
- Retain the safety language that describes fictional examples, synthetic evidence and asset observations, source-grounded drafts, local-only processing, human review, and the prohibition on compliance conclusions.

## 2026-08-30 — Evaluator-facing architecture diagram

- Add a Mermaid architecture diagram to the architecture document. It shows the upload and local-corpus boundary, typed intake, tested LangGraph workflow, bounded recovery routes, human interrupt, guarded export, and separately consented local case persistence.
- State explicitly that the current Streamlit screen presents deterministic package results and an in-memory decision preview; it does not yet invoke a paid provider or a write-capable graph run.
- Replace the Mermaid block with a standalone SVG architecture diagram after the local editor preview could not render the Mermaid consistently. The image preserves the same architecture and can be opened directly in a browser or file viewer.

## 2026-08-31 — Agent communication diagram

- Add a standalone SVG that shows the six agent roles, their typed handoffs, local source and synthetic-data inputs, Quality Reviewer validation feedback, and the human decision before guarded local export.

## 2026-08-31 — Nebius structured-output adapter

- Add an OpenAI-compatible Nebius AI Studio adapter for schema-constrained chat completions. It requires an environment-supplied API key and an account-selected model name, uses timeouts and the existing retry wrapper, and is tested only with a local recording transport.
- Keep the fake provider as default and leave the Nebius adapter disconnected from the Streamlit UI and LangGraph workflow. No credential was read and no network request was made. A paid smoke test still requires the exact preview and a separate explicit approval.

## 2026-08-31 — One-time NERC intake catalog and requirement-specific drafting seam

- Bundle a reviewed, static local catalog of NERC Functional Entity and current ERO Enterprise Regional Entity names with public-source URLs and a collection date. The app does not crawl or contact NERC at runtime.
- Use native dropdowns that accept a typed new value: NERC choices guide Functional Entity and regional-jurisdiction context, while asset scope and review objective remain clearly labeled local suggestions because they are organization-specific.
- Add a source-grounded provider seam that constructs a draft request from exactly one retrieved requirement mapping. Keep the fake provider as the executable default; connecting Nebius remains blocked on account-model selection and explicit approval of the exact request that would transmit one retrieved excerpt.

## 2026-08-31 — Multi-select case-scope intake

- Change Functional Entity, Regional Entity, and asset-scope fields from one choice to local multi-select inputs, while preserving typed additions and beginner hover help.
- Keep the existing strict Applicability Agent contract string-based by joining selected values only at its boundary; an empty selection still makes the agent ask a direct scope question rather than guessing.

## 2026-08-31 — Token Factory structured-output compatibility

- Use Token Factory's documented `response_format` JSON-schema request shape when the configured base URL is Token Factory, while retaining the existing AI Studio guided-JSON shape.
- Keep the model call disconnected from the UI and graph. A prior no-corpus smoke request returned the input object instead of the strict contract, so no source-grounded drafting request will be sent until the corrected bounded smoke request is separately approved and parses successfully.

## 2026-08-31 — Bounded full-draft output limit

- Keep the 700-token limit for the no-corpus connectivity smoke check, but give the complete draft-control and remediation schema an explicit 1,400-token cap. This is a separate, reviewable request limit rather than an unbounded model setting.
- Reject a provider response with no structured content using a concise safe error, rather than accepting it or exposing a response body.

## 2026-08-31 — Token Factory completion and reasoning limits

- Send Token Factory's documented `max_completion_tokens` alongside the bounded output limit, so visible output and model reasoning share an explicit cap.
- Use the provider-documented low reasoning effort only for full structured drafting, preserving the smaller smoke request and requiring a new explicit approval before the updated source-grounded request.

## 2026-08-31 — Review-and-send model boundary in Streamlit

- Add an optional Review package expander that previews one matched requirement-level local source and requires a checkbox plus send click before Token Factory can be called.
- Read ignored local provider settings only when the approved send action is invoked. Keep the key, raw request, and raw source excerpt out of the page, logs, persistence, and export.
- Store only a traceability-validated draft result and safe model/latency summary in temporary browser session state. The existing local deterministic package remains the default and no external call is automatic.
- Use `moonshotai/Kimi-K3` for this optional UI action because its approved no-corpus smoke request and an approved CIP-010-5 R1 draft both returned valid structured results; do not silently fall back to Kimi-K2.6 for the same action.

## 2026-08-31 — Focused review interface

- Reduce the landing page to the upload-and-scope task plus an optional walkthrough; remove repeated safety cards and waypoints from the main path.
- Replace the post-upload chat-style task selector with a single handoff to the review package. Consolidate the review into requirements/sources, draft controls/remediation, evidence/baseline, and human decision; graph and optional model details are advanced.

## 2026-08-31 — Unbounded intake multi-selects

- Remove arbitrary selection-count limits from Functional Entity, Regional Entity, and asset-scope inputs; users may select every relevant local option.
- Catch unexpected typed-intake validation errors at the Streamlit boundary and show a short corrective message instead of a framework stack trace.

## 2026-08-31 — Safe review-package navigation

- Change the Open review package button to use a Streamlit pre-rerun callback, so it updates the keyed workspace selector before that widget is instantiated.

## 2026-08-31 — Hot-reload-safe retrieval boundary

- Serialize the session-held uploaded standard before constructing a RetrievalQuery, so Streamlit module reloads cannot mix two Pydantic StandardVersion class identities.

## 2026-08-31 — Expandable requirement excerpts

- Show only an expandable full locally retrieved excerpt for each requirement, preserving the visible page/section provenance without redundant truncated text. Render it in a read-only field that wraps long lines.`r`n- Hide Streamlit's redundant empty-menu row only while one of the three intake multiselects is active and all its available options have been selected; do not change other dropdown behavior.
## 2026-08-31 — Compact all-listed scope choices

- Replace manual selection of every option with one All listed choice for Functional Entity, Regional Entity, and asset scope. Expand that compact selection only when validating the local case intake.
- Limit manual selections to fewer than the complete local option list, so Streamlit never leaves an empty dropdown panel over the next field. Preserve typed local values and migrate an existing browser session that already selected every listed value.
## 2026-08-31 — Focused source-and-controls application

- Remove Evidence Analyst and Baseline Analyst processing from the CIP Wayfinder runtime and user interface. The app now focuses on cited requirements, draft controls/remediation, and human decision.
- Keep the separate synthetic evidence and baseline learning modules and their tests in the repository as coursework evidence, but do not invoke or display them in the application.
## 2026-09-01 — Requirement-aware offline drafting

- Replace the ID-only deterministic control template with an offline drafter that uses the combined approved-local text for the selected requirement and recognizes the requirement area to produce specific activities, cadence, retained records, escalation, and remediation.
- Keep the model provider optional and approval-gated. The default package remains local, source-grounded draft guidance and does not make a compliance conclusion.
## 2026-09-01 — Local graph-display helpers

- Restore the landing walkthrough and Advanced demo graph-path helpers after the simplified app flow removed their earlier implementations. Both display the four local review steps only; they do not invoke the graph, a provider, or a write.

## 2026-09-01 — Bounded MVP caching

- Treat the approved read-only SQLite corpus as the persistent public-standard layer and cache derived review packages with Streamlit `cache_data`, bounded to 32 entries.
- Invalidate derived packages on public-document hash, parsed standard/requirements, corpus file revision, or cache-policy version. Do not cache raw PDF bytes, credentials, approval state, evidence, or operational data in the shared cache.
- Cache an exact, traceability-validated model result only in the current browser session. The exact provider, model, request/prompt/source content, and output-schema version form its opaque key; the user still reviews and approves the send action before reuse.
- Exclude semantic caching from the MVP and expose only safe per-session counts. A local developer clear button remains hidden unless `NCI_ENABLE_CACHE_CONTROLS=true`.

## 2026-09-02 — Meaningful human approval and Word deliverable

- Separate approval to transmit one public requirement excerpt to Token Factory from approval of the complete reviewed package. Model generation happens first so the reviewer never approves unseen content.
- Give the package decision three explicit outcomes: Approve for export, Needs editing, and Reject. Only Approve for export, with reviewer role and rationale, creates a file.
- Generate a genuine `.docx` entirely in browser-session memory. Include scope, requirement/source provenance, complete local draft controls, ordered remediation, any previously reviewed Token Factory draft, and the human decision.
- Bind approval to the exact package context. Hide a prior download when the local package, intake, corpus revision, or model draft changes, and require a new decision.
- Define approval narrowly as authorization for local draft-document export, not a compliance determination, legal opinion, workflow approval, or operational implementation.

## 2026-09-02 — Restore direct intake multi-selects

- Remove the compact All listed shortcuts from Functional Entity, Regional Entity, and asset scope because they add an unnecessary abstraction without improving scope selection.
- Restore direct multi-select dropdowns containing only the real local choices. Keep multiple selection and typed custom values, and remove the artificial selection caps and submission-time expansion helpers.

## 2026-09-03 — Remove non-product advanced demo details

- Remove the Advanced demo details expander because its graph animation and cache diagnostics do not create a usable Visio-style workflow or help complete the review.
- Remove the graph-path animation button and the developer-only cache-counter/clear controls from the product UI. Keep the tested LangGraph and caching implementations in the codebase as assignment architecture and internal behavior.
- Keep the landing walkthrough, source review, draft controls/remediation, optional Token Factory enhancement, and human decision unchanged at this milestone.

## 2026-09-03 — Approval-gated Word email delivery

- Replace the browser download with a recipient field and configured SMTP delivery of the in-memory `.docx` attachment.
- Keep package approval separate from the external send: the user must review the destination and attachment summary, check a send-authorization statement, and press the send button.
- Revalidate the recipient and exact package context immediately before sending. Package or model changes invalidate the prior approval.
- Load SMTP credentials only from environment values or the ignored `.env`; never display, log, cache, or persist them. Retain only a masked delivery receipt in browser session state.
- Unit-test the boundary with injected recording and failing transports; automated tests make no network call and send no real email.

## 2026-09-03 — Compact requirement-language display

- Remove the nested fixed-height source-excerpt text area from each requirement because it creates unnecessary white space and repeats interface labels.
- Display all matched local requirement chunks directly as literal text. Collapse PDF extraction whitespace without changing the source words.
- Keep one compact page, section, and retrieval-date line after the language so the source remains traceable.

## 2026-09-03 — Plain-language requirement summaries

- Replace the literal requirement-text display with a collapsed vital-information summary covering purpose, key activity, timing, typical owner, and expected evidence.
- Preserve compact page, section, and retrieval-date citations so the reviewer can verify the draft summary against the official local source.

## 2026-09-03 — Restore direct download alongside optional email

- Keep the approved Word package in browser-session memory and provide an immediate local download button after package approval.
- Retain email as an optional, separately authorized external action. SMTP configuration is required only for email delivery, not for download.
- Require a new package decision whenever the intake, source corpus, or local draft changes.

## 2026-09-04 — Remove optional model enhancement from the product

- Remove the Optional model enhancement section and its secondary transmission approval from the Review package page to keep the analyst workflow focused.
- Remove model-result session state, caching, approval invalidation, and model-generated content from the Word export contract.
- Keep the structured-provider seam and fake-provider tests as disconnected learning code; the Streamlit product now makes no external model request.
- Keep package approval and optional SMTP email authorization as the two visible human gates.
- Migrate cache counters stored by an already-open browser session by retaining current dashboard counters and dropping the removed model counters on the next rerun.

## 2026-09-11 — Expand ingestion to NERC standards-related PDFs

- Replace the CIP-010-5/CIP-007-6 filename allowlist with content-based discovery for all fourteen NERC Reliability Standard families published on NERC's standards page.
- Accept decimal and letter versions plus regional standard suffixes, normalize common Unicode PDF dash characters, and preserve repeated requirement labels by combining them with their standard identity in multi-standard documents.
- Require searchable text, a recognized standard reference in the PDF body, multiple NERC identity signals, and the existing public-document authorization attestation. Treat this as a best-effort local gate rather than proof of publication authenticity.
- Dynamically classify the document and build a typed local knowledge profile containing its title, type, referenced standards, requirement or topic items, page locations, and bounded extractive summaries.
- Prefer approved read-only corpus matches. When no corpus match exists, use the content-validated uploaded page summary and locator rather than pretending the standard is unsupported.
- Keep the two-workspace UI, local-only processing, bounded 32-entry cache, draft-only controls, approval-gated Word creation, direct download, and separately authorized SMTP delivery.
- Bump the cache-policy version and include the expanded document profile in cache identity so stale two-standard packages cannot be reused.
## 2026-09-11 — Fixed package objective and typed Review Package Agent

- Remove the editable Review objective from intake because the uploaded document and scoped user context now drive analysis.
- Show the fixed product objective on the loading page: prepare a source-grounded draft package for SME tailoring.
- Add a deterministic, strict Review Package Agent that preserves supplied mappings, controls, remediation, knowledge items, and source chunks while flagging missing approved-corpus support.
- Keep quality review, human approval, deterministic Word rendering, download, and separately authorized email delivery outside the agent's authority.

## 2026-09-11 — Remove Asset Scope from upload intake

- Remove Asset Scope from the first-page form because the current document-driven review does not use it to change extraction or package assembly.
- Require only Functional Entity and Regional Entity user context; derive standard/version from the validated NERC document.
- Remove asset scope from the upload-flow readiness contract and Word metadata while retaining asset-specific tailoring questions inside draft controls.
- Keep the separate LangGraph demonstration's selected synthetic asset ID unchanged.
## 2026-09-16 — Submission-only verification

The v4 system diagram was subsequently redrawn in the connected v3 visual style. Source fallback, Review Package Agent, structural quality review, valid-package approval, and separate SMTP consent appear in the product flow; synthetic LangGraph state/recovery/interrupt/export appear in an isolated panel. This is a documentation correction only.

The subsequent v4 documentation refresh preserves v3, corrects the roster/intake/source/state descriptions, updates diagrams and test evidence, and verifies public GitHub and existing Drive-video landing-page access. Video content/duration, a final Google Doc URL, and the submission form remain unverified. No application behavior changed and no external publication was performed in that refresh.

- Verified 167 tests, 15 offline evaluations, dependency compatibility, initial Streamlit rendering, health, diff formatting and common credential patterns.
- Corrected demo instructions and added coding-prompt examples. Did not add Excel automation or change application behavior.
- Preserve existing local changes; do not imply the tested tree has been published or the assignment submitted. Final delivery links remain required.

## 2026-09-11 — Expand the approved local CIP retrieval index

- Allowlists the 24 distinct `cip-*.pdf` standard-version files supplied in the approved corpus directory through `approved_cip_manifest.json`.
- Exclude the byte-identical `cip-008-7.1 (1).pdf` duplicate and do not ingest spreadsheets, synthetic organization context, the glossary, or multi-standard status summaries through the one-standard-per-document adapter.
- Build local metadata-rich page chunks in SQLite without an embedding API, external tokenizer, web crawl, or model call.
- Use neutral enforcement and effective-date metadata when those facts have not been independently curated; reviewers must verify current status against NERC.

## 2026-09-11 — Recognize exact approved-corpus uploads

- Connect the upload gate to the same approved corpus directory and manifest used to build local retrieval.
- Accept weakly branded PDFs only when their SHA-256 hash exactly matches a manifest-listed local PDF and the manifest standard/version agrees with a standard reference extracted from the PDF body.
- Continue to require a searchable PDF, a recognized standard reference, and the user's public-document authorization attestation.
- Never trust a filename or mere presence in the corpus folder; altered and unlisted files must still pass the independent NERC identity-signal threshold.

## 2026-09-12 — Bound retrieval to primary section-B requirements

- Use one shared deterministic parser for uploaded-document knowledge and approved-corpus ingestion so requirement identities and boundaries cannot drift.
- Extract only top-level `R1`, `R2`, and similar blocks between `B. Requirements and Measures` and `C. Compliance`; end each block at its matching measure or the next requirement.
- Exclude measures, compliance sections, appendices, version history, and cross-document requirement citations from the primary requirement list.
- Rebuild the 24-document corpus as 84 bounded requirement chunks with start/end page provenance.
- Present the primary standard once, keep every requirement collapsed initially, and derive its plain-language synopsis from its own source block rather than a generic control draft.
- Bump the dashboard cache policy to `nerc-primary-requirements-v3` and clear stale uploaded-document session state so prior page-level results cannot be reused after hot reload.

## 2026-09-12 — Show both requirement summary and official extracted wording

- Keep the plain-language synopsis and add the official requirement wording from the same bounded section-B source block beneath it.
- Render PDF wording with Streamlit's literal text element so source content is not interpreted as Markdown and no fixed-height text area creates excess whitespace.
- Retain a bounded requirement source block for content-validated uploads without a corpus match, while continuing to omit raw PDF bytes and unrelated document text from shared cache state.
- Use the same extracted requirement wording in the Word package fallback path and bump the cache/session policy to `nerc-requirement-source-text-v4`.

## Inline effective-date citation

- Place the source document and page numbers directly beneath Standard effective date.
- Remove the separate effective-date details expander; keep requirement dates in Requirements and sources.
- Preserve catalog data, date calculation rules, and the jurisdiction/snapshot notice.
