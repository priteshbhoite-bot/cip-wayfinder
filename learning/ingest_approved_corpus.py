"""Run local-only ingestion for the approved NERC PDFs listed in the manifest."""

from pathlib import Path

from nerc_compliance_intelligence.local_corpus import LocalCorpusStore, LocalPdfCorpusAdapter


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CORPUS_DIRECTORY = PROJECT_ROOT.parent / "approved-nerc-corpus"
MANIFEST = PROJECT_ROOT / "data" / "corpus_manifests" / "approved_cip_manifest.json"
DATABASE = PROJECT_ROOT / "data" / "approved_nerc_corpus.sqlite"


def main() -> None:
    store = LocalCorpusStore(DATABASE)
    results = LocalPdfCorpusAdapter(CORPUS_DIRECTORY, MANIFEST).ingest_all(store)
    for result in results:
        print(f"{result.source_id}: {result.status} ({result.chunk_count} chunks)")
    print(
        f"Indexed {len(results)} approved CIP documents into "
        f"{store.count_chunks()} bounded requirement chunks."
    )


if __name__ == "__main__":
    main()
