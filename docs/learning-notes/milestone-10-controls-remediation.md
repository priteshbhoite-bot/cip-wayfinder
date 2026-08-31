# Milestone 10 — Traceable draft controls and remediation

`src/nerc_compliance_intelligence/control_remediation.py` is a small, deterministic drafting layer. It is not an LLM, does not decide whether a rule applies, and does not declare compliance. It creates generic draft content only after local retrieval has supplied a requirement identifier.

## One example, explained line by line

```python
generation_input = ControlGenerationInput(                         # 1
    retrieved_mappings=[retrieved_mapping],                         # 2
    selected_requirement_ids=["Synthetic demo reference"],         # 3
)
output = generate_draft_control_and_remediation(generation_input)  # 4
```

1. `ControlGenerationInput` is the typed container for the drafting request.
2. `retrieved_mapping` is the requirement record returned by the existing retrieval tool. Its `requirement_reference` is the allowed ID list.
3. This selects one such retrieved ID. A made-up ID is rejected before anything is drafted.
4. The fake generator returns a draft control and an ordered draft remediation plan. Every text-bearing field includes the same selected ID in `requirement_ids`.

The returned control contains an objective, activity, type, owner role, performer, trigger/frequency, procedure, evidence expectation, exception/escalation route, test procedure, assumption, and tailoring question. The remediation plan has three numbered steps; each has an action, owner, decision, and end state.

`validate_traceability()` is a second safety check. It walks every meaningful text field and rejects an ID that was not in the supplied retrieval result. The plan remains a draft and still must pass the existing human approval interrupt before any local export.
