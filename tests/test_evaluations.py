"""Tests for the local Milestone 13D evaluation runner and tracing preview."""

from nerc_compliance_intelligence.evaluations import markdown_results_table, run_offline_evaluations
from nerc_compliance_intelligence.tracing import build_tracing_preview, load_tracing_settings


def test_all_fifteen_offline_evaluations_pass_and_format_as_markdown() -> None:
    results = run_offline_evaluations()
    table = markdown_results_table(results)

    assert len(results) == 15
    assert all(result.passed for result in results)
    assert table.count("| PASS |") == 15
    assert "Traceback" not in table


def test_langsmith_preview_uses_no_credential_value_or_network_call() -> None:
    preview = build_tracing_preview(load_tracing_settings({"NCI_LANGSMITH_TRACING": "true", "NCI_LANGSMITH_PROJECT": "local-demo"}))

    assert preview.status == "preview_only"
    assert preview.credential_variable == "LANGSMITH_API_KEY"
    assert preview.network_calls_enabled is False
