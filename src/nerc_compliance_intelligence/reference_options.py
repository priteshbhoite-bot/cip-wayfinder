"""One-time, local NERC reference choices for the Streamlit intake form."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CATALOG_PATH = PROJECT_ROOT / "data" / "nerc_reference_options.json"


class ReferenceSource(BaseModel):
    """One public source used to curate the local catalog."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    label: str = Field(min_length=1)
    url: str = Field(min_length=1)


class NercReferenceOptions(BaseModel):
    """Typed, inspectable landing-page choices and their provenance."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    catalog_name: str = Field(min_length=1)
    retrieved_on: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    purpose: str = Field(min_length=1)
    sources: list[ReferenceSource] = Field(min_length=1)
    functional_entities: list[str] = Field(min_length=1)
    regional_entities: list[str] = Field(min_length=1)


def load_nerc_reference_options(path: Path = CATALOG_PATH) -> NercReferenceOptions:
    """Load the bundled catalog without contacting an external service."""
    return NercReferenceOptions.model_validate_json(path.read_text(encoding="utf-8"))
