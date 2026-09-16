"""Tests for the manifest-driven local PDF adapter using the user-provided public PDFs."""

from pathlib import Path
import re

import pytest

from nerc_compliance_intelligence.local_corpus import LocalCorpusStore, LocalPdfCorpusAdapter, RetrievalQuery
from nerc_compliance_intelligence.schemas import StandardVersion


CORPUS_DIRECTORY = Path(__file__).resolve().parents[2] / "approved-nerc-corpus"
MANIFEST = Path("data/corpus_manifests/approved_cip_manifest.json")


@pytest.mark.skipif(not CORPUS_DIRECTORY.exists(), reason="approved local corpus is not present")
def test_adapter_ingests_local_pdfs_idempotently_and_preserves_provenance(tmp_path: Path) -> None:
    store = LocalCorpusStore(tmp_path / "approved-corpus.sqlite")
    adapter = LocalPdfCorpusAdapter(CORPUS_DIRECTORY, MANIFEST)

    first = adapter.ingest_all(store)
    second = adapter.ingest_all(store)
    chunks = store.retrieve(RetrievalQuery(standard=StandardVersion(standard_id="CIP-010", version="5", scope_role="primary")))

    assert [result.status for result in first] == ["inserted"] * 24
    assert [result.status for result in second] == ["unchanged"] * 24
    assert chunks
    assert chunks[0].metadata.source_url.endswith("cip-010-5.pdf")
    assert chunks[0].metadata.retrieval_date.isoformat() == "2026-09-11"
    assert len(first) == 24
    assert sum(result.chunk_count for result in first) == 210
    assert {result.source_id for result in first} == {result.source_id for result in second}
    assert store.count_chunks() == sum(result.chunk_count for result in first)
    for entry in adapter.manifest.documents:
        requirement_chunks = store.retrieve(
            RetrievalQuery(
                standard=StandardVersion(
                    standard_id=entry.standard_id,
                    version=entry.version,
                    scope_role="primary",
                ),
            )
        )
        assert any(
            chunk.metadata.requirement_reference == "R1"
            or chunk.metadata.requirement_reference.startswith("R1.")
            for chunk in requirement_chunks
        ), f"missing R1 retrieval coverage for {entry.standard_id}-{entry.version}"
        all_standard_chunks = store.retrieve(
            RetrievalQuery(
                standard=StandardVersion(
                    standard_id=entry.standard_id,
                    version=entry.version,
                    scope_role="primary",
                )
            )
        )
        assert all(chunk.metadata.section == "B. Requirements and Measures" for chunk in all_standard_chunks)
        assert all(re.fullmatch(r"R\d+(?:\.\d+)?", chunk.metadata.requirement_reference) for chunk in all_standard_chunks)
        assert all(not re.search(r"(?m)^\s*M\s*\d+\s*\.", chunk.text) for chunk in all_standard_chunks)
        assert all("C. Compliance" not in chunk.text for chunk in all_standard_chunks)
