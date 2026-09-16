"""Deterministic extraction of requirements and requirement-table parts.

The parser reads only section B and stops before section C.  It first bounds
each top-level requirement, then—when the PDF exposes a four-column NERC table
layout—replaces that parent with separately traceable requirement-part rows.
The Measures column is deliberately discarded.
"""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field, model_validator


_SECTION_START = re.compile(
    r"(?im)^\s*B\.\s*Requirements\s+and\s+Measures\s*$"
)
_SECTION_END = re.compile(r"(?im)^\s*C\.\s*Compliance\b")
_TOP_LEVEL_MARKER = re.compile(
    r"(?im)^\s*(?P<kind>[RM])\s*(?P<number>\d+)\s*\.(?!\d)"
)
_PAGE_LINE = re.compile(r"(?i)^\s*Page\s+\d+\s+of\s+\d+\s*$")
_STANDARD_HEADER = re.compile(
    r"(?i)^\s*[A-Z]{3}-\d{3}(?:-[A-Z]{2,8})?-\d+(?:\.\d+)?[a-z]?\s+[—–\-�]\s+.+$"
)
_TABLE_HEADER = re.compile(
    r"\bPart\b.*\bApplicable\s+Systems\b.*\bRequirements\b.*\bMeasures\b",
    re.IGNORECASE,
)
_TABLE_TITLE = re.compile(
    r"Table\s+R\s*(?P<number>\d+)\s*[—–\-]?\s*(?P<domain>[^\r\n]+)",
    re.IGNORECASE,
)
_TABLE_PART = re.compile(r"^\s*(?P<part>\d+\.\d+)(?!\.\d)\.?\s*$")
MAX_REQUIREMENT_SUMMARY_CHARACTERS = 1_500


class RequirementSourceBlock(BaseModel):
    """One bounded requirement or requirement part from section B."""

    model_config = ConfigDict(frozen=True)

    requirement_reference: str = Field(pattern=r"^R\d+(?:\.\d+)?$")
    parent_requirement_reference: str = Field(pattern=r"^R\d+$")
    domain: str = Field(min_length=1)
    applicable_systems: str = Field(min_length=1)
    start_page: int = Field(ge=1)
    end_page: int = Field(ge=1)
    text: str = Field(min_length=1)
    summary: str = Field(min_length=1)

    @model_validator(mode="after")
    def require_ordered_page_range(self) -> "RequirementSourceBlock":
        if self.end_page < self.start_page:
            raise ValueError("requirement source page range must be ordered")
        return self


def _without_page_noise(text: str) -> str:
    """Remove repeated page furniture while preserving requirement wording."""
    retained: list[str] = []
    for raw_line in text.replace("\x00", " ").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if _PAGE_LINE.fullmatch(line):
            continue
        if "Reliability | Resilience | Security" in line:
            continue
        if _STANDARD_HEADER.fullmatch(line) and _TOP_LEVEL_MARKER.match(line) is None:
            continue
        retained.append(line)
    return "\n".join(retained).strip()


def summarize_requirement_text(text: str, requirement_reference: str) -> str:
    """Create a bounded, plain-language synopsis from one requirement block."""
    cleaned = _without_page_noise(text).replace("�", " ")
    cleaned = re.sub(
        rf"(?i)^\s*{re.escape(requirement_reference)}\s*\.\s*",
        "",
        cleaned,
        count=1,
    )
    cleaned = re.sub(
        r"\[[^\]]*(?:Violation\s+Risk\s+Factor|VRF|Time\s*[- ]?Horizon)[^\]]*\]",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = " ".join(cleaned.split())
    cleaned = re.sub(r"(?i)^Each\s+Responsible\s+Entity\s+shall\b", "The Responsible Entity must", cleaned)
    cleaned = re.sub(r"(?i)^The\s+Responsible\s+Entity\s+shall\b", "The Responsible Entity must", cleaned)
    cleaned = re.sub(r"\bshall\b", "must", cleaned, flags=re.IGNORECASE)
    requirement_number = requirement_reference.removeprefix("R")
    part_pattern = re.compile(
        rf"(?<![\d.])(?P<label>{re.escape(requirement_number)}\.\d+)\.\s*"
    )
    parts = list(part_pattern.finditer(cleaned))
    if parts:
        main_statement = cleaned[: parts[0].start()].strip(" ;:")
        summarized_parts: list[str] = []
        for index, part in enumerate(parts):
            end = parts[index + 1].start() if index + 1 < len(parts) else len(cleaned)
            part_text = cleaned[part.end() : end].strip(" ;:")
            part_text = re.sub(r"(?:;?\s+(?:and|or))$", "", part_text, flags=re.IGNORECASE)
            if len(part_text) > 220:
                part_text = part_text[:219].rsplit(" ", 1)[0] + "…"
            summarized_parts.append(f"{part.group('label')}: {part_text}")
        cleaned = f"{main_statement} Key parts: {'; '.join(summarized_parts)}"
    if len(cleaned) > MAX_REQUIREMENT_SUMMARY_CHARACTERS:
        shortened = cleaned[: MAX_REQUIREMENT_SUMMARY_CHARACTERS - 1].rsplit(" ", 1)[0]
        cleaned = f"{shortened}…"
    return cleaned.strip() or f"Review {requirement_reference} in the cited source section."


def _domain_from_requirement(text: str, requirement_reference: str) -> str:
    """Use the NERC table title when present, without inventing a domain."""
    parent_number = requirement_reference.removeprefix("R").split(".", 1)[0]
    for match in _TABLE_TITLE.finditer(text):
        if match.group("number") == parent_number:
            domain = " ".join(match.group("domain").split()).strip(" .")
            domain = re.split(r"\s*\[", domain, maxsplit=1)[0].strip(" .")
            if domain:
                return domain
    return f"Requirement R{parent_number}"


def _join_table_fragments(parts: list[str]) -> str:
    """Join fixed-column PDF fragments while repairing wrapped hyphenation."""
    text = "\n".join(part.rstrip() for part in parts if part.strip())
    text = re.sub(r"(?<=\w)-\s*\n\s*(?=\w)", "", text)
    return " ".join(text.replace("\uf0b7", "•").split()).strip()


def _requirements_page_bounds(page_texts: list[tuple[int, str]]) -> tuple[int, int] | None:
    """Return inclusive pages occupied by section B."""
    start_page: int | None = None
    end_page: int | None = None
    for page_number, text in page_texts:
        if start_page is None and _SECTION_START.search(text):
            start_page = page_number
        if start_page is not None:
            end_page = page_number
            if _SECTION_END.search(text):
                break
    if start_page is None or end_page is None:
        return None
    return start_page, end_page


def _extract_requirement_table_parts(
    page_texts: list[tuple[int, str]],
    layout_page_texts: list[tuple[int, str]],
    parent_references: set[str],
) -> list[RequirementSourceBlock]:
    """Extract the Applicable Systems and Requirements columns from NERC tables."""
    bounds = _requirements_page_bounds(page_texts)
    if bounds is None:
        return []
    first_page, last_page = bounds
    extracted: list[RequirementSourceBlock] = []
    active_reference: str | None = None
    active_parent: str | None = None
    active_domain = ""
    active_start_page = 0
    active_end_page = 0
    active_systems: list[str] = []
    active_requirement: list[str] = []

    def finish_active() -> None:
        nonlocal active_reference, active_parent, active_domain
        nonlocal active_start_page, active_end_page, active_systems, active_requirement
        if active_reference and active_parent:
            requirement_text = _join_table_fragments(active_requirement)
            applicable_systems = _join_table_fragments(active_systems)
            if requirement_text:
                source_text = f"{active_reference}. {requirement_text}"
                extracted.append(
                    RequirementSourceBlock(
                        requirement_reference=active_reference,
                        parent_requirement_reference=active_parent,
                        domain=active_domain or f"Requirement {active_parent}",
                        applicable_systems=(
                            applicable_systems
                            or "See the applicable systems column in the cited NERC requirement table."
                        ),
                        start_page=active_start_page,
                        end_page=active_end_page or active_start_page,
                        text=source_text,
                        summary=summarize_requirement_text(source_text, active_reference),
                    )
                )
        active_reference = None
        active_parent = None
        active_domain = ""
        active_start_page = 0
        active_end_page = 0
        active_systems = []
        active_requirement = []

    for page_number, layout_text in layout_page_texts:
        if page_number < first_page or page_number > last_page:
            continue
        lines = layout_text.replace("\x00", " ").splitlines()
        header_indexes = [index for index, line in enumerate(lines) if _TABLE_HEADER.search(line)]
        if not header_indexes:
            continue
        for header_index in header_indexes:
            header = lines[header_index]
            lowered_header = header.casefold()
            part_column = lowered_header.find("part")
            systems_column = lowered_header.find("applicable systems")
            requirements_column = lowered_header.find("requirements")
            measures_column = lowered_header.find("measures")
            if not (0 <= part_column < systems_column < requirements_column < measures_column):
                continue

            title_match = None
            for candidate in reversed(lines[max(0, header_index - 8) : header_index]):
                candidate_match = _TABLE_TITLE.search(candidate)
                if candidate_match:
                    title_match = candidate_match
                    break
            if title_match is None:
                continue
            table_parent = f"R{title_match.group('number')}"
            if table_parent not in parent_references:
                continue
            table_domain = " ".join(title_match.group("domain").split()).strip(" .")
            if active_parent is not None and active_parent != table_parent:
                finish_active()

            for line in lines[header_index + 1 :]:
                if _PAGE_LINE.fullmatch(line.strip()) or _SECTION_END.match(line):
                    break
                padded = line.ljust(measures_column)
                part_value = padded[part_column:systems_column].strip()
                systems_value = padded[systems_column:requirements_column].strip()
                requirement_value = padded[requirements_column:measures_column].strip()
                part_match = _TABLE_PART.fullmatch(part_value)
                if part_match:
                    reference = f"R{part_match.group('part')}"
                    if reference != active_reference:
                        finish_active()
                        active_reference = reference
                        active_parent = table_parent
                        active_domain = table_domain or f"Requirement {table_parent}"
                        active_start_page = page_number
                    active_end_page = page_number
                if active_reference is not None and active_parent == table_parent:
                    if systems_value:
                        active_systems.append(systems_value)
                    if requirement_value:
                        active_requirement.append(requirement_value)
                    active_end_page = page_number

    finish_active()
    unique: list[RequirementSourceBlock] = []
    seen: set[str] = set()
    for block in extracted:
        if block.requirement_reference in seen:
            continue
        unique.append(block)
        seen.add(block.requirement_reference)
    return unique


def _extract_structured_table_parts(
    page_texts: list[tuple[int, str]],
    table_pages: list[tuple[int, list[list[list[str | None]]]]],
    parent_references: set[str],
) -> list[RequirementSourceBlock]:
    """Read logical table cells returned by a coordinate-aware PDF extractor."""
    bounds = _requirements_page_bounds(page_texts)
    if bounds is None:
        return []
    first_page, last_page = bounds
    extracted: list[RequirementSourceBlock] = []

    for page_number, tables in table_pages:
        if page_number < first_page or page_number > last_page:
            continue
        for table in tables:
            header_index = next(
                (
                    index
                    for index, row in enumerate(table)
                    if {"part", "applicable systems", "requirements", "measures"}.issubset(
                        {" ".join(str(cell).split()).casefold() for cell in row if cell}
                    )
                ),
                None,
            )
            if header_index is None:
                continue
            title_text = " ".join(
                " ".join(str(cell).split())
                for row in table[: header_index + 1]
                for cell in row
                if cell
            )
            title_match = _TABLE_TITLE.search(title_text)
            if title_match is None:
                continue
            parent_reference = f"R{title_match.group('number')}"
            if parent_reference not in parent_references:
                continue
            domain = " ".join(title_match.group("domain").split()).strip(" .")
            domain = re.split(
                r"\b(?:Part|Applicable\s+Systems|Requirements|Measures)\b",
                domain,
                maxsplit=1,
                flags=re.IGNORECASE,
            )[0].strip(" .")

            for row in table[header_index + 1 :]:
                values = [" ".join(str(cell).split()) for cell in row if cell and str(cell).strip()]
                if len(values) < 3:
                    continue
                part_index = next(
                    (
                        index
                        for index, value in enumerate(values)
                        if _TABLE_PART.fullmatch(value)
                    ),
                    None,
                )
                if part_index is None or len(values) - part_index < 3:
                    continue
                part = _TABLE_PART.fullmatch(values[part_index])
                assert part is not None
                reference = f"R{part.group('part')}"
                systems = values[part_index + 1]
                requirement = values[part_index + 2]
                if not requirement:
                    continue
                source_text = f"{reference}. {requirement}"
                extracted.append(
                    RequirementSourceBlock(
                        requirement_reference=reference,
                        parent_requirement_reference=parent_reference,
                        domain=domain or f"Requirement {parent_reference}",
                        applicable_systems=systems,
                        start_page=page_number,
                        end_page=page_number,
                        text=source_text,
                        summary=summarize_requirement_text(source_text, reference),
                    )
                )

    combined: dict[str, RequirementSourceBlock] = {}
    for block in extracted:
        existing = combined.get(block.requirement_reference)
        if existing is None:
            combined[block.requirement_reference] = block
            continue
        combined[block.requirement_reference] = existing.model_copy(
            update={
                "end_page": max(existing.end_page, block.end_page),
                "applicable_systems": _join_table_fragments(
                    [existing.applicable_systems, block.applicable_systems]
                ),
                "text": _join_table_fragments([existing.text, block.text]),
                "summary": summarize_requirement_text(
                    _join_table_fragments([existing.text, block.text]),
                    existing.requirement_reference,
                ),
            }
        )
    return list(combined.values())


def extract_requirement_blocks(
    page_texts: list[tuple[int, str]],
    layout_page_texts: list[tuple[int, str]] | None = None,
    table_pages: list[tuple[int, list[list[list[str | None]]]]] | None = None,
) -> list[RequirementSourceBlock]:
    """Extract section-B requirements, preferring bounded table-part rows."""
    in_requirements_section = False
    finished = False
    active_reference: str | None = None
    active_start_page = 0
    active_end_page = 0
    active_parts: list[str] = []
    extracted: list[RequirementSourceBlock] = []

    def append_active(value: str, page_number: int) -> None:
        nonlocal active_end_page
        cleaned = value.strip()
        if active_reference is not None and cleaned:
            active_parts.append(cleaned)
            active_end_page = page_number

    def finish_active() -> None:
        nonlocal active_reference, active_start_page, active_end_page, active_parts
        if active_reference is None:
            return
        source_text = _without_page_noise("\n".join(active_parts))
        if source_text:
            extracted.append(
                RequirementSourceBlock(
                    requirement_reference=active_reference,
                    parent_requirement_reference=active_reference,
                    domain=_domain_from_requirement(source_text, active_reference),
                    applicable_systems=(
                        "See the Applicability section and any applicable systems table in the cited NERC source."
                    ),
                    start_page=active_start_page,
                    end_page=active_end_page or active_start_page,
                    text=source_text,
                    summary=summarize_requirement_text(source_text, active_reference),
                )
            )
        active_reference = None
        active_start_page = 0
        active_end_page = 0
        active_parts = []

    for page_number, raw_text in page_texts:
        if finished:
            break
        page_text = raw_text.replace("\x00", " ")
        if not in_requirements_section:
            section_start = _SECTION_START.search(page_text)
            if section_start is None:
                continue
            in_requirements_section = True
            page_text = page_text[section_start.end() :]

        section_end = _SECTION_END.search(page_text)
        if section_end is not None:
            page_text = page_text[: section_end.start()]
            finished = True

        markers = list(_TOP_LEVEL_MARKER.finditer(page_text))
        if active_reference is not None:
            prefix_end = markers[0].start() if markers else len(page_text)
            append_active(page_text[:prefix_end], page_number)

        for index, marker in enumerate(markers):
            next_start = markers[index + 1].start() if index + 1 < len(markers) else len(page_text)
            marker_kind = marker.group("kind").upper()
            marker_number = marker.group("number")
            if marker_kind == "M":
                if active_reference == f"R{marker_number}":
                    finish_active()
                continue

            finish_active()
            active_reference = f"R{marker_number}"
            active_start_page = page_number
            active_end_page = page_number
            append_active(page_text[marker.start() : next_start], page_number)

        if finished:
            finish_active()

    finish_active()

    unique: list[RequirementSourceBlock] = []
    seen: set[str] = set()
    for block in extracted:
        if block.requirement_reference in seen:
            continue
        unique.append(block)
        seen.add(block.requirement_reference)
    table_parts = (
        _extract_structured_table_parts(
            page_texts,
            table_pages,
            {block.requirement_reference for block in unique},
        )
        if table_pages
        else []
    )
    if not table_parts and layout_page_texts:
        table_parts = _extract_requirement_table_parts(
            page_texts,
            layout_page_texts,
            {block.requirement_reference for block in unique},
        )
    if not table_parts:
        return unique
    parts_by_parent: dict[str, list[RequirementSourceBlock]] = {}
    for part in table_parts:
        parts_by_parent.setdefault(part.parent_requirement_reference, []).append(part)

    detailed: list[RequirementSourceBlock] = []
    for parent in unique:
        detailed.extend(parts_by_parent.get(parent.requirement_reference, [parent]))
    return detailed
