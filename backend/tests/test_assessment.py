"""Structural/failure tests use fake HTTP; live semantic test is opt-in."""

import json
import os

import httpx
import pytest
from nobluff.model import AssessmentError, OllamaSettings, assess_claims
from nobluff.model.assessment import SOURCE_LIMIT
from nobluff.schemas import Claim, Evidence


@pytest.fixture
def claims():
    return [
        Claim(id="c1", text="The exporter selects ASCII encoding.", kind="behavior")
    ]


@pytest.fixture
def evidence():
    return [
        Evidence(
            id="e1",
            kind="source",
            revision="fixture-v1",
            path="exporter.py",
            start_line=1,
            end_line=1,
            excerpt="open(path, encoding='utf-8')",
        )
    ]


def finding(**changes):
    return {
        "claim_id": "c1",
        "assessment": "contradicted",
        "evidence_ids": ["e1"],
        "explanation": "The source selects UTF-8.",
        "limitations": [],
        "suggested_next_step": None,
    } | changes


def envelope(findings, **changes):
    return {
        "model": "qwen3:8b",
        "done": True,
        "done_reason": "stop",
        "message": {"content": json.dumps({"findings": findings})},
    } | changes


def run(claims, evidence, handler):
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        return assess_claims(claims, evidence, OllamaSettings(), client=client)


def test_supplied_evidence_and_schema_are_sent(claims, evidence):
    def handler(request):
        payload = json.loads(request.content)
        assert payload["stream"] is False
        assert payload["format"]["additionalProperties"] is False
        data = json.loads(payload["messages"][1]["content"])
        assert data["evidence"][0]["excerpt"] == evidence[0].excerpt
        assert data["claims"][0]["id"] == "c1"
        return httpx.Response(200, json=envelope([finding()]))

    result = run(claims, evidence, handler)
    assert result.basis == "qwen"
    assert result.attempts == 1
    assert result.findings[0].assessment == "contradicted"
    assert SOURCE_LIMIT in result.findings[0].limitations


def test_missing_evidence_is_inconclusive_without_model(claims, monkeypatch):
    monkeypatch.setenv("NOBLUFF_MODEL_TIMEOUT", "invalid")
    result = assess_claims(claims, [])
    assert result.basis == "no_evidence"
    assert result.model is None
    assert result.attempts == 0
    assert result.findings[0].assessment == "inconclusive"


@pytest.mark.parametrize(
    "findings",
    [
        [],
        [finding(claim_id="invented")],
        [finding(), finding()],
        [finding(evidence_ids=["invented"])],
        [finding(evidence_ids=[])],
        [finding(assessment="inconclusive", evidence_ids=[], limitations=[])],
        [finding(assessment="definitely_true")],
        [finding(confidence=99)],
    ],
)
def test_invalid_findings_never_become_success(claims, evidence, findings):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(200, json=envelope(findings))

    with pytest.raises(AssessmentError) as exc:
        run(claims, evidence, handler)
    assert exc.value.code == "invalid_output"
    assert len(calls) == 2


def test_retry_recovers_without_fabricated_fallback(claims, evidence):
    calls = []

    def handler(request):
        calls.append(json.loads(request.content))
        return httpx.Response(
            200, json=envelope([] if len(calls) == 1 else [finding()])
        )

    assert run(claims, evidence, handler).attempts == 2
    assert "Previous output was invalid" in calls[1]["messages"][0]["content"]


def test_findings_reordered_to_match_claims(claims, evidence):
    claims.append(Claim(id="c2", text="UTF-8 is selected.", kind="behavior"))
    result = run(
        claims,
        evidence,
        lambda request: httpx.Response(
            200,
            json=envelope(
                [
                    finding(claim_id="c2", assessment="supported"),
                    finding(),
                ]
            ),
        ),
    )
    assert [f.claim_id for f in result.findings] == ["c1", "c2"]


def test_unrelated_evidence_can_remain_inconclusive(claims, evidence):
    result = run(
        claims,
        evidence,
        lambda request: httpx.Response(
            200,
            json=envelope(
                [
                    finding(
                        assessment="inconclusive",
                        evidence_ids=[],
                        explanation="Relevant code is missing.",
                        limitations=[
                            "The supplied snippet does not answer this claim."
                        ],
                        suggested_next_step="Retrieve the exporter implementation.",
                    ),
                ]
            ),
        ),
    )
    assert result.findings[0].assessment == "inconclusive"


@pytest.mark.parametrize(
    "error,code", [(httpx.ConnectError, "unavailable"), (httpx.ReadTimeout, "timeout")]
)
def test_transport_errors_are_not_verdicts(claims, evidence, error, code):
    def handler(request):
        raise error("private details", request=request)

    with pytest.raises(AssessmentError) as exc:
        run(claims, evidence, handler)
    assert exc.value.code == code
    assert "private details" not in str(exc.value)


@pytest.mark.parametrize(
    "changes", [{"model": "other"}, {"done": False}, {"done_reason": "length"}]
)
def test_incomplete_or_wrong_model_rejected(claims, evidence, changes):
    with pytest.raises(AssessmentError):
        run(
            claims,
            evidence,
            lambda request: httpx.Response(200, json=envelope([finding()], **changes)),
        )


def test_mixed_revisions_rejected(claims, evidence):
    evidence.append(evidence[0].model_copy(update={"id": "e2", "revision": "other"}))
    with pytest.raises(AssessmentError, match="one pinned revision"):
        assess_claims(claims, evidence)


def test_execution_evidence_requires_future_runner_integration(claims):
    run_evidence = Evidence(
        id="e", kind="execution", revision="r", excerpt="pass", execution_id="run"
    )
    with pytest.raises(AssessmentError) as exc:
        assess_claims(claims, [run_evidence])
    assert exc.value.code == "unsupported_evidence"


@pytest.mark.parametrize("target", ["claims", "evidence"])
def test_duplicate_input_ids_rejected(claims, evidence, target):
    (claims if target == "claims" else evidence).append(
        (claims if target == "claims" else evidence)[0]
    )
    with pytest.raises(AssessmentError):
        assess_claims(claims, evidence)


def test_input_bounds(claims, evidence):
    with pytest.raises(AssessmentError):
        assess_claims([], evidence)
    evidence[0].excerpt = "x" * 12001
    with pytest.raises(AssessmentError) as exc:
        assess_claims(claims, evidence)
    assert exc.value.code == "input_too_large"


@pytest.mark.skipif(
    os.getenv("NOBLUFF_LIVE_MODEL") != "1", reason="Opt-in actual Qwen assessment"
)
def test_live_supported_contradicted_and_inconclusive():
    from pathlib import Path

    data = json.loads(
        (
            Path(__file__).resolve().parents[2]
            / "examples/evidence-assessment/input.json"
        ).read_text()
    )
    result = assess_claims(
        [Claim.model_validate(x) for x in data["claims"]],
        [Evidence.model_validate(x) for x in data["evidence"]],
    )
    assert {f.claim_id: f.assessment for f in result.findings} == {
        "claim-ascii": "contradicted",
        "claim-utf8": "supported",
        "claim-runtime": "inconclusive",
    }


@pytest.mark.parametrize(('text','kind'), [('export_csv raises UnicodeEncodeError.', 'behavior'),
    ('The tool intermittently crashes.', 'behavior'), ('The database causes the issue.', 'cause'),
    ('The proposed change fixes the issue.', 'fix')])
def test_source_model_cannot_conclusively_verdict_runtime_or_fix_claims(evidence, text, kind):
    claims = [Claim(id='c1', text=text, kind=kind)]
    result = run(claims, evidence, lambda request: httpx.Response(200, json=envelope([finding()])))
    assert result.findings[0].assessment == 'inconclusive'
    assert 'runtime' in result.findings[0].explanation
    assert SOURCE_LIMIT in result.findings[0].limitations
