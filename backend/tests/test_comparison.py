import hashlib
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from nobluff.api import create_app
from nobluff.schemas import ExecutionResult
from nobluff.verification.comparison import compare_runs
from nobluff.verification.policy import VerificationPlan, verify_snapshot
from test_verification_policy import TEST, make_service


def execution(revision, status, plan, image="sha256:" + "a" * 64, stdout=None):
    return ExecutionResult(
        id=str(uuid4()),
        revision=revision,
        test_hash=hashlib.sha256(plan.test_code.encode()).hexdigest(),
        command=["pytest"],
        environment={"image": image},
        status=status,
        exit_code=0 if status == "passed" else 1,
        stdout=stdout if stdout is not None else "E   UnicodeEncodeError: ascii\n",
        duration_ms=1,
    )


@pytest.mark.parametrize(
    ("before", "after", "expected"),
    [
        ("failed", "passed", "fix_verified_for_test"),
        ("passed", "passed", "not_reproduced_for_test"),
        ("failed", "failed", "still_failing"),
        ("setup_error", "passed", "inconclusive"),
        ("timeout", "passed", "inconclusive"),
    ],
)
def test_verdicts_are_scoped_to_comparable_runs(before, after, expected):
    plan = VerificationPlan(
        claim_id="c1",
        test_code=TEST,
        approved=True,
        expected_failure="UnicodeEncodeError",
    )
    assert (
        compare_runs(
            execution("a", before, plan), execution("b", after, plan), plan
        ).status
        == expected
    )


def test_different_test_or_image_cannot_verify_fix():
    plan = VerificationPlan(
        claim_id="c1",
        test_code=TEST,
        approved=True,
        expected_failure="UnicodeEncodeError",
    )
    before, after = (
        execution("a", "failed", plan),
        execution("b", "passed", plan, image="sha256:" + "b" * 64),
    )
    assert compare_runs(before, after, plan).status == "inconclusive"
    after.test_hash = "c" * 64
    with pytest.raises(ValueError, match="identical approved test"):
        compare_runs(before, after, plan)


def check_api_comparison(source_repo, runner):
    service, original = make_service(source_repo, runner)
    with TestClient(create_app(service)) as client:
        data = {
            "repository": "example/fixture",
            "revision": original,
            "comparison_revision": source_repo[2],
            "report_text": "unicode fails",
        }
        identifier = client.post("/api/analyses", json=data).json()["id"]
        url = f"/api/analyses/{identifier}"
        plan = {
            "claim_id": "c1",
            "test_code": TEST,
            "approved": True,
            "expected_failure": "UnicodeEncodeError",
        }
        assert client.post(url + "/comparison", json=plan).status_code == 202
        report = client.get(url).json()
        assert report["stage"] == "complete", report["errors"]
        assert report["comparison_revision"] == source_repo[2]
        assert report["approved_tests"][0]["test_code"] == TEST
        assert report["comparisons"][0]["status"] == "fix_verified_for_test"
        assert (
            report["executions"][0]["test_hash"] == report["executions"][1]["test_hash"]
        )
        assert client.post(url + "/comparison", json=plan).status_code == 422
        assert (
            "fix_verified_for_test" in client.get(url + "/export?format=markdown").text
        )
        return report


def test_api_comparison_records_original_and_fix_and_exports(source_repo):
    def runner(snapshot, plan):
        return execution(
            snapshot.commit,
            "failed" if snapshot.commit == source_repo[1] else "passed",
            plan,
        )

    check_api_comparison(source_repo, runner)


@pytest.mark.runner
def test_full_comparison_api_runs_real_docker(source_repo):
    report = check_api_comparison(source_repo, verify_snapshot)
    assert report["executions"][0]["environment"]["image"].startswith("sha256:")
