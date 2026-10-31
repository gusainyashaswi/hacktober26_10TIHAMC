"""Deterministic HTTP tests; these do not measure a real model's accuracy."""

import json
import os

import httpx
import pytest
from nobluff.model import ExtractionError, OllamaSettings, extract_claims

DRAFT = {
    "claims": [
        {
            "text": "The exporter crashes on emoji names.",
            "kind": "behavior",
            "search_terms": ["exporter", "emoji"],
            "reported_as": "assertion",
        }
    ]
}


def envelope(content=None, **changes):
    return {
        "model": "qwen3:8b",
        "done": True,
        "done_reason": "stop",
        "message": {"content": json.dumps(DRAFT) if content is None else content},
    } | changes


def run(handler, text="The exporter crashes on emoji names."):
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        return extract_claims(text, OllamaSettings(), client=client)


def test_schema_and_prompt_sent_and_result_validated():
    def handler(request):
        assert str(request.url) == "http://127.0.0.1:11434/api/chat"
        body = json.loads(request.content)
        assert body["format"]["additionalProperties"] is False
        assert body["stream"] is False
        assert body["think"] is False
        assert body["model"] == "qwen3:8b"
        assert (
            json.loads(body["messages"][1]["content"])["report_text"]
            == "The exporter crashes on emoji names."
        )
        return httpx.Response(200, json=envelope())

    result = run(handler)
    assert result.claims[0].id == "claim-1"
    assert result.claims[0].reported_as == "assertion"
    assert result.attempts == 1
    assert result.warnings


def test_invalid_output_retried_once_then_recovers():
    requests = []

    def handler(request):
        requests.append(json.loads(request.content))
        return httpx.Response(
            200, json=envelope("broken") if len(requests) == 1 else envelope()
        )

    result = run(handler)
    assert result.attempts == 2
    assert "Previous output was invalid" in requests[1]["messages"][0]["content"]


@pytest.mark.parametrize(
    "response",
    [
        envelope("not-json"),
        envelope("{}"),
        envelope(done=False),
        envelope(done_reason="length"),
        envelope(model="different-model"),
        envelope(json.dumps({"claims": [DRAFT["claims"][0], DRAFT["claims"][0]]})),
        envelope(
            json.dumps({"claims": [DRAFT["claims"][0] | {"assessment": "supported"}]})
        ),
    ],
)
def test_invalid_output_never_becomes_success(response):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(200, json=response)

    with pytest.raises(ExtractionError) as exc:
        run(handler)
    assert exc.value.code == "invalid_output"
    assert len(calls) == 2


@pytest.mark.parametrize(
    "status,code",
    [(404, "model_not_found"), (503, "server_error"), (302, "server_error")],
)
def test_server_failures_are_actionable(status, code):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(
            status,
            text="sensitive server body",
            headers={"Location": "https://example.com"},
        )

    with pytest.raises(ExtractionError) as exc:
        run(handler)
    assert exc.value.code == code
    assert "sensitive" not in str(exc.value)
    assert len(calls) == 1


@pytest.mark.parametrize(
    "error,code", [(httpx.ConnectError, "unavailable"), (httpx.ReadTimeout, "timeout")]
)
def test_network_errors_are_not_retried(error, code):
    def handler(request):
        raise error("internal diagnostic", request=request)

    with pytest.raises(ExtractionError) as exc:
        run(handler)
    assert exc.value.code == code
    assert "internal diagnostic" not in str(exc.value)


@pytest.mark.parametrize("text", ["", "   ", "a" * 12001])
def test_invalid_input_never_calls_server(text):
    def handler(request):
        pytest.fail("Invalid input must not reach Ollama")

    with pytest.raises(ExtractionError):
        run(handler, text)


def test_empty_claim_list_is_valid():
    result = run(lambda request: httpx.Response(200, json=envelope('{"claims": []}')))
    assert result.claims == []


def test_invented_search_terms_are_dropped():
    draft = {
        "claims": [
            DRAFT["claims"][0] | {"search_terms": ["emoji", "invented.py", "EMOJI"]}
        ]
    }
    result = run(lambda request: httpx.Response(200, json=envelope(json.dumps(draft))))
    assert result.claims[0].search_terms == ["emoji"]


def test_large_response_is_rejected():
    with pytest.raises(ExtractionError) as exc:
        run(lambda request: httpx.Response(200, content=b"x" * 128001))
    assert exc.value.code == "response_too_large"


def test_invalid_envelope_is_rejected():
    with pytest.raises(ExtractionError) as exc:
        run(lambda request: httpx.Response(200, text="not json"))
    assert exc.value.code == "invalid_response"


def test_environment_configuration(monkeypatch):
    monkeypatch.setenv("NOBLUFF_OLLAMA_URL", "http://localhost:11434/")
    monkeypatch.setenv("NOBLUFF_MODEL_TIMEOUT", "30")
    settings = OllamaSettings.from_env()
    assert settings.base_url == "http://localhost:11434"
    assert settings.timeout_seconds == 30


def test_bad_configuration_is_safe(monkeypatch):
    monkeypatch.setenv("NOBLUFF_OLLAMA_URL", "http://user:secret@localhost:11434")
    with pytest.raises(ExtractionError) as exc:
        extract_claims("The exporter crashes.")
    assert exc.value.code == "invalid_configuration"
    assert "secret" not in str(exc.value)


@pytest.mark.skipif(
    os.getenv("NOBLUFF_LIVE_MODEL") != "1", reason="Opt-in real local Ollama test"
)
def test_live_qwen_claim_extraction():
    result = extract_claims(
        "The CSV exporter crashes on emoji names. I think export_csv uses ASCII encoding."
    )
    assert len(result.claims) == 2
    assert {c.reported_as for c in result.claims} == {"assertion", "hypothesis"}
    assert any(
        "ascii" in c.text.lower() and c.reported_as == "hypothesis"
        for c in result.claims
    )
