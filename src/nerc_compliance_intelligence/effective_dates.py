"""Offline extraction of the supplied US requirement-date table; no date inference."""

from __future__ import annotations

from datetime import date, datetime
from hashlib import sha256
from pathlib import Path
import re

import pdfplumber
from pydantic import BaseModel, ConfigDict, Field


class RequirementDate(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    row_id: int = Field(ge=1)
    requirement: str = Field(pattern=r"^R\d+(?:\.\d+)*$")
    requirement_date: date | None
    part_date: date | None
    inactive_date: date | None
    status: str
    page: int = Field(ge=1)
    no_parts: bool = False
    source_note: str = ""


class EffectiveDateSchedule(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    standard_version: str = Field(pattern=r"^CIP-\d{3}-\d+(?:\.\d+)?[a-z]?$")
    jurisdiction: str = "United States"
    source_name: str
    source_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    extracted_on: date
    rows: list[RequirementDate] = Field(min_length=1)


def date_summary(schedule: EffectiveDateSchedule) -> str:
    """Summarize all listed rows, never a partial subset or another version."""
    rows = [row for row in schedule.rows if not row.no_parts]
    if any(row.source_note for row in rows):
        return "Review date notes"
    dates = {value for row in rows for value in (row.requirement_date, row.part_date) if value}
    if not dates:
        return "Not specified"
    if any(row.requirement_date is None for row in rows):
        return "Incomplete dates"
    if len(dates) > 1:
        return "Multiple effective dates"
    return next(iter(dates)).isoformat()


def _text(value: str | None) -> str:
    return " ".join((value or "").split())


def _date(value: str) -> date | None:
    if not value:
        return None
    # Unexpected formulas or notes must be reviewed, not silently discarded.
    return datetime.strptime(value, "%b %d, %Y").date()


def parse_date_table(table: list[list[str | None]], page: int) -> list[tuple[str, RequirementDate]]:
    """Use column names, not offsets that could confuse regulatory-order dates."""
    if not table:
        return []
    header = [_text(cell) for cell in table[0]]
    if "Effective Date of Requirement" not in header:
        return []
    needed = ["#", "Status", "Standard", "Standard Version", "Requirement / Part",
              "Effective Date of Requirement", "Effective Date of Part", "Inactive Date of Requirement / Part"]
    if any(name not in header for name in needed):
        raise ValueError(f"Incomplete date table header on page {page}")
    result: list[tuple[str, RequirementDate]] = []
    for cells in table[1:]:
        if len(cells) != len(header):
            raise ValueError(f"Unexpected date row width on page {page}")
        values = dict(zip(header, map(_text, cells), strict=True))
        if not values["#"]:
            raise ValueError(f"Unidentified date row on page {page}")
        label = values["Requirement / Part"]
        no_parts = label.startswith("No Parts for ")
        label = label.removeprefix("No Parts for ").rstrip(".")
        identity = re.fullmatch(r"(\d+(?:\.\d+)*)(?:\.\s*|\s+)?(.*)", label)
        if identity is None:
            raise ValueError(f"Unrecognized requirement label on page {page}")
        label, note = identity.groups()
        version = values["Standard Version"]
        if not version.startswith(values["Standard"] + "-"):
            raise ValueError("Standard/version mismatch in source table")
        result.append((version, RequirementDate(
            row_id=int(values["#"]), requirement="R" + label,
            requirement_date=_date(values["Effective Date of Requirement"]),
            part_date=_date(values["Effective Date of Part"]),
            inactive_date=_date(values["Inactive Date of Requirement / Part"]),
            status=values["Status"], page=page, no_parts=no_parts, source_note=note,
        )))
    return result


def extract_date_schedules(path: Path) -> dict[str, EffectiveDateSchedule]:
    """Read only date tables and require the export's declared row count."""
    groups: dict[str, list[RequirementDate]] = {}
    row_ids: set[int] = set()
    with pdfplumber.open(path) as pdf:
        title = pdf.pages[0].extract_text() or ""
        count = re.search(r"(\d+) entries", title)
        if "US Effective Date Status" not in title or count is None:
            raise ValueError("Expected the approved US effective-date reference export")
        for page_number, page in enumerate(pdf.pages, start=1):
            if "Effective Date of Requirement" not in (page.extract_text() or ""):
                continue
            for table in page.extract_tables():
                for version, row in parse_date_table(table, page_number):
                    if row.row_id in row_ids:
                        raise ValueError("Duplicate effective-date source row")
                    row_ids.add(row.row_id)
                    groups.setdefault(version, []).append(row)
    if row_ids != set(range(1, int(count.group(1)) + 1)):
        raise ValueError("Date extraction did not cover every declared source row")
    digest = sha256(path.read_bytes()).hexdigest()
    return {version: EffectiveDateSchedule(
        standard_version=version, source_name=path.name, source_sha256=digest,
        extracted_on=date.today(), rows=rows,
    ) for version, rows in groups.items()}
