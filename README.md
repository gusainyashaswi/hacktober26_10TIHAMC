# No Bluff

Checks the technical claims in issues and pull requests against source code and documentation.

## Install
Requires Python 3.11 or newer and a running local Ollama installation.

```sh
python -m pip install -e './backend[dev]'
ollama pull qwen3:8b
```

## Run
The first implemented workflow extracts unverified claims from issue text:

```sh
python -m nobluff.model --report examples/claim-extraction/input.txt
```

For a local HTTP API with submission and progress polling:

```sh
python -m uvicorn nobluff.api:create_app --factory --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000/docs for interactive API documentation. See
[API integration](docs/api.md) for Devishi's frontend connection.

This is claim extraction only. Repository investigation, evidence assessment,
verification and connecting the web interface are separate integration work.
See [model integration](docs/model-integration.md) and [shared contracts](docs/contracts.md).

A standalone [source evidence assessor](docs/evidence-assessment.md) now compares
claims against supplied, verified file evidence. It is not yet connected to the
API or repository loader. A real model run on labelled synthetic evidence is in
`examples/evidence-assessment/`.

## Examples
See the examples folder.
