"""User approval and snapshot materialization around Yashaswi's Docker runner."""

import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator

from nobluff.retrieval import Snapshot, safe_path
from nobluff.schemas import Contract, Text
from nobluff.verification.runner import run_verification


class VerificationPlan(Contract):
    claim_id: Text
    test_code: str = Field(min_length=1, max_length=8000)
    approved: Literal[True]
    expected_failure: Text | None = Field(
        default=None, max_length=100, pattern=r"^[A-Za-z_][A-Za-z0-9_]*$"
    )

    @field_validator("approved", mode="before")
    @classmethod
    def explicit_boolean(cls, value):
        if value is not True:
            raise ValueError("Execution requires explicit boolean approval")
        return value

    @field_validator("test_code")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("Test code must not be blank")
        return value


def verify_snapshot(snapshot: Snapshot, plan: VerificationPlan):
    """Mount only copied snapshot files, never the operator's live working tree."""
    with tempfile.TemporaryDirectory(prefix="nobluff-approved-") as directory:
        root = Path(directory)
        root.chmod(0o755)
        for file in snapshot.files:
            if not safe_path(file.path):
                raise ValueError("Unsafe snapshot path")
            path = root / file.path
            path.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
            path.write_text(file.text, encoding="utf-8")
            path.chmod(0o644)
        test = root / "_nobluff_reproduction" / "test_approved.py"
        test.parent.mkdir(mode=0o755)
        test.write_bytes(plan.test_code.encode("utf-8"))
        test.chmod(0o644)
        image = os.getenv("NOBLUFF_RUNNER_IMAGE", "nobluff-runner:ci")
        docker = shutil.which("docker")
        if docker:
            try:
                result = subprocess.run(
                    [docker, "image", "inspect", "--format", "{{.Id}}", image],
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode == 0 and re.fullmatch(
                    r"sha256:[0-9a-f]{64}", result.stdout.strip()
                ):
                    image = result.stdout.strip()
            except (OSError, subprocess.TimeoutExpired):
                pass  # The runner records the setup failure; never fall back to host execution.
        return run_verification(
            root,
            test,
            timeout_seconds=15,
            image=image,
            revision=snapshot.commit,
        )


def observed_expected_failure(run, plan):
    # Do not match the exception name merely printed in a test's source or heading.
    return bool(
        run.status == "failed"
        and plan.expected_failure
        and re.search(
            r"(?m)^E\s+" + re.escape(plan.expected_failure) + r"(?::|\s|$)",
            run.stdout + "\n" + run.stderr,
        )
    )
