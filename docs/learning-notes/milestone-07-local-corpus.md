# Milestone 7 Learning Note: Local Corpus Ingestion

## Corpus inspection result

No approved NERC corpus files were present in this repository when Milestone 7 was built. The project therefore uses `tests/fixtures/corpus/synthetic_cip_fixture.json`, a two-chunk synthetic fixture. It is not NERC content and must not be presented as a compliance source.

## What ingestion does

`LocalCorpusStore.ingest_file()` accepts an explicitly supplied local JSON path. It reads bytes from that path, calculates a SHA-256 hash, validates the JSON shape with Pydantic, and stores the chunks in SQLite. It never follows `source_url`, makes an HTTP request, or crawls the web.

The source ID and content hash make ingestion idempotent: a second ingestion of the unchanged file returns `unchanged` and does not duplicate chunks. If the file changes with the same source ID, the old chunks are replaced as one local update.

## Metadata kept with every chunk

Each chunk retains standard, version, requirement reference, Functional Entity, jurisdiction, enforcement status, effective date, page, section, source URL, and retrieval date. The source URL is provenance text only; it is never fetched by this code.

## Existing tool interface

The existing `requirement_lookup()` function keeps its typed input/output shape. When a `LocalCorpusStore` is passed in, it retrieves local chunks and returns both a compatible `RequirementMapping` and the full chunk metadata. Existing fake-only calls continue to work without a corpus store.

## Adding approved local documents later

Convert each approved local source into the documented JSON shape, preserve its original source metadata, and call `ingest_file()` with its local path. Do not paste confidential material into source code, tests, or Git. No web-crawling feature should be added to this MVP.
