# Actual HTTP extraction example

The issue text in input.json is illustrative and is not a claim about this
repository. actual-response.json records an actual local HTTP API call using
Qwen3-8B via Ollama. The request associates a repository label for future
ingestion; this run did not load or inspect that repository or resolve its
revision. Its stage is awaiting_evidence, not complete or verified.

Start the API as described in docs/api.md, then:

```sh
curl -H 'Content-Type: application/json' --data-binary @examples/api-extraction/input.json http://127.0.0.1:8000/api/analyses
curl http://127.0.0.1:8000/api/analyses/ID_FROM_FIRST_RESPONSE
```

Poll until awaiting_evidence or error. Timings/IDs and model wording can differ.
run-metadata.json records the actual endpoint, model digest and capture time.
