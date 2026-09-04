"""Small, explicit cache-key policy for the Streamlit MVP.

The functions in this module are deliberately independent of Streamlit so the
invalidation rules can be tested without starting the application.
"""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from nerc_compliance_intelligence.providers import ProviderSettings, StructuredRequest
from nerc_compliance_intelligence.uploaded_standard import UploadedStandard


CACHE_POLICY_VERSION = "mvp-cache-v1"
DASHBOARD_CACHE_MAX_ENTRIES = 32
MODEL_OUTPUT_SCHEMA_VERSION = "control-generation-output-v1"


class CacheMetrics(BaseModel):
    """Safe, per-browser-session counters shown in developer details."""

    model_config = ConfigDict(extra="forbid")

    dashboard_hits: int = Field(default=0, ge=0)
    dashboard_misses: int = Field(default=0, ge=0)
    model_hits: int = Field(default=0, ge=0)
    model_misses: int = Field(default=0, ge=0)
    avoided_model_calls: int = Field(default=0, ge=0)


def stable_fingerprint(namespace: str, payload: Any) -> str:
    """Return a deterministic SHA-256 key without exposing the input content."""
    if isinstance(payload, BaseModel):
        payload = payload.model_dump(mode="json")
    canonical = json.dumps(
        {"namespace": namespace, "payload": payload},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=str,
    )
    return sha256(canonical.encode("utf-8")).hexdigest()


def file_revision(path: Path) -> str:
    """Create a cheap revision token, including a live SQLite WAL when present."""
    try:
        details = path.stat()
    except OSError:
        return "missing"
    revision_parts = [(path.name, details.st_size, details.st_mtime_ns)]
    write_ahead_log = Path(f"{path}-wal")
    try:
        wal_details = write_ahead_log.stat()
    except OSError:
        pass
    else:
        revision_parts.append((write_ahead_log.name, wal_details.st_size, wal_details.st_mtime_ns))
    return stable_fingerprint("file-revision", revision_parts)


def dashboard_cache_key(uploaded: UploadedStandard, corpus_path: Path) -> str:
    """Key public derived data by document identity, requirements, and corpus revision."""
    return stable_fingerprint(
        "dashboard",
        {
            "policy_version": CACHE_POLICY_VERSION,
            "content_hash": uploaded.content_hash,
            "standard": uploaded.standard.model_dump(mode="json"),
            "requirements": [item.model_dump(mode="json") for item in uploaded.requirements],
            "corpus_revision": file_revision(corpus_path),
        },
    )


def model_result_cache_key(
    request: StructuredRequest,
    settings: ProviderSettings,
    provider_endpoint: str = "",
) -> str:
    """Key one exact approved request without including credentials in the key."""
    return stable_fingerprint(
        "model-result",
        {
            "policy_version": CACHE_POLICY_VERSION,
            "schema_version": MODEL_OUTPUT_SCHEMA_VERSION,
            "provider": settings.provider,
            "model": settings.model,
            "provider_endpoint": provider_endpoint,
            "request": request.model_dump(mode="json"),
        },
    )
