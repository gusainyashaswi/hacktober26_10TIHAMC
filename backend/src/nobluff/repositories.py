"""Public GitHub snapshots or operator-configured local repositories."""

import hashlib
import io
import json
import os
import re
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from urllib.parse import quote

import httpx

from nobluff.github import _resolve_token
from nobluff.retrieval import (
    MAX_FILE_SIZE,
    MAX_FILES,
    MAX_TOTAL_SIZE,
    Snapshot,
    SnapshotError,
    SnapshotFile,
    load_local_snapshot,
    safe_path,
)

MAX_ARCHIVE_DOWNLOAD_SIZE = int(
    os.getenv("NOBLUFF_MAX_ARCHIVE_SIZE", str(100 * 1024 * 1024))
)


class RepositoryLoader:
    def __init__(
        self,
        local_repositories: dict[str, str] | None = None,
        client: httpx.Client | None = None,
    ):
        self.local_repositories = local_repositories or {}
        self.client = client
        self._directories = []

    @classmethod
    def from_env(cls):
        mapping = json.loads(os.getenv("NOBLUFF_LOCAL_REPOSITORIES", "{}"))
        if not isinstance(mapping, dict) or any(
            not isinstance(k, str) or not isinstance(v, str) for k, v in mapping.items()
        ):
            raise ValueError(
                "NOBLUFF_LOCAL_REPOSITORIES must map GitHub URLs to local paths"
            )
        return cls(mapping)

    def close(self):
        for directory in self._directories:
            directory.cleanup()
        self._directories.clear()

    def _get(self, client, url, limit):
        try:
            headers = {}
            if "api.github.com" in url:
                token = _resolve_token()
                if token:
                    headers["Authorization"] = f"Bearer {token}"
            with client.stream(
                "GET",
                url,
                headers=headers,
                timeout=httpx.Timeout(60, connect=10),
                follow_redirects=False,
            ) as response:
                if response.status_code in (401, 403, 429):
                    raise SnapshotError(
                        "GitHub denied access or rate-limited this request"
                    )
                if response.status_code != 200:
                    raise SnapshotError(
                        "Public repository or revision could not be downloaded"
                    )
                data = bytearray()
                for chunk in response.iter_bytes():
                    data.extend(chunk)
                    if len(data) > limit:
                        raise SnapshotError(
                            "Repository download exceeded its size limit"
                        )
                return bytes(data)
        except httpx.RequestError as exc:
            raise SnapshotError("GitHub download failed or timed out") from exc

    def load(self, repository: str, revision: str) -> Snapshot:
        match = re.fullmatch(
            r"https://github\.com/([A-Za-z0-9][A-Za-z0-9-]{0,38})/([A-Za-z0-9_.-]{1,100})",
            repository,
        )
        if not match or match[2] in (".", ".."):
            raise SnapshotError(
                "Only canonical public GitHub repository identities are accepted"
            )
        if repository in self.local_repositories:
            snapshot = load_local_snapshot(
                self.local_repositories[repository], revision
            )
            return Snapshot(
                repository, revision, snapshot.commit, snapshot.location, snapshot.files
            )
        if self.client is None:
            with httpx.Client(trust_env=False) as client:
                return self._remote(client, repository, revision, match[1], match[2])
        return self._remote(self.client, repository, revision, match[1], match[2])

    def _remote(self, client, repository, revision, owner, name):
        if re.fullmatch(r"[0-9a-f]{40}", revision):
            commit = revision
        else:
            try:
                metadata = json.loads(
                    self._get(
                        client,
                        f"https://api.github.com/repos/{owner}/{name}/commits/{quote(revision, safe='')}",
                        1024 * 1024,
                    )
                )
                commit = metadata["sha"]
                if not isinstance(commit, str) or not re.fullmatch(
                    r"[0-9a-f]{40}", commit
                ):
                    raise ValueError
            except (KeyError, TypeError, ValueError) as exc:
                raise SnapshotError("GitHub returned an invalid commit") from exc
        archive = self._get(
            client,
            f"https://codeload.github.com/{owner}/{name}/zip/{commit}",
            MAX_ARCHIVE_DOWNLOAD_SIZE,
        )
        directory = tempfile.TemporaryDirectory(prefix="nobluff-snapshot-")
        root = Path(directory.name)
        files = []
        total = 0
        try:
            with zipfile.ZipFile(io.BytesIO(archive)) as bundle:
                entries = bundle.infolist()
                if len(entries) > 10000:
                    raise SnapshotError("Archive has too many entries")
                for info in entries:
                    parts = PurePosixPath(info.filename).parts
                    if (
                        not parts
                        or info.filename.startswith("/")
                        or "//" in info.filename
                        or ".." in parts
                        or any(c in info.filename for c in "\\\x00:\r\n")
                    ):
                        raise SnapshotError("Unsafe archive path")
                    if parts[0] != f"{name}-{commit}":
                        raise SnapshotError(
                            "Archive root does not match the pinned commit"
                        )
                    path = "/".join(parts[1:])
                    mode = info.external_attr >> 16
                    if (
                        info.is_dir()
                        or mode & 0o170000 == 0o120000
                        or not safe_path(path)
                    ):
                        continue
                    if info.file_size > MAX_FILE_SIZE:
                        continue
                    if (
                        total + info.file_size > MAX_TOTAL_SIZE
                        or len(files) >= MAX_FILES
                    ):
                        raise SnapshotError(
                            "Snapshot exceeds file or total size limits"
                        )
                    with bundle.open(info) as stream:
                        raw = stream.read(MAX_FILE_SIZE + 1)
                    if len(raw) > MAX_FILE_SIZE:
                        raise SnapshotError(
                            "Archive member exceeded its declared limit"
                        )
                    try:
                        text = raw.decode("utf-8")
                    except UnicodeError:
                        continue
                    if "\0" in text:
                        continue
                    target = root / path
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(raw)
                    blob = hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest()
                    files.append(SnapshotFile(path, blob, text))
                    total += len(raw)
        except (zipfile.BadZipFile, OSError, RuntimeError, ValueError) as exc:
            directory.cleanup()
            raise SnapshotError(
                "Repository archive could not be loaded safely"
            ) from exc
        except SnapshotError:
            directory.cleanup()
            raise
        self._directories.append(directory)
        return Snapshot(
            repository,
            revision,
            commit,
            root,
            tuple(sorted(files, key=lambda f: f.path)),
        )
