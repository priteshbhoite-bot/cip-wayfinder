"""Offline UI regressions for full-length, literal review content."""

from streamlit.testing.v1 import AppTest


def test_review_details_render_complete_text_without_code_blocks_or_tables() -> None:
    script = '''
import streamlit as st
from nerc_compliance_intelligence.app import demo_dashboard_data, _render_review_package
data = demo_dashboard_data()
package = data["packages"][0]
long_text = "Long source sentence. " * 100 + "<b>literal ending</b>"
package["source_chunks"] = []
package["knowledge_item"] = package["knowledge_item"].model_copy(update={"source_text": long_text})
st.session_state["requirement_source_" + package["mapping"].requirement_reference] = True
st.session_state["control_remediation_" + package["mapping"].requirement_reference] = True
_render_review_package(data)
'''
    app = AppTest.from_string(script, default_timeout=30).run()
    assert not app.exception
    displayed = [element.value for element in app.text]
    assert "Long source sentence. " * 100 + "<b>literal ending</b>" in displayed
    assert not app.dataframe
    assert not app.code

    from nerc_compliance_intelligence.app import demo_dashboard_data

    for step in demo_dashboard_data()["packages"][0]["remediation"].steps:
        for field in (step.action, step.owner_role, step.decision, step.end_state):
            assert field.text in displayed
