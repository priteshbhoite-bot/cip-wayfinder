"""Safe, deterministic analysis of synthetic evidence documents for Milestone 11.

Document text is untrusted data.  This module extracts only a small allowlist of
label/value facts; it never follows instructions found in a document.
"""

from __future__ import annotations

import re
from datetime import date
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


ALLOWED_FACT_LABELS = (
    "Evidence ID",
    "Asset ID",
    "Captured On",
    "Change Approval",
    "Baseline Fingerprint",
)
_FACT_PATTERN = re.compile(r"^([A-Za-z ]+):\s*(.+)$")
_INSTRUCTION_PATTERN = re.compile(r"\b(ignore|instruction|system prompt|assistant)\b", re.IGNORECASE)


class ConfidenceLevel(str, Enum):
    """Plain-language confidence labels for a synthetic evidence observation."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class SyntheticEvidenceDocument(BaseModel):
    """A fictional document fixture. Its text must never be treated as commands."""

    document_id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    document_text: str = Field(min_length=1)
    synthetic: bool = True


class ObservableFact(BaseModel):
    """A label/value pair explicitly present in a permitted document-text field."""

    label: str
    value: str


class EvidenceAnalysisInput(BaseModel):
    """The fixed context the analyst uses instead of trusting document instructions."""

    document: SyntheticEvidenceDocument
    expected_asset_id: str = Field(min_length=1)
    expected_baseline_fingerprint: str | None = None
    as_of_date: date


class EvidenceAnalysisOutput(BaseModel):
    """Draft analytical observations, never a compliance conclusion or approval."""

    model_config = ConfigDict(frozen=True)

    observable_facts: list[ObservableFact]
    possible_control_support: list[str]
    missing_fields: list[str]
    age_days: int | None = Field(default=None, ge=0)
    inconsistencies: list[str]
    confidence: ConfidenceLevel
    sme_questions: list[str]
    ignored_instruction_lines: int = Field(ge=0)
    safety_note: str = "Document text was treated as untrusted data; this is a draft observation, not a compliance conclusion."


def extract_observable_facts(document_text: str) -> tuple[list[ObservableFact], int]:
    """Extract only exact allowed labels and count directive-like lines as ignored."""
    facts: list[ObservableFact] = []
    ignored_instruction_lines = 0
    for raw_line in document_text.splitlines():
        line = raw_line.strip()
        if _INSTRUCTION_PATTERN.search(line):
            ignored_instruction_lines += 1
            continue
        match = _FACT_PATTERN.match(line)
        if match and match.group(1) in ALLOWED_FACT_LABELS:
            facts.append(ObservableFact(label=match.group(1), value=match.group(2).strip()))
    return facts, ignored_instruction_lines


def analyze_evidence(analysis_input: EvidenceAnalysisInput) -> EvidenceAnalysisOutput:
    """Make explainable observations using fixed rules, not document-provided commands."""
    facts, ignored_instruction_lines = extract_observable_facts(analysis_input.document.document_text)
    values = {fact.label: fact.value for fact in facts}
    missing_fields = [label for label in ALLOWED_FACT_LABELS if not values.get(label)]
    inconsistencies: list[str] = []
    support: list[str] = []
    questions: list[str] = []
    age_days: int | None = None

    captured_on = values.get("Captured On")
    if captured_on:
        try:
            captured_date = date.fromisoformat(captured_on)
            age_days = (analysis_input.as_of_date - captured_date).days
            if age_days < 0:
                inconsistencies.append("Captured On is after the analysis date.")
                age_days = None
            elif age_days > 30:
                questions.append("Is this synthetic evidence still current enough for the organization-specific review?")
        except ValueError:
            inconsistencies.append("Captured On is not an ISO date (YYYY-MM-DD).")

    if values.get("Asset ID") and values["Asset ID"] != analysis_input.expected_asset_id:
        inconsistencies.append("Document Asset ID does not match the review asset.")
        questions.append("Is this document related to the selected synthetic asset, or was the wrong artifact supplied?")
    if values.get("Change Approval", "").casefold() == "approved":
        support.append("The document records a synthetic approved change status.")
    elif values.get("Change Approval"):
        questions.append("Can an SME clarify the synthetic change-approval status?")

    fingerprint = values.get("Baseline Fingerprint")
    if analysis_input.expected_baseline_fingerprint and fingerprint:
        if fingerprint == analysis_input.expected_baseline_fingerprint:
            support.append("The document fingerprint matches the supplied synthetic baseline.")
        else:
            inconsistencies.append("Document baseline fingerprint does not match the supplied synthetic baseline.")
            questions.append("Should an SME investigate the synthetic baseline variance before tailoring a control?")

    if missing_fields:
        questions.append("Please provide or explain the missing synthetic fields: " + ", ".join(missing_fields) + ".")
    if ignored_instruction_lines:
        questions.append("The document contained instruction-like text that was ignored. Can an SME confirm the factual fields above?")

    if not missing_fields and not inconsistencies and age_days is not None and age_days <= 30:
        confidence = ConfidenceLevel.HIGH
    elif len(missing_fields) <= 1 and not inconsistencies:
        confidence = ConfidenceLevel.MEDIUM
    else:
        confidence = ConfidenceLevel.LOW

    return EvidenceAnalysisOutput(
        observable_facts=facts,
        possible_control_support=support,
        missing_fields=missing_fields,
        age_days=age_days,
        inconsistencies=inconsistencies,
        confidence=confidence,
        sme_questions=questions,
        ignored_instruction_lines=ignored_instruction_lines,
    )
