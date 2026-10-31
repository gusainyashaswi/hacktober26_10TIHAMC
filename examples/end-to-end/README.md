# Actual Qwen and Docker end-to-end runs

These are **controlled synthetic inputs with actual outputs**, not public historical issues or an accuracy benchmark. Qwen3-8B ran through Ollama HTTP; the approved regression test ran in real Docker. API calls used FastAPI TestClient. Model/commit identity and generation time are in `metadata.json`.

| Case | Input | Source result | Controlled execution |
| --- | --- | --- | --- |
| Unicode | `unicode-input.json` | Runtime claim remains inconclusive before execution | Original raises UnicodeEncodeError; identical test passes on fix |
| Contradicted | `contradicted-input.json` | Source uses ASCII, contradicting UTF-8 selection | None; no runtime claim is made |
| Inconclusive | `inconclusive-input.json` | Remote-database hypothesis is not established | None; absence of evidence is not disproof |

`*-source-output.json` records the source phase. `*-output.json` and Markdown record final reports. `approved-test.json` is the reviewed test, including a UTF-8 content assertion so a no-op function cannot pass. `observed-rejection.json` preserves an earlier actual rejected model response as a development failure case; it is not a successful investigation or accepted verdict. Requiring citation fields in model output and conservatively gating runtime/cause/fix claims were added after live validation exposed model errors. The gate is heuristic and does not guarantee semantic correctness.

Prepare the fixture without invoking a model:

```bash
python examples/end-to-end/generate.py --prepare-only --fixture-directory /tmp/nobluff-demo-fixture
```

This creates a tiny local Git repository with two reproducible commits. Its source is never executed on the host. Fixed fixture author dates make commit IDs repeatable; they are demo history, not project development history. Keep expected results in this README, outside the model-visible fixture.

To regenerate actual outputs, install `./backend[dev]`, start Ollama with `qwen3:8b`, start Docker, and build/set the runner image:

```bash
docker build -t nobluff-runner:ci runner
export NOBLUFF_RUNNER_IMAGE=nobluff-runner:ci
python examples/end-to-end/generate.py --fixture-directory /tmp/nobluff-demo-fixture
```

The script writes new actual outputs; it does not replace failed runs with invented successes. You can select one case with `--case unicode`. Model interpretations can vary. Broad public-issue evaluation and independent teammate review are separate work; do not present these three tiny cases as an accuracy percentage.
