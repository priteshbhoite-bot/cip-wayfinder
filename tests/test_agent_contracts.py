"""Contract tests for strict, fake-first Milestone 8 agents."""

from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError

from nerc_compliance_intelligence.agent_contracts import (
    ApplicabilityAgentInput,
    ApplicabilityAgentOutput,
    FakeStandardsModel,
    SourceCitation,
    StandardsAgentInput,
    StandardsAgentOutput,
    run_applicability_agent,
    run_standards_agent,
)
from nerc_compliance_intelligence.local_corpus import CorpusMetadata, RequirementChunk


def _source() -> RequirementChunk:
    return RequirementChunk(
        chunk_id="fixture-source-001",
        text="Synthetic source text only.",
        metadata=CorpusMetadata(
            standard_id="CIP-010",
            version="5",
            requirement_reference="Synthetic demo reference",
            **{"Functional Entity": "Synthetic entity"},
            jurisdiction="Synthetic jurisdiction",
            enforcement_status="Synthetic fixture",
            effective_date=date(2026, 1, 1),
            page=1,
            section="Synthetic section",
            source_url="https://example.invalid/fixture",
            retrieval_date=date(2026, 8, 27),
        ),
    )


def test_standards_agent_default_output_uses_only_the_retrieved_source() -> None:
    source = _source()

    output = run_standards_agent(StandardsAgentInput(retrieved_sources=[source], scope_role="primary"))

    assert output.citations[0].chunk_id == source.chunk_id
    assert output.requirement_mappings[0].draft_summary == source.text


def test_standards_agent_rejects_a_model_that_cites_an_unretrieved_source() -> None:
    source = _source()

    class FabricatingModel(FakeStandardsModel):
        def invoke(self, prompt: str, agent_input: StandardsAgentInput) -> StandardsAgentOutput:
            output = super().invoke(prompt, agent_input)
            return output.model_copy(update={"citations": [output.citations[0].model_copy(update={"chunk_id": "not-retrieved"})]})

    with pytest.raises(ValueError, match="not retrieved"):
        run_standards_agent(StandardsAgentInput(retrieved_sources=[source], scope_role="primary"), FabricatingModel())


def test_applicability_agent_asks_for_every_missing_scope_group() -> None:
    output = run_applicability_agent(ApplicabilityAgentInput())

    assert output.missing_fields == ["functional_entity", "jurisdiction", "standard_version"]
    assert output.ready_for_retrieval is False
    assert len(output.questions) == 3


def test_applicability_agent_marks_complete_scope_ready_without_guessing() -> None:
    output = run_applicability_agent(
        ApplicabilityAgentInput(
            functional_entity="Synthetic entity",
            jurisdiction="Synthetic jurisdiction",
            standard_id="CIP-010",
            version="5",
        )
    )

    assert output.missing_fields == []
    assert output.questions == []
    assert output.ready_for_retrieval is True


def test_contract_schemas_reject_extra_fields_and_inconsistent_readiness() -> None:
    with pytest.raises(ValidationError):
        ApplicabilityAgentInput.model_validate({"jurisdiction": "scope", "guessed_field": "not allowed"})
    with pytest.raises(ValidationError, match="ready_for_retrieval"):
        ApplicabilityAgentOutput(missing_fields=["jurisdiction"], questions=["Which jurisdiction?"], ready_for_retrieval=True)
