"""Contract tests for the local deterministic Milestone 13A Quality Reviewer."""

from __future__ import annotations

from datetime import date

from nerc_compliance_intelligence.baseline_analysis import AssetSnapshot, analyze_baseline
from nerc_compliance_intelligence.control_remediation import ControlGenerationInput, generate_draft_control_and_remediation
from nerc_compliance_intelligence.evidence_analysis import EvidenceAnalysisInput, analyze_evidence
from nerc_compliance_intelligence.fake_tools import RequirementLookupInput, requirement_lookup
from nerc_compliance_intelligence.quality_review import QualitySeverity, ReviewPackage, review_package
from nerc_compliance_intelligence.schemas import StandardVersion
from tests.fixtures.synthetic_evidence_documents import INCOMPLETE_EVIDENCE, STRONG_EVIDENCE


def _valid_package() -> ReviewPackage:
    lookup = requirement_lookup(RequirementLookupInput(standard=StandardVersion(standard_id="CIP-010", version="5", scope_role="primary"), requirement_reference="Synthetic demo reference"))
    assert lookup.mapping is not None
    generated = generate_draft_control_and_remediation(ControlGenerationInput(retrieved_mappings=[lookup.mapping], selected_requirement_ids=[lookup.mapping.requirement_reference]))
    expected = AssetSnapshot(asset_id="SUB-ALPHA-RTU-01", software="firmware-1.0", ports_services=["ssh:22"], patches=["patch-1"], accounts=["svc_rtu"], baseline_version="baseline-a", observation_date=date(2026, 8, 1))
    observed = expected.model_copy(update={"observation_date": date(2026, 8, 20)})
    return ReviewPackage(
        requirement_mappings=[lookup.mapping], control=generated.control, remediation_plan=generated.remediation_plan,
        evidence_analysis=analyze_evidence(EvidenceAnalysisInput(document=STRONG_EVIDENCE, expected_asset_id="SUB-ALPHA-RTU-01", expected_baseline_fingerprint="baseline-a", as_of_date=date(2026, 8, 27))),
        baseline_observation=analyze_baseline(expected, observed, generated.control.control_id, date(2026, 8, 27)),
    )


def test_complete_synthetic_package_passes_deterministic_validation() -> None:
    result = review_package(_valid_package())

    assert result.is_valid is True
    assert result.issues == []
    assert len(result.checked_components) == 5


def test_mismatched_control_link_is_a_safe_error() -> None:
    package = _valid_package()
    altered = package.model_copy(update={"remediation_plan": package.remediation_plan.model_copy(update={"control_id": "wrong-control"})})

    result = review_package(altered)

    assert result.is_valid is False
    assert result.issues[0].code == "remediation.control_link_missing"
    assert result.issues[0].severity is QualitySeverity.ERROR
    assert "wrong-control" not in result.issues[0].message


def test_incomplete_untrusted_evidence_creates_warnings_but_no_stack_trace() -> None:
    package = _valid_package()
    evidence = analyze_evidence(EvidenceAnalysisInput(document=INCOMPLETE_EVIDENCE, expected_asset_id="SUB-ALPHA-RTU-01", expected_baseline_fingerprint="baseline-a", as_of_date=date(2026, 8, 27)))

    result = review_package(package.model_copy(update={"evidence_analysis": evidence}))

    assert result.is_valid is True
    assert {issue.code for issue in result.issues} == {"evidence.untrusted_text_ignored", "evidence.incomplete"}
    assert all("Traceback" not in issue.message for issue in result.issues)
