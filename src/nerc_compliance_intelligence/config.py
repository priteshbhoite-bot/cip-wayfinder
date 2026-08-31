"""Safe, non-secret configuration for the local application shell."""

from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Literal

from pydantic import BaseModel, Field


class AppSettings(BaseModel):
    """Configuration values that are safe to show on the local landing page."""

    app_name: str = Field(default="CIP Wayfinder", min_length=1)
    environment: Literal["local", "test"] = "local"
    provider_mode: Literal["fake"] = "fake"
    operational_writes_enabled: bool = False


def load_settings(environ: Mapping[str, str] | None = None) -> AppSettings:
    """Load only safe display settings from an environment mapping.

    Secrets are deliberately not read here. The provider mode and operational
    write flag are fixed to their safe MVP defaults.
    """
    source = os.environ if environ is None else environ
    return AppSettings(
        app_name=source.get("NCI_APP_NAME", "CIP Wayfinder"),
        environment=source.get("NCI_ENVIRONMENT", "local"),
    )
