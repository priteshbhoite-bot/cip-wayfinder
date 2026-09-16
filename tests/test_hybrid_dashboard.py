"""Pure contract tests for the upload-driven Streamlit dashboard data."""

from __future__ import annotations

from datetime import date
from io import BytesIO
from pathlib import Path

from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from nerc_compliance_intelligence.app import SCREEN_NAMES, _official_requirement_text, _requirement_source_line, _requirement_vital_summary, uploaded_dashboard_data
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
    page = writer.add_blank_page(width=612, height=792)
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    font_reference = writer._add_object(font)
    page[NameObject("/Resources")] = DictionaryObject(
        {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font_reference})}
    )
    stream = DecodedStreamObject()
    stream.set_data(
        b"BT /F1 10 Tf 36 740 Td "
        b"(North American Electric Reliability Corporation - NERC | Reliability Standard CIP-007-6. "
        b"This public standard supports a local learning review.) Tj ET"
    )
    page[NameObject("/Contents")] = writer._add_object(stream)
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
    assert dashboard["control"].objective.requirement_ids == ["CIP-007-6 overview"]
    assert dashboard["remediation"].is_draft is True
    assert len(dashboard["packages"]) == 1
    assert dashboard["review_package_agent"].items[0].mapping == dashboard["mapping"]


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


def test_new_nerc_family_uses_dynamic_uploaded_knowledge_without_a_corpus_match() -> None:
    standard = StandardVersion(standard_id="PRC-005", version="6", scope_role="primary")
    uploaded = UploadedStandard(
        file_name="protection-maintenance.pdf",
        content_hash="c" * 64,
        standard=standard,
        page_count=3,
        extracted_character_count=500,
        requirements=[
            UploadedRequirementOption(
                requirement_reference="R1",
                page=3,
                title="Protection system maintenance program",
                summary="The section focuses on maintaining a documented protection-system maintenance program.",
                standard=standard,
                source_requirement_reference="R1",
            )
        ],
        document_title="Protection System Maintenance",
        document_type="NERC Reliability Standard",
        referenced_standards=[standard],
        nerc_identity_signals=["North American Electric Reliability Corporation name"],
    )

    dashboard = uploaded_dashboard_data(uploaded)

    assert dashboard["local_source_match_count"] == 0
    assert dashboard["mapping"].standard.standard_id == "PRC-005"
    assert dashboard["mapping"].draft_summary == uploaded.requirements[0].summary
    assert dashboard["packages"][0]["knowledge_item"].page == 3
    assert dashboard["control"].objective.requirement_ids == ["R1"]
    assert dashboard["review_package_agent"].missing_information == [
        "R1: no approved local corpus match; verify the uploaded-document summary against the official source."
    ]


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
    summary = _requirement_vital_summary(dashboard["packages"][0]["knowledge_item"])
    assert "CIP-010-5 R1" in control.title.text
    assert summary.startswith("**What it requires:**")
    assert source_chunks[0].text not in summary
    assert _official_requirement_text(source_chunks, dashboard["packages"][0]["knowledge_item"]) == source_chunks[0].text


def test_uploaded_dashboard_serializes_standard_at_the_retrieval_boundary() -> None:
    project_root = Path(__file__).resolve().parents[1]
    app_source = (project_root / "src" / "nerc_compliance_intelligence" / "app.py").read_text(encoding="utf-8")

    assert "standard=(requirement.standard or uploaded_standard.standard).model_dump()" in app_source
