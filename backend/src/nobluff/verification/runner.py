"""Controlled Docker runner: runs pytest inside a pinned image with hard limits.

Nothing from the repository is baked into the image; source_dir is mounted
read-only at /src.  The container has no network access, runs as a non-root
user, and is forcefully stopped on wall-clock timeout.

Public API
----------
run_verification(source_dir, test_file, *, timeout_seconds, image) -> ExecutionResult
"""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import time
import uuid
from pathlib import Path

from nobluff.schemas import ExecutionResult, ExecutionStatus

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_ENV_RUNNER_IMAGE = "NOBLUFF_RUNNER_IMAGE"

# Docker resource caps (conservative laptop-friendly values).
_CPUS = "1"
_MEMORY = "256m"
_PIDS_LIMIT = "64"

# Byte cap for captured output slices – prevents memory exhaustion.
_MAX_OUTPUT_BYTES = 65_536  # 64 KiB per stream

# Where source is mounted inside the container (read-only).
_CONTAINER_SRC = "/src"

# Revision sentinel used when no VCS revision is supplied.
_NO_REVISION = "unversioned"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sha256(path: Path) -> str:
    """Return the hex SHA-256 digest of the file at *path*."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _cap(text: str, limit: int = _MAX_OUTPUT_BYTES) -> str:
    """Truncate *text* to at most *limit* bytes, re-decoded as UTF-8."""
    encoded = text.encode("utf-8", errors="replace")
    if len(encoded) <= limit:
        return text
    return encoded[:limit].decode("utf-8", errors="replace") + "\n[truncated]"


def _docker_bin() -> str | None:
    """Return the absolute path of the docker executable, or None."""
    return shutil.which("docker")


def _build_command(
    *,
    container_name: str,
    source_dir: Path,
    test_rel: str,
    image: str,
) -> list[str]:
    """Return the docker run argument list (never a shell string).

    Parameters
    ----------
    container_name:
        Deterministic name used to stop the container on timeout.
    source_dir:
        Absolute path to the host directory mounted read-only at /src.
    test_rel:
        POSIX path of the test file relative to source_dir, executed inside
        the container as /src/<test_rel>.
    image:
        Docker image name.
    """
    container_test_path = f"{_CONTAINER_SRC}/{test_rel}"
    return [
        "docker",
        "run",
        "--rm",
        "--name",
        container_name,
        "--network",
        "none",
        "--read-only",
        "--user",
        "runner",
        "--cpus",
        _CPUS,
        "--memory",
        _MEMORY,
        "--pids-limit",
        _PIDS_LIMIT,
        "--tmpfs",
        "/tmp",
        "--mount",
        f"type=bind,source={source_dir},target={_CONTAINER_SRC},readonly",
        image,
        "python",
        "-m",
        "pytest",
        container_test_path,
        "-o",
        "cache_dir=/tmp/.pytest_cache",
        "-v",
        "--tb=short",
    ]


def _classify(
    *,
    returncode: int | None,
    timed_out: bool,
    setup_error: bool,
    blocked: bool,
) -> ExecutionStatus:
    """Map execution outcome to an ExecutionStatus literal."""
    if blocked:
        return "blocked"
    if setup_error:
        return "setup_error"
    if timed_out:
        return "timeout"
    if returncode == 0:
        return "passed"
    return "failed"


def _stop_container(docker: str, name: str) -> None:
    """Best-effort: stop and remove a named container."""
    try:
        subprocess.run(
            [docker, "stop", name],
            check=False,
            capture_output=True,
            timeout=10,
        )
    except Exception:  # noqa: BLE001, S110
        pass
    try:
        subprocess.run(
            [docker, "rm", "-f", name],
            check=False,
            capture_output=True,
            timeout=10,
        )
    except Exception:  # noqa: BLE001, S110
        pass


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def run_verification(
    source_dir: Path | str,
    test_file: Path | str,
    timeout_seconds: float = 120.0,
    image: str | None = None,
    revision: str = _NO_REVISION,
) -> ExecutionResult:
    """Run *test_file* inside a Docker container with hard resource limits.

    Parameters
    ----------
    source_dir:
        Directory that contains the test file and any source it imports.
        Mounted read-only at /src inside the container.
    test_file:
        Path to the test file on the host. Must be inside
        source_dir; otherwise the result status is ``"blocked"``.
    timeout_seconds:
        Wall-clock timeout enforced by this process (Python-side).
    image:
        Docker image to run. If not provided, reads NOBLUFF_RUNNER_IMAGE
        from environment. Must be pre-built; this function never pulls.
    revision:
        VCS revision string recorded in the result (informational only).

    Returns
    -------
    ExecutionResult
        A validated schema object. The exit_code is None for statuses that
        preclude execution (blocked, setup_error, timeout if the process did
        not terminate before cleanup).
    """
    run_id = str(uuid.uuid4())
    container_name = f"nobluff-runner-{run_id}"

    # Sentinel used for command when execution never started (schema requires min_length=1).
    _NO_CMD = ["docker", "run"]

    # ------------------------------------------------------------------
    # 1. Path-containment guard: test_file must be inside source_dir.
    # ------------------------------------------------------------------
    source_dir = Path(source_dir).resolve()
    test_file = Path(test_file).resolve()
    try:
        test_rel = str(test_file.relative_to(source_dir))
    except ValueError:
        test_hash = _sha256(test_file) if test_file.exists() else "0" * 64
        return ExecutionResult(
            id=run_id,
            revision=revision,
            test_hash=test_hash,
            command=_NO_CMD,
            environment={},
            status="blocked",
            exit_code=None,
            stdout="",
            stderr="blocked: test_file is outside source_dir",
            duration_ms=0,
        )

    # ------------------------------------------------------------------
    # 2. Hash the test file before execution.
    # ------------------------------------------------------------------
    try:
        test_hash = _sha256(test_file)
    except OSError as exc:
        return ExecutionResult(
            id=run_id,
            revision=revision,
            test_hash="0" * 64,
            command=_NO_CMD,
            environment={},
            status="setup_error",
            exit_code=None,
            stdout="",
            stderr=f"setup_error: cannot read test file: {exc}",
            duration_ms=0,
        )

    # ------------------------------------------------------------------
    # 3. Resolve runner image from argument or environment.
    # ------------------------------------------------------------------
    resolved_image = image if image is not None else os.environ.get(_ENV_RUNNER_IMAGE)
    if resolved_image is not None:
        resolved_image = resolved_image.strip() or None

    if not resolved_image:
        return ExecutionResult(
            id=run_id,
            revision=revision,
            test_hash=test_hash,
            command=_NO_CMD,
            environment={},
            status="setup_error",
            exit_code=None,
            stdout="",
            stderr="setup_error: runner image is not configured (set NOBLUFF_RUNNER_IMAGE or pass image)",
            duration_ms=0,
        )

    # ------------------------------------------------------------------
    # 4. Locate docker.
    # ------------------------------------------------------------------
    docker = _docker_bin()
    if docker is None:
        return ExecutionResult(
            id=run_id,
            revision=revision,
            test_hash=test_hash,
            command=_NO_CMD,
            environment={},
            status="setup_error",
            exit_code=None,
            stdout="",
            stderr="setup_error: docker executable not found on PATH",
            duration_ms=0,
        )

    # ------------------------------------------------------------------
    # 5. Build the command.
    # ------------------------------------------------------------------
    cmd = _build_command(
        container_name=container_name,
        source_dir=source_dir,
        test_rel=test_rel.replace(os.sep, "/"),
        image=resolved_image,
    )

    env_record = {"image": resolved_image, "timeout_seconds": str(timeout_seconds)}

    # ------------------------------------------------------------------
    # 5. Run with wall-clock enforcement.
    # ------------------------------------------------------------------
    timed_out = False
    returncode: int | None = None
    raw_stdout = ""
    raw_stderr = ""
    setup_error = False

    t0 = time.monotonic()
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        try:
            raw_bytes_out, raw_bytes_err = proc.communicate(timeout=timeout_seconds)
            returncode = proc.returncode
            raw_stdout = raw_bytes_out.decode("utf-8", errors="replace")
            raw_stderr = raw_bytes_err.decode("utf-8", errors="replace")

            # Detect docker image-not-found / daemon errors (exit 125 or 126).
            if returncode in (125, 126):
                setup_error = True

        except subprocess.TimeoutExpired:
            timed_out = True
            proc.kill()
            try:
                raw_bytes_out, raw_bytes_err = proc.communicate(timeout=5)
                raw_stdout = raw_bytes_out.decode("utf-8", errors="replace")
                raw_stderr = raw_bytes_err.decode("utf-8", errors="replace")
            except Exception:  # noqa: BLE001, S110
                pass
            _stop_container(docker, container_name)

    except FileNotFoundError:
        # docker binary disappeared between shutil.which and Popen
        setup_error = True
        raw_stderr = "setup_error: docker executable disappeared"
    except OSError as exc:
        setup_error = True
        raw_stderr = f"setup_error: {exc}"

    duration_ms = int((time.monotonic() - t0) * 1000)

    # ------------------------------------------------------------------
    # 6. Cap output, classify and return.
    # ------------------------------------------------------------------
    status = _classify(
        returncode=returncode,
        timed_out=timed_out,
        setup_error=setup_error,
        blocked=False,
    )

    # For statuses that preclude a meaningful exit code, clear it.
    final_exit_code: int | None = returncode
    if status in ("setup_error", "timeout", "blocked"):
        final_exit_code = None

    return ExecutionResult(
        id=run_id,
        revision=revision,
        test_hash=test_hash,
        command=cmd,
        environment=env_record,
        status=status,
        exit_code=final_exit_code,
        stdout=_cap(raw_stdout),
        stderr=_cap(raw_stderr),
        duration_ms=duration_ms,
    )
