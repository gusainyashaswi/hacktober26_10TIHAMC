"""Compatibility interface for Yogye's original snapshot consumers.

Loading and citation validation use the canonical hardened implementation.
"""
from .core import (
    Excerpt,
    Snapshot,
    SnapshotError,
    SnapshotFile,
    load_local_snapshot,
    verify_excerpt,
)

__all__ = ["Excerpt", "Snapshot", "SnapshotError", "SnapshotFile", "load_local_snapshot", "search_snippets", "verify_excerpt"]

def search_snippets(
    snapshot: Snapshot,
    terms: list[str],
    context: int = 2,
    max_results: int = 20,
) -> list[Excerpt]:
    """Find lines containing any term (case-insensitive) and return bounded windows."""
    needles = [t.lower() for t in terms if t and t.strip()]
    if not needles:
        return []

    results: list[Excerpt] = []
    for f in snapshot.files:
        lines = f.lines
        hits = [i for i, line in enumerate(lines) if any(n in line.lower() for n in needles)]
        if not hits:
            continue

        windows: list[list[int]] = []
        for i in hits:
            start, end = max(0, i - context), min(len(lines) - 1, i + context)
            if windows and start <= windows[-1][1] + 1:
                windows[-1][1] = max(windows[-1][1], end)
            else:
                windows.append([start, end])

        for start, end in windows:
            results.append(
                Excerpt(
                    path=f.path,
                    commit=snapshot.commit,
                    start_line=start + 1,
                    end_line=end + 1,
                    text="\n".join(lines[start : end + 1]),
                )
            )
            if len(results) >= max_results:
                return results
    return results

