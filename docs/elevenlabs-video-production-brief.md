# ElevenLabs Video Production Brief

## Purpose

Create a 3.5–4.5 minute narrated MP4 that helps a first-time viewer understand the fictional, local CIP Wayfinder application.

This is an educational product walkthrough, not a NERC compliance determination, legal opinion, audit conclusion, or description of a real utility environment.

## Safe content boundary

Use only the fictional utility name **Northstar Grid Services**, the fictional asset ID **SUB-ALPHA-RTU-01**, and the synthetic information below.

Do not use, upload, display, summarize, or infer from:

- API keys, account information, credit balance, or screenshots containing them;
- confidential evidence, real IT/OT exports, asset inventories, tickets, or personal data;
- raw NERC source-document pages or large excerpts;
- a claim that the app proves or certifies compliance.

The video may mention the scope boundary as: “CIP-010-5 primary and CIP-007-6 supporting.” It must say that controls and findings are drafts requiring SME tailoring and human review.

## Recommended ElevenLabs Studio workflow

1. Open ElevenLabs Studio or Image & Video.
2. Create a new landscape project at 16:9 and 1080p.
3. Choose a clear, calm, professional English voice. Do not clone a real person’s voice unless you have that person’s permission.
4. Use the narration below as the voiceover script.
5. Create one visual scene for each section below. Prefer clean diagrams, animated text, or deliberately fictional UI-style mockups.
6. If you upload local screenshots later, use only screenshots of the app’s fictional/synthetic dashboard. Do not upload a terminal, `.env` file, source PDF, or any real evidence.
7. Add captions. Keep them concise and synchronized with the narration.
8. Export as an MP4. Review the finished video before sharing it.

## Visual style

- Professional, calm, modern compliance-review presentation.
- Blue, slate, and white palette; readable sans-serif text; high contrast.
- Use simple icons for source, draft control, evidence, baseline, reviewer, pause, and export.
- Clearly label every generated result as **Draft** or **Synthetic** where relevant.
- Avoid official-looking seals, legal language, alarming risk graphics, or claims such as “compliant,” “certified,” or “approved by NERC.”

## Scene plan and narration

### Scene 1 — Title and safety boundary (0:00–0:20)

**Visual direction:** Title card: “CIP Wayfinder.” Add a small subtitle: “Fictional data • Human review required.”

**Narration:**

> This short walkthrough introduces a local learning application for a fictional compliance analyst. It uses fictional utility and asset information, synthetic evidence, and draft outputs. It does not make a NERC compliance determination, provide legal advice, or change an operational system.

### Scene 2 — Scope and user (0:20–0:40)

**Visual direction:** A simple scope card with “Northstar Grid Services,” “SUB-ALPHA-RTU-01,” “CIP-010-5 primary,” and “CIP-007-6 supporting.”

**Narration:**

> The demonstration follows a compliance analyst reviewing the fictional asset SUB-ALPHA-RTU-01 for a limited standards boundary: CIP-010 version 5 as the primary example and CIP-007 version 6 as supporting context. Missing scope is not guessed; the app asks an SME for it.

### Scene 3 — Local workflow (0:40–1:05)

**Visual direction:** Animated flow: Intake → local requirement retrieval → draft controls → synthetic evidence and baseline → draft finding → human approval pause → guarded local export.

**Narration:**

> The workflow is a local agent graph. It validates intake, retrieves a version-scoped local requirement record, creates a draft control, reviews synthetic evidence and a simulated asset baseline, and prepares a draft remediation plan. A human approval pause happens before any local workflow export.

### Scene 4 — Failure and bounded recovery (1:05–1:35)

**Visual direction:** Show a red-but-calm card: “Missing requirement reference.” Then an arrow to: “One bounded repair attempt.” End with either “Retrieved known synthetic reference” or “Safe stop.”

**Narration:**

> The demo also shows a safe failure path. When a requirement reference is missing, the app does not invent a requirement. It makes at most one bounded validation repair using the known synthetic demonstration reference. If the issue cannot be repaired, the workflow stops safely without an export.

### Scene 5 — Draft controls and traceability (1:35–2:00)

**Visual direction:** A “Draft control” card listing: objective, activity, owner, performer, frequency, procedure, evidence expectation, escalation, test procedure, assumptions, and tailoring questions. Add a visible tag: “Linked to retrieved requirement ID.”

**Narration:**

> The Control Drafting step creates a draft control—not a finalized control. Each meaningful field, including the objective, owner, evidence expectation, and test procedure, links to a retrieved requirement ID. This gives the analyst traceability while leaving organization-specific tailoring to the SME.

### Scene 6 — Evidence and baseline safety (2:00–2:30)

**Visual direction:** Split screen. Left: synthetic evidence record with fields “Evidence ID,” “Asset ID,” “Captured On,” “Change Approval,” and “Baseline Fingerprint.” Right: expected-versus-observed baseline card with a bounded review observation.

**Narration:**

> The Evidence Analyst extracts only a small set of observable fields from synthetic documents. Document text is treated as untrusted data, so embedded instructions are ignored. The Baseline Analyst compares software, ports and services, patches, accounts, and baseline version. It reports no change, approved change, unexplained change, stale observation, or missing asset for SME review.

### Scene 7 — Finding and remediation draft (2:30–2:55)

**Visual direction:** Show “Potential review lead — Draft” with “High, Medium, Low demo rubric.” Then show numbered remediation steps with action, owner, decision, and end state.

**Narration:**

> The application uses a deliberately simple High, Medium, and Low demonstration rubric based on evidence completeness, asset variance, and requirement criticality. Its output is a potential review lead and a draft remediation plan. It does not automatically close gaps or claim compliance.

### Scene 8 — Interrupt, human edit, and approval (2:55–3:30)

**Visual direction:** Pause icon with “Human approval required.” Show three choices: Edit, Reject, Approve. Animate Edit returning to the draft; animate Reject ending safely; animate Approve leading to a guarded local export.

**Narration:**

> Before export, the graph interrupts and waits for a human decision. A reviewer can edit the draft and return to the same pause, reject it and stop safely, or explicitly approve it. Only an approved decision, with a reviewer role and time, can pass the export guard.

### Scene 9 — Local export and verification (3:30–3:55)

**Visual direction:** Folder icon labeled “Local synthetic outputs only,” followed by “15 of 15 offline evaluations passed.”

**Narration:**

> An approved demonstration creates only a synthetic local workflow record in a safe local outputs folder. It does not create a ticket, publish to GitHub, connect to a production system, or change an operational control. The project also includes fifteen deterministic offline evaluations covering retrieval, safety, traceability, approval, and resume behavior.

### Scene 10 — Close (3:55–4:10)

**Visual direction:** Closing card: “Drafts + traceability + human review.” Small footer: “Local application — not a compliance conclusion.”

**Narration:**

> In summary, this MVP demonstrates a version-aware, traceable, human-governed compliance intelligence workflow using local and synthetic data. The next step for a real organization would always be qualified SME, legal, security, and compliance review.

## Copy-ready generation instruction

Paste this instruction into an ElevenLabs video-generation or Studio project after adding the narration and scene directions above:

> Create a polished 16:9 1080p product walkthrough, approximately four minutes long, using the supplied narration and scene plan. Use a calm, professional voice, readable captions, smooth transitions, simple animated compliance-workflow diagrams, and clearly fictional dashboard-style visuals. Use blue, slate, and white. Label generated controls, findings, and examples as Draft or Synthetic. Do not show real company data, real documents, credentials, terminals, source code, legal claims, or official seals. Never state that the application is compliant, certified, or approved by NERC. End with the message: “Local application — drafts require human SME review.”

## Final review checklist

- [ ] Every visual uses fictional or synthetic material only.
- [ ] No key, account detail, credit balance, terminal, `.env`, or local file path appears.
- [ ] Captions match the narration.
- [ ] The video stays under five minutes.
- [ ] The video says controls/findings are drafts and human review is required.
- [ ] The video does not make a compliance, legal, audit, or operational claim.
- [ ] You reviewed the final MP4 before sharing or submitting it.
