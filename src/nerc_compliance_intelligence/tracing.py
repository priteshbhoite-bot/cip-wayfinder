"""Optional LangSmith tracing configuration preview with no network behavior."""

from __future__ import annotations

import os
from collections.abc import Mapping

from pydantic import BaseModel, Field


class TracingSettings(BaseModel):
    """Non-secret tracing settings safe to display in a local UI or test."""

    enabled: bool = False
    project_name: str = Field(default="nerc-compliance-intelligence-local", min_length=1)
    credential_variable: str = "LANGSMITH_API_KEY"


class TracingPreview(BaseModel):
    """A safe description of tracing readiness; it never contains a credential value."""

    status: str
    project_name: str
    credential_variable: str
    network_calls_enabled: bool = False
    message: str


def load_tracing_settings(environ: Mapping[str, str] | None = None) -> TracingSettings:
    """Read only non-secret toggles; do not read or print any credential values."""
    source = os.environ if environ is None else environ
    return TracingSettings(
        enabled=source.get("NCI_LANGSMITH_TRACING", "false").casefold() == "true",
        project_name=source.get("NCI_LANGSMITH_PROJECT", "nerc-compliance-intelligence-local"),
    )


def build_tracing_preview(settings: TracingSettings) -> TracingPreview:
    """Explain the optional integration boundary without initializing a tracing client."""
    if not settings.enabled:
        return TracingPreview(status="disabled", project_name=settings.project_name, credential_variable=settings.credential_variable, message="LangSmith tracing is disabled; offline evaluation remains local.")
    return TracingPreview(status="preview_only", project_name=settings.project_name, credential_variable=settings.credential_variable, message="LangSmith tracing is configured for preview only. A future external connection requires explicit approval and the named local credential variable.")
