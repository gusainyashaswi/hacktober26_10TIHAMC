"""Tests for the controlled Docker runner.

Unit tests (no @pytest.mark.runner) exercise argument building, hashing,
path blocking and result classification without requiring Docker.

Integration tests (@pytest.mark.runner) launch a real container and require:
- Docker to be running.
- The image named by NOBLUFF_RUNNER_IMAGE (default: nobluff-runner:ci) to be
  present locally.
"""

from __future__ import annotations

import hashlib
import os
import textwrap
import uuid
from pathlib import Path
from unittest.mock import patch

import pytest
from nobluff.verification.runner import (
    _MAX_OUTPUT_BYTES,
    _build_command,
    _cap,
    _classify,
    _sha256,
    run_verification,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_CONTAINER_SRC = "/src"


def _require_runner_image() -> str:
    image = os.getenv("NOBLUFF_RUNNER_IMAGE")
    if not image:
        pytest.skip("NOBLUFF_RUNNER_IMAGE environment variable is required for runner tests")
    return image


def _make_test_file(tmp_path: Path, content: str) -> Path:
    tmp_path.chmod(0o755)  # Linux bind mounts preserve pytest owner-only directory permissions.
    f = tmp_path / "test_sample.py"
    f.write_text(textwrap.dedent(content))
    return f


# ---------------------------------------------------------------------------
# Unit: SHA-256 hashing
# ---------------------------------------------------------------------------


def test_sha256_matches_hashlib(tmp_path: Path) -> None:
    f = tmp_path / "f.txt"
    f.write_bytes(b"hello nobluff")
    expected = hashlib.sha256(b"hello nobluff").hexdigest()
    assert _sha256(f) == expected


def test_sha256_is_64_hex_chars(tmp_path: Path) -> None:
    f = tmp_path / "f.txt"
    f.write_bytes(b"")
    result = _sha256(f)
    assert len(result) == 64
    assert all(c in "0123456789abcdef" for c in result)


# ---------------------------------------------------------------------------
# Unit: output capping
# ---------------------------------------------------------------------------


def test_cap_short_string_unchanged() -> None:
    s = "hello"
    assert _cap(s, limit=100) == s


def test_cap_truncates_long_string() -> None:
    s = "x" * 200
    result = _cap(s, limit=100)
    assert len(result.encode()) > 0
    assert "[truncated]" in result


def test_cap_exact_limit_unchanged() -> None:
    s = "a" * _MAX_OUTPUT_BYTES
    result = _cap(s)
    assert "[truncated]" not in result


def test_cap_one_over_limit_truncated() -> None:
    s = "a" * (_MAX_OUTPUT_BYTES + 1)
    result = _cap(s)
    assert "[truncated]" in result


# ---------------------------------------------------------------------------
# Unit: docker command construction
# ---------------------------------------------------------------------------


def test_build_command_is_list_of_strings(tmp_path: Path) -> None:
    cmd = _build_command(
        container_name="test-ctr",
        source_dir=tmp_path,
        test_rel="test_foo.py",
        image="nobluff-runner:ci",
    )
    assert isinstance(cmd, list)
    assert all(isinstance(t, str) for t in cmd)


def test_build_command_starts_with_docker_run(tmp_path: Path) -> None:
    cmd = _build_command(
        container_name="ctr",
        source_dir=tmp_path,
        test_rel="test_foo.py",
        image="img:tag",
    )
    assert cmd[0] == "docker"
    assert "run" in cmd


def test_build_command_network_none(tmp_path: Path) -> None: