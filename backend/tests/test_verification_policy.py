import hashlib

import pytest
from fastapi.testclient import TestClient
from nobluff.api import create_app
from nobluff.model import AssessmentResult, ClaimExtractionResult, OllamaSettings
from nobluff.pipeline import AnalysisService
from nobluff.repositories import RepositoryLoader
from nobluff.retrieval import load_local_snapshot
from nobluff.schemas import Claim, ExecutionResult, Finding
from nobluff.verification.policy import (
    VerificationPlan,
    observed_expected_failure,
    verify_snapshot,
)
from pydantic import ValidationError

TEST = "from exporter import export_csv\ndef test_unicode(tmp_path):\n    export_csv(tmp_path / 'out.csv', ['José'])\n"


def make_service(source_repo, runner):
    repo, original, _, _ = source_repo
    loader = RepositoryLoader({"https://github.com/example/fixture": str(repo)})

    def extract(text, settings):
        return ClaimExtractionResult(
            model=settings.model,
            created_at="fixture",
            attempts=1,
            elapsed_ms=1,
            claims=[
                Claim(
                    id="c1",
                    text="Unicode export raises UnicodeEncodeError.",
                    kind="behavior",
                    search_terms=["export_csv"],
                )
            ],
        )

    def assess(claims, evidence, settings):
        return AssessmentResult(
            model=settings.model,
            basis="qwen",
            created_at="fixture",
            attempts=1,
            elapsed_ms=1,
            findings=[
                Finding(
                    claim_id="c1",
                    assessment="inconclusive",
                    evidence_ids=[evidence[0].id],
                    explanation="Runtime test is required.",
                    limitations=["Source review only."],
                )
            ],
        )

    return AnalysisService(
        OllamaSettings(),
        extractor=extract,
        assessor=assess,
        snapshot_loader=loader.load,
        runner=runner,
    ), original


@pytest.mark.parametrize("approved", [False, "true", 1, None])
def test_requires_explicit_approval(approved):
    with pytest.raises(ValidationError):
        VerificationPlan(claim_id="c1", test_code=TEST, approved=approved)


def test_api_approval_claim_mapping_and_real_evidence_records(source_repo):
    def runner(snapshot, plan):
        return ExecutionResult(
            id="run1",
            revision=snapshot.commit,
            test_hash=hashlib.sha256(plan.test_code.encode()).hexdigest(),
            command=["fixture"],
            environment={"test_double": "true"},
            status="failed",
            exit_code=1,
            stdout="E   UnicodeEncodeError: ascii cannot encode\n",
            duration_ms=1,
        )

    service, original = make_service(source_repo, runner)
    with TestClient(create_app(service)) as client:
        start = client.post(
            "/api/analyses",
            json={
                "repository": "example/fixture",
                "revision": original,
                "report_text": "unicode fails",
            },
        ).json()
        url = f"/api/analyses/{start['id']}"
        plan = {
            "claim_id": "c1",
            "test_code": TEST,
            "approved": True,
            "expected_failure": "UnicodeEncodeError",
        }
        assert (
            client.post(
                url + "/verification", json=plan | {"approved": False}
            ).status_code
            == 422
        )
        assert (
            client.post(
                url + "/verification", json=plan | {"claim_id": "fabricated"}
            ).status_code
            == 422
        )
        assert client.post(url + "/verification", json=plan).status_code == 202
        report = client.get(url).json()
        assert report["stage"] == "complete"
        assert (
            report["executions"][0]["test_hash"]
            == hashlib.sha256(TEST.encode()).hexdigest()
        )
        assert report["findings"][0]["assessment"] == "supported"
        assert report["evidence"][-1]["execution_id"] == "run1"


def test_expected_error_in_test_source_is_not_proof():
    plan = VerificationPlan(
        claim_id="c1",
        test_code=TEST,
        approved=True,
        expected_failure="UnicodeEncodeError",
    )
    run = ExecutionResult(
        id="r",
        revision="r",
        test_hash="a" * 64,
        command=["pytest"],
        environment={},
        status="failed",
        exit_code=1,
        stdout="    raise UnicodeEncodeError\nE   AssertionError: wrong failure\n",
        duration_ms=1,
    )
    assert not observed_expected_failure(run, plan)


@pytest.mark.runner
def test_approved_snapshot_failure_and_fix_use_identical_test(source_repo):
    repo, original, fix, _ = source_repo
    plan = VerificationPlan(
        claim_id="c1",
        test_code=TEST,
        approved=True,
        expected_failure="UnicodeEncodeError",
    )
    before = verify_snapshot(load_local_snapshot(repo, original), plan)
    after = verify_snapshot(load_local_snapshot(repo, fix), plan)
    assert before.status == "failed", before.stderr + before.stdout
    assert observed_expected_failure(before, plan)
    assert after.status == "passed", after.stderr + after.stdout
    assert before.test_hash == after.test_hash
    assert before.environment["image"] == after.environment["image"]
    assert before.environment["image"].startswith("sha256:")


@pytest.mark.runner
@pytest.mark.parametrize(
    ("test_code", "status"),
    [
        ("import missing_nobluff_dependency\ndef test_x(): pass\n", "setup_error"),
        (
            'def test_big_output():\n    print("x" * 5000000)\n    assert False\n',
            "failed",
        ),
        (
            'import os\nfrom pathlib import Path\nimport pytest\ndef test_controls():\n    assert os.getuid() != 0\n    with pytest.raises(OSError): Path("/src/no-write").write_text("no")\n    with pytest.raises(OSError): Path("/root/no-write").write_text("no")\n',
            "passed",
        ),
    ],
)
def test_real_runner_controls_and_failure_categories(source_repo, test_code, status):
    repo, original, _, _ = source_repo
    run = verify_snapshot(
        load_local_snapshot(repo, original),
        VerificationPlan(claim_id="c1", test_code=test_code, approved=True),
    )
    assert run.status == status, run.stderr + run.stdout
    assert len(run.stdout.encode()) <= 65600


@pytest.mark.runner
def test_timeout_is_not_a_reproduced_bug(tmp_path):
    from nobluff.verification import run_verification
    test = tmp_path / 'test_timeout.py'
    test.write_text('import time\ndef test_wait(): time.sleep(10)\n')
    run = run_verification(tmp_path, test, timeout_seconds=1, revision='fixture')
    assert run.status == 'timeout'
    assert run.exit_code is None
    assert run.duration_ms < 15000
