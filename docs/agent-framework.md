# Agent Framework

This local MVP uses six narrow agent roles. They are deterministic Python/graph nodes in the current release, not six paid model calls.

![CIP Wayfinder agent communication diagram](../assets/cip-wayfinder-agent-communication.svg)

| Role | Input | Output | Boundary |
|---|---|---|---|
| Intake and Scope | Synthetic case fields | Missing-scope message or valid scope | Does not guess Functional Entity, jurisdiction, standard/version, or asset scope. |
| Requirement and Citation | Version-scoped local retrieval result | Requirement mapping and citation metadata | Uses retrieved sources only. |
| Control Drafting | Retrieved requirement ID | Draft control and remediation steps | Every meaningful field has retrieved requirement IDs; all text remains draft. |
| Evidence Insight | Synthetic evidence document | Facts, support signals, gaps, confidence, SME questions | Text is untrusted data; embedded instructions are ignored. |
| Risk and Remediation | Synthetic evidence/baseline observations | Potential findings and draft plan | Uses a simple demo rubric; no compliance conclusion or automatic closure. |
| Human Handoff and Workflow | Draft plan and human decision | Pause, revise, reject, or approved local export | Interrupt occurs before export; only explicit approval can export. |

The Quality Reviewer runs before handoff to check traceability and control links. The Applicability Agent asks questions for missing scope rather than determining applicability.
