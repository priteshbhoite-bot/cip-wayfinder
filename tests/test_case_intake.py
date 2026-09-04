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
            functional_entity=["Fictional Transmission Operator", "Fictional Reliability Coordinator"],
            jurisdiction=["Fictional demonstration jurisdiction", "Fictional neighboring jurisdiction"],
            asset_scope=["SUB-ALPHA-RTU-01 simulated review scope", "Synthetic control-center supporting scope"],
            review_objective="Prepare a source-grounded draft review package.",
        ),
        STANDARD,
    )

    assert assessment.ready_for_review is True
    assert assessment.questions == []
    assert assessment.applicability.safety_note.startswith("Scope intake only")


def test_scope_fields_accept_multiple_trimmed_values_and_remove_duplicates() -> None:
    intake = CaseIntake(
        functional_entity=[" Transmission Operator ", "Transmission Operator", "Reliability Coordinator"],
        jurisdiction=["WECC", "WECC", "TRE"],
        asset_scope=["Synthetic RTU group", "Synthetic server group"],
    )

    assert intake.functional_entity == ["Transmission Operator", "Reliability Coordinator"]
    assert intake.jurisdiction == ["WECC", "TRE"]
    assert intake.asset_scope == ["Synthetic RTU group", "Synthetic server group"]


def test_scope_fields_allow_all_available_role_and_region_choices() -> None:
    functional_entities = [f"Functional Entity {number}" for number in range(18)]
    regional_entities = [f"Regional Entity {number}" for number in range(18)]
    asset_scopes = [f"Synthetic asset scope {number}" for number in range(25)]

    intake = CaseIntake(
        functional_entity=functional_entities,
        jurisdiction=regional_entities,
        asset_scope=asset_scopes,
    )

    assert intake.functional_entity == functional_entities
    assert intake.jurisdiction == regional_entities
    assert intake.asset_scope == asset_scopes
