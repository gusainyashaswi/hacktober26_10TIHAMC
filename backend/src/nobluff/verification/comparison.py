"""Interpret actual controlled runs without claiming general issue correctness."""

import hashlib
import re

from nobluff.schemas import ComparisonResult
from nobluff.verification.policy import observed_expected_failure


def compare_runs(before, after, plan):
    expected_hash = hashlib.sha256(plan.test_code.encode("utf-8")).hexdigest()
    if before.test_hash != expected_hash or after.test_hash != expected_hash:
        raise ValueError("Runner did not execute identical approved test bytes")
    image = before.environment.get("image", "")
    comparable = bool(
        re.fullmatch(r"sha256:[0-9a-f]{64}", image)
    ) and image == after.environment.get("image")
    status = "inconclusive"
    if comparable and before.revision != after.revision:
        if before.status == "passed":
            status = "not_reproduced_for_test"
        elif observed_expected_failure(before, plan):
            if after.status == "passed":
                status = "fix_verified_for_test"
            elif after.status == "failed":
                status = "still_failing"
    return ComparisonResult(
        claim_id=plan.claim_id,
        original_execution_id=before.id,
        comparison_execution_id=after.id,
        test_hash=expected_hash,
        status=status,
        limitations=[
            "Verdict applies only to the approved test, selected snapshots, and recorded environment.",
            "A passing test does not prove a complete fix; a failing test does not establish the root cause.",
        ],
    )
