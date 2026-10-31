# Local extraction API

Start from repository root with the backend installed and Ollama running:

```sh
python -m pip install -e './backend[dev]'
python -m uvicorn nobluff.api:create_app --factory --host 127.0.0.1 --port 8000
```

Use one worker. Reports are process-local, disappear on restart, and are bounded
to 100 per process. One inference runs at a time. Busy/full requests receive 429
with Retry-After. This local development API has no authentication; do not expose
it publicly. The API never downloads or executes repository code in this version.

## Frontend handoff

Base URL: http://127.0.0.1:8000. Interactive docs: /docs; schema: /openapi.json.
CORS allows exactly http://localhost:5173 and http://127.0.0.1:5173. No credentials.

1. POST /api/analyses with JSON below. A 202 response contains `{ "id": "..." }`.
   Location identifies the polling URL. X-NoBluff-Scope is claim_extraction_only.
2. Poll GET /api/analyses/{id}. It returns the shared AnalysisReport format.
3. queued/extracting mean work is pending. **awaiting_evidence** means extraction
   finished, not that the issue was verified. Stop polling at awaiting_evidence
   or error for this version. Render claims and their assertion/hypothesis labels.
4. error includes sanitized errors; do not display a success report. Unknown IDs
   return 404. Validation failures return 422; oversized request bodies return 413.

```json
{
  "repository": "owner/repository",
  "revision": "main",
  "report_text": "The CSV exporter crashes on emoji. I think it uses ASCII.",
  "comparison_revision": null
}
```

Repository also accepts an HTTPS github.com repository URL with optional .git.
Local paths, arbitrary hosts, credentials, query parameters and issue URLs are
rejected. Repository availability/public visibility is **not checked** until
ingestion is integrated. revision and comparison_revision are requested labels,
**not resolved commits** in this extraction-only response. No source evidence,
findings or executions are generated. Do not label these reports verified.

Report text is capped at 12000 characters; body bytes at 64000. Extra request
fields, including model/server overrides, are rejected. Model settings come only
from the server operator's environment as documented in model-integration.md.

GET /api/health checks this API, not Ollama readiness. It reports capability
flags so the UI can explain the current scope. POST /api/analyses/{id}/verification
returns 501 for known IDs, explicitly saying no code was executed. Verification
and exports are not silently simulated. They remain integration work.

## Service integration

AnalysisService owns report state and extraction. Its public get method returns
a deep copy. BackgroundTasks executes the synchronous extractor off the event
loop. It is not a durable job queue; do not deploy it with multiple workers.
When Yogye's retrieval lands, resolve requested revisions into immutable commits
before adding any source evidence, then connect retrieval and assessment. When
Yashaswi's runner lands, replace the explicit 501 verification handler with the
approved execution contract. No placeholder verdicts are currently inserted.

CI tests inject a fake extractor to verify routing, errors, states and boundaries.
The recorded API example separately exercises HTTP against actual local Qwen.
