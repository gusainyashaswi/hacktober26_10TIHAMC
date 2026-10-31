"""Local repository snapshot loading at an exact revision.

PROVISIONAL: the Snapshot fields follow docs/snapshot-interface.md and must be
agreed with Gurmehar and Yashaswi before integration.

Nothing here executes repository code. Files are read from git object storage
with `git cat-file`; no checkout, install, or import of repository code happens.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

MAX_FILES = 2_000
MAX_FILE_BYTES = 512 * 1024
MAX_TOTAL_BYTES = 16 * 1024 * 1024
TEXT_SUFFIXES = frozenset({".py", ".md", ".rst", ".txt", ".toml", ".cfg", ".ini"})
EXCLUDED_PARTS = frozenset({".git", "node_modules", ".venv", "venv", "__pycache__"})
_SYMLINK_MODE = "120000"


class SnapshotError(Exception):
    """Raised when a snapshot cannot be loaded safely."""


@dataclass(frozen=True)
class SnapshotFile:
    path: str  # repo-relative POSIX path
    blob: str  # git object id of the file content
    text: str

    @property
    def lines(self) -> list[str]:
        return self.text.splitlines()


@dataclass(frozen=True)
class Snapshot:
    repository: str  # identity, e.g. "local:/abs/path"
    requested_revision: str
    commit: str  # exact 40-hex commit id
    location: str  # local repository the snapshot was read from
    files: tuple[SnapshotFile, ...]

    def get(self, path: str) -> SnapshotFile | None:
        for f in self.files:
            if f.path == path:
                return f
        return None


@dataclass(frozen=True)
class Excerpt:
    path: str
    commit: str
    start_line: int  # 1-based, inclusive
    end_line: int  # 1-based, inclusive
    text: str


def _git(repo: Path, *args: str) -> bytes:
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        msg = proc.stderr.decode("utf-8", errors="replace").strip()
        raise SnapshotError(f"git {args[0]} failed: {msg or 'unknown error'}")
    return proc.stdout


def resolve_commit(repo: Path, revision: str) -> str:
    if not revision or revision.startswith("-"):
        raise SnapshotError(f"invalid revision: {revision!r}")
    try:
        out = _git(repo, "rev-parse", "--verify", f"{revision}^{{commit}}")
    except SnapshotError as exc:
        raise SnapshotError(f"revision not found: {revision}") from exc
    commit = out.decode().strip()
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise SnapshotError(f"unexpected commit id: {commit}")
    return commit


def _is_safe_path(path: str) -> bool:
    if not path:
        return False
    p = PurePosixPath(path)
    return not p.is_absolute() and ".." not in p.parts and "\\" not in path


def _is_candidate(path: str) -> bool:
    p = PurePosixPath(path)
    if p.suffix not in TEXT_SUFFIXES:
        return False
    return not any(part in EXCLUDED_PARTS for part in p.parts)


def load_local_snapshot(repo_path: str | Path, revision: str) -> Snapshot:
    """Load candidate text files at an exact revision of a local git repository."""
    repo = Path(repo_path).resolve()
    if not repo.is_dir():
        raise SnapshotError(f"not a directory: {repo}")

    commit = resolve_commit(repo, revision)
    listing = _git(repo, "ls-tree", "-r", "-z", "--full-tree", commit)

    files: list[SnapshotFile] = []
    total = 0
    for entry in listing.split(b"\0"):
        if not entry:
            continue
        meta, _, raw_path = entry.partition(b"\t")
        mode, kind, blob = meta.decode().split()
        path = raw_path.decode("utf-8", errors="replace")

        if kind != "blob" or mode == _SYMLINK_MODE:
            continue  # skip trees, submodules and symlinks
        if not _is_safe_path(path) or not _is_candidate(path):
            continue
        if len(files) >= MAX_FILES:
            raise SnapshotError(f"snapshot exceeds {MAX_FILES} files")

        content = _git(repo, "cat-file", "blob", blob)
        if len(content) > MAX_FILE_BYTES:
            continue  # oversized files are excluded, not decoded
        total += len(content)
        if total > MAX_TOTAL_BYTES:
            raise SnapshotError("snapshot exceeds total size limit")

        files.append(
            SnapshotFile(path=path, blob=blob, text=content.decode("utf-8", errors="replace"))
        )

    files.sort(key=lambda f: f.path)
    return Snapshot(
        repository=f"local:{repo}",
        requested_revision=revision,
        commit=commit,
        location=str(repo),
        files=tuple(files),
    )


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


def verify_excerpt(snapshot: Snapshot, excerpt: Excerpt) -> bool:
    """True only if the excerpt matches the pinned snapshot at its stated lines."""
    f = snapshot.get(excerpt.path)
    if f is None or excerpt.commit != snapshot.commit:
        return False
    lines = f.lines
    if not (1 <= excerpt.start_line <= excerpt.end_line <= len(lines)):
        return False
    return "\n".join(lines[excerpt.start_line - 1 : excerpt.end_line]) == excerpt.text
