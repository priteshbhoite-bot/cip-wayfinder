"""Local, in-memory validation of one user-supplied NERC standard PDF.

Uploads are treated as untrusted local data. This module validates a narrow
MVP scope and returns metadata only; it does not write files, call a model, or
send the document to an external service.
"""

from __future__ import annotations

import hashlib
import re
from io import BytesIO

from pydantic import BaseModel, ConfigDict, Field
from pypdf import PdfReader

from nerc_compliance_intelligence.schemas import RequirementMapping, StandardVersion


MAX_UPLOAD_BYTES = 20 * 1024 * 1024
_STANDARD_FILENAME_PATTERN = re.compile(r"(?i)\b(cip)[-_ ]?(007|010)[-_ ]?(6|5)\b")
_SUPPORTED_STANDARDS = {("007", "6"), ("010", "5")}


class UploadValidationError(ValueError):
    """A concise local upload error suitable for display without a stack trace."""


class UploadedStandard(BaseModel):
    """Safe metadata retained in a Streamlit session after one PDF is validated."""

    model_config = ConfigDict(frozen=True)

    file_name: str = Field(min_length=1)
    content_hash: str = Field(min_length=64, max_length=64)
    standard: StandardVersion
    page_count: int = Field(ge=1)
    extracted_character_count: int = Field(ge=0)
    requirements: list["UploadedRequirementOption"] = Field(min_length=1)
    source_type: str = "user-supplied local PDF"
    stored_persistently: bool = False


class UploadedRequirementOption(BaseModel):
    """One requirement label and page location extracted locally from the PDF."""

    requirement_reference: str = Field(min_length=1)
    page: int = Field(ge=1)


class UploadedStandardAnalysis(BaseModel):
    """A source-grounded mapping for safe, generic local draft generation."""

    uploaded_standard: UploadedStandard
    requirement_mapping: RequirementMapping
    safety_note: str = "Local metadata analysis only; no compliance conclusion, external upload, or persistent write occurred."


def validate_uploaded_standard(
    *,
    file_name: str,
    file_bytes: bytes,
    authorized_public_document: bool,
    scope_role: str = "primary",
) -> UploadedStandard:
    """Validate exactly one authorized public PDF in the two-version MVP scope."""
    if not authorized_public_document:
        raise UploadValidationError("confirm that the PDF is authorized and publicly available before local analysis")
    if not file_name.lower().endswith(".pdf"):
        raise UploadValidationError("upload one PDF file at a time")
    if not file_bytes.startswith(b"%PDF-"):
        raise UploadValidationError("the uploaded file is not a valid PDF")
    if len(file_bytes) > MAX_UPLOAD_BYTES:
        raise UploadValidationError("the uploaded PDF exceeds the 20 MB local MVP limit")

    match = _STANDARD_FILENAME_PATTERN.search(file_name)
    if match is None:
        raise UploadValidationError("name the file with CIP-010-5 or CIP-007-6 so the local MVP can keep the version boundary")
    standard_number, version = match.group(2), match.group(3)
    if (standard_number, version) not in _SUPPORTED_STANDARDS:
        raise UploadValidationError("this local MVP supports only CIP-010-5 and CIP-007-6")

    try:
        reader = PdfReader(BytesIO(file_bytes))
        page_count = len(reader.pages)
        if page_count < 1:
            raise UploadValidationError("the uploaded PDF has no readable pages")
        page_texts = [(page_number, page.extract_text() or "") for page_number, page in enumerate(reader.pages, start=1)]
        extracted_character_count = sum(len(text) for _, text in page_texts)
    except UploadValidationError:
        raise
    except Exception as error:
        raise UploadValidationError("the uploaded PDF could not be read safely") from error

    requirements: list[UploadedRequirementOption] = []
    seen_references: set[str] = set()
    for page_number, text in page_texts:
        for requirement_match in re.finditer(r"\bR\s*(\d+)\.", text):
            reference = f"R{requirement_match.group(1)}"
            if reference not in seen_references:
                requirements.append(UploadedRequirementOption(requirement_reference=reference, page=page_number))
                seen_references.add(reference)
    if not requirements:
        requirements.append(UploadedRequirementOption(requirement_reference="Document overview", page=1))

    return UploadedStandard(
        file_name=file_name,
        content_hash=hashlib.sha256(file_bytes).hexdigest(),
        standard=StandardVersion(standard_id=f"CIP-{standard_number}", version=version, scope_role=scope_role),
        page_count=page_count,
        extracted_character_count=extracted_character_count,
        requirements=requirements,
    )


def analyze_uploaded_standard(
    uploaded_standard: UploadedStandard,
    selected_requirement_reference: str | None = None,
) -> UploadedStandardAnalysis:
    """Create a generic source mapping for one extracted local requirement label."""
    selected_reference = selected_requirement_reference or uploaded_standard.requirements[0].requirement_reference
    selected_option = next((item for item in uploaded_standard.requirements if item.requirement_reference == selected_reference), None)
    if selected_option is None:
        raise UploadValidationError("select a requirement reference extracted from this local PDF")
    mapping = RequirementMapping(
        mapping_id=f"uploaded-{uploaded_standard.content_hash[:12]}",
        standard=uploaded_standard.standard,
        requirement_reference=selected_option.requirement_reference,
        source_name=uploaded_standard.file_name,
        source_locator=f"uploaded local PDF, page {selected_option.page}",
        draft_summary="Local requirement label and page location are available for draft workflow generation; an SME must verify the requirement content before relying on the draft.",
    )
    return UploadedStandardAnalysis(uploaded_standard=uploaded_standard, requirement_mapping=mapping)
