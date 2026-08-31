"""Automated tests for fake-first structured provider behavior."""

from __future__ import annotations

import pytest

from nerc_compliance_intelligence.agent_contracts import ApplicabilityAgentOutput
from nerc_compliance_intelligence.providers import (
    NebiusStructuredProvider,
    FakeStructuredProvider,
    LiveProviderApprovalRequiredError,
    ProviderResponseError,
    ProviderSettings,
    ProviderTemporaryError,
    ProviderTimeoutError,
    StructuredRequest,
    build_live_smoke_preview,
    build_nebius_provider_from_environment,
    generate_with_retry,
    live_provider_is_not_enabled,
    load_provider_settings,
    load_local_provider_environment,
)


REQUEST = StructuredRequest(
    operation="fake_applicability_test",
    system_prompt="Return structured output only.",
    input_payload={},
    response_schema_name="ApplicabilityAgentOutput",
)
VALID_OUTPUT = {
    "missing_fields": ["asset_scope"],
    "questions": ["What asset scope should this review consider?"],
    "ready_for_retrieval": False,
}


class RecordingNebiusTransport:
    """Local response fixture that captures request shape without a network call."""

    def __init__(self, response: dict[str, object]) -> None:
        self.response = response
        self.calls: list[dict[str, object]] = []

    def post_json(
        self,
        url: str,
        headers: dict[str, str],
        payload: dict[str, object],
        timeout_seconds: float,
    ) -> dict[str, object]:
        self.calls.append({"url": url, "headers": headers, "payload": payload, "timeout_seconds": timeout_seconds})
        return self.response


def test_fake_provider_is_the_environment_default() -> None:
    settings = load_provider_settings({})

    assert settings.provider == "fake"
    assert settings.model == "fake-structured-v1"
    assert settings.credential_variable is None


def test_local_provider_environment_loads_nci_values_without_overriding_process_values(tmp_path) -> None:
    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text("NCI_MODEL_PROVIDER=nebius\nNCI_NEBIUS_API_KEY=not-a-real-key\nOTHER_VALUE=ignored\n", encoding="utf-8")

    environment = load_local_provider_environment(dotenv_path, {"NCI_MODEL_NAME": "process-model"})

    assert environment["NCI_MODEL_PROVIDER"] == "nebius"
    assert environment["NCI_MODEL_NAME"] == "process-model"
    assert environment["NCI_NEBIUS_API_KEY"] == "not-a-real-key"
    assert "OTHER_VALUE" not in environment


def test_fake_provider_returns_a_validated_structured_output() -> None:
    provider = FakeStructuredProvider(scripted_responses=[VALID_OUTPUT], simulated_latency_ms=3)
    result = generate_with_retry(provider, REQUEST, ApplicabilityAgentOutput, ProviderSettings())

    assert result.model == "fake-structured-v1"
    assert result.latency_ms == 3
    assert result.attempts == 1
    assert result.parsed_output.missing_fields == ["asset_scope"]


def test_fake_provider_retries_a_temporary_error_within_the_bound() -> None:
    provider = FakeStructuredProvider(scripted_responses=[ProviderTemporaryError("temporary"), VALID_OUTPUT])
    result = generate_with_retry(provider, REQUEST, ApplicabilityAgentOutput, ProviderSettings(max_retries=2))

    assert provider.call_count == 2
    assert result.attempts == 2


def test_fake_provider_stops_after_the_configured_retry_limit() -> None:
    provider = FakeStructuredProvider(scripted_responses=[ProviderTemporaryError("one"), ProviderTemporaryError("two"), ProviderTemporaryError("three")])

    with pytest.raises(ProviderTemporaryError):
        generate_with_retry(provider, REQUEST, ApplicabilityAgentOutput, ProviderSettings(max_retries=2))

    assert provider.call_count == 3


def test_fake_provider_enforces_timeout_without_waiting() -> None:
    provider = FakeStructuredProvider(scripted_responses=[VALID_OUTPUT], simulated_latency_ms=2_000)

    with pytest.raises(ProviderTimeoutError, match="timeout"):
        generate_with_retry(provider, REQUEST, ApplicabilityAgentOutput, ProviderSettings(timeout_seconds=1, max_retries=0))


def test_live_preview_exposes_variable_name_and_request_but_not_a_secret() -> None:
    preview = build_live_smoke_preview(ProviderSettings(provider="nebius", model="Qwen/fake-name"))

    assert preview.credential_variable == "NCI_NEBIUS_API_KEY"
    assert preview.request.operation == "structured_applicability_smoke"
    assert preview.request.max_output_tokens == 700
    assert preview.requires_explicit_user_approval is True


def test_live_provider_is_blocked_without_a_separate_approval_step() -> None:
    with pytest.raises(LiveProviderApprovalRequiredError, match="explicit user approval"):
        live_provider_is_not_enabled()


def test_nebius_provider_uses_schema_constrained_chat_request_without_network() -> None:
    transport = RecordingNebiusTransport({"choices": [{"message": {"content": '{"missing_fields":["asset_scope"],"questions":["What asset scope should this review consider?"],"ready_for_retrieval":false}'}}]})
    provider = NebiusStructuredProvider(api_key="test-key-not-a-real-secret", transport=transport)
    settings = ProviderSettings(provider="nebius", model="account-approved-model", timeout_seconds=7, max_retries=0)

    result = provider.generate(REQUEST, ApplicabilityAgentOutput, settings)

    assert result.model == "account-approved-model"
    assert result.parsed_output.missing_fields == ["asset_scope"]
    assert transport.calls[0]["url"] == "https://api.studio.nebius.ai/v1/chat/completions"
    assert transport.calls[0]["headers"] == {"Authorization": "Bearer test-key-not-a-real-secret", "Content-Type": "application/json"}
    assert transport.calls[0]["payload"]["extra_body"] == {"guided_json": ApplicabilityAgentOutput.model_json_schema()}


def test_nebius_provider_requires_an_account_selected_model() -> None:
    provider = NebiusStructuredProvider(api_key="test-key-not-a-real-secret", transport=RecordingNebiusTransport({}))

    with pytest.raises(ValueError, match="NCI_MODEL_NAME"):
        provider.generate(REQUEST, ApplicabilityAgentOutput, ProviderSettings(provider="nebius"))


def test_token_factory_provider_uses_documented_json_schema_response_format() -> None:
    transport = RecordingNebiusTransport({"choices": [{"message": {"content": '{"missing_fields":["asset_scope"],"questions":["What asset scope should this review consider?"],"ready_for_retrieval":false}'}}]})
    provider = NebiusStructuredProvider(
        api_key="test-key-not-a-real-secret",
        base_url="https://api.tokenfactory.nebius.com/v1",
        transport=transport,
    )

    provider.generate(REQUEST, ApplicabilityAgentOutput, ProviderSettings(provider="nebius", model="moonshotai/Kimi-K2.6"))

    response_format = transport.calls[0]["payload"]["response_format"]
    assert response_format["type"] == "json_schema"
    assert response_format["json_schema"]["name"] == "ApplicabilityAgentOutput"
    assert response_format["json_schema"]["strict"] is True
    assert transport.calls[0]["payload"]["max_completion_tokens"] == 700
    assert "reasoning_effort" not in transport.calls[0]["payload"]


def test_token_factory_provider_includes_a_requested_low_reasoning_limit() -> None:
    transport = RecordingNebiusTransport({"choices": [{"message": {"content": '{"missing_fields":["asset_scope"],"questions":["What asset scope should this review consider?"],"ready_for_retrieval":false}'}}]})
    provider = NebiusStructuredProvider(api_key="test-key-not-a-real-secret", base_url="https://api.tokenfactory.nebius.com/v1", transport=transport)
    request = REQUEST.model_copy(update={"max_output_tokens": 2_000, "reasoning_effort": "low"})

    provider.generate(request, ApplicabilityAgentOutput, ProviderSettings(provider="nebius", model="moonshotai/Kimi-K2.6"))

    assert transport.calls[0]["payload"]["max_completion_tokens"] == 2_000
    assert transport.calls[0]["payload"]["reasoning_effort"] == "low"


def test_nebius_provider_factory_reads_a_key_only_when_constructed() -> None:
    transport = RecordingNebiusTransport({})
    provider = build_nebius_provider_from_environment(
        {"NCI_NEBIUS_API_KEY": "test-key-not-a-real-secret"},
        transport=transport,
    )

    assert provider.base_url == "https://api.studio.nebius.ai/v1"
    assert transport.calls == []


def test_nebius_provider_rejects_an_invalid_structured_response() -> None:
    provider = NebiusStructuredProvider(api_key="test-key-not-a-real-secret", transport=RecordingNebiusTransport({"choices": []}))

    with pytest.raises(ProviderResponseError, match="schema-constrained"):
        provider.generate(REQUEST, ApplicabilityAgentOutput, ProviderSettings(provider="nebius", model="account-approved-model"))


def test_nebius_provider_rejects_a_response_with_no_content() -> None:
    provider = NebiusStructuredProvider(api_key="test-key-not-a-real-secret", transport=RecordingNebiusTransport({"choices": [{"message": {"content": None}}]}))

    with pytest.raises(ProviderResponseError, match="no usable structured content"):
        provider.generate(REQUEST, ApplicabilityAgentOutput, ProviderSettings(provider="nebius", model="account-approved-model"))
