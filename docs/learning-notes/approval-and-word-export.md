# What “Approve” means in CIP Wayfinder

The earlier button felt pointless because it only displayed the decision back to the user. The updated flow gives approval a useful but narrow job.

## Two different approvals

### Gate 1: permission to use Token Factory

This approval answers: **May the app send this displayed public requirement excerpt to the external model?**

The user sees the model, requirement, source locator, excerpt size, token limit, and retry limit before approving. Token Factory returns a draft for review. This is permission to transmit bounded public data, not approval of the returned content.

### Gate 2: approval to prepare the Word attachment

This approval answers: **May the app turn the exact package I reviewed into a Word attachment?**

The reviewer must provide a role and rationale. The app then creates a `.docx` in memory. This approval does not send it.

### Gate 3: approval to send email

The user enters a recipient and reviews the attachment name, size, and standard. SMTP is called only after the user checks the separate authorization box and presses **Send approved Word package**. A changed package invalidates the earlier approval. The app keeps only a masked delivery receipt in session memory.

## Why the model runs before final approval

A reviewer should not approve content they have not seen. Therefore, Token Factory generation is optional and happens before the package decision. The reviewer can inspect the model output, compare it with the cited source and local draft, and then approve, return for editing, or reject the package.

## What the Word package contains

- review scope and objective;
- requirements and source provenance;
- approved-local public excerpts;
- draft controls and detailed control activities;
- ordered remediation actions and decision points;
- any optional Token Factory draft, clearly labeled as model-generated;
- reviewer role, rationale, and decision time;
- repeated warnings that this is draft guidance, not a compliance conclusion.

## What approval does not mean

Approval does not say that the organization complies with NERC. It does not provide legal advice, approve a production workflow, close a finding, or authorize an IT/OT change. Those activities need separate organization-specific governance.
