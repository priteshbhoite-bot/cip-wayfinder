# Under-Five-Minute Demonstration Script

## 0:00–0:25 — Safety and scope

Open the Streamlit app. State that Northstar Grid Services and `SUB-ALPHA-RTU-01` are fictional, data is synthetic/local, and the app does not declare compliance or make operational changes.

## 0:25–0:55 — Case intake and standards

Open **Start a review**. Enter the fictional Functional Entity, jurisdiction, asset scope, and review objective, then upload one approved public CIP PDF. First leave one intake field blank and submit: point out that the Applicability Agent asks a direct question rather than guessing. Complete the field and submit again.

## 0:55–1:20 — Source-grounded package

Open **Review package**. Show the three summary measures: requirements, local source matches, and draft controls. Open **Requirements and sources**, expand one requirement's vital-information summary, and point out its purpose, key activity, timing, owner, evidence expectation, page, section, and retrieval date. Explain that the summary is draft guidance and the citation leads the reviewer back to the official local source.

## 1:20–1:50 — Demonstrate a failure and recovery

Run the fake graph using a missing requirement reference. Explain that the graph takes the empty-retrieval path, uses at most one validation repair, and safely stops if no repair is possible. Then rerun the known synthetic requirement reference to continue. This is recovery, not an invented requirement.

## 1:50–2:25 — Controls, evidence, and baseline

Show the draft control and Traceability tab. Show the synthetic evidence facts and baseline observation. Explain that embedded evidence instructions are ignored and that all controls remain drafts linked to retrieved IDs.

## 2:25–2:50 — Findings and remediation

Show the demo risk explanation and draft remediation steps. Emphasize that a potential finding requires SME review and is not automatically closed.

## 2:50–3:20 — Tested graph boundary

Explain that the LangGraph retry, repair, and interrupt behavior is verified by automated tests rather than presented as a product workflow diagram. The app does not claim to generate a Visio-style workflow.

## 3:20–3:45 — Interrupt and human edit

Run the graph until its approval interrupt. Select **edit** once. Show that the graph records a visible synthetic revision and returns to the same approval interrupt using the same thread ID/checkpointer.

## 3:45–4:15 — Explicit approval, download, and email delivery

In **Human decision**, first choose **Needs editing**, enter a reviewer role and rationale, and apply the decision. Point out that no document is created. Then choose **Approve package** with a fresh rationale. Show the direct-download button, then the separate recipient field, attachment summary, and send-authorization checkbox for optional email delivery. For a safe classroom demo, download locally or explain the configured SMTP boundary and use a test mailbox; never expose credentials. Show that package approval alone sends nothing and does not declare compliance, start a workflow, or authorize implementation.

## 4:15–4:40 — Verification and close

Run `uv run python -m nerc_compliance_intelligence.evaluations` and point to the 15 PASS results. Close with the limitations: no compliance conclusion, no operational action, optional tracing disconnected, and human tailoring still required.
