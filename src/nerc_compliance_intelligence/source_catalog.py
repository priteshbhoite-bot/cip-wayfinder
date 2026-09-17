"""Offline, packaged fingerprints for explicitly approved public CIP documents."""

from datetime import date
from hashlib import sha256
from pathlib import Path
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator


CATALOG_PATH = Path(__file__).with_name("cip_source_catalog.json")


class CatalogDocument(BaseModel):
    """An exact-byte approval, not a claim of current legal applicability."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    standard_id: str = Field(pattern=r"^CIP-\d{3}$")
    version: str = Field(pattern=r"^\d+(?:\.\d+)?[a-z]?$")
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    source_url: str
    retrieval_date: date
    fingerprinted_on: date
    approval_basis: str = "Previously approved local corpus; remote bytes not reverified"
    enforcement_status: str = "Not assessed; verify for the relevant jurisdiction and date"

    @field_validator("source_url")
    @classmethod
    def require_official_url(cls, value: str) -> str:
        url = urlparse(value)
        if url.scheme != "https" or url.hostname not in {"www.nerc.com", "nerc.com", "prod.nerc.com"} or url.username or url.password:
            raise ValueError("catalog source must be an official HTTPS NERC URL")
        return value


class SourceCatalog(BaseModel):
    model_config = ConfigDict(extra="forbid")
    documents: list[CatalogDocument]


def match_catalog_document(raw_pdf: bytes, path: Path = CATALOG_PATH) -> CatalogDocument | None:
    """Match exact bytes only; a filename or standard label never grants approval."""
    catalog = SourceCatalog.model_validate_json(path.read_bytes())
    digest = sha256(raw_pdf).hexdigest()
    matches = [entry for entry in catalog.documents if entry.sha256 == digest]
    if len(matches) > 1:
        raise ValueError("ambiguous source fingerprint")
    return matches[0] if matches else None
