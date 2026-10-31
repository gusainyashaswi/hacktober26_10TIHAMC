"""Pinned local snapshots and shared Evidence adapter.

Adapted from Yogye Berry's provisional snapshot interface:
https://github.com/YogyeBerry/nobluff-retrieval at bf87384e2cf0afe646e0a06b7988e5fcd91dcd6f.
The integration adds bounded Git reads, timeouts, strict decoding and Claim/Evidence
compatibility. No repository module is imported or executed.
"""

import ast
import hashlib
import os
import re
import selectors
import subprocess
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from time import monotonic

from nobluff.schemas import Claim, Evidence

MAX_FILES = 2000
MAX_FILE_SIZE = 512 * 1024
MAX_TOTAL_SIZE = 16 * 1024 * 1024
SUFFIXES = {".py", ".md", ".rst", ".txt", ".toml", ".cfg", ".ini", ".json"}
EXCLUDED = {".git", "node_modules", ".venv", "venv", "__pycache__"}


class SnapshotError(RuntimeError):
    pass


@dataclass(frozen=True)
class SnapshotFile:
    path: str
    blob: str
    text: str

    @property
    def lines(self) -> tuple[str, ...]:
        return tuple(self.text.splitlines())


@dataclass(frozen=True)
class Snapshot:
    repository: str
    requested_revision: str
    commit: str
    location: Path
    files: tuple[SnapshotFile, ...]

    def get(self, path: str) -> SnapshotFile | None:
        return next((f for f in self.files if f.path == path), None)


@dataclass(frozen=True)
class Excerpt:
    path: str
    commit: str
    start_line: int
    end_line: int
    text: str


def safe_path(path: str) -> bool:
    parts = PurePosixPath(path).parts
    return bool(
        path
        and not path.startswith("/")
        and not any(c in path for c in "\\\x00:\r\n")
        and ".." not in parts
        and not any(p in EXCLUDED for p in parts)
        and PurePosixPath(path).suffix.lower() in SUFFIXES
    )


def _git(repo: Path, args: list[str], limit: int = 1024 * 1024) -> bytes:
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update(
        GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull, GIT_TERMINAL_PROMPT="0"
    )
    command = [
        "git",
        "--no-replace-objects",
        "-c",
        "core.hooksPath=/dev/null",
        "-c",
        "core.fsmonitor=false",
        "-C",
        str(repo),
        *args,
    ]
    try:
        with subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, env=env
        ) as process:
            output = bytearray()
            deadline = monotonic() + 10
            with selectors.DefaultSelector() as selector:
                selector.register(process.stdout, selectors.EVENT_READ)
                while True:
                    if monotonic() > deadline:
                        process.kill()
                        raise SnapshotError("Git operation timed out")
                    if not selector.select(0.1):
                        continue
                    chunk = os.read(process.stdout.fileno(), 65536)
                    if not chunk:
                        break
                    output.extend(chunk)
                    if len(output) > limit:
                        process.kill()
                        raise SnapshotError("Git output exceeded its size limit")
            if process.wait(timeout=1) != 0:
                raise SnapshotError("Git revision or object could not be read")
            return bytes(output)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise SnapshotError("Git repository could not be read") from exc


def load_local_snapshot(repo_path: str | Path, revision: str) -> Snapshot:
    repo = Path(repo_path).resolve()
    if not repo.is_dir():
        raise SnapshotError("Repository directory not found")
    if (
        not revision
        or revision.startswith("-")
        or len(revision) > 200
        or any(c.isspace() for c in revision)
    ):
        raise SnapshotError("Invalid revision")
    commit = (
        _git(repo, ["rev-parse", "--verify", f"{revision}^{{commit}}"], 100)
        .decode()
        .strip()
    )
    if not re.fullmatch(r"[0-9a-f]{40,64}", commit):
        raise SnapshotError("Invalid resolved commit")
    tree = _git(repo, ["ls-tree", "-rlz", "--full-tree", commit])
    files = []
    total = 0
    for entry in tree.split(b"\0"):
        if not entry:
            continue
        meta, raw_path = entry.split(b"\t", 1)
        mode, kind, blob, size = meta.split()
        try:
            path = raw_path.decode("utf-8")
        except UnicodeError:
            continue
        if mode not in (b"100644", b"100755") or kind != b"blob" or not safe_path(path):
            continue
        size = int(size)
        if size > MAX_FILE_SIZE:
            continue
        if total + size > MAX_TOTAL_SIZE or len(files) >= MAX_FILES:
            raise SnapshotError("Snapshot exceeds file or total size limits")
        raw = _git(repo, ["cat-file", "blob", blob.decode()], MAX_FILE_SIZE)
        try:
            text = raw.decode("utf-8")
        except UnicodeError:
            continue
        if "\0" in text:
            continue
        total += size
        files.append(SnapshotFile(path, blob.decode(), text))
    return Snapshot(
        f"local:{repo}",
        revision,
        commit,
        repo,
        tuple(sorted(files, key=lambda f: f.path)),
    )


def verify_excerpt(snapshot: Snapshot, excerpt: Excerpt) -> bool:
    file = snapshot.get(excerpt.path)
    return bool(
        file
        and excerpt.commit == snapshot.commit
        and type(excerpt.start_line) is int
        and type(excerpt.end_line) is int
        and 1 <= excerpt.start_line <= excerpt.end_line <= len(file.lines)
        and excerpt.text
        == "\n".join(file.lines[excerpt.start_line - 1 : excerpt.end_line])
    )


def retrieve_evidence(snapshot: Snapshot, claims: list[Claim]) -> list[Evidence]:
    """Bounded heuristic retrieval; absence of a match does not disprove a claim."""
    terms = {t.casefold() for c in claims for t in c.search_terms if len(t) > 1}
    if not terms:
        terms = {
            t.casefold()
            for c in claims
            for t in re.findall(r"[A-Za-z_][A-Za-z_0-9]{3,}", c.text)
        }
    candidates = []
    for file in snapshot.files:
        lines = file.lines
        hits = [
            i
            for i, line in enumerate(lines, 1)
            if any(t in line.casefold() for t in terms)
        ]
        if not hits:
            continue
        score = sum(file.text.casefold().count(t) for t in terms)
        if file.path.endswith(".py"):
            try:
                nodes = [
                    n
                    for n in ast.walk(ast.parse(file.text))
                    if isinstance(
                        n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
                    )
                ]
                for node in nodes:
                    if any(t in node.name.casefold() for t in terms):
                        score += 10
                        start, end = (
                            node.lineno,
                            min(node.end_lineno or node.lineno, node.lineno + 24),
                        )
                        candidates.append(
                            (
                                score,
                                Excerpt(
                                    file.path,
                                    snapshot.commit,
                                    start,
                                    end,
                                    "\n".join(lines[start - 1 : end]),
                                ),
                            )
                        )
            except (SyntaxError, RecursionError):
                pass
        for hit in hits[:3]:
            start, end = max(1, hit - 2), min(len(lines), hit + 3)
            candidates.append(
                (
                    score,
                    Excerpt(
                        file.path,
                        snapshot.commit,
                        start,
                        end,
                        "\n".join(lines[start - 1 : end]),
                    ),
                )
            )
    result = []
    seen = set()
    budget = 4000
    for _, excerpt in sorted(
        candidates, key=lambda x: (-x[0], x[1].path, x[1].start_line)
    ):
        key = (excerpt.path, excerpt.start_line, excerpt.end_line)
        if key in seen or not verify_excerpt(snapshot, excerpt):
            continue
        seen.add(key)
        if not excerpt.text.strip() or len(excerpt.text) > budget:
            continue
        digest = hashlib.sha256(
            f"{snapshot.commit}:{key}:{excerpt.text}".encode()
        ).hexdigest()[:16]
        kind = (
            "test"
            if "tests" in PurePosixPath(excerpt.path).parts
            or PurePosixPath(excerpt.path).name.startswith("test_")
            else "source"
            if excerpt.path.endswith(".py")
            else "documentation"
        )
        result.append(
            Evidence(
                id=f"e-{digest}",
                kind=kind,
                revision=snapshot.commit,
                path=excerpt.path,
                start_line=excerpt.start_line,
                end_line=excerpt.end_line,
                excerpt=excerpt.text,
            )
        )
        budget -= len(excerpt.text)
        if len(result) == 8:
            break
    return result
