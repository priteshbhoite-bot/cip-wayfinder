"""Offline tests for source-preserving tailoring and fresh human approval."""

from io import BytesIO
from zipfile import ZipFile

import pytest
from pydantic import ValidationError
from streamlit.testing.v1 import AppTest

from nerc_compliance_intelligence.app import demo_dashboard_data
from nerc_compliance_intelligence.package_revision import DraftRevision, editable_fields, revise_package
from nerc_compliance_intelligence.review_package_agent import ReviewPackageAgentItem


def revision(**changes: str) -> DraftRevision:
    return DraftRevision.model_validate({"requirement": "Document overview", "field": "control.owner_role",
        "text": "Fictional Configuration Manager", "feedback": "Tailor ownership to the synthetic example.",
        "reviewer_role": "Synthetic SME", **changes})


def test_revision_preserves_sources_ids_and_other_requirements() -> None:
    package = demo_dashboard_data()["review_package_agent"]
    other = ReviewPackageAgentItem.model_validate_json(package.items[0].model_dump_json().replace("Document overview", "R2"))
    package = package.model_copy(update={"items": [package.items[0], other]})
    before = package.model_dump_json()
    updated = revise_package(package, revision())
    assert package.model_dump_json() == before
    assert updated.items[1] == other
    assert updated.items[0].control.owner_role.text == "Fictional Configuration Manager"
    for name in ("mapping", "knowledge_item", "source_chunks"):
        assert getattr(updated.items[0], name) == getattr(package.items[0], name)
    assert updated.items[0].control.owner_role.requirement_ids == ["Document overview"]
    assert updated.items[0].control.is_draft


@pytest.mark.parametrize("field", ["mapping.source_locator", "control.control_id", "control.is_draft", "control.owner_role.requirement_ids", "remediation.steps.0.step_number"])
def test_protected_fields_cannot_be_changed(field: str) -> None:
    with pytest.raises(ValueError, match="listed draft text"):
        revise_package(demo_dashboard_data()["review_package_agent"], revision(field=field))


@pytest.mark.parametrize("field", ["text", "feedback", "reviewer_role"])
def test_blank_revision_details_are_rejected(field: str) -> None:
    with pytest.raises(ValidationError):
        revision(**{field: "   "})


def test_unknown_requirement_and_unchanged_text_are_rejected() -> None:
    package = demo_dashboard_data()["review_package_agent"]
    with pytest.raises(ValueError, match="existing requirement"):
        revise_package(package, revision(requirement="R999"))
    with pytest.raises(ValueError, match="Change the draft text"):
        revise_package(package, revision(text=package.items[0].control.owner_role.text))


def test_all_existing_editable_fields_validate_including_remediation() -> None:
    package = demo_dashboard_data()["review_package_agent"]
    for field in editable_fields(package.items[0]):
        changed = revise_package(package, revision(field=field, text="Synthetic SME revised wording"))
        assert editable_fields(changed.items[0])[field][1] == "Synthetic SME revised wording"


SCRIPT = '''
import streamlit as st
from nerc_compliance_intelligence.app import demo_dashboard_data, _render_review_package
from nerc_compliance_intelligence.case_intake import CaseIntake, assess_case_intake
data = demo_dashboard_data()
if st.session_state.get("test_scope"):
    st.session_state.case_intake_assessment = assess_case_intake(
        CaseIntake(functional_entity=["Transmission Owner"], jurisdiction=["Synthetic region"]), data["uploaded"].standard)
if st.session_state.get("test_new_document"):
    data["uploaded"] = data["uploaded"].model_copy(update={"content_hash": "1" * 64})
_render_review_package(data)
'''


def click(app: AppTest, label: str) -> None:
    next(button for button in app.button if button.label == label).click().run()
    assert not app.exception


def decide(app: AppTest, label: str) -> None:
    app.session_state["package_export_decision_choice"] = label
    app.text_input(key="decision_preview_reviewer_role").set_value("Synthetic SME")
    app.text_area(key="decision_preview_notes").set_value("Reviewing fictional ownership and draft wording.")
    click(app, "Apply package decision")


def save_owner(app: AppTest) -> None:
    app.selectbox(key="revision_field_Document overview").select("control.owner_role").run()
    next(area for area in app.text_area if area.label == "Revised draft text").set_value("Fictional Configuration Manager")
    next(area for area in app.text_area if area.label == "Why is this change needed?").set_value("Clarify the fictional control owner.")
    click(app, "Save revision")


def test_ui_edit_save_review_reapprove_exports_revised_content() -> None:
    app = AppTest.from_string(SCRIPT, default_timeout=30).run()
    assert not app.session_state["review_edit_pending"]
    decide(app, "Approve package")
    original = app.session_state["approved_package_bytes"]
    original_context = app.session_state["approved_package_context_key"]
    assert original
    app.session_state["approved_package_send_authorization"] = True
    decide(app, "Needs editing")
    assert app.session_state["review_edit_pending"]
    assert app.session_state["approved_package_bytes"] is None
    assert not app.session_state["approved_package_send_authorization"]
    assert not app.get("download_button")
    assert next(b for b in app.button if b.label == "Finish editing and review").disabled
    decide(app, "Approve package")
    assert app.session_state["approved_package_bytes"] is None
    assert any("finish editing" in e.value for e in app.error)
    save_owner(app)
    assert app.session_state["review_edit_pending"]
    assert app.session_state["approved_package_bytes"] is None
    app.run()
    assert "Fictional Configuration Manager" in app.session_state["review_revision_json"]
    click(app, "Finish editing and review")
    assert app.session_state["decision_preview"] is None
    assert not app.session_state["approved_package_bytes"]
    decide(app, "Approve package")
    assert app.session_state["approved_package_context_key"] != original_context
    with ZipFile(BytesIO(app.session_state["approved_package_bytes"])) as doc:
        assert b"Fictional Configuration Manager" in doc.read("word/document.xml")
    assert len(app.session_state["review_revision_history"]) == 1
    # A new session cannot see another reviewer's private revision.
    other = AppTest.from_string(SCRIPT, default_timeout=30).run()
    assert other.session_state["review_revision_json"] is None
    # New document must clear private edits, old approval and attachment.
    app.session_state["test_new_document"] = True
    app.run()
    assert not app.exception
    assert app.session_state["review_revision_json"] is None
    assert app.session_state["approved_package_bytes"] is None


def test_reject_while_editing_never_delivers() -> None:
    app = AppTest.from_string(SCRIPT, default_timeout=30).run()
    decide(app, "Needs editing")
    save_owner(app)
    decide(app, "Reject")
    assert not app.session_state["review_edit_pending"]
    assert app.session_state["approved_package_bytes"] is None
    assert not app.get("download_button")


def test_blank_feedback_does_not_save_and_scope_change_clears_revisions() -> None:
    app = AppTest.from_string(SCRIPT, default_timeout=30).run()
    decide(app, "Needs editing")
    next(area for area in app.text_area if area.label == "Revised draft text").set_value("Synthetic changed title")
    click(app, "Save revision")
    assert app.error
    assert app.session_state["review_revision_json"] is None
    save_owner(app)
    app.session_state["test_scope"] = True
    app.run()
    assert not app.exception
    assert app.session_state["review_revision_json"] is None
    assert app.session_state["review_revision_history"] == []


def test_revision_length_and_extra_metadata_rejected() -> None:
    with pytest.raises(ValidationError):
        revision(text="x" * 12001)
    with pytest.raises(ValidationError):
        DraftRevision.model_validate({**revision().model_dump(), "source_locator": "replace"})
