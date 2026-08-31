"""Tests for the manifest-driven local PDF adapter using the user-provided public PDFs."""

from pathlib import Path

import pytest

from nerc_compliance_intelligence.local_corpus import LocalCorpusStore, LocalPdfCorpusAdapter, RetrievalQuery
from nerc_compliance_intelligence.schemas import StandardVersion


CORPUS_DIRECTORY = Path(__file__).resolve().parents[2] / "approved-nerc-corpus"
MANIFEST = Path("data/corpus_manifests/approved_nerc_manifest.json")


@pytest.mark.skipif(not CORPUS_DIRECTORY.exists(), reason="approved local corpus is not present")
def test_adapter_ingests_local_pdfs_idempotently_and_preserves_provenance(tmp_path: Path) -> None:
    store = LocalCorpusStore(tmp_path / "approved-corpus.sqlite")
    adapter = LocalPdfCorpusAdapter(CORPUS_DIRECTORY, MANIFEST)

    first = adapter.ingest_all(store)
    second = adapter.ingest_all(store)
    chunks = store.retrieve(RetrievalQuery(standard=StandardVersion(standard_id="CIP-010", version="5", scope_role="primary")))

    assert [result.status for result in first] == ["inserted", "inserted"]
    assert [result.status for result in second] == ["unchanged", "unchanged"]
    assert chunks
    assert chunks[0].metadata.source_url.endswith("cip-010-5.pdf")
    assert chunks[0].metadata.retrieval_date.isoformat() == "2026-08-27"
