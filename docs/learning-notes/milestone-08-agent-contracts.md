# Milestone 8 Learning Note: Agent Contracts

The Standards Agent and Applicability Agent use the same idea as a form with required boxes: a strict Pydantic schema says exactly what may enter and leave the agent. Unknown fields are rejected.

The default models are deterministic Python classes, not LLM calls. This keeps tests repeatable and prevents credentials or network access from being needed. A future hosted model can be added only by implementing the small `invoke()` protocol and passing the contract tests.

The Standards Agent receives retrieved chunks. It may create a mapping only by copying the retrieved chunk text and its source metadata into a citation. The contract rejects a made-up chunk ID, page, source URL, requirement reference, or draft summary.

The Applicability Agent does not decide whether a standard applies. It asks one direct question for each missing scope group: Functional Entity, jurisdiction, standard/version, and asset scope. It becomes ready for retrieval only after every group is supplied.

Sample state transition:

```text
{}  →  missing: Functional Entity, jurisdiction, standard/version, asset scope
full scope supplied  →  ready_for_retrieval: true
retrieved source chunk supplied  →  source-grounded draft mapping plus citation
```
