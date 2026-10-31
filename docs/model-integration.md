# Local Qwen claim extraction

This module extracts **unverified** claims. It does not retrieve evidence, decide
truth, generate verdicts, or run code. Import `extract_claims` from `nobluff.model`.
It returns ClaimExtractionResult with validated shared Claim objects, model name,
UTC time, elapsed milliseconds, attempts and an explicit warning.

## Run

```sh
python -m pip install -e './backend[dev]'
ollama pull qwen3:8b
python -m nobluff.model --report examples/claim-extraction/input.txt
```

Ollama must already be running. No closed-model API key is used. To save JSON,
add `--output /tmp/nobluff-claims.json`. This command is intentionally standalone;
the full analysis API/CLI will connect it to retrieval later.

Operator environment configuration (never accept arbitrary endpoints from a web
request): NOBLUFF_OLLAMA_URL defaults to http://127.0.0.1:11434; NOBLUFF_MODEL to
qwen3:8b; NOBLUFF_MODEL_TIMEOUT to 120 seconds (maximum 300). URL must be an HTTP(S)
origin without credentials, path, query or fragment. No redirects or environment
proxy settings are used by the owned client. Explicitly configuring another
server sends report text to that server; there is no automatic cloud fallback.

## Bounds and failures

Reports are limited to 12000 characters, with at most 20 claims. Requests use
8192 context tokens, 2048 generated tokens, temperature zero, thinking disabled
and JSON schema output. These limits are configuration choices, not model quality
guarantees. HTTPX uses a five-second connection timeout and the configured read,
write and pool timeout; these are inactivity/operation limits, not a total wall
clock deadline. Responses are capped at 128000 decoded bytes.

Invalid structured output is retried once with a corrective instruction. Network
and server failures are not retried. Truncated output, unexpected model identity,
invented extra fields and duplicate claim text are rejected. Failures raise
ExtractionError with a stable code; the command writes a short error to stderr
and exits 2. No fake claims or empty-success fallback is returned on failure.

IDs are assigned by the application as claim-1, claim-2 etc.
Search terms are deduplicated, limited to five per claim, and retained only when
they appear in the supplied report (case-insensitive). This prevents invented
search identifiers from passing directly into retrieval.

Assertions describe
what the reporter states, even when unverified or intermittent. Hypotheses are
explicitly suspected explanations. The prompt treats report instructions as
untrusted data; this is mitigation, not proof of prompt-injection immunity. The
module has no execution tools. Semantic correctness still requires evaluation.

## Test

```sh
python -m pytest backend/tests/test_extraction.py -q
NOBLUFF_LIVE_MODEL=1 python -m pytest backend/tests/test_extraction.py -k live_qwen -q
```

Most tests use HTTPX MockTransport and require no model. The opt-in test makes an
actual Ollama call and checks assertion/hypothesis separation on one short input.
Its success does not establish accuracy on arbitrary issue reports.

References: https://docs.ollama.com/api/chat and
https://docs.ollama.com/capabilities/structured-outputs
