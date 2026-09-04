"""Tests for explicit cache identity and invalidation rules."""

from pathlib import Path

from nerc_compliance_intelligence.cache_policy import CACHE_POLICY_VERSION, dashboard_cache_key, file_revision, model_result_cache_key, stable_fingerprint
from nerc_compliance_intelligence.providers import ProviderSettings, StructuredRequest
from nerc_compliance_intelligence.schemas import StandardVersion
from nerc_compliance_intelligence.uploaded_standard import UploadedRequirementOption, UploadedStandard


def _request(prompt: str = "Use only the supplied source.") -> StructuredRequest:
    return StructuredRequest(
        operation="draft",
        system_prompt=prompt,
        input_payload={"requirement": "R1", "source": "public excerpt"},
        response_schema_name="ControlGenerationOutput",
    )


def test_stable_fingerprint_is_order_independent_and_opaque() -> None:
    first = stable_fingerprint("test", {"b": 2, "a": 1})
    second = stable_fingerprint("test", {"a": 1, "b": 2})

    assert first == second
    assert len(first) == 64
    assert "test" not in first


def test_model_cache_key_changes_with_prompt_or_model() -> None:
    settings = ProviderSettings(provider="nebius", model="model-a")
    same_key = model_result_cache_key(_request(), settings)

    assert same_key == model_result_cache_key(_request(), settings)
    assert same_key != model_result_cache_key(_request("A changed prompt."), settings)
    assert same_key != model_result_cache_key(_request(), settings.model_copy(update={"model": "model-b"}))
    assert same_key != model_result_cache_key(_request(), settings, "https://another-endpoint.example/v1")
    assert CACHE_POLICY_VERSION not in same_key
    assert "public excerpt" not in same_key


def test_file_revision_changes_when_local_file_changes(tmp_path: Path) -> None:
    local_file = tmp_path / "corpus.sqlite"
    assert file_revision(local_file) == "missing"

    local_file.write_text("first", encoding="utf-8")
    first = file_revision(local_file)
    local_file.write_text("a longer second value", encoding="utf-8")

    assert file_revision(local_file) != first


def test_dashboard_cache_key_changes_with_public_document_identity(tmp_path: Path) -> None:
    corpus = tmp_path / "corpus.sqlite"
    corpus.write_text("public corpus", encoding="utf-8")
    uploaded = UploadedStandard(
        file_name="CIP-010-5.pdf",
        content_hash="a" * 64,
        standard=StandardVersion(standard_id="CIP-010", version="5", scope_role="primary"),
        page_count=1,
        extracted_character_count=20,
        requirements=[UploadedRequirementOption(requirement_reference="R1", page=1)],
    )

    first = dashboard_cache_key(uploaded, corpus)
    changed = uploaded.model_copy(update={"content_hash": "b" * 64})

    assert first == dashboard_cache_key(uploaded, corpus)
    assert first != dashboard_cache_key(changed, corpus)
