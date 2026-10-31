# Shared contracts version 1

Import from `nobluff.schemas`. These models are the shared format for Gurmehar's
pipeline, Yogye's evidence, Yashaswi's executions and Devishi's interface.

## Usage

```python
from nobluff.schemas import AnalysisReport

report = AnalysisReport.model_validate_json(payload)
json_payload = report.model_dump_json(indent=2)
schema = AnalysisReport.model_json_schema()
```

Use `model_dump(mode="json")` for JSON-compatible dictionaries. Revalidate the
whole report at API/export boundaries, especially after mutating nested lists.

## Fields

- AnalysisRequest: repository, revision, report_text, optional comparison_revision.
- Claim: id, text, kind, search_terms, reported_as (assertion or hypothesis).
- Evidence: id, kind, revision, path, start_line, end_line, excerpt, execution_id.
- Finding: claim_id, assessment, evidence_ids, explanation, limitations,
  suggested_next_step.
- ExecutionResult: id, revision, test_hash, command, environment, status,
  exit_code, stdout, stderr, duration_ms.
- AnalysisReport: schema_version, is_example, id, repository, revision,
  comparison_revision, model, stage, claims, evidence, findings, executions, errors.

Source coordinates are one-based and inclusive. Paths use repository-relative
POSIX notation. File evidence kinds are source, documentation and test;
execution evidence instead references an ExecutionResult. Identifiers are unique
within their collection. Revisions on evidence and executions must match either
the report's original or comparison revision. Loading code must resolve real
revisions to immutable commits; the schema itself cannot perform that lookup.

Claim kinds: behavior, cause, documentation, fix, other. An assertion describes
what the reporter states, not verified truth. An explicit suspected explanation
is a hypothesis. Missing reproduction details do not turn an observation into a
hypothesis.

Assessments: supported, contradicted, inconclusive. Conclusive findings require
evidence references; inconclusive findings require limitations. One finding per
claim; every claim requires a finding when stage is complete. Empty in-progress
collections are allowed. No numeric confidence score is defined.

Stages: queued, loading, extracting, awaiting_evidence, retrieving, assessing, awaiting_verification,
verifying, complete, error. They are serialized states, not an enforced state
machine; orchestration owns transitions and completeness of actual work.

The extraction API stops at awaiting_evidence. It has not loaded the repository,
resolved revision labels, assessed claims or run reproductions. See api.md.

Execution statuses: not_run, passed, failed, setup_error, timeout, blocked.
Passed requires exit code zero; failed requires a nonzero code. Neither means a
technical claim is automatically true or false. Commands are argument arrays,
not shell strings. Environment is a string-to-string map (for example image and
Python version). test_hash is lowercase SHA-256 of exact test bytes. Record the
same hash for before/after runs; the runner must actually verify this invariant.

## Boundaries

These contracts check structure and references, not factual correctness. Yogye
must check source existence, file bounds and excerpts against the pinned snapshot.
Gurmehar must corroborate assessments; an existing evidence ID is not proof of a
claim. Yashaswi controls approval, command policy, resource limits, actual test
identity and expected failure matching. The API must reject unsafe repository
inputs; the transport-neutral request also serves a local CLI and does not
enforce URL policy. Do not send secrets in logs or environment metadata.

## Integration order

1. Merge these contracts after CI and review.
2. Yogye emits Evidence; Yashaswi emits ExecutionResult.
3. Gurmehar composes and revalidates AnalysisReport.
4. Devishi renders the report and clearly labels is_example reports.

`examples/contracts/report.json` is labelled synthetic data. Live Qwen output and
actual reproduction evidence must be added separately when implemented.

## Local checks

```sh
python -m pip install -e './backend[dev]'
python -m ruff check backend
python -m pytest backend/tests -m 'not runner' -q
```
