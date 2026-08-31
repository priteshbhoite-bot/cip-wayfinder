# Milestone 3 Learning Note: Data Models

This milestone defines the names and shapes of information the future agent graph will carry. A Pydantic model is like a typed form: it lists the fields a record needs and rejects records that do not match the form. These records are synthetic drafts, not compliance conclusions.

## Field groups

### Standards and requirement mapping

- `StandardVersion.standard_id`, `version`, and `scope_role` identify the narrow demonstration boundary: standard family, version, and whether it is primary or supporting.
- `RequirementMapping.mapping_id` gives one synthetic requirement record a stable name. `standard` connects it to a version. `requirement_reference`, `source_name`, and `source_locator` reserve citation fields for future approved local sources. `draft_summary` is a synthetic learning summary, not an interpretation.

### Draft control process

- `ProcessStep.step_number` puts actions in order. `action` says what the draft step is, `owner_role` says who would own it, and `requires_human_approval` marks a review boundary.
- `ControlDesign.control_id` and `mapping_id` connect a draft control to its requirement mapping. `title`, `objective`, and `process_steps` describe the draft process. `is_draft` is required to stay true so the app cannot represent the control as final.

### Evidence and baseline observations

- `EvidenceArtifact.artifact_id`, `label`, and `collected_on` identify one synthetic evidence item. `source_type` and `synthetic` are safety fields that reject live or confidential evidence.
- `EvidenceObservation.observation_id` identifies a note about an artifact. `artifact_id` links it back to the evidence, `observation` stores the synthetic note, and `supports_draft_control` can be true, false, or unknown.
- `BaselineObservation.observation_id`, `asset_id`, and `baseline_reference` identify a synthetic comparison. `observed_value` holds the demonstration value, `matches_baseline` records the comparison, and `synthetic` blocks live asset exports.

### Findings and validation

- `PotentialFinding.finding_id`, `title`, `risk_level`, and `rationale` describe a possible issue to review. `related_artifact_ids` and `related_baseline_observation_ids` show the synthetic records behind it. `requires_human_review` must remain true; this is never an automatic compliance conclusion.
- `ValidationResult.check_name` names a local validation check, `is_valid` says whether it passed, and `messages` holds clear feedback.

### Human decision and full state

- `HumanDecision.decision` records pending, approve, reject, or revise. `reviewer_role`, `decided_at`, and `notes` record who made a completed decision and why. This model records a decision shape only; it does not perform a write.
- `AgentState.review_id`, `asset_id`, and `created_at` identify one in-memory review. Its remaining fields collect the standards, mappings, controls, evidence, observations, findings, validation results, and human decision. `status` is a simple draft label. The model rejects baseline observations that name a different asset.

## Valid and invalid examples

`learning/milestone_03_examples.py` contains one complete valid synthetic state plus three deliberately invalid examples. The tests confirm that the valid state can be converted to JSON-compatible data and rebuilt without losing meaning, while invalid data is rejected early with a clear validation error.
