import sys
from pathlib import Path

import pytest
from nobluff.retrieval.adapter import retrieve_evidence
from nobluff.retrieval.snapshot import load_local_snapshot
from nobluff.schemas import Claim

FIXTURES = Path(__file__).resolve().parents[3] / "fixtures" / "retrieval"
sys.path.insert(0, str(FIXTURES))
from build_tiny_repo import build


@pytest.fixture
def repo(tmp_path):
    commits = build(tmp_path / "tiny")
    return tmp_path / "tiny", commits


def make_claim(terms):
    return Claim(
        id="c1",
        text="average() crashes on an empty list",
        kind="behavior",
        search_terms=terms,
    )


def test_evidence_maps_commit_to_revision_and_text_to_excerpt(repo):
    path, commits = repo
    snap = load_local_snapshot(path, commits["original"])
    evidence = retrieve_evidence(snap, [make_claim(["average"])])
    assert evidence
    for ev in evidence:
        assert ev.revision == snap.commit
        assert ev.kind == "source"
        source = snap.get(ev.path).lines[ev.start_line - 1 : ev.end_line]
        assert ev.excerpt == "\n".join(source)
        assert ev.execution_id is None


def test_evidence_ids_are_deterministic_and_unique(repo):
    path, commits = repo
    snap = load_local_snapshot(path, commits["original"])
    first = retrieve_evidence(snap, [make_claim(["average"])])
    second = retrieve_evidence(snap, [make_claim(["average"])])
    assert [e.id for e in first] == [e.id for e in second]
    assert len({e.id for e in first}) == len(first)


def test_fix_revision_evidence_is_tagged_with_fix_commit(repo):
    path, commits = repo
    original = load_local_snapshot(path, commits["original"])
    fix = load_local_snapshot(path, commits["fix"])
    assert retrieve_evidence(original, [make_claim(["average"])])
    fix_evidence = retrieve_evidence(fix, [make_claim(["average"])])
    assert fix_evidence
    assert {e.revision for e in fix_evidence} == {fix.commit}


def test_claim_without_search_terms_returns_no_evidence(repo):
    path, commits = repo
    snap = load_local_snapshot(path, commits["original"])
    assert retrieve_evidence(snap, [make_claim([])]) == []


def test_unmatched_term_returns_no_evidence(repo):
    path, commits = repo
    snap = load_local_snapshot(path, commits["original"])
    assert retrieve_evidence(snap, [make_claim(["nonexistent_symbol_xyz"])]) == []
