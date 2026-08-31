"""Deterministic, traceable draft controls and remediation plans for Milestone 10.

The module deliberately does not interpret a standard, decide applicability, or
claim compliance.  It can only create generic draft language from requirement
identifiers already returned by local retrieval.
"""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field, model_validator

from nerc_compliance_intelligence.providers import ProviderResult, ProviderSettings, StructuredProvider, StructuredRequest, generate_with_retry
from nerc_compliance_intelligence.schemas import RequirementMapping


class TraceableContent(BaseModel):
    """One piece of draft text and the retrieved requirement IDs supporting it."""

    text: str = Field(min_length=1)
    requirement_ids: list[str] = Field(min_length=1)


class ControlActivity(BaseModel):
    """One repeatable draft activity within a control."""

    activity: TraceableContent


class DraftControl(BaseModel):
    """A complete control draft whose meaningful text is individually traceable."""

    model_config = ConfigDict(frozen=True)

    control_id: str = Field(min_length=1)
    title: TraceableContent
    objective: TraceableContent
    activities: list[ControlActivity] = Field(min_length=1)
    control_type: TraceableContent
    owner_role: TraceableContent
    performer: TraceableContent
    trigger_frequency: TraceableContent
    procedure: TraceableContent
    evidence_expectation: TraceableContent
    exception_escalation: TraceableContent
    test_procedure: TraceableContent
    assumptions: list[TraceableContent] = Field(min_length=1)
    tailoring_questions: list[TraceableContent] = Field(min_length=1)
    is_draft: bool = True

    @model_validator(mode="after")
    def remain_a_draft(self) -> "DraftControl":
        """Prevent generated content from being represented as final."""
        if not self.is_draft:
            raise ValueError("control drafts must remain drafts")
        return self

    def traceable_items(self) -> list[TraceableContent]:
        """Return every text-bearing field so one validator can check all links."""
        return [
            self.title,
            self.objective,
            *(item.activity for item in self.activities),
            self.control_type,
            self.owner_role,
            self.performer,
            self.trigger_frequency,
            self.procedure,
            self.evidence_expectation,
            self.exception_escalation,
            self.test_procedure,
            *self.assumptions,
            *self.tailoring_questions,
        ]


class RemediationStep(BaseModel):
    """One ordered, draft-only remediation action with a decision and end state."""

    step_number: int = Field(ge=1)
    action: TraceableContent
    owner_role: TraceableContent
    decision: TraceableContent
    end_state: TraceableContent


class DraftRemediationPlan(BaseModel):
    """An ordered remediation draft; it is not an approved operational workflow."""

    model_config = ConfigDict(frozen=True)

    plan_id: str = Field(min_length=1)
    control_id: str = Field(min_length=1)
    steps: list[RemediationStep] = Field(min_length=1)
    is_draft: bool = True

    @model_validator(mode="after")
    def require_ordered_draft_steps(self) -> "DraftRemediationPlan":
        """Require 1, 2, 3 order and preserve the draft-only safety label."""
        if not self.is_draft:
            raise ValueError("remediation plans must remain drafts")
        numbers = [step.step_number for step in self.steps]
        if numbers != list(range(1, len(numbers) + 1)):
            raise ValueError("remediation steps must be ordered consecutively from 1")
        return self

    def traceable_items(self) -> list[TraceableContent]:
        """Return all text-bearing remediation fields for trace validation."""
        return [
            content
            for step in self.steps
            for content in (step.action, step.owner_role, step.decision, step.end_state)
        ]


class ControlGenerationInput(BaseModel):
    """Only retrieved requirement mappings may supply identifiers to the drafter."""

    retrieved_mappings: list[RequirementMapping] = Field(min_length=1)
    selected_requirement_ids: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def selected_ids_must_have_been_retrieved(self) -> "ControlGenerationInput":
        retrieved_ids = {mapping.requirement_reference for mapping in self.retrieved_mappings}
        unknown = set(self.selected_requirement_ids) - retrieved_ids
        if unknown:
            raise ValueError(f"selected requirement IDs were not retrieved: {sorted(unknown)}")
        return self


class ControlGenerationOutput(BaseModel):
    """The deterministic result, validated against the input's retrieved IDs."""

    model_config = ConfigDict(extra="forbid")

    control: DraftControl
    remediation_plan: DraftRemediationPlan


def validate_traceability(
    output: ControlGenerationOutput,
    retrieved_mappings: list[RequirementMapping],
) -> None:
    """Reject draft text that cites an ID absent from the supplied retrieval result."""
    retrieved_ids = {mapping.requirement_reference for mapping in retrieved_mappings}
    for content in [*output.control.traceable_items(), *output.remediation_plan.traceable_items()]:
        unknown = set(content.requirement_ids) - retrieved_ids
        if unknown:
            raise ValueError(f"draft content cites IDs that were not retrieved: {sorted(unknown)}")


def build_source_grounded_control_draft_request(generation_input: ControlGenerationInput) -> StructuredRequest:
    """Create a one-requirement drafting request without evidence or asset data."""
    if len(generation_input.selected_requirement_ids) != 1:
        raise ValueError("source-grounded drafting requires exactly one selected requirement ID")
    requirement_id = generation_input.selected_requirement_ids[0]
    mapping = next(item for item in generation_input.retrieved_mappings if item.requirement_reference == requirement_id)
    return StructuredRequest(
        operation="source_grounded_requirement_control_draft",
        system_prompt=(
            "Create a draft-only control and remediation plan for exactly one requirement. "
            "Use only the supplied retrieved local requirement record. Do not make a compliance determination. "
            "Every meaningful text field must cite the supplied requirement_reference and is_draft must remain true. "
            "Return only the requested JSON schema."
        ),
        input_payload={
            "requirement": {
                "standard_id": mapping.standard.standard_id,
                "version": mapping.standard.version,
                "requirement_reference": mapping.requirement_reference,
                "source_name": mapping.source_name,
                "source_locator": mapping.source_locator,
                "retrieved_excerpt": mapping.draft_summary,
            },
            "safety_boundary": "Draft guidance for SME tailoring only; no compliance conclusion or operational action.",
        },
        response_schema_name="ControlGenerationOutput",
        max_output_tokens=2_000,
        reasoning_effort="low",
    )


def validate_requirement_specific_traceability(output: ControlGenerationOutput, requirement_id: str) -> None:
    """Require every generated statement to cite the one requested requirement."""
    for content in [*output.control.traceable_items(), *output.remediation_plan.traceable_items()]:
        if set(content.requirement_ids) != {requirement_id}:
            raise ValueError("requirement-specific draft content must cite exactly the selected requirement ID")


def generate_source_grounded_control_draft(
    generation_input: ControlGenerationInput,
    provider: StructuredProvider,
    settings: ProviderSettings,
) -> ProviderResult[ControlGenerationOutput]:
    """Run a pre-approved provider through the bounded source-grounded seam.

    The fake provider is the test default. The UI and graph intentionally do not
    call this function until the user selects a model and approves the exact
    bounded request that would transmit one retrieved excerpt.
    """
    request = build_source_grounded_control_draft_request(generation_input)
    result = generate_with_retry(provider, request, ControlGenerationOutput, settings)
    validate_traceability(result.parsed_output, generation_input.retrieved_mappings)
    validate_requirement_specific_traceability(result.parsed_output, generation_input.selected_requirement_ids[0])
    return result


def generate_draft_control_and_remediation(
    generation_input: ControlGenerationInput,
) -> ControlGenerationOutput:
    """Create a safe, generic fake draft linked only to selected retrieved IDs."""
    requirement_ids = generation_input.selected_requirement_ids
    identifier_suffix = re.sub(r"[^a-z0-9]+", "-", "-".join(requirement_ids).casefold()).strip("-")
    selected_mapping = next(
        mapping
        for mapping in generation_input.retrieved_mappings
        if mapping.requirement_reference == requirement_ids[0]
    )
    standard_label = f"{selected_mapping.standard.standard_id}-{selected_mapping.standard.version} {selected_mapping.requirement_reference}"

    def traced(text: str) -> TraceableContent:
        return TraceableContent(text=text, requirement_ids=requirement_ids)

    control = DraftControl(
        control_id=f"draft-control-{identifier_suffix}",
        title=traced(f"Draft {standard_label} review control"),
        objective=traced(f"Draft a repeatable, human-reviewed review of {standard_label} against the cited local source material and supporting synthetic records."),
        activities=[ControlActivity(activity=traced(f"Review the cited local source material for {standard_label}, the synthetic evidence, and the simulated baseline observation."))],
        control_type=traced("Detective and preventive draft control"),
        owner_role=traced("Compliance manager"),
        performer=traced("Compliance analyst"),
        trigger_frequency=traced("For each synthetic review and after a simulated material change."),
        procedure=traced("Compare the retrieved requirement with draft control language and record questions for human review."),
        evidence_expectation=traced("Retain synthetic review notes, cited requirement metadata, and approval decision in the local demonstration record."),
        exception_escalation=traced("Escalate incomplete synthetic inputs or unresolved variance to the compliance manager; do not close the draft gap automatically."),
        test_procedure=traced("A reviewer checks that every draft statement cites a retrieved requirement ID and that an approval decision exists before export."),
        assumptions=[traced("This is a fictional local demonstration using synthetic evidence and simulated asset observations.")],
        tailoring_questions=[traced("Which organization-specific owner, frequency, evidence retention period, and escalation route should the SME approve?")],
    )
    remediation_plan = DraftRemediationPlan(
        plan_id=f"draft-remediation-{identifier_suffix}",
        control_id=control.control_id,
        steps=[
            RemediationStep(step_number=1, action=traced("Validate the synthetic evidence and baseline variance with the assigned reviewer."), owner_role=traced("Compliance analyst"), decision=traced("Are the synthetic inputs complete enough to continue?"), end_state=traced("Continue to draft tailoring questions, or stop safely and request missing information.")),
            RemediationStep(step_number=2, action=traced("Document organization-specific control tailoring and the proposed remediation approach."), owner_role=traced("Compliance manager"), decision=traced("Does the reviewer approve the draft for local export?"), end_state=traced("Approve for local draft export, request edits, or reject with no workflow creation.")),
            RemediationStep(step_number=3, action=traced("Present the approved draft at the existing human approval gate."), owner_role=traced("Compliance manager"), decision=traced("Was explicit human approval recorded?"), end_state=traced("Only an approved decision may create the simulated local workflow; all other outcomes stop without a write.")),
        ],
    )
    output = ControlGenerationOutput(control=control, remediation_plan=remediation_plan)
    validate_traceability(output, generation_input.retrieved_mappings)
    return output
