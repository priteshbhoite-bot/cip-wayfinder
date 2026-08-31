"""Lesson 01: Build a small fictional compliance-review case.

This file intentionally uses basic Python building blocks before the project
introduces databases, agent graphs, or model calls.
"""

from typing import Any

# Variables give a name to a value. A string is text inside quotation marks.
UTILITY_NAME: str = "Northstar Grid Services"
DEFAULT_ASSET_ID: str = "SUB-ALPHA-RTU-01"

# A list keeps values in order. Here it stores fictional evidence labels.
EVIDENCE_LABELS: list[str] = ["baseline record", "change approval record"]

# A dictionary connects a key (such as "standard") to a value.
CASE_DETAILS: dict[str, str] = {
    "standard": "CIP-010-5",
    "version_boundary": "synthetic demo scope",
    "review_status": "draft",
}


def build_case_summary(asset_id: str, evidence_labels: list[str]) -> dict[str, Any]:
    """Build a simple summary for a fictional asset review.

    A function groups reusable instructions under a name. Type hints show the
    expected input and output shapes, helping people and tools catch mistakes.
    """
    if not asset_id.strip():
        raise ValueError("asset_id must not be blank")

    return {
        "utility": UTILITY_NAME,
        "asset_id": asset_id,
        "standard": CASE_DETAILS["standard"],
        "evidence_count": len(evidence_labels),
        "review_status": CASE_DETAILS["review_status"],
    }


def main() -> None:
    """Print the lesson result when this file is run directly."""
    summary = build_case_summary(DEFAULT_ASSET_ID, EVIDENCE_LABELS)
    print(summary)


# The main guard runs main() only when this file is executed directly.
# It does not run when pytest imports this file to test build_case_summary().
if __name__ == "__main__":
    main()
