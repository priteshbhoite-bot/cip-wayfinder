"""Local-only, idempotent ingestion and retrieval for requirement chunks.

This module never downloads documents or follows source URLs. Source URLs are
metadata preserved from approved local files, not instructions to fetch data.
"""

from __future__ import annotations

import hashlib
from io import BytesIO
import json
import sqlite3
from datetime import date, datetime, timezone
from pathlib import Path
import re

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from pypdf import PdfReader

from nerc_compliance_intelligence.schemas import RequirementMapping, StandardVersion


class CorpusMetadata(BaseModel):
    """Required provenance fields kept with every locally ingested chunk."""

    model_config = ConfigDict(populate_by_name=True, frozen=True)

    standard_id: str = Field(pattern=r"^CIP-\d{3}$")
    version: str = Field(pattern=r"^\d+$")
    requirement_reference: str = Field(min_length=1)
    functional_entity: str = Field(min_length=1, alias="Functional Entity")
    jurisdiction: str = Field(min_length=1)
    enforcement_status: str = Field(min_length=1)
    effective_date: date | None
    page: int = Field(ge=1)
    section: str = Field(min_length=1)
    source_url: str = Field(min_length=1)
    retrieval_date: date


class RequirementChunk(BaseModel):
    """One small text unit plus the metadata needed to trace its local source."""

    chunk_id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    metadata: CorpusMetadata


class LocalCorpusDocument(BaseModel):
    """The supported local JSON document shape for this MVP."""

    source_id: str = Field(min_length=1)
    chunks: list[RequirementChunk] = Field(min_length=1)


class PdfCorpusManifestEntry(BaseModel):
    """Document-level provenance supplied locally, never fetched from the web."""

    filename: str
    source_id: str
    standard_id: str
    version: str
    functional_entity: str
    jurisdiction: str
    enforcement_status: str
    effective_date: date | None
    source_url: str
    retrieval_date: date


class PdfCorpusManifest(BaseModel):
    documents: list[PdfCorpusManifestEntry] = Field(min_length=1)


class IngestionResult(BaseModel):
    source_id: str
    content_hash: str
    status: str
    chunk_count: int


class RetrievalQuery(BaseModel):
    standard: StandardVersion
    requirement_reference: str | None = None
    functional_entity: str | None = None
    text_contains: str | None = None


class LocalCorpusStore:
    """A small SQLite index that can be opened read-only for safe retrieval."""

    def __init__(self, database_path: Path, *, read_only: bool = False) -> None:
        self.database_path = database_path
        self.read_only = read_only
        if read_only:
            if not self.database_path.is_file():
                raise FileNotFoundError(f"local corpus index was not found: {self.database_path}")
        else:
            self.database_path.parent.mkdir(parents=True, exist_ok=True)
            self._initialize()

    def _connect(self) -> sqlite3.Connection:
        if self.read_only:
            connection = sqlite3.connect(f"file:{self.database_path.resolve().as_posix()}?mode=ro", uri=True)
        else:
            connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS ingested_sources (
                    source_id TEXT PRIMARY KEY,
                    content_hash TEXT NOT NULL,
                    ingested_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS requirement_chunks (
                    chunk_id TEXT PRIMARY KEY,
                    source_id TEXT NOT NULL,
                    text TEXT NOT NULL,
                    metadata_json TEXT NOT NULL
                );
                """
            )

    def ingest_file(self, source_path: Path) -> IngestionResult:
        """Ingest one explicitly supplied local JSON document without network access."""
        if self.read_only:
            raise PermissionError("a read-only local corpus store cannot ingest documents")
        raw_content = source_path.read_bytes()
        content_hash = hashlib.sha256(raw_content).hexdigest()
        try:
            document = LocalCorpusDocument.model_validate_json(raw_content)
        except ValidationError as error:
            raise ValueError(f"invalid local corpus document: {error}") from error

        return self.ingest_document(document, content_hash)

    def ingest_document(self, document: LocalCorpusDocument, content_hash: str) -> IngestionResult:
        """Index already-parsed local content using its source hash for idempotency."""
        if self.read_only:
            raise PermissionError("a read-only local corpus store cannot ingest documents")
        with self._connect() as connection:
            existing = connection.execute(
                "SELECT content_hash FROM ingested_sources WHERE source_id = ?",
                (document.source_id,),
            ).fetchone()
            if existing and existing["content_hash"] == content_hash:
                return IngestionResult(
                    source_id=document.source_id,
                    content_hash=content_hash,
                    status="unchanged",
                    chunk_count=len(document.chunks),
                )

            connection.execute("DELETE FROM requirement_chunks WHERE source_id = ?", (document.source_id,))
            for chunk in document.chunks:
                connection.execute(
                    "INSERT INTO requirement_chunks (chunk_id, source_id, text, metadata_json) VALUES (?, ?, ?, ?)",
                    (
                        chunk.chunk_id,
                        document.source_id,
                        chunk.text,
                        json.dumps(chunk.metadata.model_dump(mode="json", by_alias=True), sort_keys=True),
                    ),
                )
            connection.execute(
                "INSERT OR REPLACE INTO ingested_sources (source_id, content_hash, ingested_at) VALUES (?, ?, ?)",
                (document.source_id, content_hash, datetime.now(timezone.utc).isoformat()),
            )
        return IngestionResult(
            source_id=document.source_id,
            content_hash=content_hash,
            status="inserted" if existing is None else "updated",
            chunk_count=len(document.chunks),
        )

    def retrieve(self, query: RetrievalQuery) -> list[RequirementChunk]:
        """Return exact version-scoped local chunks, optionally narrowed by metadata/text."""
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT chunk_id, text, metadata_json FROM requirement_chunks ORDER BY chunk_id"
            ).fetchall()

        matches: list[RequirementChunk] = []
        for row in rows:
            metadata = CorpusMetadata.model_validate_json(row["metadata_json"])
            if metadata.standard_id != query.standard.standard_id or metadata.version != query.standard.version:
                continue
            if query.requirement_reference and metadata.requirement_reference != query.requirement_reference:
                continue
            if query.functional_entity and metadata.functional_entity != query.functional_entity:
                continue
            if query.text_contains and query.text_contains.casefold() not in row["text"].casefold():
                continue
            matches.append(RequirementChunk(chunk_id=row["chunk_id"], text=row["text"], metadata=metadata))
        return matches

    def count_chunks(self) -> int:
        """Return the number of locally indexed chunks for idempotency tests."""
        with self._connect() as connection:
            row = connection.execute("SELECT COUNT(*) AS count FROM requirement_chunks").fetchone()
        return int(row["count"])


class LocalPdfCorpusAdapter:
    """Extract page chunks from explicitly supplied local PDFs listed in a local manifest."""

    def __init__(self, corpus_directory: Path, manifest_path: Path) -> None:
        self.corpus_directory = corpus_directory.resolve()
        self.manifest = PdfCorpusManifest.model_validate_json(manifest_path.read_bytes())

    def ingest_all(self, store: LocalCorpusStore) -> list[IngestionResult]:
        """Read only manifest-listed local files and send deterministic chunks to the store."""
        results: list[IngestionResult] = []
        for entry in self.manifest.documents:
            source_path = (self.corpus_directory / entry.filename).resolve()
            if not source_path.is_relative_to(self.corpus_directory):
                raise ValueError("manifest filename must stay inside the local corpus directory")
            raw_pdf = source_path.read_bytes()
            document = self._extract_document(entry, raw_pdf)
            content_hash = hashlib.sha256(raw_pdf + document.model_dump_json().encode("utf-8")).hexdigest()
            results.append(store.ingest_document(document, content_hash))
        return results

    def _extract_document(self, entry: PdfCorpusManifestEntry, raw_pdf: bytes) -> LocalCorpusDocument:
        reader = PdfReader(BytesIO(raw_pdf))
        chunks: list[RequirementChunk] = []
        current_requirement = "Document introduction"
        for page_number, page in enumerate(reader.pages, start=1):
            text = (page.extract_text() or "").replace("\x00", "").strip()
            if not text:
                continue
            requirement_match = re.search(r"\bR\s*(\d+)\.", text)
            if requirement_match:
                current_requirement = f"R{requirement_match.group(1)}"
            section = "B. Requirements and Measures" if "Requirements and Measures" in text else "Extracted PDF page"
            chunks.append(
                RequirementChunk(
                    chunk_id=f"{entry.source_id}-page-{page_number}",
                    text=text,
                    metadata=CorpusMetadata(
                        standard_id=entry.standard_id,
                        version=entry.version,
                        requirement_reference=current_requirement,
                        **{"Functional Entity": entry.functional_entity},
                        jurisdiction=entry.jurisdiction,
                        enforcement_status=entry.enforcement_status,
                        effective_date=entry.effective_date,
                        page=page_number,
                        section=section,
                        source_url=entry.source_url,
                        retrieval_date=entry.retrieval_date,
                    ),
                )
            )
        return LocalCorpusDocument(source_id=entry.source_id, chunks=chunks)


def chunk_to_mapping(chunk: RequirementChunk, scope_role: str) -> RequirementMapping:
    """Adapt a retrieved local chunk to the existing requirement-tool output shape."""
    return RequirementMapping(
        mapping_id=f"local-{chunk.chunk_id}",
        standard=StandardVersion(
            standard_id=chunk.metadata.standard_id,
            version=chunk.metadata.version,
            scope_role=scope_role,
        ),
        requirement_reference=chunk.metadata.requirement_reference,
        source_name="Approved local corpus document",
        source_locator=f"page {chunk.metadata.page}, section {chunk.metadata.section}",
        draft_summary=chunk.text,
    )
