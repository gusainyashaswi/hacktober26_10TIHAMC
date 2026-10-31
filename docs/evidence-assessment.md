# Source evidence assessment

```python
from nobluff.model import assess_claims

result = assess_claims(claims, evidence)
findings = result.findings
```

Inputs are shared Claim and Evidence objects. Yogye must verify paths, line
ranges, excerpts and revision against the actual pinned snapshot before calling
this function. Evidence objects alone do not establish source authenticity.

This phase accepts 1-20 claims and 0-20 source/documentation/test snippets from
one revision, up to 12000 characters of serialized input. Oversized input is
rejected, not silently truncated. Mixed revisions and execution evidence are
rejected; future before/after and runner integration must handle them explicitly.

With no evidence, every claim is inconclusive, attempts is 0, model is null and
basis is no_evidence. No model is called. With evidence, Qwen3-8B via local Ollama
returns schema-constrained findings. The application enforces one finding per
claim, only supplied evidence IDs, evidence for conclusive findings and limitations
for inconclusive findings. It returns findings in input claim order and adds a
static-review limitation to each. No test is executed by this module.

Malformed/incomplete output or invalid citations get one corrective retry.
Persistent invalid output raises AssessmentError rather than fabricating a
successful response. Transport errors use sanitized codes and are not retried.
Ollama settings, response-size cap and inactivity timeouts reuse the extractor's
HTTP helper. See model-integration.md for exact timeout semantics and configuration.

Structural validation cannot establish semantic correctness. An existing
evidence ID might still be irrelevant. The prompt requests direct relevance and
conservative uncertainty; independent review/evaluation remains necessary. Prompts
treat source text and reports as untrusted data, but this is not a guarantee of
prompt-injection resistance. No tools or execution permissions are provided.

The current API still stops at awaiting_evidence. This PR implements the assessor
and tests only. After retrieval merges, Gurmehar must call it using verified
Evidence, set report.findings, and revalidate the full AnalysisReport before
returning a complete source-review report. Do not claim runner integration.

Tests use mocked HTTP except the opt-in live check:

```sh
python -m pytest backend/tests/test_assessment.py -q
NOBLUFF_LIVE_MODEL=1 python -m pytest backend/tests/test_assessment.py -k live -q
```
