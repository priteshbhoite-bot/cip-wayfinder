"""Pure contract tests for the upload-driven Streamlit dashboard data."""

from __future__ import annotations

from datetime import date
from io import BytesIO
from pathlib import Path

from pypdf import PdfWriter

from nerc_compliance_intelligence.app import SCREEN_NAMES, _requirement_source_line, _requirement_vital_summary, uploaded_dashboard_data
from nerc_compliance_intelligence.local_corpus import (
    CorpusMetadata,
    LocalCorpusDocument,
    LocalCorpusStore,
    RequirementChunk,
)
from nerc_compliance_intelligence.schemas import StandardVersion
from nerc_compliance_intelligence.uploaded_standard import (
    UploadedRequirementOption,
    UploadedStandard,
    validate_uploaded_standard,
)


def _pdf_bytes() -> bytes:
    output = BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    writer.write(output)
    return output.getvalue()


def test_uploaded_document_populates_chat_options_and_detail_views() -> None:
    uploaded = validate_uploaded_standard(file_name="CIP-007-6.pdf", file_bytes=_pdf_bytes(), authorized_public_document=True)
    dashboard = uploaded_dashboard_data(uploaded)

    assert SCREEN_NAMES == ("Start a review", "Review package")
    assert "evidence" not in dashboard
    assert "baseline" not in dashboard
    assert dashboard["uploaded"].file_name == "CIP-007-6.pdf"
    assert dashboard["mapping"].standard.standard_id == "CIP-007"
    assert dashboard["control"].objective.requirement_ids == ["Document overview"]
    assert dashboard["remediation"].is_draft is True
    assert len(dashboard["packages"]) == 1


def test_review_package_generates_a_separate_traceable_draft_for_every_requirement() -> None:
    uploaded = UploadedStandard(
        file_name="CIP-010-5.pdf",
        content_hash="a" * 64,
        standard=StandardVersion(standard_id="CIP-010", version="5", scope_role="primary"),
        page_count=2,
        extracted_character_count=200,
        requirements=[
            UploadedRequirementOption(requirement_reference="R1", page=1),
            UploadedRequirementOption(requirement_reference="R2", page=2),
        ],
    )

    dashboard = uploaded_dashboard_data(uploaded)

    assert [package["mapping"].requirement_reference for package in dashboard["packages"]] == ["R1", "R2"]
    assert [package["control"].objective.requirement_ids for package in dashboard["packages"]] == [["R1"], ["R2"]]
    assert len({package["control"].control_id for package in dashboard["packages"]}) == 2


def test_review_package_uses_matching_read_only_local_source_chunks(tmp_path: Path) -> None:
    index_path = tmp_path / "approved-corpus.sqlite"
    writable_store = LocalCorpusStore(index_path)
    metadata = CorpusMetadata(
        standard_id="CIP-010",
        version="5",
        requirement_reference="R1",
        **{"Functional Entity": "Synthetic entity"},
        jurisdiction="Synthetic jurisdiction",
        enforcement_status="Synthetic test only",
        effective_date=date(2026, 1, 1),
        page=7,
        section="Requirements and Measures",
        source_url="https://example.invalid/cip-010-5",
        retrieval_date=date(2026, 8, 30),
    )
    writable_store.ingest_document(
        LocalCorpusDocument(
            source_id="local-cip-010-5",
            chunks=[RequirementChunk(chunk_id="cip-010-r1-page-7", text="Locally indexed\n\nrequirement   source text for R1.", metadata=metadata)],
        ),
        content_hash="b" * 64,
    )
    uploaded = UploadedStandard(
        file_name="CIP-010-5.pdf",
        content_hash="a" * 64,
        standard=StandardVersion(standard_id="CIP-010", version="5", scope_role="primary"),
        page_count=7,
        extracted_character_count=100,
        requirements=[UploadedRequirementOption(requirement_reference="R1", page=7)],
    )

    dashboard = uploaded_dashboard_data(uploaded, corpus_database_path=index_path)

    assert dashboard["local_source_match_count"] == 1
    assert dashboard["packages"][0]["mapping"].source_locator == "page 7, section Requirements and Measures"
    source_chunks = dashboard["packages"][0]["source_chunks"]
    assert source_chunks[0].text == "Locally indexed\n\nrequirement   source text for R1."
    assert _requirement_source_line(source_chunks) == "Source: page 7, Requirements and Measures | retrieved 2026-08-30"
    control = dashboard["packages"][0]["control"]
    summary = _requirement_vital_summary(control)
    assert "CIP-010-5 R1" in control.title.text
    assert "**Purpose:**" in summary
    assert "**Key activity:**" in summary
    assert "**Timing:**" in summary
    assert "**Typical owner:**" in summary
    assert "**Evidence to retain:**" in summary
    assert source_chunks[0].text not in summary


def test_uploaded_dashboard_serializes_standard_at_the_retrieval_boundary() -> None:
    project_root = Path(__file__).resolve().parents[1]
    app_source = (project_root / "src" / "nerc_compliance_intelligence" / "app.py").read_text(encoding="utf-8")

    assert "standard=uploaded_standard.standard.model_dump()" in app_source
