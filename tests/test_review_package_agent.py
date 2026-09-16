"""Contract tests for the source-grounded Review Package Agent."""

from __future__ import annotations

import pytest

from nerc_compliance_intelligence.app import demo_dashboard_data
from nerc_compliance_intelligence.review_package_agent import (
    FakeReviewPackageModel,
    REVIEW_PACKAGE_OBJECTIVE,
    ReviewPackageAgentInput,
    ReviewPackageAgentOutput,
    run_review_package_agent,
)


def test_review_package_agent_assembles_existing_grounded_content() -> None:
    dashboard = demo_dashboard_data()
    output = dashboard["review_package_agent"]

    assert output.objective == REVIEW_PACKAGE_OBJECTIVE
    assert output.document_title == dashboard["uploaded"].document_title
    assert output.items[0].mapping == dashboard["mapping"]
    assert output.items[0].control == dashboard["control"]
    assert output.items[0].remediation == dashboard["remediation"]
    assert output.local_source_match_count == 0
    assert output.missing_information
    assert dashboard["quality_review"].is_valid is True


def test_review_package_agent_rejects_changed_source_grounded_content() -> None:
    dashboard = demo_dashboard_data()
    valid_output = dashboard["review_package_agent"]
    agent_input = ReviewPackageAgentInput(
        uploaded_standard=dashboard["uploaded"],
        items=valid_output.items,
    )

    class RewritingModel(FakeReviewPackageModel):
        def invoke(
            self,
            prompt: str,
            supplied_input: ReviewPackageAgentInput,
        ) -> ReviewPackageAgentOutput:
            output = super().invoke(prompt, supplied_input)
            return output.model_copy(update={"document_title": "Invented title"})

    with pytest.raises(ValueError, match="changed source-grounded input"):
        run_review_package_agent(agent_input, RewritingModel())
