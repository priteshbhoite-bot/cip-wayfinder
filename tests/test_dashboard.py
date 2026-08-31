"""Offline checks for the hybrid Streamlit dashboard's safe display data."""

from pathlib import Path

from nerc_compliance_intelligence.app import APP_DESCRIPTION, LANDING_FIELD_HELP, LANDING_HIGHLIGHTS, REFERENCE_OPTIONS, REVIEW_GRAPH_STEPS, SCREEN_NAMES, _model_draft_candidate, demo_dashboard_data


def test_dashboard_has_two_simple_workspaces_after_local_upload() -> None:
    dashboard = demo_dashboard_data()

    assert SCREEN_NAMES == ("Start a review", "Review package")
    assert dashboard["control"].is_draft is True
    assert dashboard["remediation"].is_draft is True
    assert dashboard["baseline"].requires_sme_review is True


def test_dashboard_traceability_stays_with_the_uploaded_document_mapping() -> None:
    dashboard = demo_dashboard_data()

    assert dashboard["control"].objective.requirement_ids == ["Document overview"]
    assert dashboard["remediation"].steps[0].action.requirement_ids == ["Document overview"]
    assert len(dashboard["packages"]) == len(dashboard["uploaded"].requirements)


def test_landing_page_explainer_image_is_packaged_with_the_project() -> None:
    project_root = Path(__file__).resolve().parents[1]

    assert (project_root / "assets" / "local-review-package-flow.png").is_file()


def test_cip_wayfinder_working_logo_is_packaged_with_the_project() -> None:
    project_root = Path(__file__).resolve().parents[1]

    assert (project_root / "assets" / "cip-wayfinder-logo.png").is_file()


def test_review_graph_animation_stops_at_the_human_approval_boundary() -> None:
    assert REVIEW_GRAPH_STEPS[-1] == "Pause for human approval"
    assert len(REVIEW_GRAPH_STEPS) == 6


def test_every_landing_field_has_beginner_safe_hover_help() -> None:
    assert set(LANDING_FIELD_HELP) == {
        "functional_entity",
        "jurisdiction",
        "asset_scope",
        "review_objective",
        "standard_pdf",
        "authorization",
    }
    assert all(help_text for help_text in LANDING_FIELD_HELP.values())


def test_landing_reference_options_are_available_offline() -> None:
    assert "Transmission Operator" in REFERENCE_OPTIONS.functional_entities
    assert len(REFERENCE_OPTIONS.regional_entities) == 6


def test_landing_page_has_three_color_coded_review_waypoints() -> None:
    assert [highlight[1] for highlight in LANDING_HIGHLIGHTS] == ["Upload", "Explore", "Decide"]
    assert [highlight[3] for highlight in LANDING_HIGHLIGHTS] == ["blue", "violet", "green"]


def test_app_description_explains_the_single_standard_review_boundary() -> None:
    description = " ".join(APP_DESCRIPTION)

    assert "one approved local NERC CIP standard at a time" in description
    assert "human review" in description


def test_model_draft_candidate_requires_a_matched_requirement_level_source() -> None:
    dashboard = demo_dashboard_data()

    assert _model_draft_candidate(dashboard) is None
