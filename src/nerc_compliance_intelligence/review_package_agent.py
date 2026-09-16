"""Typed, deterministic assembly agent for the human review package.

The agent organizes already-grounded document knowledge, draft controls, and
remediation plans. It cannot retrieve new material, invent requirement IDs,
approve its own output, render a file, or send an email.
"""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field, model_validator

from nerc_compliance_intelligence.control_remediation import DraftControl, DraftRemediationPlan
from nerc_compliance_intelligence.local_corpus import RequirementChunk
from nerc_compliance_intelligence.schemas import RequirementMapping
from nerc_compliance_intelligence.uploaded_standard import UploadedRequirementOption, UploadedStandard


REVIEW_PACKAGE_OBJECTIVE = "Prepare a source-grounded draft package for SME tailoring."
REVIEW_PACKAGE_AGENT_PROMPT = """You are the Review Package Agent for CIP Wayfinder.
Organize only the supplied, source-grounded document knowledge, draft controls,
and remediation plans into a package for SME tailoring. Preserve every source
link and requirement ID. Identify missing approved-corpus support rather than
inventing information. Keep all content draft-only. Do not determine compliance,
approve the package, render a file, send email, or perform an operational action.
Return the strict output schema only."""


class ReviewPackageAgentItem(BaseModel):
    """One fully traceable package item assembled for human review."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    mapping: RequirementMapping
    knowledge_item: UploadedRequirementOption
    control: DraftControl
    remediation: DraftRemediationPlan
    source_chunks: list[RequirementChunk] = Field(default_factory=list)

    @model_validator(mode="after")
    def keep_item_traceable(self) -> "ReviewPackageAgentItem":
        reference = self.mapping.requirement_reference
        if self.knowledge_item.requirement_reference != reference:
            raise ValueError("knowledge item and requirement mapping must use the same reference")
        if self.remediation.control_id != self.control.control_id:
            raise ValueError("remediation plan must link to its draft control")
        for content in [*self.control.traceable_items(), *self.remediation.traceable_items()]:
            if set(content.requirement_ids) != {reference}:
                raise ValueError("every assembled draft statement must cite its package requirement")
        return self


class ReviewPackageAgentInput(BaseModel):
    """Source-grounded material the agent is permitted to organize."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    uploaded_standard: UploadedStandard
    items: list[ReviewPackageAgentItem] = Field(min_length=1)


class ReviewPackageAgentOutput(BaseModel):
    """Strict package content passed to quality review and human approval."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    objective: str = REVIEW_PACKAGE_OBJECTIVE
    document_title: str = Field(min_length=1)
    document_type: str = Field(min_length=1)
    referenced_standards: list[str] = Field(min_length=1)
    items: list[ReviewPackageAgentItem] = Field(min_length=1)
    local_source_match_count: int = Field(ge=0)
    missing_information: list[str] = Field(default_factory=list)
    safety_note: str = (
        "Draft source-grounded package for SME tailoring; not a compliance conclusion or approval."
    )

    @model_validator(mode="after")
    def keep_objective_and_count_consistent(self) -> "ReviewPackageAgentOutput":
        if self.objective != REVIEW_PACKAGE_OBJECTIVE:
            raise ValueError("Review Package Agent objective cannot be changed")
        expected_matches = sum(bool(item.source_chunks) for item in self.items)
        if self.local_source_match_count != expected_matches:
            raise ValueError("local source match count must match assembled package items")
        return self


class ReviewPackageModel(Protocol):
    def invoke(
        self,
        prompt: str,
        agent_input: ReviewPackageAgentInput,
    ) -> ReviewPackageAgentOutput: ...


class FakeReviewPackageModel:
    """Default local agent that organizes supplied objects without rewriting them."""

    def invoke(
        self,
        prompt: str,
        agent_input: ReviewPackageAgentInput,
    ) -> ReviewPackageAgentOutput:
        del prompt
        uploaded = agent_input.uploaded_standard
        referenced_standards = [
            f"{standard.standard_id}-{standard.version}"
            for standard in (uploaded.referenced_standards or [uploaded.standard])
        ]
        missing_information = [
            (
                f"{item.mapping.requirement_reference}: no approved local corpus match; "
                "verify the uploaded-document summary against the official source."
            )
            for item in agent_input.items
            if not item.source_chunks
        ]
        return ReviewPackageAgentOutput(
            document_title=uploaded.document_title,
            document_type=uploaded.document_type,
            referenced_standards=referenced_standards,
            items=agent_input.items,
            local_source_match_count=sum(bool(item.source_chunks) for item in agent_input.items),
            missing_information=missing_information,
        )


def run_review_package_agent(
    agent_input: ReviewPackageAgentInput,
    model: ReviewPackageModel | None = None,
) -> ReviewPackageAgentOutput:
    """Assemble and verify a draft package without granting approval or export authority."""
    output = (model or FakeReviewPackageModel()).invoke(REVIEW_PACKAGE_AGENT_PROMPT, agent_input)
    uploaded = agent_input.uploaded_standard
    expected_standards = [
        f"{standard.standard_id}-{standard.version}"
        for standard in (uploaded.referenced_standards or [uploaded.standard])
    ]
    if (
        output.document_title != uploaded.document_title
        or output.document_type != uploaded.document_type
        or output.referenced_standards != expected_standards
        or output.items != agent_input.items
    ):
        raise ValueError("Review Package Agent changed source-grounded input content")
    return output
