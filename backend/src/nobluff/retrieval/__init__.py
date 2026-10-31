"""One canonical retrieval interface shared by API, adapters and runner."""
from .core import (
    MAX_FILE_SIZE,
    MAX_FILES,
    MAX_TOTAL_SIZE,
    Excerpt,
    Snapshot,
    SnapshotError,
    SnapshotFile,
    load_local_snapshot,
    retrieve_evidence,
    safe_path,
    verify_excerpt,
)

__all__ = ["MAX_FILES", "MAX_FILE_SIZE", "MAX_TOTAL_SIZE", "Excerpt", "Snapshot",
           "SnapshotError", "SnapshotFile", "load_local_snapshot", "retrieve_evidence",
           "safe_path", "verify_excerpt"]
