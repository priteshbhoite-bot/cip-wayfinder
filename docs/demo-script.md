# Under-Five-Minute Demonstration Script

## 0:00–0:25 — Safety and scope

Open the Streamlit app. State that Northstar Grid Services and `SUB-ALPHA-RTU-01` are fictional, data is synthetic/local, and the app does not declare compliance or make operational changes.

## 0:25–0:55 — Case intake and standards

Open **Start a review**. Enter the fictional Functional Entity, jurisdiction, asset scope, and review objective, then upload one approved public CIP PDF. First leave one intake field blank and submit: point out that the Applicability Agent asks a direct question rather than guessing. Complete the field and submit again.

## 0:55–1:20 — Source-grounded package

Open **Review package**. Show the four summary measures: requirement labels, local source matches, draft controls, and decision status. Open **Source and requirement** and point out the short local excerpt plus the cited standard/version, page, section, source URL, and retrieval date. State that the source is local and read-only.

## 1:20–1:50 — Demonstrate a failure and recovery

Run the fake graph using a missing requirement reference. Explain that the graph takes the empty-retrieval path, uses at most one validation repair, and safely stops if no repair is possible. Then rerun the known synthetic requirement reference to continue. This is recovery, not an invented requirement.

## 1:50–2:25 — Controls, evidence, and baseline

Show the draft control and Traceability tab. Show the synthetic evidence facts and baseline observation. Explain that embedded evidence instructions are ignored and that all controls remain drafts linked to retrieved IDs.

## 2:25–2:50 — Findings and remediation

Show the demo risk explanation and draft remediation steps. Emphasize that a potential finding requires SME review and is not automatically closed.

## 2:50–3:20 — Graph path and interrupt

Open **Review graph progress** and select **Animate local review path**. Explain that this is a visual explanation of the already-tested graph: retries are bounded, repair is bounded, and the path stops at a human approval interrupt. It does not run a workflow export.

## 3:20–3:45 — Interrupt and human edit

Run the graph until its approval interrupt. Select **edit** once. Show that the graph records a visible synthetic revision and returns to the same approval interrupt using the same thread ID/checkpointer.

## 3:45–4:15 — Explicit approval and local export

In **Human decision**, choose **edit**, enter a reviewer role and rationale, and preview it. Explain that the production graph would return the draft to the interrupt. Then use the graph test or terminal demonstration to show explicit approve with reviewer data. Explain that only the guarded graph route allows a synthetic local JSON below `outputs/workflows/`. Do not show or use real evidence, credentials, or an external system.

## 4:15–4:40 — Verification and close

Run `uv run python -m nerc_compliance_intelligence.evaluations` and point to the 15 PASS results. Close with the limitations: no compliance conclusion, no operational action, optional tracing disconnected, and human tailoring still required.
