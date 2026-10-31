#!/usr/bin/env python3
"""Build a controlled tiny git repository fixture with original and fix revisions."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


def build(dest_dir: str | Path) -> dict[str, str]:
    dest = Path(dest_dir).resolve()
    dest.mkdir(parents=True, exist_ok=True)

    fixtures_dir = Path(__file__).parent / "tiny_repo"
    v1_dir = fixtures_dir / "v1"
    v2_dir = fixtures_dir / "v2"

    env = os.environ.copy()
    env["GIT_AUTHOR_NAME"] = "NoBluff Fixture"
    env["GIT_AUTHOR_EMAIL"] = "fixture@example.invalid"
    env["GIT_COMMITTER_NAME"] = "NoBluff Fixture"
    env["GIT_COMMITTER_EMAIL"] = "fixture@example.invalid"

    # Step 1: Copy v1 into destination directory
    shutil.copytree(v1_dir, dest, dirs_exist_ok=True)

    # Step 2: Initialize git repository with main branch
    subprocess.run(
        ["git", "init", "-b", "main"],
        cwd=dest,
        env=env,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "commit.gpgsign", "false"],
        cwd=dest,
        env=env,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "NoBluff Fixture"],
        cwd=dest,
        env=env,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "fixture@example.invalid"],
        cwd=dest,
        env=env,
        check=True,
        capture_output=True,
    )

    # Step 3: Commit original revision
    subprocess.run(["git", "add", "-A"], cwd=dest, env=env, check=True, capture_output=True)
    subprocess.run(
        [
            "git",
            "commit",
            "--no-gpg-sign",
            "-m",
            "Original revision: average() fails on empty input",
        ],
        cwd=dest,
        env=env,
        check=True,
        capture_output=True,
    )

    orig_sha = subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=dest,
        env=env,
        text=True,
    ).strip()

    # Step 4: Overlay v2 and commit fix
    shutil.copytree(v2_dir, dest, dirs_exist_ok=True)
    subprocess.run(["git", "add", "-A"], cwd=dest, env=env, check=True, capture_output=True)
    subprocess.run(
        [
            "git",
            "commit",
            "--no-gpg-sign",
            "-m",
            "Fix: return 0 for empty input; test unchanged",
        ],
        cwd=dest,
        env=env,
        check=True,
        capture_output=True,
    )

    fix_sha = subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=dest,
        env=env,
        text=True,
    ).strip()

    return {"original": orig_sha, "fix": fix_sha}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python fixtures/build_tiny_repo.py <dest_dir>", file=sys.stderr)
        sys.exit(1)

    out_dir = Path(sys.argv[1]).resolve()
    if out_dir.exists() and any(out_dir.iterdir()):
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    result = build(out_dir)
    print(json.dumps(result, indent=2))

