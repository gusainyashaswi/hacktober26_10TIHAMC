# Actual model assessment of synthetic evidence

input.json contains synthetic claims and source, not a fetched public repository.
The fixture revision label is not a Git commit. actual-output.json is an actual
local Qwen response to this fixture, with NoBluff's validation and static-review
limitations applied. It demonstrates source interpretation, not retrieval or
reproduction. It must not be presented as a real issue investigation.

```sh
python -m pip install -e './backend[dev]'
python examples/evidence-assessment/run.py
```

Expected reference outcomes (not passed to the model): ASCII selection is
contradicted; UTF-8 selection is supported; the reporter's runtime observation
is inconclusive without their input, environment or execution evidence. This is
one small semantic check, not a general accuracy measurement.
