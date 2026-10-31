"""Adapter from retrieval snippets to the shared NoBluff Evidence contract."""

from __future__ import annotations

import hashlib
from collections.abc import Iterable

from nobluff.retrieval.snapshot import (
    Excerpt,
    Snapshot,
)
from nobluff.schemas import Claim, Evidence


def _evidence_id(ex: Excerpt) -> str:
    key = f"{ex.commit}:{ex.path}:{ex.start_line}:{ex.end_line}"
    return f"ev-{hashlib.sha256(key.encode()).hexdigest()[:12]}"


def excerpt_to_evidence(ex: Excerpt) -> Evidence:
    return Evidence(
        id=_evidence_id(ex),
        kind="source",
        revision=ex.commit,
        path=ex.path,
        start_line=ex.start_line,
        end_line=ex.end_line,
        excerpt=ex.text,
        execution_id=None,
    )


def retrieve_evidence(
    snapshot: Snapshot,
    claims: Iterable[Claim],
    context: int = 2,
    max_results_per_claim: int = 20,
) -> list[Evidence]:
    """Return verified Evidence for each claim's search_terms, deduplicated by id."""
    from nobluff.retrieval.core import retrieve_evidence as canonical_retrieve

    # One shared aggregate budget, AST retrieval and citation validator.
    return canonical_retrieve(snapshot, list(claims))
