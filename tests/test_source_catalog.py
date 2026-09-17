"""Offline catalog contracts use synthetic PDF bytes, never a network provider."""

import hashlib
from datetime import date
from pathlib import Path

import pytest
from pydantic import ValidationError

from nerc_compliance_intelligence import uploaded_standard as uploads
from nerc_compliance_intelligence.source_catalog import (
    CATALOG_PATH, CatalogDocument, EffectiveDateInfo, SourceCatalog, match_catalog_document,
)
from test_uploaded_standard import _pdf_bytes


def entry(raw: bytes, standard_id: str = "CIP-010", version: str = "5") -> CatalogDocument:
    return CatalogDocument(
        standard_id=standard_id, version=version,
        sha256=hashlib.sha256(raw).hexdigest(),
        source_url=f"https://www.nerc.com/globalassets/standards/reliability-standards/cip/{standard_id.lower()}-{version}.pdf",
        retrieval_date=date(2026, 9, 11), fingerprinted_on=date(2026, 9, 17),
    )


def test_catalog_covers_approved_families_and_exact_versions() -> None:
    catalog = SourceCatalog.model_validate_json(CATALOG_PATH.read_bytes())
    assert len(catalog.documents) == 24
    assert {d.standard_id for d in catalog.documents} == {f"CIP-{n:03}" for n in range(2, 16)}
    assert len({d.sha256 for d in catalog.documents}) == 24
    assert ("CIP-002", "5.1a") in {(d.standard_id, d.version) for d in catalog.documents}


def test_exact_bytes_only_and_official_urls(tmp_path: Path) -> None:
    raw = b"synthetic approved document"
    path = tmp_path / "catalog.json"
    path.write_text(SourceCatalog(documents=[entry(raw)]).model_dump_json())
    assert match_catalog_document(raw, path) is not None
    assert match_catalog_document(raw + b"altered", path) is None
    with pytest.raises(ValidationError):
        CatalogDocument.model_validate({**entry(raw).model_dump(), "source_url": "https://nerc.com.example.org/a.pdf"})


@pytest.mark.parametrize("standard_id,version", [
    (d.standard_id, d.version)
    for d in SourceCatalog.model_validate_json(CATALOG_PATH.read_bytes()).documents
])
def test_cloud_upload_without_corpus_preserves_version_parts_and_citation(
    monkeypatch: pytest.MonkeyPatch, standard_id: str, version: str,
) -> None:
    raw = _pdf_bytes(
        f"{standard_id}-{version} Cyber Security\n"
        "B. Requirements and Measures\n"
        "R1. Each Responsible Entity shall document the source-specific procedure.\n"
        "1.1. Retain the approval and review records.\n"
        "M1. Evidence examples are not requirement text.\nC. Compliance",
        nerc_metadata=False,
    )
    approved = entry(raw, standard_id, version)
    approved = approved.model_copy(update={"effective_date_info": EffectiveDateInfo(
        date=date(2030, 1, 1), jurisdiction="Synthetic test jurisdiction",
        source_reference="Synthetic implementation plan, section 2",
    )})
    monkeypatch.setattr(uploads, "match_catalog_document", lambda data: approved if data == raw else None)
    result = uploads.validate_uploaded_standard(file_name="renamed.pdf", file_bytes=raw, authorized_public_document=True)
    assert (result.standard.standard_id, result.standard.version) == (standard_id, version)
    assert result.verified_source_url == approved.source_url
    assert result.effective_date_info == approved.effective_date_info
    mapping = uploads.analyze_uploaded_standard(result, "R1").requirement_mapping
    assert approved.source_url in mapping.source_locator
    assert "1.1." in mapping.draft_summary
    assert "Evidence examples" not in mapping.draft_summary
    from nerc_compliance_intelligence.control_remediation import ControlGenerationInput, generate_draft_control_and_remediation
    draft = generate_draft_control_and_remediation(ControlGenerationInput(retrieved_mappings=[mapping], selected_requirement_ids=["R1"]))
    assert draft.control.objective.requirement_ids == ["R1"]


def test_catalog_content_mismatch_and_unverified_version_stop(monkeypatch: pytest.MonkeyPatch) -> None:
    raw = _pdf_bytes("CIP-010-5 This searchable document describes configuration management and review processes for applicable systems.", nerc_metadata=False)
    monkeypatch.setattr(uploads, "match_catalog_document", lambda data: entry(raw, version="4"))
    with pytest.raises(uploads.UploadValidationError, match="version does not match"):
        uploads.validate_uploaded_standard(file_name="cip-010-4.pdf", file_bytes=raw, authorized_public_document=True)
    monkeypatch.setattr(uploads, "match_catalog_document", lambda data: None)
    with pytest.raises(uploads.UploadValidationError, match="Source verification needed"):
        uploads.validate_uploaded_standard(file_name="cip-010-5.pdf", file_bytes=raw, authorized_public_document=True)


def test_effective_date_requires_jurisdiction_and_source() -> None:
    with pytest.raises(ValidationError):
        EffectiveDateInfo.model_validate({"date": "2030-01-01"})
