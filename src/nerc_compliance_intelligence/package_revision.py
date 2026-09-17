"""Session-only SME tailoring of draft text, never source records or citations."""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from nerc_compliance_intelligence.quality_review import review_source_grounded_package
from nerc_compliance_intelligence.review_package_agent import ReviewPackageAgentItem, ReviewPackageAgentOutput

RevisionText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=12000)]


class DraftRevision(BaseModel):
    """One explicit reviewer save, with a required explanation."""

    model_config = ConfigDict(extra="forbid")
    requirement: str = Field(min_length=1, max_length=200)
    field: str = Field(min_length=1, max_length=200)
    text: RevisionText
    feedback: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)]
    reviewer_role: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]


def editable_fields(item: ReviewPackageAgentItem) -> dict[str, tuple[str, str]]:
    """Allow only existing draft text fields; identifiers and sources are excluded."""
    fields: dict[str, tuple[str, str]] = {}
    for name in ("title", "objective", "control_type", "owner_role", "performer",
                 "trigger_frequency", "procedure", "evidence_expectation",
                 "exception_escalation", "test_procedure"):
        fields[f"control.{name}"] = (name.replace("_", " ").capitalize(), getattr(item.control, name).text)
    for name in ("activities", "assumptions", "tailoring_questions"):
        for index, content in enumerate(getattr(item.control, name)):
            suffix = ".activity" if name == "activities" else ""
            value = content.activity.text if suffix else content.text
            fields[f"control.{name}.{index}{suffix}"] = (f"{name.replace('_', ' ').capitalize()} {index + 1}", value)
    for index, step in enumerate(item.remediation.steps):
        for name in ("action", "owner_role", "decision", "end_state"):
            fields[f"remediation.steps.{index}.{name}"] = (f"Remediation step {index + 1}: {name.replace('_', ' ')}", getattr(step, name).text)
    return fields


def revise_package(package: ReviewPackageAgentOutput, revision: DraftRevision) -> ReviewPackageAgentOutput:
    """Create a validated copy and preserve all source links and other requirements."""
    payload = package.model_dump(mode="json")
    matches = [i for i, item in enumerate(package.items) if item.mapping.requirement_reference == revision.requirement]
    if len(matches) != 1:
        raise ValueError("Select one existing requirement.")
    index = matches[0]
    allowed = editable_fields(package.items[index])
    if revision.field not in allowed:
        raise ValueError("Only the listed draft text fields may be edited.")
    if revision.text == allowed[revision.field][1]:
        raise ValueError("Change the draft text before saving a revision.")
    target: Any = payload["items"][index]
    for key in revision.field.split("."):
        target = target[int(key)] if isinstance(target, list) else target[key]
    target["text"] = revision.text
    result = ReviewPackageAgentOutput.model_validate(payload)
    if not review_source_grounded_package(result).is_valid:
        raise ValueError("The revision failed structural checks; no changes were saved.")
    return result


def dashboard_with_revision(data: dict[str, Any], package: ReviewPackageAgentOutput) -> dict[str, Any]:
    """Overlay private revisions without changing the cached, generated dashboard."""
    items = [{name: getattr(item, name) for name in ("mapping", "control", "remediation", "source_chunks", "knowledge_item")} for item in package.items]
    return {**data, "review_package_agent": package, "quality_review": review_source_grounded_package(package),
            "packages": items, "mappings": [item.mapping for item in package.items],
            "mapping": items[0]["mapping"], "control": items[0]["control"], "remediation": items[0]["remediation"]}
