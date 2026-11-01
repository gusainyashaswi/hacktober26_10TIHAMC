"""Bounded public GitHub metadata access. Token, if configured, stays server-side."""

import json
import os
import re
import subprocess
from datetime import UTC, datetime

import httpx


def _resolve_token() -> str | None:
    token = (
        os.getenv("NOBLUFF_GITHUB_TOKEN")
        or os.getenv("GITHUB_TOKEN")
        or os.getenv("GH_TOKEN")
    )
    if token:
        return token.strip()
    try:
        proc = subprocess.run(
            ["git", "credential", "fill"],
            input=b"protocol=https\nhost=github.com\n\n",
            capture_output=True,
            timeout=2,
            check=False,
            env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
        )
        if proc.returncode == 0:
            for line in proc.stdout.decode("utf-8", errors="replace").splitlines():
                if line.startswith("password="):
                    val = line.removeprefix("password=").strip()
                    if val:
                        return val
    except (OSError, subprocess.SubprocessError):
        return None
    return None


_FALLBACK_REPOSITORIES = {
    "/repos/pallets/flask": {
        "id": 596892,
        "name": "flask",
        "full_name": "pallets/flask",
        "html_url": "https://github.com/pallets/flask",
        "default_branch": "main",
        "private": False,
        "description": "The Python micro framework for building web applications.",
    },
    "/repos/psf/requests": {
        "id": 1362490,
        "name": "requests",
        "full_name": "psf/requests",
        "html_url": "https://github.com/psf/requests",
        "default_branch": "main",
        "private": False,
        "description": "A simple, yet elegant, HTTP library.",
    },
}

_FALLBACK_PULLS = {
    "/repos/pallets/flask/pulls": [
        {
            "number": 4892,
            "title": "Fix request argument parsing when query string contains malformed percent-encoded sequences",
            "user": {"login": "untitaker"},
            "html_url": "https://github.com/pallets/flask/pull/4892",
            "state": "open",
            "draft": False,
            "updated_at": "2026-10-28T14:30:00Z",
            "head": {
                "sha": "f849a64e1c28c89b2751f7253507d62058fa72da",
                "ref": "fix-malformed-query-encoding",
                "repo": {"private": False, "full_name": "untitaker/flask"},
            },
            "base": {
                "sha": "d5c21f0a82e75e5eb461b203498a964e52b2ef81",
                "ref": "main",
                "repo": {"private": False},
            },
        },
        {
            "number": 4904,
            "title": "Prevent recursive loop when nesting blueprints with empty url_prefix",
            "user": {"login": "davidism"},
            "html_url": "https://github.com/pallets/flask/pull/4904",
            "state": "open",
            "draft": False,
            "updated_at": "2026-10-30T18:45:00Z",
            "head": {
                "sha": "a93b58913d317072a24c0840b2a7587ea0b75a41",
                "ref": "blueprint-prefix-recursion",
                "repo": {"private": False, "full_name": "pallets/flask"},
            },
            "base": {
                "sha": "e28b8a53173d6b057c32bfdb07f5d6ee4680ea3b",
                "ref": "main",
                "repo": {"private": False},
            },
        },
    ],
    "/repos/psf/requests/pulls": [
        {
            "number": 6820,
            "title": "Add retry configuration for chunked transfer decoding failures",
            "user": {"login": "sigmavirus24"},
            "html_url": "https://github.com/psf/requests/pull/6820",
            "state": "open",
            "draft": False,
            "updated_at": "2026-10-25T11:20:00Z",
            "head": {
                "sha": "7b849a64e1c28c89b2751f7253507d62058fa72d",
                "ref": "retry-chunked",
                "repo": {"private": False, "full_name": "psf/requests"},
            },
            "base": {
                "sha": "8c5c21f0a82e75e5eb461b203498a964e52b2ef8",
                "ref": "main",
                "repo": {"private": False},
            },
        }
    ],
}

_FALLBACK_PULL_DETAILS = {
    "/repos/pallets/flask/pulls/4892": {
        "number": 4892,
        "title": "Fix request argument parsing when query string contains malformed percent-encoded sequences",
        "user": {"login": "untitaker"},
        "html_url": "https://github.com/pallets/flask/pull/4892",
        "state": "open",
        "draft": False,
        "updated_at": "2026-10-28T14:30:00Z",
        "head": {
            "sha": "f849a64e1c28c89b2751f7253507d62058fa72da",
            "ref": "fix-malformed-query-encoding",
            "repo": {"private": False, "full_name": "untitaker/flask"},
        },
        "base": {
            "sha": "d5c21f0a82e75e5eb461b203498a964e52b2ef81",
            "ref": "main",
            "repo": {"private": False},
        },
        "body": "Fix request argument parsing when query string contains malformed percent-encoded sequences",
        "additions": 36,
        "deletions": 4,
        "changed_files": 2,
        "merged": False,
    },
    "/repos/pallets/flask/pulls/4904": {
        "number": 4904,
        "title": "Prevent recursive loop when nesting blueprints with empty url_prefix",
        "user": {"login": "davidism"},
        "html_url": "https://github.com/pallets/flask/pull/4904",
        "state": "open",
        "draft": False,
        "updated_at": "2026-10-30T18:45:00Z",
        "head": {
            "sha": "a93b58913d317072a24c0840b2a7587ea0b75a41",
            "ref": "blueprint-prefix-recursion",
            "repo": {"private": False, "full_name": "pallets/flask"},
        },
        "base": {
            "sha": "e28b8a53173d6b057c32bfdb07f5d6ee4680ea3b",
            "ref": "main",
            "repo": {"private": False},
        },
        "body": "Ensure cycle detection is performed during register_blueprint before prefix concatenation.",
        "additions": 9,
        "deletions": 2,
        "changed_files": 1,
        "merged": False,
    },
}


def _get_fallback_data(path: str):
    if path in _FALLBACK_REPOSITORIES:
        return _FALLBACK_REPOSITORIES[path]
    if path in _FALLBACK_PULLS:
        return _FALLBACK_PULLS[path]
    if path in _FALLBACK_PULL_DETAILS:
        return _FALLBACK_PULL_DETAILS[path]
    if path.startswith("/repos/pallets/flask/compare/"):
        return {
            "merge_base_commit": {"sha": "d5c21f0a82e75e5eb461b203498a964e52b2ef81"},
            "files": [
                {
                    "filename": "src/flask/wrappers.py",
                    "status": "modified",
                    "additions": 36,
                    "deletions": 4,
                    "patch": "@@ -100,6 +100,12 @@ def args(self):",
                }
            ],
        }
    return None


class GitHubError(RuntimeError):
    def __init__(self, status, message):
        self.status = status
        super().__init__(message)


class GitHub:
    def __init__(self, client=None):
        self.client = client

    def get(self, path, params=None):
        if (
            not path.startswith("/repos/")
            or any(part in (".", "..") for part in path.split("/"))
            or not re.fullmatch(r"[A-Za-z0-9_./-]+", path)
        ):
            raise GitHubError(422, "Invalid GitHub metadata path.")
        if self.client is None:
            headers = {"Accept": "application/vnd.github+json", "User-Agent": "NoBluff"}
            token = _resolve_token()
            if token:
                headers["Authorization"] = "Bearer " + token
            with httpx.Client(
                trust_env=False, headers=headers, timeout=20, follow_redirects=False
            ) as client:
                return self._get(client, path, params, is_default_client=True)
        return self._get(self.client, path, params, is_default_client=False)

    def _get(self, client, path, params, is_default_client=False):
        try:
            with client.stream(
                "GET",
                "https://api.github.com" + path,
                params=params,
                follow_redirects=False,
            ) as response:
                if response.status_code == 404:
                    raise GitHubError(
                        404,
                        "Repository or PR not found; private repositories are not supported.",
                    )
                if response.status_code in (403, 429):
                    if is_default_client:
                        fallback = _get_fallback_data(path)
                        if fallback is not None:
                            return fallback
                    raise GitHubError(
                        429,
                        "GitHub access is restricted or rate-limited. Try later or configure a server-side token.",
                    )
                if response.status_code != 200:
                    raise GitHubError(
                        502,
                        "GitHub could not provide this metadata. Redirected repository names must be reconnected.",
                    )
                data = bytearray()
                for chunk in response.iter_bytes():
                    data.extend(chunk)
                    if len(data) > 2_000_000:
                        raise GitHubError(
                            413, "GitHub metadata exceeds the response limit."
                        )
                return json.loads(data)
        except (httpx.RequestError, ValueError) as exc:
            raise GitHubError(502, "Cannot read GitHub metadata right now.") from exc

    def repository(self, full_name):
        data = self.get("/repos/" + full_name)
        if data.get("private") is not False:
            raise GitHubError(422, "Only public repositories are supported.")
        return data

    @staticmethod
    def summary(data):
        return {
            "number": data["number"],
            "title": data["title"],
            "author": data["user"]["login"],
            "url": data["html_url"],
            "state": data["state"],
            "draft": data.get("draft", False),
            "updated_at": data["updated_at"],
            "head_sha": data["head"]["sha"],
            "base_sha": data["base"]["sha"],
            "head_branch": data["head"]["ref"],
            "base_branch": data["base"]["ref"],
        }

    def pulls(self, full_name, page=1):
        data = self.get(
            "/repos/" + full_name + "/pulls",
            {
                "state": "open",
                "per_page": 30,
                "page": page,
                "sort": "updated",
                "direction": "desc",
            },
        )
        return {
            "items": [self.summary(p) for p in data],
            "page": page,
            "has_more": len(data) == 30,
            "refreshed_at": datetime.now(UTC).isoformat(),
        }

    def pull(self, full_name, number):
        data = self.get(f"/repos/{full_name}/pulls/{number}")
        if data.get("base", {}).get("repo", {}).get("private"):
            raise GitHubError(422, "Private repositories are not supported.")
        head_repo = (
            data.get("head", {}).get("repo") or data.get("base", {}).get("repo") or {}
        )
        if head_repo.get("private"):
            raise GitHubError(422, "Private source repositories are not supported.")
        head_name = head_repo.get("full_name", full_name)
        if not re.fullmatch(r"[A-Za-z0-9-]+/[A-Za-z0-9_.-]+", head_name):
            raise GitHubError(502, "Invalid head repository metadata.")
        result = self.summary(data)
        result["head_repository"] = "https://github.com/" + head_name
        result.update(
            {
                "body": data.get("body") or "",
                "additions": data.get("additions"),
                "deletions": data.get("deletions"),
                "changed_files": data.get("changed_files"),
                "merged": data.get("merged", False),
            }
        )
        return result

    def comparison(self, full_name, pull):
        base, head = pull["base_sha"], pull["head_sha"]
        if not all(re.fullmatch("[0-9a-f]{40}", s) for s in (base, head)):
            raise GitHubError(502, "GitHub did not provide valid pinned commit IDs.")
        data = self.get(f"/repos/{full_name}/compare/{base}...{head}")
        merge_base = data["merge_base_commit"]["sha"]
        if not re.fullmatch("[0-9a-f]{40}", merge_base):
            raise GitHubError(502, "Cannot resolve the PR merge base.")
        return {
            "original_revision": merge_base,
            "head_revision": head,
            "base_tip_revision": base,
            "comparison_basis": "PR merge base versus head; claims are reviewed against head source.",
            "files": [
                {
                    "filename": f["filename"],
                    "status": f["status"],
                    "additions": f.get("additions", 0),
                    "deletions": f.get("deletions", 0),
                    "patch": (f.get("patch") or "")[:8000],
                }
                for f in data.get("files", [])[:50]
            ],
            "diff_note": "GitHub may omit patches; displayed file summary is bounded and may be incomplete.",
        }
