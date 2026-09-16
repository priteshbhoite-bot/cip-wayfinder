"""Tests for dynamic, local-only NERC PDF knowledge extraction."""

from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path

import pytest
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from nerc_compliance_intelligence.uploaded_standard import (
    UploadValidationError,
    _extract_standards,
    analyze_uploaded_standard,
    match_approved_local_corpus,
    validate_uploaded_standard,
)


def _pdf_bytes(text: str | None = None, *, nerc_metadata: bool = True) -> bytes:
    text = text or (
        "North American Electric Reliability Corporation\n"
        "NERC | CIP-010-5 Reliability Standard\n"
        "CIP-010-5 Cyber Security - Configuration Change Management\n"
        "B. Requirements and Measures\n"
        "R1. Each Responsible Entity shall maintain a documented configuration change management process.\n"
        "M1. Evidence may include an approved process.\n"
        "C. Compliance"
    )
    buffer = BytesIO()
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    font_reference = writer._add_object(font)
    page[NameObject("/Resources")] = DictionaryObject(
        {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font_reference})}
    )
    operations = ["BT /F1 10 Tf 36 740 Td"]
    for line_number, line in enumerate(text.splitlines()):
        escaped = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        if line_number:
            operations.append("0 -14 Td")
        operations.append(f"({escaped}) Tj")
    operations.append("ET")
    stream = DecodedStreamObject()
    stream.set_data("\n".join(operations).encode("latin-1", errors="replace"))
    page[NameObject("/Contents")] = writer._add_object(stream)
    if nerc_metadata:
        writer.add_metadata({"/Title": "Synthetic NERC standard document", "/Author": "NERC"})
    else:
        writer.add_metadata({"/Title": "Unrelated document", "/Author": "Example author"})
    writer.write(buffer)
    return buffer.getvalue()


def test_authorized_supported_pdf_stays_in_memory_and_has_safe_metadata() -> None:
    uploaded = validate_uploaded_standard(
        file_name="CIP-010-5.pdf", file_bytes=_pdf_bytes(), authorized_public_document=True
    )
    analysis = analyze_uploaded_standard(uploaded)

    assert uploaded.standard.standard_id == "CIP-010"
    assert uploaded.standard.version == "5"
    assert uploaded.stored_persistently is False
    assert uploaded.document_type == "NERC Reliability Standard"
    assert uploaded.requirements[0].requirement_reference == "R1"
    assert analysis.requirement_mapping.requirement_reference == "R1"
    assert "shall maintain" in analysis.requirement_mapping.draft_summary
    assert analysis.requirement_mapping.domain == "Requirement R1"
    assert uploaded.requirements[0].source_text is not None
    assert "shall maintain" in uploaded.requirements[0].source_text
    assert "M1." not in uploaded.requirements[0].source_text
    assert uploaded.nerc_identity_signals


def test_any_nerc_standard_family_and_complex_version_can_be_discovered_from_content() -> None:
    uploaded = validate_uploaded_standard(
        file_name="shared-protection-document.pdf",
        file_bytes=_pdf_bytes(
            "North American Electric Reliability Corporation\n"
            "NERC | Reliability Standard PRC-006-NPCC-2\n"
            "This NERC document also discusses CIP-002-5.1a and MOD-032-2.\n"
            "R1. Each Responsible Entity shall document the applicable program."
        ),
        authorized_public_document=True,
    )

    labels = [f"{item.standard_id}-{item.version}" for item in uploaded.referenced_standards]
    assert labels == ["PRC-006-NPCC-2", "CIP-002-5.1a", "MOD-032-2"]
    assert uploaded.standard.standard_id == "PRC-006-NPCC"
    assert uploaded.standard.version == "2"


def test_supporting_nerc_document_builds_one_dynamic_topic_per_referenced_standard() -> None:
    uploaded = validate_uploaded_standard(
        file_name="reliability-guideline.pdf",
        file_bytes=_pdf_bytes(
            "North American Electric Reliability Corporation\n"
            "NERC | Reliability Guideline\n"
            "This reliability guideline explains planning considerations related to BAL-003-2 and TOP-003-8."
        ),
        authorized_public_document=True,
    )

    assert uploaded.document_type == "NERC reliability guideline"
    assert [item.requirement_reference for item in uploaded.requirements] == [
        "BAL-003-2 overview",
        "TOP-003-8 overview",
    ]
    assert all(item.summary for item in uploaded.requirements)


def test_requirement_list_uses_only_primary_standard_section_b() -> None:
    uploaded = validate_uploaded_standard(
        file_name="complete-set-extract.pdf",
        file_bytes=_pdf_bytes(
            "North American Electric Reliability Corporation\n"
            "NERC | Reliability Standards\n"
            "BAL-003-2 Resource and Demand Balancing\n"
            "B. Requirements and Measures\n"
            "R1. Each Responsible Entity shall document its balancing process.\n"
            "M1. Evidence may include a dated balancing record.\n"
            "C. Compliance\n"
            "TOP-003-8 Transmission Operations cross-reference.\n"
            "R1. This appendix reference must not become a requirement item."
        ),
        authorized_public_document=True,
    )

    assert [item.requirement_reference for item in uploaded.requirements] == ["R1"]
    assert uploaded.requirements[0].source_requirement_reference == "R1"
    assert uploaded.requirements[0].standard is not None
    assert uploaded.requirements[0].standard.standard_id == "BAL-003"


def test_unicode_pdf_dashes_are_normalized_for_standard_discovery() -> None:
    standards = _extract_standards(
        "NERC Reliability Standard CIP‑002‑5.1a and PRC–005–6",
        "",
        "primary",
    )

    assert [(item.standard_id, item.version) for item in standards] == [
        ("CIP-002", "5.1a"),
        ("PRC-005", "6"),
    ]


def test_exact_manifest_approved_pdf_can_use_local_corpus_identity(tmp_path: Path) -> None:
    pdf_bytes = _pdf_bytes(
        "CIP-010-5 Configuration Change Management and Vulnerability Assessments\n"
        "R1. Each Responsible Entity shall maintain a documented configuration change management process.",
        nerc_metadata=False,
    )
    corpus_directory = tmp_path / "approved-corpus"
    corpus_directory.mkdir()
    (corpus_directory / "cip-010-5.pdf").write_bytes(pdf_bytes)
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "documents": [
                    {
                        "filename": "cip-010-5.pdf",
                        "source_id": "approved-cip-010-5",
                        "standard_id": "CIP-010",
                        "version": "5",
                        "functional_entity": "Responsible Entity",
                        "jurisdiction": "United States",
                        "enforcement_status": "Verify current status",
                        "effective_date": None,
                        "source_url": "https://www.nerc.com/example/cip-010-5.pdf",
                        "retrieval_date": "2026-09-11",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    matched = match_approved_local_corpus(
        pdf_bytes,
        corpus_directory=corpus_directory,
        manifest_path=manifest_path,
    )
    uploaded = validate_uploaded_standard(
        file_name="renamed-copy.pdf",
        file_bytes=pdf_bytes,
        authorized_public_document=True,
        approved_corpus_directory=corpus_directory,
        approved_corpus_manifest_path=manifest_path,
    )

    assert matched is not None
    assert matched.standard.standard_id == "CIP-010"
    assert uploaded.standard.standard_id == "CIP-010"
    assert "exact approved local corpus byte match" in uploaded.nerc_identity_signals


def test_same_named_but_different_pdf_is_not_trusted_by_manifest(tmp_path: Path) -> None:
    approved_bytes = _pdf_bytes()
    unapproved_bytes = _pdf_bytes(
        "This unrelated searchable paper mentions CIP-010-5 and NERC once in a comparison. "
        "It contains no official branding, publication context, or standards material.",
        nerc_metadata=False,
    )
    corpus_directory = tmp_path / "approved-corpus"
    corpus_directory.mkdir()
    (corpus_directory / "cip-010-5.pdf").write_bytes(approved_bytes)
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "documents": [
                    {
                        "filename": "cip-010-5.pdf",
                        "source_id": "approved-cip-010-5",
                        "standard_id": "CIP-010",
                        "version": "5",
                        "functional_entity": "Responsible Entity",
                        "jurisdiction": "United States",
                        "enforcement_status": "Verify current status",
                        "effective_date": None,
                        "source_url": "https://www.nerc.com/example/cip-010-5.pdf",
                        "retrieval_date": "2026-09-11",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(UploadValidationError, match="could not be identified locally"):
        validate_uploaded_standard(
            file_name="cip-010-5.pdf",
            file_bytes=unapproved_bytes,
            authorized_public_document=True,
            approved_corpus_directory=corpus_directory,
            approved_corpus_manifest_path=manifest_path,
        )


@pytest.mark.parametrize(
    ("file_name", "file_bytes", "authorized", "message"),
    [
        ("CIP-010-5.pdf", _pdf_bytes(), False, "authorized and publicly available"),
        (
            "CIP-010-5.pdf",
            _pdf_bytes(
                "An unrelated searchable business document that only uses a misleading filename. "
                "It contains ordinary project notes, schedules, budgets, and status updates.",
                nerc_metadata=False,
            ),
            True,
            "recognized NERC Reliability Standard reference",
        ),
        (
            "CIP-010-5.pdf",
            _pdf_bytes(
                "This unrelated searchable paper mentions CIP-010-5 and NERC once in a comparison. "
                "It contains no official branding, publication context, or standards material.",
                nerc_metadata=False,
            ),
            True,
            "could not be identified locally",
        ),
        ("guidance.pdf", _pdf_bytes("North American Electric Reliability Corporation NERC Reliability Guidance without a standard number."), True, "recognized NERC Reliability Standard reference"),
        ("CIP-010-5.txt", b"not a PDF", True, "one PDF"),
        ("CIP-010-5.pdf", b"not a PDF", True, "not a valid PDF"),
    ],
)
def test_invalid_or_out_of_scope_uploads_are_rejected_safely(
    file_name: str, file_bytes: bytes, authorized: bool, message: str
) -> None:
    with pytest.raises(UploadValidationError, match=message):
        validate_uploaded_standard(
            file_name=file_name,
            file_bytes=file_bytes,
            authorized_public_document=authorized,
        )
