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
from nerc_compliance_intelligence.requirement_extraction import summarize_requirement_text
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
                "domain": mapping.domain,
                "applicable_systems": mapping.applicable_systems,
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
    if mapping.domain and mapping.domain != "Requirement":
        return mapping.domain
    match = re.search(r"Table\s+R\s*\d+\s*[–-]\s*([^\n.]{3,100})", source_text, flags=re.IGNORECASE)
    if match:
        return match.group(1).strip(" -–")
    return f"{mapping.standard.standard_id}-{mapping.standard.version} {mapping.requirement_reference}"


def _cadence_from_source(source_text: str) -> str | None:
    """Return a visible timing phrase when the source states one."""
    match = re.search(
        r"(?:at least once every|within|intervals? no greater than)\s+"
        r"\d+\s+calendar\s+(?:days|months)",
        source_text,
        flags=re.IGNORECASE,
    )
    return match.group(0).casefold() if match else None


def _local_requirement_context(mapping: RequirementMapping) -> RequirementDraftContext:
    """Map approved CIP wording to bounded, readable local draft actions."""
    source_text = _source_text(mapping)
    title = _requirement_title(mapping, source_text)
    normalized_title = title.casefold()
    cadence = _cadence_from_source(source_text)
    requirement_summary = summarize_requirement_text(
        source_text,
        mapping.requirement_reference,
    )

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
        if "physical input/output ports" in source_text.casefold():
            return RequirementDraftContext(
                title="Physical input/output port protection",
                activity="Inventory applicable physical input/output ports, determine whether each port is necessary, and protect unnecessary ports through configuration restrictions, physical controls, or an approved procedural safeguard.",
                owner_role="System security owner with the applicable system owner",
                trigger_frequency="Before production use, after relevant configuration changes, and during the documented periodic review",
                evidence_expectation="Retain the physical-port inventory, necessity determination, protection method, approval, and validation evidence.",
                exception_escalation="Escalate an exposed unnecessary physical port or an unsupported protection method to the system security owner.",
            )
        return RequirementDraftContext(
            title=title,
            activity="Maintain an approved logical ports and services baseline for each applicable system or asset group. Document the business or operational need for every enabled port or service and compare actual configurations with the approved baseline.",
            owner_role="System security owner with the applicable system owner",
            trigger_frequency="Before enabling or changing an in-scope port or service and during the documented periodic review",
            evidence_expectation="Retain the port/service inventory, documented business need, approval or technical-feasibility rationale, and review record.",
            exception_escalation="Escalate an enabled port or service without documented need or an unprotected physical port to the system security owner.",
        )
    if "security patch management" in normalized_title:
        lowered_source = source_text.casefold()
        if "source or sources" in lowered_source and "tracking" in lowered_source:
            return RequirementDraftContext(
                title="Patch source and asset tracking",
                activity="Maintain an asset-to-patch-source mapping with product, version, monitored source, monitoring method, and accountable owner. Document the workflow for identifying, evaluating, disposing, implementing, and retaining evidence for security patches.",
                owner_role="Patch management owner with the applicable system owner",
                trigger_frequency="When an applicable asset or patch source changes and during each patch-monitoring cycle",
                evidence_expectation="Retain the asset inventory, approved patch-source mapping, monitoring records, ownership assignments, and patch-management procedure.",
                exception_escalation="Escalate an updateable asset without a monitored patch source or accountable owner to the patch management owner.",
            )
        if "evaluate security patches" in lowered_source:
            return RequirementDraftContext(
                title="Security patch applicability evaluation",
                activity="Review every documented patch source, identify releases since the previous completed evaluation, assess applicability, and record the evaluator, evaluation date, decision, and rationale.",
                owner_role="Patch management owner with the applicable system owner",
                trigger_frequency=cadence.capitalize() if cadence else "At the source-defined patch-evaluation interval",
                evidence_expectation="Retain dated source checks, released-patch inventories, applicability decisions, rationales, reviewer records, and any linked patch application or mitigation plan disposition records.",
                exception_escalation="Escalate an overdue evaluation or an unevaluated released patch to the patch management owner.",
            )
        if "take one of the following actions" in lowered_source:
            return RequirementDraftContext(
                title="Patch application or mitigation disposition",
                activity="Track each applicable patch through disposition. Before the source-defined deadline, apply the patch, create a dated mitigation plan, or revise an existing mitigation plan with defined actions and a completion timeframe.",
                owner_role="Patch management owner with the applicable system owner",
                trigger_frequency=cadence.capitalize() if cadence else "After each applicable patch evaluation and before the source-defined disposition deadline",
                evidence_expectation="Retain the applicability record, disposition deadline, installation evidence or dated mitigation plan, planned actions, timeframe, and approvals.",
                exception_escalation="Escalate an applicable patch without timely installation evidence or a complete dated mitigation plan.",
            )
        if "implement the plan within" in lowered_source:
            return RequirementDraftContext(
                title="Patch mitigation plan completion and approval",
                activity="Track mitigation-plan milestones and complete each plan within its stated timeframe. Require documented CIP Senior Manager or delegate approval before revising the plan or extending its timeframe.",
                owner_role="Patch management owner with CIP Senior Manager oversight",
                trigger_frequency="Continuously against each approved mitigation-plan timeframe",
                evidence_expectation="Retain mitigation implementation records, milestone tracking, completion validation, and approvals for revisions or extensions.",
                exception_escalation="Escalate an overdue mitigation action or an unapproved plan revision or extension to the CIP Senior Manager or delegate.",
            )
        return RequirementDraftContext(
            title=title,
            activity="Evaluate security patches from documented sources for applicability, then apply the patch, create or revise a mitigation plan, or document why the patch is not applicable.",
            owner_role="Patch management owner with the applicable system owner",
            trigger_frequency=cadence.capitalize() if cadence else "At the source-defined patch-evaluation interval and after an applicable patch is identified",
            evidence_expectation="Retain documented patch sources, applicability evaluations, patch actions, mitigation plans, and completion or revision records.",
            exception_escalation="Escalate an overdue applicability evaluation, patch action, or mitigation-plan milestone to the patch management owner.",
        )
    if "malicious code prevention" in normalized_title:
        lowered_source = source_text.casefold()
        if "mitigate the threat" in lowered_source:
            return RequirementDraftContext(
                title="Malicious code response",
                activity="Maintain and execute a documented process to triage, contain, eradicate, recover from, and record detected malicious code, including required escalation decisions.",
                owner_role="Cybersecurity operations owner with the applicable system owner",
                trigger_frequency="Whenever malicious code is detected",
                evidence_expectation="Retain detection records, investigation notes, containment and eradication actions, recovery validation, escalation, and closure evidence.",
                exception_escalation="Escalate an unresolved malicious-code detection or incomplete response record to cybersecurity operations and incident response leadership.",
            )
        if "signatures or patterns" in lowered_source:
            return RequirementDraftContext(
                title="Malicious code signature and pattern updates",
                activity="Document the approved source, retrieval method, testing, installation, failure handling, and validation process for malicious-code signatures or patterns.",
                owner_role="Cybersecurity operations owner with the applicable system owner",
                trigger_frequency="When updated signatures or patterns are released and at the organization-approved monitoring interval",
                evidence_expectation="Retain update notifications, testing results, deployment records, failed-update investigations, and validation evidence.",
                exception_escalation="Escalate stale signatures, failed updates, or incomplete testing and installation evidence to cybersecurity operations.",
            )
        return RequirementDraftContext(
            title=title,
            activity="Maintain documented malicious-code prevention processes and record the response used to mitigate the threat of detected malicious code.",
            owner_role="Cybersecurity operations owner with the applicable system owner",
            trigger_frequency="Continuously for detection capability and whenever malicious code is detected",
            evidence_expectation="Retain the documented prevention process, detection or response records, and mitigation actions for detected malicious code.",
            exception_escalation="Escalate a detected malicious-code event without documented mitigation to the cybersecurity operations owner.",
        )
    if "security event monitoring" in normalized_title:
        lowered_source = source_text.casefold()
        if "log events" in lowered_source:
            activity = "Maintain a logging baseline and configure applicable systems to record the source-required security event classes. Test that each required event can be generated, collected, and retrieved."
            evidence = "Retain the logging baseline, configuration evidence, event-generation tests, collection results, and documented technical limitations."
        elif "generate alerts" in lowered_source:
            activity = "Maintain an approved security-event alert catalog, configure the source-required alerts, verify recipients and escalation paths, and periodically test alert generation and receipt."
            evidence = "Retain the alert catalog, rule configuration, recipient and escalation mapping, test events, delivery results, and exception records."
        elif "retain applicable event logs" in lowered_source:
            activity = "Configure applicable log sources or centralized logging systems to retain the required event records for the source-defined period and periodically validate available history and capacity."
            evidence = "Retain configuration records, storage and capacity checks, retention-period reports, gap investigations, and validation results."
        else:
            activity = "Perform and document the source-required review of summarized or sampled logged events, record systems covered and findings, and escalate potential undetected Cyber Security Incidents."
            evidence = "Retain the review method, review date, reviewer, systems covered, sampled or summarized events, findings, disposition, and escalation records."
        return RequirementDraftContext(
            title=title,
            activity=activity,
            owner_role="Security monitoring owner with the applicable system owner",
            trigger_frequency=cadence.capitalize() if cadence else "At the source-defined interval and when a monitoring exception occurs",
            evidence_expectation=evidence,
            exception_escalation="Escalate missing logs, failed alerts, retention gaps, overdue reviews, or unresolved findings to the security monitoring owner.",
        )
    if "system access control" in normalized_title:
        return RequirementDraftContext(
            title=title,
            activity=f"Establish and operate an access-control procedure that addresses this source-derived requirement: {requirement_summary} Record applicable systems, configuration or procedural enforcement, exceptions, approvals, and validation results.",
            owner_role="Identity and access management owner with the applicable system owner",
            trigger_frequency=cadence.capitalize() if cadence else "Before granting or changing access and at the source-defined review interval",
            evidence_expectation="Retain applicable-system scope, access-control configuration or procedures, account or authorization records, exceptions, approvals, and validation evidence.",
            exception_escalation="Escalate an unenforced access requirement, unauthorized access, overdue action, or unsupported technical exception to the access-control owner.",
        )
    return RequirementDraftContext(
        title=title,
        activity=(
            f"Establish and maintain a documented {title.casefold()} procedure. Identify the applicable systems, "
            f"assign accountable owners, perform and record the required activity, and resolve exceptions. "
            f"The procedure must address this source-derived requirement: {requirement_summary}"
        ),
        owner_role=f"{title} control owner with the applicable system owner",
        trigger_frequency="At the source-defined interval or before the applicable activity is completed",
        evidence_expectation=(
            "Retain the approved procedure, applicability record, completed activity records, exceptions, "
            "required approvals, and validation evidence linked to the cited requirement."
        ),
        exception_escalation=(
            f"Escalate an overdue activity, an unresolved exception, or incomplete {title.casefold()} evidence "
            "to the control owner and compliance manager for SME disposition."
        ),
    )


def generate_draft_control_and_remediation(
    generation_input: ControlGenerationInput,
) -> ControlGenerationOutput:
    """Create a local, source-aware draft while preserving traceable requirement IDs."""
    requirement_ids = generation_input.selected_requirement_ids
    selected_mapping = next(
        mapping
        for mapping in generation_input.retrieved_mappings
        if mapping.requirement_reference == requirement_ids[0]
    )
    context = _local_requirement_context(selected_mapping)
    standard_label = f"{selected_mapping.standard.standard_id}-{selected_mapping.standard.version} {selected_mapping.requirement_reference}"
    control_id = re.sub(
        r"[^A-Z0-9]+",
        "-",
        f"DRAFT-{selected_mapping.standard.standard_id}-{selected_mapping.standard.version}-{selected_mapping.requirement_reference}".upper(),
    ).strip("-")
    requirement_summary = summarize_requirement_text(
        _source_text(selected_mapping),
        selected_mapping.requirement_reference,
    )

    def traced(text: str) -> TraceableContent:
        return TraceableContent(text=text, requirement_ids=requirement_ids)

    control = DraftControl(
        control_id=control_id,
        title=traced(f"{context.title} - {selected_mapping.requirement_reference} draft control"),
        objective=traced(f"Ensure the organization can consistently demonstrate the actions required by {standard_label}: {requirement_summary}"),
        activities=[ControlActivity(activity=traced(context.activity))],
        control_type=traced("Preventive and detective draft control"),
        owner_role=traced(context.owner_role),
        performer=traced("Assigned compliance or cybersecurity analyst under the named owner"),
        trigger_frequency=traced(context.trigger_frequency),
        procedure=traced(f"Use the cited local source at {selected_mapping.source_locator}. {context.activity}"),
        evidence_expectation=traced(context.evidence_expectation),
        exception_escalation=traced(context.exception_escalation),
        test_procedure=traced(f"A reviewer samples an in-scope {context.title} record and confirms the required documentation is present and linked to {standard_label}."),
        assumptions=[traced("Applicability, ownership, technology capabilities, frequencies, and evidence retention must be confirmed by the organization's SMEs before implementation.")],
        tailoring_questions=[traced(f"Which of the source-listed applicable systems are in scope, who owns the {context.title.casefold()} process, what operating workflow will be used, and what evidence will demonstrate consistent performance?")],
    )
    remediation_plan = DraftRemediationPlan(
        plan_id=f"draft-remediation-{control_id.casefold()}",
        control_id=control.control_id,
        steps=[
            RemediationStep(step_number=1, action=traced(f"Identify affected systems and records that may not demonstrate {requirement_summary} Apply documented interim safeguards when the SME determines they are necessary."), owner_role=traced(context.owner_role), decision=traced("Is there a credible current exposure or missed requirement activity that needs immediate containment?"), end_state=traced("Affected scope, current condition, interim safeguards, owner, and escalation are documented.")),
            RemediationStep(step_number=2, action=traced(context.activity), owner_role=traced(context.owner_role), decision=traced("Has the corrective action been implemented for every confirmed in-scope system and exception?"), end_state=traced("The approved procedure is implemented, exceptions are governed, and supporting records are retained.")),
            RemediationStep(step_number=3, action=traced(f"Validate the corrected {context.title.casefold()} process through record review or testing, confirm evidence completeness, and obtain required human approval before closure."), owner_role=traced("Independent reviewer or compliance manager"), decision=traced("Do validation results and retained evidence support closure of the remediation item?"), end_state=traced("The reviewer records validation results and either closes the item or returns it for additional corrective action.")),
        ],
    )
    output = ControlGenerationOutput(control=control, remediation_plan=remediation_plan)
    validate_traceability(output, generation_input.retrieved_mappings)
    return output
