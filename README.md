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

This is claim extraction only. Repository investigation, evidence assessment,
verification and the web interface are separate integration work.
See [model integration](docs/model-integration.md) and [shared contracts](docs/contracts.md).

## Examples
See the examples folder.
