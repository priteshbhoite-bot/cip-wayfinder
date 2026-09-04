"""Deterministic, traceable draft controls and remediation plans for Milestone 10.

The module deliberately does not interpret a standard, decide applicability, or
claim compliance.  It can only create generic draft language from requirement
identifiers already returned by local retrieval.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

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


@dataclass(frozen=True)
class RequirementDraftContext:
    """Requirement-specific local drafting details derived from approved source text."""

    title: str
    activity: str
    owner_role: str
    trigger_frequency: str
    evidence_expectation: str
    exception_escalation: str


def _source_text(mapping: RequirementMapping) -> str:
    """Normalize locally retrieved text without adding facts from outside the source."""
    return " ".join(mapping.draft_summary.split())


def _requirement_title(mapping: RequirementMapping, source_text: str) -> str:
    """Prefer the requirement table title visible in the approved local source."""
    match = re.search(r"Table\s+R\s*\d+\s*[–-]\s*([^\n.]{3,100})", source_text, flags=re.IGNORECASE)
    if match:
        return match.group(1).strip(" -–")
    return f"{mapping.standard.standard_id}-{mapping.standard.version} {mapping.requirement_reference}"


def _cadence_from_source(source_text: str) -> str | None:
    """Return a visible timing phrase when the source states one."""
    match = re.search(r"(?:at least once every|within)\s+\d+\s+calendar\s+(?:days|months)", source_text, flags=re.IGNORECASE)
    return match.group(0).casefold() if match else None


def _local_requirement_context(mapping: RequirementMapping) -> RequirementDraftContext:
    """Map approved CIP wording to bounded, readable local draft actions."""
    source_text = _source_text(mapping)
    title = _requirement_title(mapping, source_text)
    normalized_title = title.casefold()
    cadence = _cadence_from_source(source_text)

    if "configuration change management" in normalized_title:
        return RequirementDraftContext(
            title=title,
            activity="For each in-scope configuration change, document authorization, impact assessment, testing results, and post-change verification before closing the change record.",
            owner_role="Configuration change manager with the applicable system owner",
            trigger_frequency="Before implementation and after each authorized in-scope configuration change",
            evidence_expectation="Retain the approved change record, impact assessment, test results, and post-change verification record linked to the change.",
            exception_escalation="Escalate incomplete authorization, testing, or verification records to the configuration change manager for SME disposition.",
        )
    if "configuration monitoring" in normalized_title:
        return RequirementDraftContext(
            title=title,
            activity="Maintain a documented configuration-monitoring process for the source-listed security-relevant configuration changes and investigate detected unauthorized changes.",
            owner_role="Configuration monitoring owner with the applicable system owner",
            trigger_frequency=cadence.capitalize() if cadence else "At the source-defined monitoring interval and when an unauthorized change is detected",
            evidence_expectation="Retain monitoring outputs, detected-change investigations, and documented disposition for each unauthorized change.",
            exception_escalation="Escalate a detected unauthorized change or missing investigation record to the configuration monitoring owner.",
        )
    if "vulnerability assessment" in normalized_title:
        return RequirementDraftContext(
            title=title,
            activity="Perform and document the source-required vulnerability assessment method for each applicable system, including the assessment results and any follow-up actions.",
            owner_role="Vulnerability assessment owner with the applicable system owner",
            trigger_frequency=cadence.capitalize() if cadence else "At the source-defined vulnerability-assessment interval",
            evidence_expectation="Retain the assessment scope, method, results, and documented follow-up actions for each applicable system.",
            exception_escalation="Escalate an overdue assessment, incomplete result, or unresolved follow-up action to the vulnerability assessment owner.",
        )
    if "ports and services" in normalized_title:
        return RequirementDraftContext(
            title=title,
            activity="Document the need for enabled logical ports and services, limit unnecessary network-accessible ports, and protect the source-listed physical input/output ports.",
            owner_role="System security owner with the applicable system owner",
            trigger_frequency="Before enabling or changing an in-scope port or service and during the documented periodic review",
            evidence_expectation="Retain the port/service inventory, documented business need, approval or technical-feasibility rationale, and review record.",
            exception_escalation="Escalate an enabled port or service without documented need or an unprotected physical port to the system security owner.",
        )
    if "security patch management" in normalized_title:
        return RequirementDraftContext(
            title=title,
            activity="Evaluate security patches from documented sources for applicability, then apply the patch, create or revise a mitigation plan, or document why the patch is not applicable.",
            owner_role="Patch management owner with the applicable system owner",
            trigger_frequency=cadence.capitalize() if cadence else "At the source-defined patch-evaluation interval and after an applicable patch is identified",
            evidence_expectation="Retain documented patch sources, applicability evaluations, patch actions, mitigation plans, and completion or revision records.",
            exception_escalation="Escalate an overdue applicability evaluation, patch action, or mitigation-plan milestone to the patch management owner.",
        )
    if "malicious code prevention" in normalized_title:
        return RequirementDraftContext(
            title=title,
            activity="Maintain documented malicious-code prevention processes and record the response used to mitigate the threat of detected malicious code.",
            owner_role="Cybersecurity operations owner with the applicable system owner",
            trigger_frequency="Continuously for detection capability and whenever malicious code is detected",
            evidence_expectation="Retain the documented prevention process, detection or response records, and mitigation actions for detected malicious code.",
            exception_escalation="Escalate a detected malicious-code event without documented mitigation to the cybersecurity operations owner.",
        )
    return RequirementDraftContext(
        title=title,
        activity=f"Maintain a documented process that addresses the locally retrieved {title} requirement and record the result of each in-scope review.",
        owner_role="Compliance manager with the applicable system owner",
        trigger_frequency="At the source-defined interval or before the applicable activity is completed",
        evidence_expectation="Retain the documented process, in-scope review records, and required approvals linked to the cited requirement.",
        exception_escalation="Escalate incomplete process records or unresolved review questions to the compliance manager for SME disposition.",
    )


def generate_draft_control_and_remediation(
    generation_input: ControlGenerationInput,
) -> ControlGenerationOutput:
    """Create a local, source-aware draft while preserving traceable requirement IDs."""
    requirement_ids = generation_input.selected_requirement_ids
    identifier_suffix = re.sub(r"[^a-z0-9]+", "-", "-".join(requirement_ids).casefold()).strip("-")
    selected_mapping = next(
        mapping
        for mapping in generation_input.retrieved_mappings
        if mapping.requirement_reference == requirement_ids[0]
    )
    context = _local_requirement_context(selected_mapping)
    standard_label = f"{selected_mapping.standard.standard_id}-{selected_mapping.standard.version} {selected_mapping.requirement_reference}"

    def traced(text: str) -> TraceableContent:
        return TraceableContent(text=text, requirement_ids=requirement_ids)

    control = DraftControl(
        control_id=f"draft-control-{identifier_suffix}",
        title=traced(f"Draft {standard_label} — {context.title}"),
        objective=traced(f"Maintain a documented, human-reviewed process for {context.title} that addresses the cited {standard_label} source requirement."),
        activities=[ControlActivity(activity=traced(context.activity))],
        control_type=traced("Preventive and detective draft control"),
        owner_role=traced(context.owner_role),
        performer=traced("Assigned compliance or cybersecurity analyst under the named owner"),
        trigger_frequency=traced(context.trigger_frequency),
        procedure=traced(f"Use the cited local source at {selected_mapping.source_locator} to guide the review; {context.activity}"),
        evidence_expectation=traced(context.evidence_expectation),
        exception_escalation=traced(context.exception_escalation),
        test_procedure=traced(f"A reviewer samples an in-scope {context.title} record and confirms the required documentation is present and linked to {standard_label}."),
        assumptions=[traced("This local draft is based only on the approved retrieved requirement text and requires organization-specific SME tailoring.")],
        tailoring_questions=[traced(f"Which systems, owner roles, documented interval, retention period, and exception route should the SME approve for {context.title}?")],
    )
    remediation_plan = DraftRemediationPlan(
        plan_id=f"draft-remediation-{identifier_suffix}",
        control_id=control.control_id,
        steps=[
            RemediationStep(step_number=1, action=traced(f"Confirm the applicable systems and current documented process for {context.title}."), owner_role=traced(context.owner_role), decision=traced("Is the in-scope process and supporting documentation complete enough for SME review?"), end_state=traced("Proceed with the requirement-specific review or request the missing scope and documentation.")),
            RemediationStep(step_number=2, action=traced(context.activity), owner_role=traced(context.owner_role), decision=traced("Does the completed review satisfy the organization-tailored draft procedure?"), end_state=traced("Record the result, document an exception, or return the draft for tailoring.")),
            RemediationStep(step_number=3, action=traced(context.exception_escalation), owner_role=traced("Compliance manager"), decision=traced("Has a human reviewer approved the proposed draft disposition?"), end_state=traced("Keep the draft for human decision; no operational change or workflow closure occurs automatically.")),
        ],
    )
    output = ControlGenerationOutput(control=control, remediation_plan=remediation_plan)
    validate_traceability(output, generation_input.retrieved_mappings)
    return output
