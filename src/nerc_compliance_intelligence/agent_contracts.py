"""Strict, fake-first contracts for the Milestone 8 Standards and Applicability Agents."""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field, model_validator

from nerc_compliance_intelligence.local_corpus import RequirementChunk, chunk_to_mapping
from nerc_compliance_intelligence.schemas import RequirementMapping, StandardVersion


STANDARDS_AGENT_PROMPT = """You are the Standards Agent for a local compliance review application.
Use only the retrieved source chunks supplied in the input. Do not use memory,
web knowledge, or unstated interpretation. Every draft summary must exactly
reflect a supplied chunk and every citation must identify that chunk's standard,
version, requirement, page/section, source URL, and retrieval date. Return the
strict output schema only. Do not declare compliance or provide legal advice."""

APPLICABILITY_AGENT_PROMPT = """You are the Applicability Agent for a local compliance review application.
Do not guess scope. If Functional Entity, jurisdiction, or standard/version is
missing, ask a direct question for each missing value. Return
ready_for_retrieval=true only when all three scope groups are present. Return the
strict output schema only. Do not make an applicability or compliance decision."""


class StrictSchema(BaseModel):
    """Base model that rejects undeclared fields in agent contracts."""

    model_config = ConfigDict(extra="forbid")


class SourceCitation(StrictSchema):
    chunk_id: str
    standard_id: str
    version: str
    requirement_reference: str
    page: int = Field(ge=1)
    section: str
    source_url: str
    retrieval_date: str


class StandardsAgentInput(StrictSchema):
    retrieved_sources: list[RequirementChunk] = Field(min_length=1)
    scope_role: str = Field(pattern=r"^(primary|supporting)$")


class StandardsAgentOutput(StrictSchema):
    requirement_mappings: list[RequirementMapping] = Field(min_length=1)
    citations: list[SourceCitation] = Field(min_length=1)
    safety_note: str = "Draft source-grounded output; not a compliance conclusion."


class ApplicabilityAgentInput(StrictSchema):
    functional_entity: str | None = None
    jurisdiction: str | None = None
    standard_id: str | None = None
    version: str | None = None


class ApplicabilityAgentOutput(StrictSchema):
    missing_fields: list[str]
    questions: list[str]
    ready_for_retrieval: bool
    safety_note: str = "Scope intake only; not an applicability or compliance decision."

    @model_validator(mode="after")
    def keep_readiness_consistent(self) -> "ApplicabilityAgentOutput":
        if self.ready_for_retrieval != (not self.missing_fields):
            raise ValueError("ready_for_retrieval must match whether scope fields are missing")
        if len(self.questions) != len(self.missing_fields):
            raise ValueError("every missing field requires one direct question")
        return self


class StandardsModel(Protocol):
    def invoke(self, prompt: str, agent_input: StandardsAgentInput) -> StandardsAgentOutput: ...


class ApplicabilityModel(Protocol):
    def invoke(self, prompt: str, agent_input: ApplicabilityAgentInput) -> ApplicabilityAgentOutput: ...


class FakeStandardsModel:
    """Default deterministic model: it copies only the first supplied local chunk."""

    def invoke(self, prompt: str, agent_input: StandardsAgentInput) -> StandardsAgentOutput:
        chunk = agent_input.retrieved_sources[0]
        metadata = chunk.metadata
        return StandardsAgentOutput(
            requirement_mappings=[chunk_to_mapping(chunk, agent_input.scope_role)],
            citations=[
                SourceCitation(
                    chunk_id=chunk.chunk_id,
                    standard_id=metadata.standard_id,
                    version=metadata.version,
                    requirement_reference=metadata.requirement_reference,
                    page=metadata.page,
                    section=metadata.section,
                    source_url=metadata.source_url,
                    retrieval_date=metadata.retrieval_date.isoformat(),
                )
            ],
        )


class FakeApplicabilityModel:
    """Default deterministic model: it asks instead of guessing missing scope."""

    _QUESTIONS = {
        "functional_entity": "Which Functional Entity should this review consider?",
        "jurisdiction": "Which jurisdiction applies to this review?",
        "standard_version": "Which standard ID and version should this review use?",
    }

    def invoke(self, prompt: str, agent_input: ApplicabilityAgentInput) -> ApplicabilityAgentOutput:
        missing: list[str] = []
        if not agent_input.functional_entity:
            missing.append("functional_entity")
        if not agent_input.jurisdiction:
            missing.append("jurisdiction")
        if not agent_input.standard_id or not agent_input.version:
            missing.append("standard_version")
        return ApplicabilityAgentOutput(
            missing_fields=missing,
            questions=[self._QUESTIONS[field] for field in missing],
            ready_for_retrieval=not missing,
        )


def run_standards_agent(
    agent_input: StandardsAgentInput,
    model: StandardsModel | None = None,
) -> StandardsAgentOutput:
    """Run the fake-first Standards Agent and reject output unsupported by retrieved chunks."""
    output = (model or FakeStandardsModel()).invoke(STANDARDS_AGENT_PROMPT, agent_input)
    sources_by_id = {chunk.chunk_id: chunk for chunk in agent_input.retrieved_sources}
    for mapping, citation in zip(output.requirement_mappings, output.citations, strict=True):
        chunk = sources_by_id.get(citation.chunk_id)
        if chunk is None:
            raise ValueError("Standards Agent cited a source that was not retrieved")
        metadata = chunk.metadata
        if (
            citation.standard_id != metadata.standard_id
            or citation.version != metadata.version
            or citation.requirement_reference != metadata.requirement_reference
            or citation.page != metadata.page
            or citation.section != metadata.section
            or citation.source_url != metadata.source_url
            or citation.retrieval_date != metadata.retrieval_date.isoformat()
            or mapping.requirement_reference != metadata.requirement_reference
            or mapping.draft_summary != chunk.text
        ):
            raise ValueError("Standards Agent output contains a claim unsupported by its retrieved source")
    return output


def run_applicability_agent(
    agent_input: ApplicabilityAgentInput,
    model: ApplicabilityModel | None = None,
) -> ApplicabilityAgentOutput:
    """Run the fake-first scope intake agent without making applicability decisions."""
    return (model or FakeApplicabilityModel()).invoke(APPLICABILITY_AGENT_PROMPT, agent_input)
