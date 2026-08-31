"""Fake-first structured model provider contracts for Milestone 9.

No live network client is implemented here. A live request is deliberately
blocked until an explicit, separate approval step is added.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
import json
from pathlib import Path
import re
from time import perf_counter
from typing import Any, Generic, Literal, Protocol, TypeVar
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from pydantic import BaseModel, ConfigDict, Field


OutputModel = TypeVar("OutputModel", bound=BaseModel)


class ProviderSettings(BaseModel):
    """Non-secret provider settings read from environment variables."""

    model_config = ConfigDict(extra="forbid")

    provider: str = "fake"
    model: str = "fake-structured-v1"
    timeout_seconds: float = Field(default=5.0, gt=0, le=60)
    max_retries: int = Field(default=2, ge=0, le=2)

    @property
    def credential_variable(self) -> str | None:
        return {
            "nebius": "NCI_NEBIUS_API_KEY",
            "fireworks": "NCI_FIREWORKS_API_KEY",
        }.get(self.provider)


def load_provider_settings(environ: Mapping[str, str] | None = None) -> ProviderSettings:
    """Load names and limits only; API-key values are never read or logged."""
    source = os.environ if environ is None else environ
    return ProviderSettings(
        provider=source.get("NCI_MODEL_PROVIDER", "fake"),
        model=source.get("NCI_MODEL_NAME", "fake-structured-v1"),
        timeout_seconds=float(source.get("NCI_MODEL_TIMEOUT_SECONDS", "5")),
        max_retries=int(source.get("NCI_MODEL_MAX_RETRIES", "2")),
    )


def load_local_provider_environment(
    dotenv_path: Path,
    environ: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Load local `NCI_` settings without logging credentials or file content.

    Real process environment values win over the ignored local file, which lets
    a deployment supply a secret without changing application code. The file is
    read only when a user deliberately opens the review-and-send UI.
    """
    resolved = dict(os.environ if environ is None else environ)
    if not dotenv_path.is_file():
        return resolved
    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^\s*(NCI_[A-Z0-9_]+)\s*=\s*(.+?)\s*$", raw_line)
        if match and match.group(1) not in resolved:
            resolved[match.group(1)] = match.group(2).strip().strip('"').strip("'")
    return resolved


class StructuredRequest(BaseModel):
    """The exact non-secret request shape a provider receives."""

    model_config = ConfigDict(extra="forbid")

    operation: str
    system_prompt: str
    input_payload: dict[str, Any]
    response_schema_name: str
    max_output_tokens: int = Field(default=700, ge=1, le=2_000)
    reasoning_effort: Literal["low", "medium", "high"] | None = None


class ProviderResult(BaseModel, Generic[OutputModel]):
    """A parsed structured result plus safe execution measurements."""

    model: str
    latency_ms: int = Field(ge=0)
    attempts: int = Field(ge=1)
    parsed_output: OutputModel


class ProviderTimeoutError(TimeoutError):
    """Raised when a provider's reported work exceeds the configured timeout."""


class ProviderTemporaryError(RuntimeError):
    """Raised by a recoverable provider failure that may be retried."""


class ProviderResponseError(RuntimeError):
    """Raised when a provider returns an unusable non-retryable response."""


class LiveProviderApprovalRequiredError(RuntimeError):
    """Raised instead of sending a paid request without user approval."""


class StructuredProvider(Protocol):
    def generate(
        self,
        request: StructuredRequest,
        output_model: type[OutputModel],
        settings: ProviderSettings,
    ) -> ProviderResult[OutputModel]: ...


class NebiusTransport(Protocol):
    """Small transport seam so Nebius requests can be unit-tested without a network call."""

    def post_json(
        self,
        url: str,
        headers: Mapping[str, str],
        payload: dict[str, Any],
        timeout_seconds: float,
    ) -> dict[str, Any]: ...


class UrllibNebiusTransport:
    """Send one JSON request to Nebius only when a caller explicitly invokes it."""

    def post_json(
        self,
        url: str,
        headers: Mapping[str, str],
        payload: dict[str, Any],
        timeout_seconds: float,
    ) -> dict[str, Any]:
        request = Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=dict(headers),
            method="POST",
        )
        try:
            with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310 - URL is a fixed Nebius API base.
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            if error.code == 429 or error.code >= 500:
                raise ProviderTemporaryError(f"Nebius temporarily returned HTTP {error.code}") from error
            raise ProviderResponseError(f"Nebius returned HTTP {error.code}") from error
        except URLError as error:
            raise ProviderTemporaryError("Nebius connection failed") from error
        except TimeoutError as error:
            raise ProviderTimeoutError("Nebius request exceeded the configured timeout") from error
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ProviderResponseError("Nebius returned invalid JSON") from error


@dataclass
class NebiusStructuredProvider:
    """OpenAI-compatible Nebius AI Studio adapter for schema-constrained output.

    The caller supplies the API key from an ignored environment file or an
    approved deployment secret. This class never logs the key or request body.
    """

    api_key: str
    base_url: str = "https://api.studio.nebius.ai/v1"
    transport: NebiusTransport = field(default_factory=UrllibNebiusTransport)

    def generate(
        self,
        request: StructuredRequest,
        output_model: type[OutputModel],
        settings: ProviderSettings,
    ) -> ProviderResult[OutputModel]:
        if settings.provider != "nebius":
            raise ValueError("NebiusStructuredProvider requires provider='nebius'")
        if not settings.model or settings.model == "fake-structured-v1":
            raise ValueError("set NCI_MODEL_NAME to a model available in your Nebius account")
        start = perf_counter()
        payload: dict[str, Any] = {
            "model": settings.model,
            "messages": [
                {"role": "system", "content": request.system_prompt},
                {"role": "user", "content": json.dumps(request.input_payload, sort_keys=True)},
            ],
            "temperature": 0,
            "max_tokens": request.max_output_tokens,
            "extra_body": {"guided_json": output_model.model_json_schema()},
        }
        if "tokenfactory.nebius.com" in self.base_url:
            # Token Factory documents JSON-schema output through response_format.
            # Keep guided_json as well because its text-generation examples use it.
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": output_model.__name__,
                    "schema": output_model.model_json_schema(),
                    "strict": True,
                },
            }
            payload["max_completion_tokens"] = request.max_output_tokens
            if request.reasoning_effort is not None:
                payload["reasoning_effort"] = request.reasoning_effort
        response = self.transport.post_json(
            f"{self.base_url.rstrip('/')}/chat/completions",
            {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            payload,
            settings.timeout_seconds,
        )
        try:
            content = response["choices"][0]["message"]["content"]
            if not isinstance(content, str) or not content.strip():
                raise ProviderResponseError("Nebius response contained no usable structured content")
            parsed = output_model.model_validate_json(content)
        except ProviderResponseError:
            raise
        except (IndexError, KeyError, TypeError, ValueError) as error:
            raise ProviderResponseError("Nebius response did not contain valid schema-constrained JSON") from error
        elapsed_ms = round((perf_counter() - start) * 1_000)
        return ProviderResult(model=settings.model, latency_ms=elapsed_ms, attempts=1, parsed_output=parsed)


def build_nebius_provider_from_environment(
    environ: Mapping[str, str] | None = None,
    *,
    transport: NebiusTransport | None = None,
) -> NebiusStructuredProvider:
    """Create the Nebius adapter only after a caller intentionally selects it.

    This reads the API key only at construction time and never returns it.
    It does not make a network request.
    """
    source = os.environ if environ is None else environ
    api_key = source.get("NCI_NEBIUS_API_KEY")
    if not api_key:
        raise ValueError("NCI_NEBIUS_API_KEY is required to create a Nebius provider")
    base_url = source.get("NCI_NEBIUS_BASE_URL", "https://api.studio.nebius.ai/v1")
    return NebiusStructuredProvider(
        api_key=api_key,
        base_url=base_url,
        transport=transport or UrllibNebiusTransport(),
    )


@dataclass
class FakeStructuredProvider:
    """Deterministic default provider that validates scripted structured payloads."""

    scripted_responses: list[dict[str, Any] | Exception] = field(default_factory=list)
    model_name: str = "fake-structured-v1"
    simulated_latency_ms: int = 0
    call_count: int = 0

    def generate(
        self,
        request: StructuredRequest,
        output_model: type[OutputModel],
        settings: ProviderSettings,
    ) -> ProviderResult[OutputModel]:
        self.call_count += 1
        if self.simulated_latency_ms > settings.timeout_seconds * 1_000:
            raise ProviderTimeoutError("fake provider exceeded the configured timeout")
        response = self.scripted_responses.pop(0) if self.scripted_responses else {}
        if isinstance(response, Exception):
            raise response
        start = perf_counter()
        parsed = output_model.model_validate(response)
        elapsed_ms = max(self.simulated_latency_ms, round((perf_counter() - start) * 1_000))
        return ProviderResult(model=self.model_name, latency_ms=elapsed_ms, attempts=1, parsed_output=parsed)


def generate_with_retry(
    provider: StructuredProvider,
    request: StructuredRequest,
    output_model: type[OutputModel],
    settings: ProviderSettings,
) -> ProviderResult[OutputModel]:
    """Call a provider with a bounded retry count and structured-output parsing."""
    for attempt in range(1, settings.max_retries + 2):
        try:
            result = provider.generate(request, output_model, settings)
            return result.model_copy(update={"attempts": attempt})
        except (ProviderTimeoutError, ProviderTemporaryError):
            if attempt == settings.max_retries + 1:
                raise
    raise RuntimeError("unreachable retry guard")


class LiveSmokePreview(BaseModel):
    """Reviewable plan for a single cost-sensitive request; it does not execute anything."""

    provider: str
    model: str
    credential_variable: str
    request: StructuredRequest
    expected_cost_scope: str
    requires_explicit_user_approval: bool = True


def build_live_smoke_preview(settings: ProviderSettings) -> LiveSmokePreview:
    """Show the exact tiny request before any future paid smoke test."""
    if settings.provider not in {"nebius", "fireworks"} or settings.credential_variable is None:
        raise ValueError("a live smoke preview requires provider 'nebius' or 'fireworks'")
    request = StructuredRequest(
        operation="structured_applicability_smoke",
        system_prompt="Return the supplied JSON shape only. Do not infer missing scope.",
        input_payload={"functional_entity": None, "jurisdiction": None, "standard_id": None, "version": None, "asset_scope": None},
        response_schema_name="ApplicabilityAgentOutput",
        max_output_tokens=700,
    )
    return LiveSmokePreview(
        provider=settings.provider,
        model=settings.model,
        credential_variable=settings.credential_variable,
        request=request,
        expected_cost_scope="One small structured request, no tools, no corpus text, timeout limited by NCI_MODEL_TIMEOUT_SECONDS, and no retries beyond NCI_MODEL_MAX_RETRIES.",
    )


def live_provider_is_not_enabled(*_: Any, **__: Any) -> None:
    """Make any accidental attempt at a paid call fail safely before network activity."""
    raise LiveProviderApprovalRequiredError("live provider calls require explicit user approval after preview review")
