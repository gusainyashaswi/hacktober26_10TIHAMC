from dataclasses import replace

import pytest
from nobluff.retrieval import (
    Excerpt,
    SnapshotError,
    _git,
    load_local_snapshot,
    retrieve_evidence,
    safe_path,
    verify_excerpt,
)
from nobluff.schemas import Claim, Evidence


def test_exact_revision_and_verified_shared_evidence(source_repo):
    repo, original, fix, _ = source_repo
    snapshot = load_local_snapshot(repo, original)
    assert snapshot.commit == original
    assert "'ascii'" in snapshot.get("exporter.py").text
    assert "'utf-8'" in load_local_snapshot(repo, fix).get("exporter.py").text
    claims = [
        Claim(
            id="c",
            text="export_csv selects ASCII.",
            kind="behavior",
            search_terms=["export_csv", "encoding"],
        )
    ]
    evidence = retrieve_evidence(snapshot, claims)
    assert evidence
    for item in evidence:
        Evidence.model_validate(item.model_dump())
        assert item.revision == original
        assert verify_excerpt(
            snapshot,
            Excerpt(
                item.path, item.revision, item.start_line, item.end_line, item.excerpt
            ),
        )
    assert retrieve_evidence(snapshot, claims) == evidence


def test_fabricated_or_wrong_revision_excerpt_fails(source_repo):
    repo, original, fix, _ = source_repo
    snapshot = load_local_snapshot(repo, original)
    item = Excerpt("exporter.py", original, 1, 1, "def export_csv(path, rows):")
    assert verify_excerpt(snapshot, item)
    for bad in [
        replace(item, commit=fix),
        replace(item, text="invented"),
        replace(item, start_line=0),
        replace(item, end_line=500),
        replace(item, path="missing.py"),
    ]:
        assert not verify_excerpt(snapshot, bad)


@pytest.mark.parametrize(
    "path",
    [
        "../a.py",
        "/a.py",
        "a\\b.py",
        "a:b.py",
        ".git/a.py",
        "node_modules/a.py",
        "x.bin",
    ],
)
def test_unsafe_or_excluded_paths(path):
    assert not safe_path(path)


def test_unknown_revision_and_bounded_git_output(source_repo):
    repo, _, _, _ = source_repo
    for revision in ["--help", "missing-branch", "HEAD\nother"]:
        with pytest.raises(SnapshotError):
            load_local_snapshot(repo, revision)
    with pytest.raises(SnapshotError, match="size limit"):
        _git(repo, ["show", "HEAD:exporter.py"], 4)


def test_no_project_execution_and_skip_symlinks(source_repo, tmp_path):
    repo, _, _, git = source_repo
    marker = tmp_path / "executed"
    (repo / "danger.py").write_text(
        f"from pathlib import Path\nPath({str(marker)!r}).touch()\n"
    )
    (repo / "link.py").symlink_to("exporter.py")
    git("add", ".")
    git("commit", "-m", "Controlled nonexecution fixture")
    snapshot = load_local_snapshot(repo, "HEAD")
    assert snapshot.get("danger.py")
    assert snapshot.get("link.py") is None
    assert not marker.exists()


def test_invalid_utf8_not_claimed_as_exact_source(source_repo):
    repo, _, _, git = source_repo
    (repo / "invalid.py").write_bytes(b"\xff\xfe")
    git("add", ".")
    git("commit", "-m", "Controlled encoding fixture")
    assert load_local_snapshot(repo, "HEAD").get("invalid.py") is None
