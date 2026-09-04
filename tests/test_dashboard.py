"""Offline checks for the hybrid Streamlit dashboard's safe display data."""

from pathlib import Path

from nerc_compliance_intelligence.app import APP_DESCRIPTION, LANDING_FIELD_HELP, LANDING_HIGHLIGHTS, REFERENCE_OPTIONS, REVIEW_GRAPH_STEPS, SCREEN_NAMES, _model_draft_candidate, demo_dashboard_data


def test_dashboard_has_two_simple_workspaces_after_local_upload() -> None:
    dashboard = demo_dashboard_data()

    assert SCREEN_NAMES == ("Start a review", "Review package")
    assert dashboard["control"].is_draft is True
    assert dashboard["remediation"].is_draft is True


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
    assert len(REVIEW_GRAPH_STEPS) == 4


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


def test_scope_fields_use_direct_unbounded_multiselects() -> None:
    project_root = Path(__file__).resolve().parents[1]
    app_source = (project_root / "src" / "nerc_compliance_intelligence" / "app.py").read_text(encoding="utf-8")

    assert "All listed" not in app_source
    assert "_expand_all_listed_choice" not in app_source
    assert "max_selections=" not in app_source
    assert 'st.multiselect("Functional Entity", REFERENCE_OPTIONS.functional_entities' in app_source
    assert 'st.multiselect("Regional Entity", REFERENCE_OPTIONS.regional_entities' in app_source
    assert 'st.multiselect("Asset scope", REFERENCE_OPTIONS.asset_scope_suggestions' in app_source


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


def test_review_package_contains_only_product_facing_sections() -> None:
    project_root = Path(__file__).resolve().parents[1]
    app_source = (project_root / "src" / "nerc_compliance_intelligence" / "app.py").read_text(encoding="utf-8")

    for section_name in (
        "Requirements and sources",
        "Draft controls and remediation",
        "Optional model enhancement",
        "Human decision",
        "Approve package",
        "Download approved Word package",
        "Recipient email address",
        "Send approved Word package",
    ):
        assert section_name in app_source
    assert "Advanced demo details" not in app_source
    assert "Show graph path" not in app_source
    assert "st.download_button" in app_source
    assert "mime=WORD_MIME_TYPE" in app_source


def test_open_review_button_uses_a_pre_rerun_workspace_callback() -> None:
    project_root = Path(__file__).resolve().parents[1]
    app_source = (project_root / "src" / "nerc_compliance_intelligence" / "app.py").read_text(encoding="utf-8")

    assert "def _open_review_workspace" in app_source
    assert "on_click=_open_review_workspace" in app_source


def test_requirement_section_shows_a_summary_instead_of_verbatim_source_language() -> None:
    project_root = Path(__file__).resolve().parents[1]
    app_source = (project_root / "src" / "nerc_compliance_intelligence" / "app.py").read_text(encoding="utf-8")

    assert "st.markdown(_requirement_vital_summary(control))" in app_source
    assert "_compact_requirement_language(source_chunks)" not in app_source
    assert "Plain-language draft summary" in app_source
    assert "not the official NERC requirement wording" in app_source
    assert "height=240" not in app_source


def test_review_package_sections_and_requirement_details_start_collapsed() -> None:
    project_root = Path(__file__).resolve().parents[1]
    app_source = (project_root / "src" / "nerc_compliance_intelligence" / "app.py").read_text(encoding="utf-8")

    for section_name in (
        "Requirements and sources",
        "Draft controls and remediation",
        "Optional model enhancement",
        "Human decision",
    ):
        assert f'st.expander("{section_name}", expanded=False' in app_source
    assert '"Show vital requirement summary"' in app_source
    assert "value=False" in app_source
    assert "if show_requirement:" in app_source

def test_dashboard_runtime_does_not_include_evidence_or_baseline_analysis() -> None:
    dashboard = demo_dashboard_data()

    assert "evidence" not in dashboard
    assert "baseline" not in dashboard

def test_review_renderer_has_no_stale_evidence_or_baseline_data_access() -> None:
    project_root = Path(__file__).resolve().parents[1]
    app_source = (project_root / "src" / "nerc_compliance_intelligence" / "app.py").read_text(encoding="utf-8")

    assert 'data["evidence"]' not in app_source
    assert 'data["baseline"]' not in app_source

def test_landing_walkthrough_targets_the_existing_local_display_helper() -> None:
    project_root = Path(__file__).resolve().parents[1]
    app_source = (project_root / "src" / "nerc_compliance_intelligence" / "app.py").read_text(encoding="utf-8")

    assert "def _render_guided_tour" in app_source
    assert "_render_guided_tour()" in app_source
    assert "_render_graph_path_animation" not in app_source
