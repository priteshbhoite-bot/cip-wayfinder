"""Contract and validation tests for Milestone 10 traceable draft generation."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from nerc_compliance_intelligence.control_remediation import (
    ControlGenerationInput,
    ControlGenerationOutput,
    DraftRemediationPlan,
    RemediationStep,
    TraceableContent,
    build_source_grounded_control_draft_request,
    generate_source_grounded_control_draft,
    generate_draft_control_and_remediation,
    validate_traceability,
)
from nerc_compliance_intelligence.fake_tools import RequirementLookupInput, requirement_lookup
from nerc_compliance_intelligence.providers import FakeStructuredProvider, ProviderSettings
from nerc_compliance_intelligence.schemas import StandardVersion


def _retrieved_mappings() -> list:
    result = requirement_lookup(
        RequirementLookupInput(
            standard=StandardVersion(standard_id="CIP-010", version="5", scope_role="primary"),
            requirement_reference="Synthetic demo reference",
        )
    )
    assert result.mapping is not None
    return [result.mapping]


def test_fake_generation_has_every_requested_control_field_and_trace() -> None:
    mappings = _retrieved_mappings()
    output = generate_draft_control_and_remediation(
        ControlGenerationInput(retrieved_mappings=mappings, selected_requirement_ids=["Synthetic demo reference"])
    )

    assert output.control.is_draft is True
    assert output.control.activities[0].activity.requirement_ids == ["Synthetic demo reference"]
    assert output.control.tailoring_questions[0].requirement_ids == ["Synthetic demo reference"]
    assert [step.step_number for step in output.remediation_plan.steps] == [1, 2, 3]
    assert all(step.decision.text and step.end_state.text for step in output.remediation_plan.steps)
    validate_traceability(output, mappings)


def test_selected_requirement_must_be_present_in_retrieval() -> None:
    with pytest.raises(ValidationError, match="were not retrieved"):
        ControlGenerationInput(retrieved_mappings=_retrieved_mappings(), selected_requirement_ids=["R999"])


def test_trace_validation_rejects_content_with_an_unknown_requirement_id() -> None:
    mappings = _retrieved_mappings()
    output = generate_draft_control_and_remediation(
        ControlGenerationInput(retrieved_mappings=mappings, selected_requirement_ids=["Synthetic demo reference"])
    )
    altered_control = output.control.model_copy(
        update={"objective": TraceableContent(text="Untraceable draft text", requirement_ids=["R999"])}
    )
    altered = ControlGenerationOutput(control=altered_control, remediation_plan=output.remediation_plan)

    with pytest.raises(ValueError, match="not retrieved"):
        validate_traceability(altered, mappings)


def test_remediation_steps_must_be_consecutive_and_ordered() -> None:
    content = TraceableContent(text="Draft text", requirement_ids=["Synthetic demo reference"])
    with pytest.raises(ValidationError, match="ordered consecutively"):
        DraftRemediationPlan(
            plan_id="draft-plan",
            control_id="draft-control",
            steps=[RemediationStep(step_number=2, action=content, owner_role=content, decision=content, end_state=content)],
        )


def test_source_grounded_request_contains_only_the_selected_requirement() -> None:
    mapping = _retrieved_mappings()[0]
    request = build_source_grounded_control_draft_request(
        ControlGenerationInput(retrieved_mappings=[mapping], selected_requirement_ids=[mapping.requirement_reference])
    )

    assert request.operation == "source_grounded_requirement_control_draft"
    assert request.input_payload["requirement"]["requirement_reference"] == mapping.requirement_reference
    assert request.input_payload["requirement"]["retrieved_excerpt"] == mapping.draft_summary
    assert request.max_output_tokens == 2_000
    assert request.reasoning_effort == "low"
    assert "evidence" not in request.input_payload
    assert "baseline" not in request.input_payload


def test_source_grounded_fake_draft_is_requirement_specific_and_traceable() -> None:
    mapping = _retrieved_mappings()[0]
    generation_input = ControlGenerationInput(retrieved_mappings=[mapping], selected_requirement_ids=[mapping.requirement_reference])
    expected = generate_draft_control_and_remediation(generation_input)
    result = generate_source_grounded_control_draft(
        generation_input,
        FakeStructuredProvider(scripted_responses=[expected.model_dump()]),
        ProviderSettings(),
    )

    assert result.model == "fake-structured-v1"
    assert result.parsed_output.control.objective.requirement_ids == [mapping.requirement_reference]


def test_source_grounded_request_rejects_multiple_selected_requirements() -> None:
    mappings = _retrieved_mappings()
    duplicated = mappings + [mappings[0].model_copy(update={"requirement_reference": "Second reference"})]
    with pytest.raises(ValueError, match="exactly one"):
        build_source_grounded_control_draft_request(
            ControlGenerationInput(retrieved_mappings=duplicated, selected_requirement_ids=["Synthetic demo reference", "Second reference"])
        )


def test_local_drafter_uses_retrieved_patch_management_text_for_specific_actions() -> None:
    mappings = _retrieved_mappings()
    patch_mapping = mappings[0].model_copy(
        update={
            "requirement_reference": "R2",
            "draft_summary": "CIP-007-6 Table R2 – Security Patch Management. At least once every 35 calendar days, evaluate security patches for applicability. For applicable patches, apply the patch, create or revise a mitigation plan, or document why it is not applicable.",
        }
    )
    output = generate_draft_control_and_remediation(
        ControlGenerationInput(retrieved_mappings=[patch_mapping], selected_requirement_ids=["R2"])
    )

    assert "Security patch applicability evaluation" in output.control.title.text
    assert "patch source" in output.control.activities[0].activity.text
    assert "assess applicability" in output.control.activities[0].activity.text
    assert "mitigation plan" in output.control.evidence_expectation.text
    assert "35 calendar days" in output.control.trigger_frequency.text
    assert all("synthetic" not in item.text.casefold() for item in output.control.traceable_items())
