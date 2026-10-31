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
import selectors
import shutil
import subprocess
import time
import uuid
from pathlib import Path

from nobluff.schemas import ExecutionResult, ExecutionStatus

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_IMAGE = "nobluff-runner:ci"

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
        "--pull=never",
        "--rm",
        "--name",
        container_name,
        "--network",
        "none",
        "--read-only",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges",
        "--memory-swap",
        _MEMORY,
        "--env",
        "PYTHONPATH=/src:/src/src",
        "--env",
        "PYTHONDONTWRITEBYTECODE=1",
        "--env",
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD=1",
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
    return "failed" if returncode == 1 else "setup_error"


def _read_bounded(proc, timeout):
    """Drain both pipes with bounded retained memory, not communicate-then-cap."""
    buffers = {"stdout": bytearray(), "stderr": bytearray()}
    truncated = set()
    deadline = time.monotonic() + timeout
    with selectors.DefaultSelector() as selector:
        selector.register(proc.stdout, selectors.EVENT_READ, "stdout")
        selector.register(proc.stderr, selectors.EVENT_READ, "stderr")
        while selector.get_map():
            if time.monotonic() > deadline:
                raise subprocess.TimeoutExpired(
                    proc.args,
                    timeout,
                    output=bytes(buffers["stdout"]),
                    stderr=bytes(buffers["stderr"]),
                )
            for key, _ in selector.select(0.1):
                chunk = os.read(key.fileobj.fileno(), 65536)
                if not chunk:
                    selector.unregister(key.fileobj)
                    continue
                remaining = _MAX_OUTPUT_BYTES - len(buffers[key.data])
                buffers[key.data].extend(chunk[: max(0, remaining)])
                if len(chunk) > remaining:
                    truncated.add(key.data)
    proc.wait(timeout=2)
    return tuple(
        bytes(buffers[name]) + (b"\n[truncated]" if name in truncated else b"")
        for name in ("stdout", "stderr")
    )


def _stop_container(docker: str, name: str) -> None:
    """Best-effort: stop and remove a named container."""
    try:
        subprocess.run(
            [docker, "stop", "-t", "0", name],
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
    image: str = _DEFAULT_IMAGE,
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
        Docker image to run. Must be pre-built; this function never pulls.
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
    # 3. Locate docker.
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
    # 4. Build the command.
    # ------------------------------------------------------------------
    cmd = _build_command(
        container_name=container_name,
        source_dir=source_dir,
        test_rel=test_rel.replace(os.sep, "/"),
        image=image,
    )

    env_record = {"image": image, "timeout_seconds": str(timeout_seconds)}

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
            raw_bytes_out, raw_bytes_err = _read_bounded(proc, timeout_seconds)
            returncode = proc.returncode
            raw_stdout = raw_bytes_out.decode("utf-8", errors="replace")
            raw_stderr = raw_bytes_err.decode("utf-8", errors="replace")

            # Detect docker image-not-found / daemon errors (exit 125 or 126).
            if returncode in (125, 126):
                setup_error = True

        except subprocess.TimeoutExpired as exc:
            timed_out = True
            proc.kill()
            raw_stdout = (exc.output or b"").decode("utf-8", errors="replace")
            raw_stderr = (exc.stderr or b"").decode("utf-8", errors="replace")
            try:
                proc.communicate(timeout=5)
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
    _stop_container(docker, container_name)

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
