"""Bounded public GitHub metadata access. Token, if configured, stays server-side."""

import json
import os
import re
from datetime import UTC, datetime

import httpx


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
            token = os.getenv("NOBLUFF_GITHUB_TOKEN")
            if token:
                headers["Authorization"] = "Bearer " + token
            with httpx.Client(
                trust_env=False, headers=headers, timeout=20, follow_redirects=False
            ) as client:
                return self._get(client, path, params)
        return self._get(self.client, path, params)

    def _get(self, client, path, params):
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
