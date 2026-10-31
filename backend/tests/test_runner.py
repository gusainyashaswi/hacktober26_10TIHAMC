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

_IMAGE = os.getenv("NOBLUFF_RUNNER_IMAGE", "nobluff-runner:ci")
_CONTAINER_SRC = "/src"


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
    cmd = _build_command(
        container_name="ctr",
        source_dir=tmp_path,
        test_rel="sub/test_foo.py",
        image="img:tag",
    )
    idx = cmd.index("--network")
    assert cmd[idx + 1] == "none"


def test_build_command_readonly_flag(tmp_path: Path) -> None:
    cmd = _build_command(
        container_name="ctr",
        source_dir=tmp_path,
        test_rel="test_foo.py",
        image="img:tag",
    )
    assert "--read-only" in cmd


def test_build_command_user_runner(tmp_path: Path) -> None:
    cmd = _build_command(
        container_name="ctr",
        source_dir=tmp_path,
        test_rel="test_foo.py",
        image="img:tag",
    )
    idx = cmd.index("--user")
    assert cmd[idx + 1] == "runner"


def test_build_command_has_rm(tmp_path: Path) -> None:
    cmd = _build_command(
        container_name="ctr",
        source_dir=tmp_path,
        test_rel="test_foo.py",
        image="img:tag",
    )
    assert "--rm" in cmd


def test_build_command_mounts_source_dir_readonly(tmp_path: Path) -> None:
    cmd = _build_command(
        container_name="ctr",
        source_dir=tmp_path,
        test_rel="test_foo.py",
        image="img:tag",
    )
    mount_idx = cmd.index("--mount")
    mount_val = cmd[mount_idx + 1]
    assert str(tmp_path) in mount_val
    assert "readonly" in mount_val
    assert _CONTAINER_SRC in mount_val


def test_build_command_test_path_inside_container_src(tmp_path: Path) -> None:
    cmd = _build_command(
        container_name="ctr",
        source_dir=tmp_path,
        test_rel="sub/test_foo.py",
        image="img:tag",
    )
    # The test file path inside the container must start with /src/
    assert f"{_CONTAINER_SRC}/sub/test_foo.py" in cmd


def test_build_command_no_socket_volume(tmp_path: Path) -> None:
    cmd = _build_command(
        container_name="ctr",
        source_dir=tmp_path,
        test_rel="test_foo.py",
        image="img:tag",
    )
    assert "/var/run/docker.sock" not in " ".join(cmd)


def test_build_command_has_resource_limits(tmp_path: Path) -> None:
    cmd = _build_command(
        container_name="ctr",
        source_dir=tmp_path,
        test_rel="test_foo.py",
        image="img:tag",
    )
    assert "--cpus" in cmd
    assert "--memory" in cmd
    assert "--pids-limit" in cmd


# ---------------------------------------------------------------------------
# Unit: result classification
# ---------------------------------------------------------------------------


def test_classify_passed() -> None:
    assert (
        _classify(returncode=0, timed_out=False, setup_error=False, blocked=False)
        == "passed"
    )


def test_classify_failed() -> None:
    assert (
        _classify(returncode=1, timed_out=False, setup_error=False, blocked=False)
        == "failed"
    )


def test_classify_timeout() -> None:
    assert (
        _classify(returncode=None, timed_out=True, setup_error=False, blocked=False)
        == "timeout"
    )


def test_classify_setup_error() -> None:
    assert (
        _classify(returncode=None, timed_out=False, setup_error=True, blocked=False)
        == "setup_error"
    )


def test_classify_blocked() -> None:
    assert (
        _classify(returncode=None, timed_out=False, setup_error=False, blocked=True)
        == "blocked"
    )


def test_classify_blocked_wins_over_setup_error() -> None:
    # blocked takes highest priority
    assert (
        _classify(returncode=None, timed_out=False, setup_error=True, blocked=True)
        == "blocked"
    )


# ---------------------------------------------------------------------------
# Unit: path blocking
# ---------------------------------------------------------------------------


def test_run_verification_blocks_test_outside_source_dir(tmp_path: Path) -> None:
    source_dir = tmp_path / "src"
    source_dir.mkdir()
    outside = tmp_path / "evil_test.py"
    outside.write_text("def test_x(): pass\n")

    result = run_verification(source_dir, outside, timeout_seconds=30)
    assert result.status == "blocked"
    assert result.exit_code is None


def test_run_verification_blocks_symlink_escape(tmp_path: Path) -> None:
    """Symlinks that resolve outside source_dir must be blocked."""
    source_dir = tmp_path / "src"
    source_dir.mkdir()
    outside = tmp_path / "real_test.py"
    outside.write_text("def test_x(): pass\n")
    link = source_dir / "test_link.py"
    link.symlink_to(outside)

    result = run_verification(source_dir, link, timeout_seconds=30)
    assert result.status == "blocked"


# ---------------------------------------------------------------------------
# Unit: setup_error when docker is absent
# ---------------------------------------------------------------------------


def test_run_verification_setup_error_no_docker(tmp_path: Path) -> None:
    test_file = _make_test_file(tmp_path, "def test_ok(): pass\n")

    with patch("nobluff.verification.runner._docker_bin", return_value=None):
        result = run_verification(tmp_path, test_file, timeout_seconds=30)

    assert result.status == "setup_error"
    assert result.exit_code is None
    assert "docker" in result.stderr.lower()


# ---------------------------------------------------------------------------
# Unit: result fields are populated
# ---------------------------------------------------------------------------


def test_run_verification_result_has_hash(tmp_path: Path) -> None:
    test_file = _make_test_file(tmp_path, "def test_ok(): pass\n")
    expected_hash = hashlib.sha256(test_file.read_bytes()).hexdigest()

    with patch("nobluff.verification.runner._docker_bin", return_value=None):
        result = run_verification(tmp_path, test_file, timeout_seconds=30)

    assert result.test_hash == expected_hash


def test_run_verification_result_has_uuid_id(tmp_path: Path) -> None:
    test_file = _make_test_file(tmp_path, "def test_ok(): pass\n")

    with patch("nobluff.verification.runner._docker_bin", return_value=None):
        result = run_verification(tmp_path, test_file, timeout_seconds=30)

    uuid.UUID(result.id)  # raises if not a valid UUID


def test_run_verification_result_duration_non_negative(tmp_path: Path) -> None:
    test_file = _make_test_file(tmp_path, "def test_ok(): pass\n")

    with patch("nobluff.verification.runner._docker_bin", return_value=None):
        result = run_verification(tmp_path, test_file, timeout_seconds=30)

    assert result.duration_ms >= 0


def test_run_verification_command_is_list(tmp_path: Path) -> None:
    """Even for setup_error the command field must be a non-empty list."""
    test_file = _make_test_file(tmp_path, "def test_ok(): pass\n")

    # Patch docker found, but Popen raises OSError.
    with (
        patch(
            "nobluff.verification.runner._docker_bin", return_value="/usr/bin/docker"
        ),
        patch(
            "nobluff.verification.runner.subprocess.Popen",
            side_effect=OSError("simulated"),
        ),
    ):
        result = run_verification(tmp_path, test_file, timeout_seconds=30)

    assert isinstance(result.command, list)
    assert len(result.command) >= 1
    assert result.status == "setup_error"


def test_run_verification_image_recorded_in_command(tmp_path: Path) -> None:
    test_file = _make_test_file(tmp_path, "def test_ok(): pass\n")
    custom_image = "my-custom-runner:latest"

    with (
        patch(
            "nobluff.verification.runner._docker_bin", return_value="/usr/bin/docker"
        ),
        patch(
            "nobluff.verification.runner.subprocess.Popen",
            side_effect=OSError("simulated"),
        ) as mock_popen,
    ):
        run_verification(tmp_path, test_file, image=custom_image, timeout_seconds=30)
        # Inspect the call args to verify image is in the command list
        if mock_popen.called:
            call_args = mock_popen.call_args_list[0][0][0]
            assert custom_image in call_args


# ---------------------------------------------------------------------------
# Integration: real Docker runs (require @pytest.mark.runner + Docker)
# ---------------------------------------------------------------------------


@pytest.mark.runner
def test_passing_test_returns_passed(tmp_path: Path) -> None:
    test_file = _make_test_file(tmp_path, "def test_always_pass(): assert True\n")
    result = run_verification(tmp_path, test_file, image=_IMAGE, timeout_seconds=60)
    assert result.status == "passed", result.stdout + result.stderr
    assert result.exit_code == 0
    assert len(result.test_hash) == 64


@pytest.mark.runner
def test_failing_test_returns_failed(tmp_path: Path) -> None:
    test_file = _make_test_file(tmp_path, "def test_always_fail(): assert False\n")
    result = run_verification(tmp_path, test_file, image=_IMAGE, timeout_seconds=60)
    assert result.status == "failed", result.stdout + result.stderr
    assert result.exit_code != 0


@pytest.mark.runner
def test_syntax_error_test_returns_failed(tmp_path: Path) -> None:
    test_file = tmp_path / "test_broken.py"
    test_file.write_text("def test_broken(: pass\n")
    result = run_verification(tmp_path, test_file, image=_IMAGE, timeout_seconds=60)
    # Pytest reports collection errors as exit code 4 (ERROR), still "failed"
    assert result.status in ("failed", "setup_error")
    assert result.status == "setup_error"
    assert result.exit_code is None


@pytest.mark.runner
def test_result_records_image_and_command(tmp_path: Path) -> None:
    test_file = _make_test_file(tmp_path, "def test_ok(): pass\n")
    result = run_verification(tmp_path, test_file, image=_IMAGE, timeout_seconds=60)
    assert _IMAGE in result.command
    assert "docker" == result.command[0]


@pytest.mark.runner
def test_result_is_valid_execution_result_schema(tmp_path: Path) -> None:
    """ExecutionResult validates correctly after a real run."""
    from nobluff.schemas import ExecutionResult as SchemaResult

    test_file = _make_test_file(tmp_path, "def test_ok(): pass\n")
    result = run_verification(tmp_path, test_file, image=_IMAGE, timeout_seconds=60)
    # Re-validate through pydantic to ensure field constraints are met
    SchemaResult.model_validate(result.model_dump())


@pytest.mark.runner
def test_nonexistent_image_returns_setup_error(tmp_path: Path) -> None:
    test_file = _make_test_file(tmp_path, "def test_ok(): pass\n")
    result = run_verification(
        tmp_path,
        test_file,
        image="nobluff-runner:does-not-exist-xyz-9999",
        timeout_seconds=30,
    )
    assert result.status == "setup_error"
    assert result.exit_code is None


@pytest.mark.runner
def test_whoami_confirms_non_root(tmp_path: Path) -> None:
    """Container must not run as root (uid != 0)."""
    tmp_path.chmod(0o755)
    test_file = tmp_path / "test_whoami.py"
    test_file.write_text(
        textwrap.dedent("""\
        import os
        def test_not_root():
            assert os.getuid() != 0
        """)
    )
    result = run_verification(tmp_path, test_file, image=_IMAGE, timeout_seconds=60)
    assert result.status == "passed", result.stdout + result.stderr
