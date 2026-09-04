"""Fast smoke checks for the minimal Streamlit page helpers."""

from nerc_compliance_intelligence.app import page_status
from nerc_compliance_intelligence.config import AppSettings


def test_page_status_reports_fake_local_safety_boundary() -> None:
    status = page_status(AppSettings(environment="test"))

    assert status == {
        "environment": "test",
        "provider_mode": "local deterministic workflow",
        "operational_writes": "disabled",
    }
