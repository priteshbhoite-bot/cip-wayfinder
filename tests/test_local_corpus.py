"""Tests for local-only, idempotent corpus ingestion and retrieval."""

from __future__ import annotations

from pathlib import Path

import pytest

from nerc_compliance_intelligence.fake_tools import RequirementLookupInput, requirement_lookup
from nerc_compliance_intelligence.local_corpus import LocalCorpusStore, RetrievalQuery
from nerc_compliance_intelligence.schemas import StandardVersion


FIXTURE_CORPUS = Path(__file__).parent / "fixtures" / "corpus" / "synthetic_cip_fixture.json"


def _store(tmp_path: Path) -> LocalCorpusStore:
    return LocalCorpusStore(tmp_path / "corpus-index.sqlite")


def test_ingestion_is_idempotent_and_does_not_duplicate_chunks(tmp_path: Path) -> None:
    store = _store(tmp_path)

    first = store.ingest_file(FIXTURE_CORPUS)
    second = store.ingest_file(FIXTURE_CORPUS)

    assert first.status == "inserted"
    assert second.status == "unchanged"
    assert first.content_hash == second.content_hash
    assert store.count_chunks() == 2


def test_retrieval_preserves_all_required_metadata(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.ingest_file(FIXTURE_CORPUS)

    chunks = store.retrieve(
        RetrievalQuery(
            standard=StandardVersion(standard_id="CIP-010", version="5", scope_role="primary"),
            requirement_reference="Synthetic demo reference",
        )
    )

    assert len(chunks) == 1
    metadata = chunks[0].metadata
    assert metadata.standard_id == "CIP-010"
    assert metadata.version == "5"
    assert metadata.requirement_reference == "Synthetic demo reference"
    assert metadata.functional_entity == "Synthetic entity"
    assert metadata.jurisdiction == "Synthetic demonstration jurisdiction"
    assert metadata.enforcement_status == "Synthetic fixture; not evaluated"
    assert str(metadata.effective_date) == "2026-01-01"
    assert metadata.page == 1
    assert metadata.section == "Synthetic section 1"
    assert metadata.source_url == "https://example.invalid/synthetic-cip-010-5"
    assert str(metadata.retrieval_date) == "2026-08-27"


def test_empty_retrieval_returns_no_chunks(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.ingest_file(FIXTURE_CORPUS)

    chunks = store.retrieve(
        RetrievalQuery(
            standard=StandardVersion(standard_id="CIP-010", version="5", scope_role="primary"),
            requirement_reference="No local match",
        )
    )

    assert chunks == []


def test_existing_requirement_tool_interface_can_use_local_corpus(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.ingest_file(FIXTURE_CORPUS)

    result = requirement_lookup(
        RequirementLookupInput(
            standard=StandardVersion(standard_id="CIP-010", version="5", scope_role="primary"),
            requirement_reference="Synthetic demo reference",
        ),
        corpus_store=store,
    )

    assert result.mapping is not None
    assert result.mapping.source_locator == "page 1, section Synthetic section 1"
    assert result.chunk is not None
    assert result.chunk.metadata.source_url == "https://example.invalid/synthetic-cip-010-5"


def test_invalid_local_document_is_rejected_without_ingesting(tmp_path: Path) -> None:
    invalid_document = tmp_path / "invalid.json"
    invalid_document.write_text('{"source_id": "bad", "chunks": []}', encoding="utf-8")
    store = _store(tmp_path)

    with pytest.raises(ValueError, match="invalid local corpus document"):
        store.ingest_file(invalid_document)

    assert store.count_chunks() == 0


def test_read_only_store_retrieves_without_allowing_ingestion(tmp_path: Path) -> None:
    writable_store = _store(tmp_path)
    writable_store.ingest_file(FIXTURE_CORPUS)
    read_only_store = LocalCorpusStore(tmp_path / "corpus-index.sqlite", read_only=True)

    chunks = read_only_store.retrieve(
        RetrievalQuery(
            standard=StandardVersion(standard_id="CIP-010", version="5", scope_role="primary"),
            requirement_reference="Synthetic demo reference",
        )
    )

    assert len(chunks) == 1
    with pytest.raises(PermissionError, match="read-only"):
        read_only_store.ingest_file(FIXTURE_CORPUS)
