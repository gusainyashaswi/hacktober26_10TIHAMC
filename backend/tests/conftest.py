"""Independent controlled Git fixture; no model receives expected answers."""

import os
import subprocess

import pytest


@pytest.fixture
def source_repo(tmp_path):
    repo = tmp_path / "repository"
    repo.mkdir()
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "NoBluff Fixture",
        "GIT_AUTHOR_EMAIL": "fixture@example.invalid",
        "GIT_COMMITTER_NAME": "NoBluff Fixture",
        "GIT_COMMITTER_EMAIL": "fixture@example.invalid",
    }

    def git(*args):
        return subprocess.run(
            [
                "git",
                "-c",
                "commit.gpgsign=false",
                "-c",
                "core.hooksPath=/dev/null",
                *args,
            ],
            cwd=repo,
            env=env,
            text=True,
            capture_output=True,
            check=True,
        ).stdout.strip()

    git("init", "-b", "main")
    original_source = "def export_csv(path, rows):\n    with open(path, 'w', encoding='ascii') as stream:\n        stream.write(','.join(rows))\n"
    (repo / "exporter.py").write_text(original_source)
    (repo / "README.md").write_text(
        "export_csv writes rows to a file. Unicode customer names should be supported.\n"
    )
    git("add", ".")
    git("commit", "-m", "Controlled original fixture")
    original = git("rev-parse", "HEAD")
    (repo / "exporter.py").write_text(original_source.replace("'ascii'", "'utf-8'"))
    git("add", ".")
    git("commit", "-m", "Controlled fix fixture")
    fix = git("rev-parse", "HEAD")
    return repo, original, fix, git
