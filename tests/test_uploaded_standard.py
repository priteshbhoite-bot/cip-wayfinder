"""Tests for the one-standard, local-only uploaded-PDF contract."""

from __future__ import annotations

from io import BytesIO

import pytest
from pypdf import PdfWriter

from nerc_compliance_intelligence.uploaded_standard import (
    UploadValidationError,
    analyze_uploaded_standard,
    validate_uploaded_standard,
)


def _pdf_bytes() -> bytes:
    buffer = BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
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
    assert uploaded.requirements[0].requirement_reference == "Document overview"
    assert analysis.requirement_mapping.requirement_reference == "Document overview"
    assert "Local requirement label and page location" in analysis.requirement_mapping.draft_summary


@pytest.mark.parametrize(
    ("file_name", "file_bytes", "authorized", "message"),
    [
        ("CIP-010-5.pdf", _pdf_bytes(), False, "authorized and publicly available"),
        ("CIP-011-1.pdf", _pdf_bytes(), True, "CIP-010-5 or CIP-007-6"),
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
