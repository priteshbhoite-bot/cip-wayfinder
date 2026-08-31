"""Tests for safe local configuration."""

import pytest
from pydantic import ValidationError

from nerc_compliance_intelligence.config import load_settings


def test_load_settings_uses_safe_defaults() -> None:
    settings = load_settings({})

    assert settings.app_name == "CIP Wayfinder"
    assert settings.environment == "local"
    assert settings.provider_mode == "fake"
    assert settings.operational_writes_enabled is False


def test_load_settings_rejects_an_unsupported_environment() -> None:
    with pytest.raises(ValidationError):
        load_settings({"NCI_ENVIRONMENT": "production"})
