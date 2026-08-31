"""Contract tests for local scope intake and Applicability Agent questions."""

from nerc_compliance_intelligence.case_intake import CaseIntake, assess_case_intake
from nerc_compliance_intelligence.schemas import StandardVersion


STANDARD = StandardVersion(standard_id="CIP-010", version="5", scope_role="primary")


def test_incomplete_intake_asks_for_each_missing_scope_field() -> None:
    assessment = assess_case_intake(CaseIntake(review_objective=""), STANDARD)

    assert assessment.ready_for_review is False
    assert assessment.applicability.missing_fields == [
        "functional_entity",
        "jurisdiction",
        "asset_scope",
    ]
    assert assessment.questions[-1] == "What review objective should this local draft package support?"


def test_complete_intake_is_ready_without_making_an_applicability_decision() -> None:
    assessment = assess_case_intake(
        CaseIntake(
            functional_entity="Fictional Transmission Operator",
            jurisdiction="Fictional demonstration jurisdiction",
            asset_scope="SUB-ALPHA-RTU-01 simulated review scope",
            review_objective="Prepare a source-grounded draft review package.",
        ),
        STANDARD,
    )

    assert assessment.ready_for_review is True
    assert assessment.questions == []
    assert assessment.applicability.safety_note.startswith("Scope intake only")
