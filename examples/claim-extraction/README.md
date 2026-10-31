# Actual local claim extraction

`input.txt` is an illustrative issue report. `actual-output.json` is the actual
output of NoBluff's extraction command against local Qwen3-8B via Ollama. It is
not a verified bug report: no source was retrieved and no reproduction was run.
It demonstrates model integration and extraction only. Inspect `run-metadata.json`
for the local model digest and generation settings used for this recorded run.

```sh
python -m nobluff.model --report examples/claim-extraction/input.txt --output /tmp/nobluff-claims.json
```

Outputs can vary by runtime/model. Do not present this recorded run as live.
