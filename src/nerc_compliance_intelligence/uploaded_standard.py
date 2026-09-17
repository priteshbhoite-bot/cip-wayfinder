"""Local validation and knowledge extraction for one NERC-associated PDF.

Uploads are untrusted local data. The module requires searchable PDF content,
verifies multiple NERC identity signals, discovers referenced standards and
knowledge items, and retains only bounded summaries. It does not write files,
call a model, browse the web, or send the document to an external service.
"""

from __future__ import annotations

import hashlib
import re
from io import BytesIO
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError
import pdfplumber
from pypdf import PdfReader

from nerc_compliance_intelligence.local_corpus import PdfCorpusManifest
from nerc_compliance_intelligence.requirement_extraction import extract_requirement_blocks
from nerc_compliance_intelligence.schemas import RequirementMapping, StandardVersion
from nerc_compliance_intelligence.source_catalog import EffectiveDateInfo, match_catalog_document
from nerc_compliance_intelligence.effective_dates import EffectiveDateSchedule


MAX_UPLOAD_BYTES = 20 * 1024 * 1024
MIN_SEARCHABLE_CHARACTERS = 80
MAX_KNOWLEDGE_SUMMARY_CHARACTERS = 700
NERC_STANDARD_FAMILIES = (
    "BAL",
    "CIP",
    "COM",
    "EOP",
    "FAC",
    "INT",
    "IRO",
    "MOD",
    "NUC",
    "PER",
    "PRC",
    "TOP",
    "TPL",
    "VAR",
)
_FAMILY_PATTERN = "|".join(NERC_STANDARD_FAMILIES)
_STANDARD_REFERENCE_PATTERN = re.compile(
    rf"\b(?P<family>{_FAMILY_PATTERN})-(?P<number>\d{{3}})"
    rf"(?:-(?P<regional>[A-Z]{{2,8}}))?-(?P<version>\d+(?:\.\d+)?[a-z]?)\b",
    flags=re.IGNORECASE,
)
_SENTENCE_PATTERN = re.compile(r"(?<=[.!?])\s+|\n+")
_DASH_TRANSLATION = str.maketrans(
    {"‐": "-", "‑": "-", "‒": "-", "–": "-", "—": "-", "−": "-", "\u00ad": ""}
)


class UploadValidationError(ValueError):
    """A concise local upload error suitable for display without a stack trace."""


class ApprovedCorpusMatch(BaseModel):
    """Identity of an upload that exactly matches one manifest-approved local PDF."""

    model_config = ConfigDict(frozen=True)

    file_name: str
    source_id: str
    standard: StandardVersion


class UploadedStandard(BaseModel):
    """Safe metadata retained in a Streamlit session after one PDF is validated."""

    model_config = ConfigDict(frozen=True)

    file_name: str = Field(min_length=1)
    content_hash: str = Field(min_length=64, max_length=64)
    standard: StandardVersion
    page_count: int = Field(ge=1)
    extracted_character_count: int = Field(ge=0)
    requirements: list["UploadedRequirementOption"] = Field(min_length=1)
    document_title: str = "NERC standards-related document"
    document_type: str = "NERC standards-related document"
    referenced_standards: list[StandardVersion] = Field(default_factory=list)
    nerc_identity_signals: list[str] = Field(default_factory=list)
    source_type: str = "content-validated NERC-associated local PDF"
    stored_persistently: bool = False
    verified_source_url: str | None = None
    effective_date_info: EffectiveDateInfo | None = None
    effective_date_schedule: EffectiveDateSchedule | None = None


class UploadedRequirementOption(BaseModel):
    """One requirement or document topic extracted locally from the PDF."""

    requirement_reference: str = Field(min_length=1)
    page: int = Field(ge=1)
    end_page: int | None = Field(default=None, ge=1)
    title: str = "Document overview"
    summary: str = "Review the cited source page for the complete NERC document context."
    domain: str = "Requirement"
    applicable_systems: str = "See the cited NERC source for applicability."
    source_text: str | None = Field(default=None, max_length=20_000)
    standard: StandardVersion | None = None
    source_requirement_reference: str | None = None


class UploadedStandardAnalysis(BaseModel):
    """A source-grounded mapping for safe, generic local draft generation."""

    uploaded_standard: UploadedStandard
    requirement_mapping: RequirementMapping
    safety_note: str = "Local metadata analysis only; no compliance conclusion, external upload, or persistent write occurred."


def _standard_from_match(match: re.Match[str], scope_role: str) -> StandardVersion:
    """Convert one recognized NERC standard label into the shared typed model."""
    family = match.group("family").upper()
    number = match.group("number")
    regional = match.group("regional")
    standard_id = f"{family}-{number}"
    if regional:
        standard_id = f"{standard_id}-{regional.upper()}"
    return StandardVersion(
        standard_id=standard_id,
        version=match.group("version").lower(),
        scope_role=scope_role,
    )


def _standard_label(standard: StandardVersion) -> str:
    return f"{standard.standard_id}-{standard.version}"


def _normalize_standard_dashes(value: str) -> str:
    """Normalize common PDF dash characters before matching standard labels."""
    return value.translate(_DASH_TRANSLATION)


def _extract_standards(text: str, file_name: str, scope_role: str) -> list[StandardVersion]:
    """Return unique recognized standard labels, preferring the filename match."""
    matches = [
        *_STANDARD_REFERENCE_PATTERN.finditer(_normalize_standard_dashes(file_name)),
        *_STANDARD_REFERENCE_PATTERN.finditer(_normalize_standard_dashes(text)),
    ]
    standards: list[StandardVersion] = []
    seen: set[tuple[str, str]] = set()
    for match in matches:
        candidate = _standard_from_match(match, scope_role if not standards else "supporting")
        identity = (candidate.standard_id, candidate.version)
        if identity in seen:
            continue
        standards.append(candidate)
        seen.add(identity)
    return standards


def _nerc_identity_signals(text: str, metadata_text: str) -> tuple[list[str], int]:
    """Collect independent content signals instead of trusting a filename."""
    combined = f"{text}\n{metadata_text}"
    signals: list[str] = []
    score = 0
    if re.search(r"North\s+American\s+Electric\s+Reliability\s+Corporation", combined, re.IGNORECASE):
        signals.append("North American Electric Reliability Corporation name")
        score += 3
    if re.search(r"\bNERC\s*[|—–-]", combined, re.IGNORECASE):
        signals.append("NERC-branded header or footer")
        score += 2
    if re.search(r"(?:https?://)?(?:www\.)?nerc\.(?:com|org)\b", combined, re.IGNORECASE):
        signals.append("official NERC web address")
        score += 2
    if re.search(r"\bNERC\b", combined, re.IGNORECASE):
        signals.append("NERC acronym")
        score += 1
    if re.search(r"\bReliability\s+Standard(?:s)?\b", combined, re.IGNORECASE):
        signals.append("Reliability Standard terminology")
        score += 1
    return list(dict.fromkeys(signals)), score


def match_approved_local_corpus(
    file_bytes: bytes,
    *,
    corpus_directory: Path | None,
    manifest_path: Path | None,
) -> ApprovedCorpusMatch | None:
    """Match bytes only against PDFs explicitly allowlisted by the local manifest.

    A filename alone is never trusted. Missing or invalid local corpus configuration
    simply disables this additional trust path so the content checks still apply.
    """
    if corpus_directory is None or manifest_path is None:
        return None
    try:
        corpus_root = corpus_directory.resolve()
        manifest = PdfCorpusManifest.model_validate_json(manifest_path.read_bytes())
    except (OSError, ValidationError):
        return None

    uploaded_hash = hashlib.sha256(file_bytes).hexdigest()
    for entry in manifest.documents:
        source_path = (corpus_root / entry.filename).resolve()
        try:
            source_path.relative_to(corpus_root)
        except ValueError:
            continue
        try:
            if source_path.stat().st_size != len(file_bytes):
                continue
            if hashlib.sha256(source_path.read_bytes()).hexdigest() != uploaded_hash:
                continue
        except OSError:
            continue
        return ApprovedCorpusMatch(
            file_name=entry.filename,
            source_id=entry.source_id,
            standard=StandardVersion(
                standard_id=entry.standard_id,
                version=entry.version,
                scope_role="primary",
            ),
        )
    return None


def _classify_document(text: str) -> str:
    """Classify common NERC materials without claiming legal or enforcement status."""
    lowered = text.casefold()
    if "implementation guidance" in lowered:
        return "NERC implementation guidance"
    if "reliability guideline" in lowered:
        return "NERC reliability guideline"
    if "reliability standard audit worksheet" in lowered or "rsaw" in lowered:
        return "NERC audit worksheet"
    if "compliance guidance" in lowered:
        return "NERC compliance guidance"
    if "standard authorization request" in lowered or "implementation plan" in lowered:
        return "NERC standards-development material"
    if "reliability standard" in lowered or "requirements and measures" in lowered:
        return "NERC Reliability Standard"
    return "NERC standards-related document"


def _normalize_text(value: str) -> str:
    return " ".join(value.replace("\x00", " ").split())


def _document_title(reader: PdfReader, file_name: str, page_texts: list[tuple[int, str]]) -> str:
    """Prefer PDF metadata, then a useful first-page line, then the filename stem."""
    metadata = reader.metadata
    metadata_title = _normalize_text(str(metadata.title or "")) if metadata else ""
    if 4 <= len(metadata_title) <= 200 and metadata_title.casefold() not in {"untitled", "microsoft word"}:
        return metadata_title
    for _, page_text in page_texts[:3]:
        for raw_line in page_text.splitlines():
            line = _normalize_text(raw_line)
            lowered = line.casefold()
            if (
                6 <= len(line) <= 200
                and lowered not in {"nerc", "reliability | resilience | security"}
                and "north american electric reliability corporation" not in lowered
                and not re.fullmatch(r"\d+", line)
            ):
                return line
    return Path(file_name).stem


def _summary_from_text(text: str, fallback: str) -> str:
    """Build a bounded extractive knowledge summary from local searchable text."""
    cleaned = _normalize_text(text)
    if not cleaned:
        return fallback
    sentences = [item.strip(" •-–—") for item in _SENTENCE_PATTERN.split(cleaned) if len(item.strip()) >= 20]
    priority_terms = ("purpose", "shall", "must", "requirement", "applies", "effective", "guidance", "objective")
    prioritized = [item for item in sentences if any(term in item.casefold() for term in priority_terms)]
    selected: list[str] = []
    for sentence in [*prioritized, *sentences]:
        if sentence not in selected:
            selected.append(sentence)
        if len(" ".join(selected)) >= MAX_KNOWLEDGE_SUMMARY_CHARACTERS or len(selected) == 3:
            break
    summary = " ".join(selected) or cleaned
    if len(summary) > MAX_KNOWLEDGE_SUMMARY_CHARACTERS:
        summary = summary[: MAX_KNOWLEDGE_SUMMARY_CHARACTERS - 1].rsplit(" ", 1)[0] + "…"
    return summary


def _knowledge_items(
    page_texts: list[tuple[int, str]],
    table_pages: list[tuple[int, list[list[list[str | None]]]]],
    standards: list[StandardVersion],
) -> list[UploadedRequirementOption]:
    """Build primary section-B requirements, otherwise one topic per referenced standard."""
    primary = standards[0]
    requirement_blocks = extract_requirement_blocks(page_texts, table_pages=table_pages)
    if requirement_blocks:
        return [
            UploadedRequirementOption(
                requirement_reference=block.requirement_reference,
                page=block.start_page,
                end_page=block.end_page,
                title=f"{block.requirement_reference} requirement",
                summary=block.summary,
                domain=block.domain,
                applicable_systems=block.applicable_systems,
                source_text=block.text,
                standard=primary,
                source_requirement_reference=block.requirement_reference,
            )
            for block in requirement_blocks
        ]

    full_text = "\n".join(text for _, text in page_texts)
    requirements: list[UploadedRequirementOption] = []
    for standard in standards:
        label = _standard_label(standard)
        page_number, page_text = next(
            (
                (page, text)
                for page, text in page_texts
                if re.search(
                    rf"\b{re.escape(label)}\b",
                    _normalize_standard_dashes(text),
                    re.IGNORECASE,
                )
            ),
            page_texts[0],
        )
        requirements.append(
            UploadedRequirementOption(
                requirement_reference=f"{label} overview",
                page=page_number,
                title=f"Document discussion of {label}",
                summary=_summary_from_text(page_text, f"The document references {label}."),
                standard=standard,
            )
        )
    if requirements:
        return requirements
    return [
        UploadedRequirementOption(
            requirement_reference="Document overview",
            page=1,
            title="Document overview",
            summary=_summary_from_text(full_text, "Review the uploaded NERC document."),
            standard=primary,
        )
    ]


def validate_uploaded_standard(
    *,
    file_name: str,
    file_bytes: bytes,
    authorized_public_document: bool,
    scope_role: str = "primary",
    approved_corpus_directory: Path | None = None,
    approved_corpus_manifest_path: Path | None = None,
) -> UploadedStandard:
    """Validate one searchable, authorized PDF as NERC standards-related content."""
    if not authorized_public_document:
        raise UploadValidationError("confirm that the PDF is authorized and publicly available before local analysis")
    if not file_name.lower().endswith(".pdf"):
        raise UploadValidationError("upload one PDF file at a time")
    if not file_bytes.startswith(b"%PDF-"):
        raise UploadValidationError("the uploaded file is not a valid PDF")
    if len(file_bytes) > MAX_UPLOAD_BYTES:
        raise UploadValidationError("the uploaded PDF exceeds the 20 MB local limit")

    try:
        reader = PdfReader(BytesIO(file_bytes))
        page_count = len(reader.pages)
        if page_count < 1:
            raise UploadValidationError("the uploaded PDF has no readable pages")
        page_texts = [
            (page_number, page.extract_text() or "")
            for page_number, page in enumerate(reader.pages, start=1)
        ]
        table_page_numbers = {
            page_number
            for page_number, text in page_texts
            if re.search(
                r"Part\s+Applicable\s+Systems\s+Requirements\s+Measures",
                text,
                re.IGNORECASE,
            )
        }
        with pdfplumber.open(BytesIO(file_bytes)) as pdf:
            table_pages = [
                (page_number, pdf.pages[page_number - 1].extract_tables())
                for page_number in sorted(table_page_numbers)
            ]
        extracted_character_count = sum(len(text) for _, text in page_texts)
        metadata = reader.metadata
        metadata_text = " ".join(
            str(value) for value in (metadata or {}).values() if isinstance(value, str)
        )
    except UploadValidationError:
        raise
    except Exception as error:
        raise UploadValidationError("the uploaded PDF could not be read safely") from error

    if extracted_character_count < MIN_SEARCHABLE_CHARACTERS:
        raise UploadValidationError(
            "the PDF does not contain enough searchable text to verify and explain locally; use a searchable NERC PDF"
        )
    full_text = "\n".join(text for _, text in page_texts)
    content_standards = _extract_standards(full_text, "", scope_role)
    if not content_standards:
        raise UploadValidationError(
            "the PDF does not contain a recognized NERC Reliability Standard reference such as BAL-003-2, CIP-010-5, or PRC-005-6"
        )
    approved_corpus_match = match_approved_local_corpus(
        file_bytes,
        corpus_directory=approved_corpus_directory,
        manifest_path=approved_corpus_manifest_path,
    )
    try:
        catalog_match = match_catalog_document(file_bytes)
    except (OSError, ValueError):
        raise UploadValidationError("The approved source catalog is unavailable or invalid. Ask the administrator to restore it.") from None
    content_identities = {
        (standard.standard_id, standard.version) for standard in content_standards
    }
    if catalog_match is not None:
        approved_identity = (catalog_match.standard_id, catalog_match.version)
        if approved_identity not in content_identities:
            raise UploadValidationError("The approved catalog version does not match the PDF content.")
    elif approved_corpus_match is not None:
        approved_identity = (
            approved_corpus_match.standard.standard_id,
            approved_corpus_match.standard.version,
        )
        if approved_identity not in content_identities:
            raise UploadValidationError(
                "the approved local corpus identity does not match the standard references extracted from the PDF"
            )
    else:
        approved_identity = None

    filename_standards = _extract_standards("", file_name, scope_role)
    preferred_identity = (
        approved_identity
        or (
            (filename_standards[0].standard_id, filename_standards[0].version)
            if filename_standards
            else None
        )
    )
    standards = sorted(
        content_standards,
        key=lambda item: (item.standard_id, item.version) != preferred_identity,
    )
    identity_signals, identity_score = _nerc_identity_signals(full_text, metadata_text)
    if catalog_match is not None:
        identity_signals.append("exact approved catalog fingerprint match")
    if approved_corpus_match is not None:
        identity_signals.append("exact approved local corpus byte match")
    if identity_score < 3 and approved_corpus_match is None and catalog_match is None:
        raise UploadValidationError(
            "Source verification needed: this PDF does not match the approved source catalog and has insufficient NERC identity markers. It may be a valid new version or a modified copy. Provide its official NERC download URL to the administrator; renaming the file will not verify it."
        )

    primary = standards[0]
    normalized_standards = [
        standard.model_copy(update={"scope_role": "primary" if index == 0 else "supporting"})
        for index, standard in enumerate(standards)
    ]
    return UploadedStandard(
        file_name=file_name,
        content_hash=hashlib.sha256(file_bytes).hexdigest(),
        standard=primary.model_copy(update={"scope_role": "primary"}),
        page_count=page_count,
        extracted_character_count=extracted_character_count,
        requirements=_knowledge_items(page_texts, table_pages, normalized_standards),
        document_title=_document_title(reader, file_name, page_texts),
        document_type=_classify_document(full_text),
        referenced_standards=normalized_standards,
        nerc_identity_signals=identity_signals,
        verified_source_url=catalog_match.source_url if catalog_match else None,
        effective_date_info=catalog_match.effective_date_info if catalog_match else None,
        effective_date_schedule=catalog_match.effective_date_schedule if catalog_match else None,
        source_type="approved public CIP catalog fingerprint" if catalog_match else "content-validated NERC-associated local PDF",
    )


def analyze_uploaded_standard(
    uploaded_standard: UploadedStandard,
    selected_requirement_reference: str | None = None,
) -> UploadedStandardAnalysis:
    """Create a source-grounded mapping for one dynamically extracted knowledge item."""
    selected_reference = selected_requirement_reference or uploaded_standard.requirements[0].requirement_reference
    selected_option = next((item for item in uploaded_standard.requirements if item.requirement_reference == selected_reference), None)
    if selected_option is None:
        raise UploadValidationError("select a knowledge item extracted from this local NERC PDF")
    selected_standard = selected_option.standard or uploaded_standard.standard
    page_label = (
        f"pages {selected_option.page}-{selected_option.end_page}"
        if selected_option.end_page and selected_option.end_page != selected_option.page
        else f"page {selected_option.page}"
    )
    mapping = RequirementMapping(
        mapping_id=(
            f"uploaded-{uploaded_standard.content_hash[:12]}-"
            f"{re.sub(r'[^a-z0-9]+', '-', selected_option.requirement_reference.casefold()).strip('-')}"
        ),
        standard=selected_standard,
        requirement_reference=selected_option.requirement_reference,
        source_name=uploaded_standard.file_name,
        source_locator=f"uploaded PDF, {page_label}" + (f"; {uploaded_standard.verified_source_url}" if uploaded_standard.verified_source_url else ""),
        draft_summary=selected_option.source_text or selected_option.summary,
        domain=selected_option.domain,
        applicable_systems=selected_option.applicable_systems,
    )
    return UploadedStandardAnalysis(uploaded_standard=uploaded_standard, requirement_mapping=mapping)
